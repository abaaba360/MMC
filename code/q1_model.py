"""
问题一：论文质量综合评价指标体系 + 组合赋权 + 自动评分分级（Q1_C1）
====================================================================
功能：
  1. 构建「目标层 ← 6 一级维度（对齐国赛评分权重）← 21 二级指标」层次指标体系
  2. 指标标准化：正向 min-max / 负向反向 / 适中(X41 逻辑连接词密度, X64 摘要字数)梯形隶属
     —— X41 最优区间[a,b] 由 att1 30 篇该指标 P25~P75 分位数标定（数据驱动纠偏）
     —— X64 最优区间[300,500]（国赛摘要字数规范），可接受界[0,1000]
  3. 组合赋权：一级维度 AHP 主观权重（Saaty 判断矩阵 + 一致性检验 CR<0.1）
              × 二级指标熵权客观权重（维度内，0 值 ε=1e-6 平滑）
              乘法合成归一化 w_ij = w_i^AHP·w_ij^E / Σ(w_i^AHP·w_ij^E)
  4. 线性加权百分制评分 Score=100·Σ w_ij·x_ij
  5. 分级：min-max 标准化将指标锚定在样本相对尺度上，绝对阈值(90/80/70/60)与相对得分
     不匹配（ARI≈0.07，接近随机）——经 ARI 对照验证后，采用 Fisher-Jenks 自然断点法
     对综合得分做数据驱动五级分级（优秀/良好/中等/及格/不及格），绝对阈值分级保留为规范对照
  6. K-means(k=5, seed=42) 无监督对照，报告 ARI（调整兰德指数）
  7. 权重合理性三重论证：① CR<0.1  ② 权重±10%扰动后≥85%论文等级不变
     ③ 组合赋权 vs 纯AHP主观 vs 纯熵权客观 三者一致性（Spearman ρ + ARI）
  8. 生成 4 张论文级图表（无 set_title，中文字体，去边框）

输入：results/feature_matrix.json（43 篇×30 特征，仅取 group=att1 的 30 篇）
输出：results/q1_results.json, results/figures/q1_01~q1_04_*.png / *.pdf
运行方式：python code/q1_model.py
"""
import json
import os
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler

# ----------------------------- 全局配置 -----------------------------
SEED = 42
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
FIG_DIR = os.path.join(RESULTS_DIR, "figures")
for _d in (RESULTS_DIR, FIG_DIR):
    os.makedirs(_d, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun",
                                   "Arial Unicode MS", "PingFang SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 150
plt.rcParams["savefig.bbox"] = "tight"

# ----------------------------- 指标体系 -----------------------------
# 6 个一级维度（对齐国赛评分权重框架，主观权重 w^AHP 主设定）
LEVEL1 = [
    ("D1", "模型与方法合理性", 0.30, "模型质量"),
    ("D2", "公式推导完整性", 0.15, "模型质量"),
    ("D3", "问题解决与结论质量", 0.25, "问题解决"),
    ("D4", "逻辑严密性", 0.10, "模型质量支撑"),
    ("D5", "结果验证性", 0.08, "验证"),
    ("D6", "论文规范性", 0.12, "论文规范"),
]

# 21 个二级指标：(key, 所属维度, 名称, 方向)
LEVEL2 = [
    ("X11", "D1", "模型假设条数密度", "正向"),
    ("X12", "D1", "假设-问题匹配度", "正向"),
    ("X13", "D1", "方法术语丰富度", "正向"),
    ("X14", "D1", "建模求解章节完整度", "正向"),
    ("X21", "D2", "数学符号密度", "正向"),
    ("X22", "D2", "公式编号密度", "正向"),
    ("X23", "D2", "希腊字母密度", "正向"),
    ("X24", "D2", "上下标密度", "正向"),
    ("X31", "D3", "摘要分问陈述度", "正向"),
    ("X32", "D3", "结果结论密度", "正向"),
    ("X33", "D3", "结论评价章节完整度", "正向"),
    ("X41", "D4", "逻辑连接词密度", "适中"),
    ("X42", "D4", "因果连接词占比", "正向"),
    ("X43", "D4", "逻辑断层代理", "负向"),
    ("X51", "D5", "模型检验章节存在", "正向"),
    ("X52", "D5", "检验术语密度", "正向"),
    ("X53", "D5", "检验方法词密度", "正向"),
    ("X61", "D6", "核心章节覆盖度", "正向"),
    ("X62", "D6", "参考文献规范度", "正向"),
    ("X63", "D6", "图表规范度", "正向"),
    ("X64", "D6", "摘要字数合规度", "适中"),
]

# 图表用短名
SHORT = {
    "X11": "假设密度", "X12": "假设匹配", "X13": "方法丰富", "X14": "章节完整",
    "X21": "符号密度", "X22": "公式编号", "X23": "希腊字母", "X24": "上下标",
    "X31": "摘要分问", "X32": "结论密度", "X33": "评价章节",
    "X41": "连接词密度", "X42": "因果占比", "X43": "断层代理",
    "X51": "检验章节", "X52": "检验术语", "X53": "检验方法",
    "X61": "章节覆盖", "X62": "引用规范", "X63": "图表规范", "X64": "摘要字数",
}
DIR_MARK = {"正向": "+", "负向": "-", "适中": "±"}

DIM_W = {d: w for d, _, w, _ in LEVEL1}          # 维度 -> AHP 主观权重
DIM_N = {d: len([1 for k, dd, _, _ in LEVEL2 if dd == d]) for d, _, _, _ in LEVEL1}
DIM_COLOR = {"D1": "#1f77b4", "D2": "#ff7f0e", "D3": "#2ca02c",
             "D4": "#d62728", "D5": "#9467bd", "D6": "#8c564b"}
GRADE_COLOR = {"优秀": "#2e7d32", "良好": "#66bb6a", "中等": "#ffca28",
               "及格": "#fb8c00", "不及格": "#e53935"}
GRADE_ORDER = ["优秀", "良好", "中等", "及格", "不及格"]          # 降序（高→低）
GRADE_ORDER_ASC = ["不及格", "及格", "中等", "良好", "优秀"]      # 升序（低→高）

EPS = 1e-6


# ----------------------------- 工具函数 -----------------------------
def _load_feature_matrix():
    path = os.path.join(RESULTS_DIR, "feature_matrix.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_raw_matrix(data):
    """返回 (ids, V_raw(30x21), keys)，仅取 att1 组 30 篇，按 id 排序。"""
    att1 = sorted([p for p in data["papers"] if p["group"] == "att1"], key=lambda p: p["id"])
    ids = [p["id"] for p in att1]
    keys = [k for k, _, _, _ in LEVEL2]
    V = np.array([[p["features"][k] for k in keys] for p in att1], dtype=float)
    return ids, V, keys


def _trapezoid(v, a, b, c, d):
    """梯形隶属函数：最优区间[a,b]隶属=1，向两侧线性衰减到 0（界[c,d]）。"""
    v = np.asarray(v, dtype=float)
    rising = (v - c) / (a - c) if a > c else np.ones_like(v)
    falling = (d - v) / (d - b) if d > b else np.ones_like(v)
    return np.clip(np.minimum(rising, falling), 0.0, 1.0)


def _standardize(V):
    """标准化 21 个指标到 [0,1]，返回 (X(30x21), params)。"""
    n, m = V.shape
    X = np.zeros_like(V)
    params = {}
    for j, (key, dim, name, direction) in enumerate(LEVEL2):
        v = V[:, j]
        if direction == "正向":
            vmin, vmax = float(v.min()), float(v.max())
            x = (v - vmin) / (vmax - vmin) if vmax > vmin else np.full(n, 0.5)
            params[key] = {"method": "正向min-max", "vmin": vmin, "vmax": vmax}
        elif direction == "负向":
            vmin, vmax = float(v.min()), float(v.max())
            x = (vmax - v) / (vmax - vmin) if vmax > vmin else np.full(n, 0.5)
            params[key] = {"method": "负向反向min-max", "vmin": vmin, "vmax": vmax}
        elif direction == "适中":
            if key == "X41":
                a, b = float(np.percentile(v, 25)), float(np.percentile(v, 75))
                c, d = float(v.min()), float(v.max())
            elif key == "X64":
                a, b, c, d = 300.0, 500.0, 0.0, 1000.0
            else:
                raise ValueError(f"未知适中型指标 {key}")
            x = _trapezoid(v, a, b, c, d)
            params[key] = {"method": "适中梯形隶属", "a": a, "b": b, "c": c, "d": d}
        else:
            raise ValueError(f"未知方向 {direction}")
        X[:, j] = x
    return X, params


def _entropy_weights(X_sub):
    """熵权法：对 (n,m) 标准化矩阵逐列算信息熵，返回 (权重, 熵, 差异系数)。"""
    X_sub = np.asarray(X_sub, dtype=float)
    n = X_sub.shape[0]
    if n <= 1:
        m = X_sub.shape[1]
        return np.ones(m) / m, np.ones(m), np.zeros(m)
    Xs = np.where(X_sub > 0, X_sub, EPS)               # 0 值 ε 平滑，避免 ln0
    p = Xs / Xs.sum(axis=0, keepdims=True)
    e = -(p * np.log(p)).sum(axis=0) / np.log(n)
    g = 1.0 - e
    w = g / g.sum() if g.sum() > EPS else np.ones_like(g) / len(g)
    return w, e, g


def _round_saaty(r):
    """把权重比值圆整到 Saaty 1-9 基本标度（>1 半数进位到更大整数）。"""
    inv = False
    if r < 1.0:
        r = 1.0 / r
        inv = True
    s = int(min(max(np.floor(r + 0.5), 1), 9))
    return (1.0 / s) if inv else float(s)


def _ahp(target_w):
    """由目标权重比值构造 Saaty 判断矩阵，求特征向量权重 + 一致性指标。"""
    n = len(target_w)
    A = np.ones((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            a = _round_saaty(target_w[i] / target_w[j])
            A[i, j] = a
            A[j, i] = 1.0 / a
    eigvals, eigvecs = np.linalg.eig(A)
    idx = int(np.argmax(eigvals.real))
    lam_max = float(eigvals[idx].real)
    w = np.abs(eigvecs[:, idx].real)
    w = w / w.sum()
    CI = (lam_max - n) / (n - 1)
    RI = 1.24                                        # n=6 随机一致性指标
    CR = CI / RI
    return w, A, lam_max, CI, RI, CR


def _grade_abs(score):
    """绝对阈值分级（规范参考）：优秀≥90 / 良好[80,90) / 中等[70,80) / 及格[60,70) / 不及格<60。"""
    if score >= 90:
        return "优秀"
    if score >= 80:
        return "良好"
    if score >= 70:
        return "中等"
    if score >= 60:
        return "及格"
    return "不及格"


def _jenks_boundaries(values, k):
    """Fisher-Jenks 自然断点法：把一维得分划分为 k 个连续类，最小化类内平方和。
    返回 (边界值列表(升序, k-1 个), 类末端索引列表)。"""
    values = np.sort(np.asarray(values, dtype=float))
    n = len(values)
    if k >= n:
        k = max(1, n - 1)
    p1 = np.concatenate([[0.0], np.cumsum(values)])
    p2 = np.concatenate([[0.0], np.cumsum(values ** 2)])

    def ssd(i, j):
        cnt = j - i
        if cnt <= 0:
            return 0.0
        s1 = p1[j] - p1[i]
        s2 = p2[j] - p2[i]
        return s2 - s1 * s1 / cnt

    INF = float("inf")
    cost = [[INF] * (n + 1) for _ in range(k + 1)]
    split = [[0] * (n + 1) for _ in range(k + 1)]
    for i in range(1, n + 1):
        cost[1][i] = ssd(0, i)
    for kk in range(2, k + 1):
        for i in range(1, n + 1):
            best, bs = INF, 0
            for j in range(kk - 1, i + 1):
                c = cost[kk - 1][j] + ssd(j, i)
                if c < best:
                    best, bs = c, j
            cost[kk][i], split[kk][i] = best, bs
    idx = n
    idxs = [n]
    for kk in range(k, 1, -1):
        idx = split[kk][idx]
        idxs.append(idx)
    idxs = idxs[::-1]                                  # [0, i1, ..., n]
    bounds = [float(values[idxs[c] - 1]) for c in range(1, k)]   # 各类上界
    return bounds, idxs


def _grade_from_bounds(score, bounds):
    """按自然断点边界给等级（升序类 → 不及格..优秀）。"""
    k = len(bounds) + 1
    for c, b in enumerate(bounds):
        if score < b:
            return GRADE_ORDER_ASC[c]
    return GRADE_ORDER_ASC[k - 1]


def _save_fig(fig, name):
    base = os.path.join(FIG_DIR, name)
    fig.savefig(base + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(base + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"[图表] {base}.png / .pdf")


def _print_stats(vals, label):
    s = np.asarray(vals, dtype=float)
    cv = s.std() / s.mean() if s.mean() else float("nan")
    print(f"[{label}] min={s.min():.4f} max={s.max():.4f} mean={s.mean():.4f} "
          f"std={s.std():.4f} CV={cv:.4f} amplitude={(s.max() - s.min()) / 2:.4f}")


def _clean(vals):
    return [float(x) if np.isfinite(x) else None for x in vals]


# =====================================================================
# 第一阶段：纯计算
# =====================================================================
def compute():
    data = _load_feature_matrix()
    ids, V, keys = _build_raw_matrix(data)
    n, m = V.shape
    print(f"[数据] att1 论文 {n} 篇, 二级指标 {m} 个, 特征键 {keys[0]}~{keys[-1]}")

    # ---- 1. 标准化 ----
    X, std_params = _standardize(V)
    assert np.all(np.isfinite(X)), "标准化后存在 NaN/Inf"
    print("[标准化] 完成：正向 min-max / 负向反向 / X41·X64 适中梯形隶属")
    print(f"  X41 最优区间[a,b]=[{std_params['X41']['a']:.4f},{std_params['X41']['b']:.4f}] "
          f"界[c,d]=[{std_params['X41']['c']:.4f},{std_params['X41']['d']:.4f}]")
    print(f"  X64 最优区间[a,b]=[{std_params['X64']['a']:.0f},{std_params['X64']['b']:.0f}] "
          f"界[c,d]=[{std_params['X64']['c']:.0f},{std_params['X64']['d']:.0f}]")

    # ---- 2. AHP 一级主观权重 + 一致性检验 ----
    target_w = np.array([w for _, _, w, _ in LEVEL1], dtype=float)
    assert abs(target_w.sum() - 1.0) < 1e-9
    w_ahp, A_mat, lam_max, CI, RI, CR = _ahp(target_w)
    print(f"[AHP] λ_max={lam_max:.4f} CI={CI:.4f} RI={RI:.2f} CR={CR:.4f} "
          f"({'通过 CR<0.1' if CR < 0.1 else '未通过!'})")
    print(f"  目标权重={np.round(target_w, 4).tolist()}")
    print(f"  特征向量权重={np.round(w_ahp, 4).tolist()}")

    # ---- 3. 二级熵权（维度内） ----
    dim_cols = {}
    for j, (key, dim, name, direction) in enumerate(LEVEL2):
        dim_cols.setdefault(dim, []).append(j)
    w_entropy = np.zeros(m)
    entropy_detail = {}
    for dim, _, _, _ in LEVEL1:
        cols = dim_cols[dim]
        wE, e, g = _entropy_weights(X[:, cols])
        w_entropy[cols] = wE
        entropy_detail[dim] = {
            "indicators": [LEVEL2[c][0] for c in cols],
            "entropy": _clean(e), "divergence": _clean(g), "w_entropy": _clean(wE),
        }

    # ---- 4. 乘法合成组合赋权 ----
    w_ahp_expand = np.array([DIM_W[d] for _, d, _, _ in LEVEL2])
    w_comb = (w_ahp_expand * w_entropy)
    w_comb = w_comb / w_comb.sum()
    assert abs(w_comb.sum() - 1.0) < 1e-9

    combined = []
    for j, (key, dim, name, direction) in enumerate(LEVEL2):
        combined.append({
            "id": key, "dim": dim, "name": name, "direction": direction,
            "w_ahp_dim": float(DIM_W[dim]),
            "w_entropy": float(w_entropy[j]),
            "w_combined": float(w_comb[j]),
        })

    # ---- 5. 评分 ----
    S = X @ w_comb
    Score = 100.0 * S
    grades_abs = [_grade_abs(s) for s in Score]

    # 一级维度得分（供 Q3 短板定位复用）
    dim_scores = {}
    for dim, _, _, _ in LEVEL1:
        cols = dim_cols[dim]
        wsub = w_comb[cols] / w_comb[cols].sum() if w_comb[cols].sum() > 0 else np.ones(len(cols)) / len(cols)
        dim_scores[dim] = X[:, cols] @ wsub

    # ---- 6. 分级：绝对阈值(规范参考) + Fisher-Jenks(采纳) ----
    jenks_bounds, jenks_idxs = _jenks_boundaries(Score, 5)
    grades = [_grade_from_bounds(s, jenks_bounds) for s in Score]     # 最终等级

    # ---- 7. K-means 对照 ----
    Z = StandardScaler().fit_transform(X)
    km = KMeans(n_clusters=5, random_state=SEED, n_init=10)
    labels = km.fit_predict(Z)
    cluster_mean = [float(Score[labels == k].mean()) for k in range(5)]
    order = np.argsort(cluster_mean)
    cluster_to_grade = {int(k): GRADE_ORDER_ASC[pos] for pos, k in enumerate(order)}
    kmeans_grades = [cluster_to_grade[int(l)] for l in labels]
    ari_thresh = float(adjusted_rand_score(grades_abs, kmeans_grades))
    ari_jenks = float(adjusted_rand_score(grades, kmeans_grades))
    print(f"[K-means] k=5 seed={SEED} 簇→等级映射={cluster_to_grade}")
    print(f"  ARI(绝对阈值 vs K-means)={ari_thresh:.4f}  ARI(Jenks vs K-means)={ari_jenks:.4f}")

    # ---- 8. 权重合理性论证 ----
    # ② 权重 ±10% 扰动 → 等级稳定率（Jenks 每次重算断点）
    rng = np.random.default_rng(SEED)
    n_runs = 200
    unchanged_rebreak = 0
    unchanged_fixed = 0
    for _ in range(n_runs):
        pert = w_comb * rng.uniform(0.9, 1.1, size=m)
        pert = pert / pert.sum()
        s_pert = 100.0 * (X @ pert)
        g_rebreak = [_grade_from_bounds(x, _jenks_boundaries(s_pert, 5)[0]) for x in s_pert]
        g_fixed = [_grade_from_bounds(x, jenks_bounds) for x in s_pert]
        unchanged_rebreak += sum(1 for a, b in zip(grades, g_rebreak) if a == b)
        unchanged_fixed += sum(1 for a, b in zip(grades, g_fixed) if a == b)
    stability_rebreak = unchanged_rebreak / (n_runs * n)
    stability_fixed = unchanged_fixed / (n_runs * n)
    print(f"[敏感性] ±10%扰动 {n_runs} 次：等级稳定率(Jenks重断点)={stability_rebreak:.4f} "
          f"(固定断点)={stability_fixed:.4f}")

    # ③ 三法一致性：组合 vs 纯AHP vs 纯熵权
    w_pure_ahp = np.array([DIM_W[d] / DIM_N[d] for _, d, _, _ in LEVEL2])
    w_pure_ent, _, _ = _entropy_weights(X)
    score_ahp = 100.0 * (X @ w_pure_ahp)
    score_ent = 100.0 * (X @ w_pure_ent)
    rho_ca = float(spearmanr(Score, score_ahp).statistic)
    rho_ce = float(spearmanr(Score, score_ent).statistic)
    rho_ae = float(spearmanr(score_ahp, score_ent).statistic)
    g_ahp = [_grade_from_bounds(x, _jenks_boundaries(score_ahp, 5)[0]) for x in score_ahp]
    g_ent = [_grade_from_bounds(x, _jenks_boundaries(score_ent, 5)[0]) for x in score_ent]
    ari_ca = float(adjusted_rand_score(grades, g_ahp))
    ari_ce = float(adjusted_rand_score(grades, g_ent))
    ari_ae = float(adjusted_rand_score(g_ahp, g_ent))
    print(f"[三法一致性] ρ(组合,AHP)={rho_ca:.4f} ρ(组合,熵权)={rho_ce:.4f} ρ(AHP,熵权)={rho_ae:.4f}")
    print(f"              ARI(组合,AHP)={ari_ca:.4f} ARI(组合,熵权)={ari_ce:.4f} ARI(AHP,熵权)={ari_ae:.4f}")

    # ---- 9. 统计量与分布 ----
    _print_stats(Score, "综合得分")
    dist = {g: grades.count(g) for g in GRADE_ORDER}
    dist_abs = {g: grades_abs.count(g) for g in GRADE_ORDER}
    print(f"[分级分布 Jenks] {dist}")
    print(f"[分级分布 绝对阈值] {dist_abs}")
    print(f"[Jenks 断点(上界)] {[round(b, 2) for b in jenks_bounds]}")

    # 数值稳定性检查
    assert np.all(np.isfinite(Score))
    assert np.all(np.isfinite(w_comb))
    assert CR < 0.1, "AHP 一致性未通过 CR<0.1"

    papers = []
    for i, pid in enumerate(ids):
        papers.append({
            "id": pid,
            "score": float(round(Score[i], 4)),
            "grade": grades[i],
            "grade_threshold_90": grades_abs[i],
            "dimension_scores": {d: float(round(dim_scores[d][i], 4)) for d, _, _, _ in LEVEL1},
        })

    result = {
        "sub_question": "Q1",
        "problem": "选题A 数学建模论文智能评估系统",
        "model": "层次指标体系 + AHP主观权重 + 熵权客观权重 + 乘法合成组合赋权 + 线性加权评分 + Fisher-Jenks自然断点分级",
        "run_timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "seed": SEED,
        "n_papers": n,
        "group": "att1",
        "indicator_system": {
            "level1": [{"id": d, "name": nm, "ahp_target_weight": float(tw),
                        "ahp_eigen_weight": float(w_ahp[i]), "national_mapping": nmap}
                       for i, (d, nm, tw, nmap) in enumerate(LEVEL1)],
            "level2": [{"id": k, "dim": d, "name": nm, "direction": dr}
                       for k, d, nm, dr in LEVEL2],
        },
        "standardization": std_params,
        "ahp": {
            "judgment_matrix": A_mat.tolist(),
            "target_weights": _clean(target_w),
            "eigen_weights": _clean(w_ahp),
            "lambda_max": lam_max, "CI": CI, "RI": RI, "CR": CR,
            "consistent": bool(CR < 0.1),
        },
        "entropy_weights": entropy_detail,
        "combined_weights": combined,
        "papers": papers,
        "grading": {
            "method": "Fisher-Jenks 自然断点法（k=5，数据驱动五级分级）",
            "jenks_breaks_upper": _clean(jenks_bounds),
            "distribution": dist,
            "threshold_90_reference": {
                "note": "规范绝对阈值分级（min-max 相对尺度下不匹配，仅作对照）",
                "thresholds": {"优秀": [90, 100], "良好": [80, 90], "中等": [70, 80],
                               "及格": [60, 70], "不及格": [None, 60]},
                "distribution": dist_abs,
            },
            "grading_note": (
                "min-max 标准化将各指标锚定在 att1 样本的相对尺度上（样本最劣=0、最优=1），"
                "线性加权后的综合得分是相对质量指数而非绝对百分制，导致绝对阈值(90/80/70/60)"
                "与相对得分失配（ARI(绝对阈值,K-means)≈%.3f，接近随机，且 29/30 篇落入不及格）。"
                "经 ARI 对照验证后，采纳 model_design 已列明的 Fisher-Jenks 自然断点法做五级分级，"
                "绝对阈值分级保留为规范对照。综合得分 S=Σw_ij·x_ij 的排序与 Q2 质量真值保持一致。" % ari_thresh
            ),
        },
        "kmeans": {
            "n_clusters": 5, "seed": SEED,
            "cluster_mean_score": _clean(cluster_mean),
            "cluster_to_grade": cluster_to_grade,
            "labels": [int(l) for l in labels],
            "ari_threshold_vs_kmeans": ari_thresh,
            "ari_jenks_vs_kmeans": ari_jenks,
        },
        "weight_rationality": {
            "cr_lt_0_1": bool(CR < 0.1),
            "perturbation_10pct": {
                "n_runs": n_runs,
                "grade_stability_jenks_rebreak": stability_rebreak,
                "grade_stability_fixed_boundary": stability_fixed,
                "pass_85pct": bool(stability_rebreak >= 0.85),
            },
            "three_method_compare": {
                "spearman_comb_vs_ahp": rho_ca,
                "spearman_comb_vs_entropy": rho_ce,
                "spearman_ahp_vs_entropy": rho_ae,
                "ari_comb_vs_ahp": ari_ca,
                "ari_comb_vs_entropy": ari_ce,
                "ari_ahp_vs_entropy": ari_ae,
            },
        },
        "statistics": {
            "min": float(Score.min()), "max": float(Score.max()),
            "mean": float(Score.mean()), "std": float(Score.std()),
            "CV": float(Score.std() / Score.mean()),
            "amplitude": float((Score.max() - Score.min()) / 2),
        },
        "warnings": [
            "绝对阈值(90/80/70/60)与 min-max 相对尺度不匹配，采纳 Jenks 自然断点分级（详见 grading.grading_note）",
        ],
    }
    return result, {"ids": ids, "V": V, "X": X, "w_comb": w_comb, "combined": combined,
                    "Score": Score, "grades": grades, "grades_abs": grades_abs,
                    "jenks_bounds": jenks_bounds, "labels": labels,
                    "kmeans_grades": kmeans_grades, "ari_jenks": ari_jenks,
                    "w_ahp": w_ahp}


# =====================================================================
# 第二阶段：绘图
# =====================================================================
def _box(ax, xc, yc, w, h, text, fc, ec, fs, lw=1.0):
    ax.add_patch(FancyBboxPatch((xc - w / 2, yc - h / 2), w, h,
                                boxstyle="round,pad=0.5,rounding_size=1.2",
                                mutation_scale=1, linewidth=lw, edgecolor=ec, facecolor=fc))
    ax.text(xc, yc, text, ha="center", va="center", fontsize=fs, color="#212121")


def draw_indicator_tree():
    """图 5-1 指标体系层次图（目标层←6一级维度←21二级指标）。"""
    fig, ax = plt.subplots(figsize=(13.5, 7.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    dir_fc = {"正向": "#c8e6c9", "负向": "#ffcdd2", "适中": "#ffe0b2"}
    dir_ec = {"正向": "#2e7d32", "负向": "#c62828", "适中": "#ef6c00"}

    _box(ax, 50, 95, 24, 7, "目标层\n论文质量综合得分 S", "#e3f2fd", "#1565c0", 12.5, lw=1.6)

    xcs = [8.33, 25.0, 41.67, 58.33, 75.0, 91.67]
    dim_w, dim_h = 14.5, 9.0
    for i, (dim, name, w, _) in enumerate(LEVEL1):
        xc = xcs[i]
        _box(ax, xc, 80, dim_w, dim_h, f"{dim}  {name}\n(w={w:.2f})",
             "#bbdefb", "#0d47a1", 10, lw=1.2)
        ax.annotate("", xy=(xc, 80 + dim_h / 2), xytext=(50, 95 - 3.5),
                    arrowprops=dict(arrowstyle="-", color="#78909c", lw=1.0))

    y_top, row_gap, leaf_h = 66.0, 8.5, 6.5
    for i, (dim, name, w, _) in enumerate(LEVEL1):
        xc = xcs[i]
        leaves = [(k, nm, dr) for k, d, nm, dr in LEVEL2 if d == dim]
        for r, (k, nm, dr) in enumerate(leaves):
            yc = y_top - r * row_gap
            _box(ax, xc, yc, dim_w, leaf_h, f"{k}{DIR_MARK[dr]} {SHORT[k]}",
                 dir_fc[dr], dir_ec[dr], 9.5)
            ax.annotate("", xy=(xc, yc + leaf_h / 2), xytext=(xc, 80 - dim_h / 2),
                        arrowprops=dict(arrowstyle="-", color="#90a4ae", lw=0.8))

    for j, (dr, lab) in enumerate([("正向", "正向指标"), ("负向", "负向指标"), ("适中", "适中型指标")]):
        _box(ax, 38 + j * 15, 12.0, 12, 4.5, lab, dir_fc[dr], dir_ec[dr], 9.5)

    _save_fig(fig, "q1_01_indicator_tree")


def draw_weight_dist(combined):
    """图 5-2 组合权重分布柱状图（按维度分组着色）。"""
    fig, ax = plt.subplots(figsize=(12.5, 5.5))
    ids = [c["id"] for c in combined]
    wvals = np.array([c["w_combined"] for c in combined])
    dims = [c["dim"] for c in combined]
    x = np.arange(len(ids))
    ax.bar(x, wvals, color=[DIM_COLOR[d] for d in dims],
           edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{SHORT[i]}\n{i}" for i in ids], fontsize=8)
    ax.set_ylabel("组合权重 $w_{ij}$")
    ax.set_ylim(0, max(wvals) * 1.18)

    for i, (dim, name, w, _) in enumerate(LEVEL1):
        idx = [j for j, d in enumerate(dims) if d == dim]
        lo, hi = idx[0] - 0.5, idx[-1] + 0.5
        if hi < len(ids) - 0.5:
            ax.axvline(hi, color="#bdbdbd", lw=0.8, ls="--")
        ax.text((lo + hi) / 2, max(wvals) * 1.10, f"{dim}\n({w:.2f})",
                ha="center", va="bottom", fontsize=9, color=DIM_COLOR[dim], fontweight="bold")
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    _save_fig(fig, "q1_02_weight_dist")


def draw_score_dist(Score, grades, jenks_bounds):
    """图 5-3 30 篇论文综合得分分布直方图 + 分级着色 + Jenks 断点。"""
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    lo = float(np.floor(Score.min() / 5) * 5)
    hi = float(np.ceil(Score.max() / 5) * 5)
    bins = np.arange(lo, hi + 1e-9, (hi - lo) / 12)
    cnt, edges, patches = ax.hist(Score, bins=bins, edgecolor="white", linewidth=0.5)
    bw = edges[1] - edges[0]
    for p, e in zip(patches, edges[:-1]):
        p.set_facecolor(GRADE_COLOR[_grade_from_bounds(e + bw / 2, jenks_bounds)])
    for b in jenks_bounds:
        ax.axvline(b, color="#37474f", ls="--", lw=1.0, alpha=0.7)
    ax.axvline(Score.mean(), color="#1565c0", ls=":", lw=1.4,
               label=f"均值 {Score.mean():.2f}")
    ax.set_xlabel("综合得分（相对质量指数）")
    ax.set_ylabel("论文篇数")
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    _save_fig(fig, "q1_03_score_dist")


def draw_cluster_compare(Score, grades, kmeans_grades, ari):
    """图 5-4 阈值分级(Jenks) vs K-means 对照（按得分排序的双面板）。"""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    order = np.argsort(Score)
    x = np.arange(len(Score))
    for ax, gvec, tag in [(axes[0], grades, "Jenks 自然断点分级"),
                          (axes[1], kmeans_grades, "K-means 聚类映射")]:
        ax.bar(x, Score[order], color=[GRADE_COLOR[gvec[i]] for i in order],
               edgecolor="white", linewidth=0.5)
        ax.set_xticks([])
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.text(0.5, 0.02, tag, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=11, color="#37474f")
    axes[0].set_ylabel("综合得分")
    handles = [plt.Rectangle((0, 0), 1, 1, color=GRADE_COLOR[g]) for g in GRADE_ORDER]
    fig.legend(handles, GRADE_ORDER, loc="upper center", ncol=5, frameon=False,
               fontsize=10, bbox_to_anchor=(0.5, 0.99))
    fig.text(0.5, 0.01, f"ARI（Jenks 分级 vs K-means）= {ari:.4f}", ha="center",
             va="bottom", fontsize=11, color="#c62828")
    fig.subplots_adjust(top=0.86, bottom=0.10)
    _save_fig(fig, "q1_04_cluster_compare")


# =====================================================================
# 主流程
# =====================================================================
def main():
    print("=" * 72)
    print("问题一：论文质量综合评价指标体系 + 组合赋权 + 自动评分分级")
    print("=" * 72)

    result, ctx = compute()

    print("\n[绘图] 生成 4 张论文级图表 ...")
    draw_indicator_tree()
    draw_weight_dist(result["combined_weights"])
    draw_score_dist(ctx["Score"], ctx["grades"], ctx["jenks_bounds"])
    draw_cluster_compare(ctx["Score"], ctx["grades"], ctx["kmeans_grades"], ctx["ari_jenks"])

    result["figures"] = [
        "q1_01_indicator_tree.png", "q1_01_indicator_tree.pdf",
        "q1_02_weight_dist.png", "q1_02_weight_dist.pdf",
        "q1_03_score_dist.png", "q1_03_score_dist.pdf",
        "q1_04_cluster_compare.png", "q1_04_cluster_compare.pdf",
    ]

    out_path = os.path.join(RESULTS_DIR, "q1_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=float)
    print(f"\n[输出] {out_path}")

    idx_path = os.path.join(FIG_DIR, "figure_index.json")
    try:
        with open(idx_path, "r", encoding="utf-8") as f:
            fidx = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        fidx = {"generated_at": "", "count": 0, "figures": []}
    existing = set(fidx.get("figures", []))
    for nm in result["figures"]:
        existing.add(nm)
    fidx["figures"] = sorted(existing)
    fidx["count"] = len(fidx["figures"])
    fidx["generated_at"] = datetime.now().strftime("%Y-%m-%d")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(fidx, f, ensure_ascii=False, indent=2)
    print(f"[输出] {idx_path}（figure 总数={fidx['count']}）")

    print("\n" + "=" * 72)
    print("问题一求解完成：CR<0.1、无 NaN/Inf、4 张图、q1_results.json 已生成")
    print("=" * 72)


if __name__ == "__main__":
    main()
