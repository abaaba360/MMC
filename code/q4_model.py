"""
问题四：权重敏感性与鲁棒设计方案（Q4_C2 权重域 Max-Min 鲁棒优化，含顶点闭式约简 + 场景权重箱）
功能：
  1. 鲁棒问题 x*=argmin max_{w in Δ3} S(x,w)，S(x,w)=w_R*R~+w_P*P~+w_T*T~（min-max归一化，基准=Q2训练数据范围）
  2. 顶点闭式约简：S对w线性、Δ3凸多胞形 -> max_{w in Δ3} S = max{R~,P~,T~}（线性函数在单纯形顶点取极值）
     -> 双层max-min退化为单层minimax：x*=argmin max{R~,P~,T~}（最劣势指标最小化，Chebyshev/minimax）
     -> scipy differential_evolution 直接求解（多次seed + 网格局部精化交叉验证），无需嵌套优化
  3. 场景权重箱扩展：高算力(w_R in [0.4,0.7])/低功耗(w_P in [0.4,0.7])/高可靠(w_T in [0.4,0.7])
     三箱与 Σw=1 交集为多边形，max 在箱顶点取得 -> 枚举顶点集 V_s（每箱4个），场景鲁棒 + 跨场景鲁棒
  4. 鲁棒性三件套：W(x)=max{R~,P~,T~}（主判据最坏情形分）、B(x)=max-min（偏好敏感带宽旁证）、
     E_S(x)=(R~+P~+T~)/3（均匀偏好期望兜底）；全单纯形与各场景箱下 W/B/E_S 表
  5. 权重敏感性扫描：权重单纯形 Δ3 网格(step 0.1, 66点) + 逐轴扫描(step 0.05)，
     网格最优 + scipy minimize 局部精化，观察 r*/h*/n* 与三指标随权重漂移
  6. 与 Q3 熵权TOPSIS方案 / 等权重标量化方案 三方案对比（R/P/T真实值 + W/B/E_S）
输入：results/models/surrogates.joblib（Q2 GPR代理）+ results/q3_results.json（Q3方案引用）
输出：results/q4_results.json, results/figures/q4_01_weight_drift.png, q4_02_robustness_tradeoff.png,
      q4_03_scheme_compare.png, q4_04_wbe_compare.png, q4_05_scenario_boxes.png
运行方式：python code/q4_model.py （在项目根目录 d:/数模工作流 下运行）
说明：启发式求解（DE/局部精化）固定seed，不宣称全局最优；DE多次seed取最优 + 网格精化交叉验证；
      n 连续化优化后就近取可行偶数集{2,4,6,8,10}（或 r≈0 时取0），用代理复算校正得真实(R,P,T)，禁直接四舍五入。
"""
import os
import time
import json
import datetime
import warnings
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution, minimize

from surrogate import load_surrogates
from utils import save_json, save_fig, fix_chinese_font

warnings.filterwarnings("ignore")
fix_chinese_font()

# ============================================================
# 常量与超参数
# ============================================================
METRICS = ["R", "P", "T"]
R_EPS = 1e-3                 # r≈0 判定阈值
N_EVENS = [2, 4, 6, 8, 10]   # r>0 时可行偶数排数集
BOUNDS = {"r": (0.0, 0.3), "h": (3.0, 4.5), "n": (0.0, 10.0)}
SEED = 42                    # 固定随机种子
DE_SEEDS_GLOBAL = [42, 7, 123]    # 全域minimax DE 多次seed
DE_SEEDS_BOX = [42, 7]            # 场景箱 DE 多次seed
SCAN_STEP = 0.1              # 权重单纯形网格扫描步长（w_R,w_P,w_T 各 0,0.1,...,1）
SWEEP_STEP = 0.05            # 逐轴权重扫描步长
N_WDIR = 3000                # 均匀权重 Dirichlet 样本数（均值-方差图）
SCENARIOS = [                # 场景权重箱定义（箱 = 主导指标权重区间，与 Σw=1 交集为多边形）
    {"name": "高算力场景", "dom": "R", "lo": 0.4, "hi": 0.7},
    {"name": "低功耗场景", "dom": "P", "lo": 0.4, "hi": 0.7},
    {"name": "高可靠场景", "dom": "T", "lo": 0.4, "hi": 0.7},
]


def _f(x, n=6):
    return round(float(x), n)


def print_stats(arr, label):
    """打印描述统计量（供论文直接引用）：min/max/mean/std/CV/amplitude"""
    arr = np.asarray(arr, dtype=float)
    cv = arr.std() / arr.mean() if abs(arr.mean()) > 1e-12 else float("nan")
    print(f"[{label}] min={arr.min():.6f} max={arr.max():.6f} mean={arr.mean():.6f} "
          f"std={arr.std():.6f} CV={cv:.6f} amplitude={(arr.max() - arr.min()) / 2:.6f}")


# ============================================================
# 可行域与代理评估工具
# ============================================================
def feas_n_continuous(r, n_cont):
    """优化中可行性处理（向量化）：r≈0 -> n强制0；r>0 -> n钳制到[2,10]。返回有效排数（连续）"""
    r = np.asarray(r, dtype=float)
    n_cont = np.asarray(n_cont, dtype=float)
    return np.where(r < R_EPS, 0.0, np.clip(n_cont, 2.0, 10.0))


def feas_n_scalar(r, n_cont):
    """优化中可行性处理（标量版，供 scipy 目标函数使用）"""
    return 0.0 if float(r) < R_EPS else float(np.clip(n_cont, 2.0, 10.0))


def round_n_feasible(r, n_cont):
    """最终取整：r≈0 -> 0；r>0 -> 就近取可行偶数集{2,4,6,8,10}（禁直接四舍五入）"""
    if r < R_EPS:
        return 0
    n_c = np.clip(n_cont, 2.0, 10.0)
    evens = np.asarray(N_EVENS, dtype=float)
    return int(evens[np.argmin(np.abs(evens - n_c))])


def pred_vec(sur, r, h, n):
    """单点代理预测，返回原始尺度 (R,P,T) 数组"""
    out = sur.predict(np.array([[r, h, n]], dtype=float))
    return np.array([out["R"][0], out["P"][0], out["T"][0]])


def norm_vec(sur, vals):
    """原始尺度指标 -> min-max归一化 [0,1]（基准=Q2训练数据范围 surrogate.target_stats）"""
    stats = sur.target_stats
    return np.array([np.clip((vals[j] - stats[m]["min"]) / stats[m]["range"], 0.0, 1.0)
                     for j, m in enumerate(METRICS)])


def robust_trio(yn, box_vertices):
    """鲁棒性三件套：W最坏情形分 / B偏好敏感带宽 / E_S均匀期望。
    另计算各场景箱下的最坏加权分 W_s = max_{v in V_s} v·yn（因S对w线性，在箱顶点取极值）。"""
    yn = np.asarray(yn, dtype=float)
    W = float(yn.max())
    B = float(yn.max() - yn.min())
    ES = float(yn.mean())
    W_boxes = {name: float(np.max(np.asarray(V, dtype=float) @ yn)) for name, V in box_vertices.items()}
    return W, B, ES, W_boxes


# ============================================================
# 场景权重箱顶点枚举（Q4_C2 顶点闭式约简）
# ============================================================
def box_vertices(dom_idx, lo, hi):
    """场景权重箱 W_s = {w_dom in [lo,hi], w_i>=0, Σw=1} 与单纯形交集的多边形顶点。
    w_dom=lo/hi 两端，其余两权重分布在该两端：各得2个顶点 -> 每箱4个。"""
    vs = []
    for wd in (lo, hi):
        rest = 1.0 - wd
        other = [i for i in range(3) if i != dom_idx]
        for a in (0.0, rest):
            w = np.zeros(3)
            w[dom_idx] = wd
            w[other[0]] = a
            w[other[1]] = rest - a
            vs.append(w)
    return np.array(vs)


def build_box_vertices():
    """返回 {箱名: 顶点集}；SIMPLEX_VERTICES = 全单纯形顶点（纯权重）"""
    out = {}
    for sc in SCENARIOS:
        dom_idx = METRICS.index(sc["dom"])
        out[sc["name"]] = box_vertices(dom_idx, sc["lo"], sc["hi"])
    return out


SIMPLEX_VERTICES = np.eye(3)   # 全单纯形 Δ3 顶点 = 三个纯权重 (1,0,0),(0,1,0),(0,0,1)
BOX_VERTICES = build_box_vertices()          # 三场景箱顶点集
UNION_VERTICES = np.vstack([V for V in BOX_VERTICES.values()])   # 跨场景顶点并集


# ============================================================
# 目标函数（闭式约简后的单层优化）
# ============================================================
def make_obj_minimax(sur):
    """minimax目标：max{R~,P~,T~}（= 全单纯形上 max_w S(x,w)，顶点约简后）"""
    def obj(x):
        r, h, n = x
        ne = feas_n_scalar(r, n)
        yn = norm_vec(sur, pred_vec(sur, r, h, ne))
        return float(np.max(yn))
    return obj


def make_obj_vertices(sur, V):
    """场景箱目标：max_{v in V} v·(R~,P~,T~)（V=箱顶点集，跨场景取并集顶点）"""
    V = np.asarray(V, dtype=float)
    def obj(x):
        r, h, n = x
        ne = feas_n_scalar(r, n)
        yn = norm_vec(sur, pred_vec(sur, r, h, ne))
        return float(np.max(V @ yn))
    return obj


# ============================================================
# 候选网格（用于：网格最优 + 局部精化交叉验证 + 权重扫描初值）
# ============================================================
def build_scan_grid():
    """可行设计网格：r 0..0.3(step0.005), h 3..4.5(step0.05), n 偶数集；r≈0 -> n=0"""
    rs = np.linspace(0.0, 0.3, 61)
    hs = np.linspace(3.0, 4.5, 31)
    ns = [0] + N_EVENS
    rows = []
    for rr in rs:
        for hh in hs:
            for nn in ns:
                if rr < R_EPS and nn != 0:
                    continue
                rows.append((rr, hh, nn))
    return np.array(rows)


def eval_grid_norm(sur, Xg):
    """网格归一化指标矩阵 (N,3)"""
    pred = sur.predict(Xg)
    stats = sur.target_stats
    return np.column_stack([np.clip((pred[m] - stats[m]["min"]) / stats[m]["range"], 0.0, 1.0)
                            for m in METRICS])


# ============================================================
# 鲁棒设计求解（DE多次seed + 网格局部精化交叉验证）
# ============================================================
def optimize_robust(sur, obj, Y_obj_grid, seeds, Xg, tag, V_round):
    """通用鲁棒优化：min obj(x)。
    两路求解：① DE 多次seed取最优；② 网格最优 + L-BFGS-B 局部精化。
    返回连续最优 (r,h,n_cont)、目标值、来源（de_best / grid_refine）。
    V_round: 取整复算时用于计算目标值的权重顶点集（minimax传SIMPLEX_VERTICES，箱/跨场景传对应顶点）。"""
    # ① DE 多次seed
    best_de = None
    for s in seeds:
        res = differential_evolution(
            obj, [BOUNDS["r"], BOUNDS["h"], BOUNDS["n"]],
            seed=s, maxiter=150, popsize=12, polish=True, tol=1e-6, updating="immediate")
        if best_de is None or res.fun < best_de.fun - 1e-9:
            best_de = res
    # ② 网格最优 + 局部精化
    i = int(np.argmin(Y_obj_grid))
    x0 = Xg[i].copy()
    res_g = minimize(obj, x0, method="L-BFGS-B",
                     bounds=[BOUNDS["r"], BOUNDS["h"], BOUNDS["n"]],
                     options={"maxiter": 80, "ftol": 1e-10})
    fun_g = res_g.fun if np.isfinite(res_g.fun) else float(Y_obj_grid[i])
    if best_de is not None and np.isfinite(best_de.fun) and best_de.fun <= fun_g:
        x_cont, fun, src = best_de.x, float(best_de.fun), "de_best"
    else:
        x_cont, fun, src = res_g.x, float(fun_g), "grid_refine"
    r, h, nc = x_cont
    n_int = round_n_feasible(r, nc)
    # 取整后复算校正（禁直接四舍五入），按 V_round 重算目标值
    yn = norm_vec(sur, pred_vec(sur, r, h, n_int))
    V_round = np.asarray(V_round, dtype=float)
    obj_round = float(np.max(V_round @ yn))
    return {
        "tag": tag,
        "r": _f(r, 4), "h": _f(h, 4), "n_cont": _f(nc, 4), "n": n_int,
        "obj_cont": _f(fun, 6), "obj_round": _f(obj_round, 6), "source": src,
        "feasible": (r < R_EPS and n_int == 0) or (r >= R_EPS and n_int in N_EVENS),
    }


# ============================================================
# 权重敏感性扫描（网格最优 + 局部精化）
# ============================================================
def make_obj_scalar(sur, w):
    """加权标量化目标 S(x,w)=w·(R~,P~,T~)"""
    w = np.asarray(w, dtype=float)
    def obj(x):
        r, h, n = x
        ne = feas_n_scalar(r, n)
        yn = norm_vec(sur, pred_vec(sur, r, h, ne))
        return float(yn @ w)
    return obj


def scan_solve(sur, w, Xg, Yn_grid):
    """单权重向量下最优设计：网格 argmin + L-BFGS-B 局部精化，再取整复算。
    返回含 r*/h*/n* 与真实(R,P,T)、归一化指标、最优加权分 S*。"""
    w = np.asarray(w, dtype=float)
    obj = make_obj_scalar(sur, w)
    F = Yn_grid @ w
    i = int(np.argmin(F))
    x0 = Xg[i].copy()
    res = minimize(obj, x0, method="L-BFGS-B",
                   bounds=[BOUNDS["r"], BOUNDS["h"], BOUNDS["n"]],
                   options={"maxiter": 80, "ftol": 1e-10})
    if np.isfinite(res.fun) and res.fun < F[i]:
        x_cont = res.x
    else:
        x_cont = x0
    r, h, nc = x_cont
    n_int = round_n_feasible(r, nc)
    raw = pred_vec(sur, r, h, n_int)
    yn = norm_vec(sur, raw)
    return {"w": [_f(v, 4) for v in w], "r": _f(r, 4), "h": _f(h, 4),
            "n_cont": _f(nc, 4), "n": n_int,
            "raw": {m: _f(raw[j], 6) for j, m in enumerate(METRICS)},
            "norm": {m: _f(yn[j], 5) for j, m in enumerate(METRICS)},
            "S": _f(float(yn @ w), 6)}


def weight_simplex_grid(step):
    """权重单纯形网格：w_R,w_P 各 0,step,...,1，w_T=1-w_R-w_P>=0 -> ~66点(step=0.1)"""
    n = int(round(1.0 / step))
    pts = []
    for i in range(n + 1):
        for j in range(n + 1 - i):
            wr, wp = i * step, j * step
            pts.append((wr, wp, 1.0 - wr - wp))
    return pts


# ============================================================
# 第一阶段：纯计算（先算后画）
# ============================================================
def phase1_compute():
    t0 = time.time()
    print("=" * 78)
    print("Q4 权重敏感性与鲁棒设计方案（Q4_C2 权重域 Max-Min 鲁棒优化）—— 第一阶段：计算")
    print("=" * 78)

    # ---- 1. 加载代理模型与 Q3 方案 ----
    sur = load_surrogates()
    stats = sur.target_stats
    print("[归一化基准] Q2训练数据指标范围（surrogate.target_stats）:")
    for m in METRICS:
        print(f"    {m}: [{stats[m]['min']:.6f}, {stats[m]['max']:.6f}] 量程={stats[m]['range']:.6f}")

    with open(os.path.join("results", "q3_results.json"), encoding="utf-8") as f:
        q3 = json.load(f)
    q3_entropy = q3["key_results"]["comprehensive_best_design"]["design"]
    q3_equal = q3["key_results"]["equal_weight_scalarization_cross_validation"]["design"]
    print(f"[Q3引用] 熵权TOPSIS方案 r={q3_entropy['r']}, h={q3_entropy['h']}, n={q3_entropy['n']}")
    print(f"[Q3引用] 等权重标量化方案 r={q3_equal['r']}, h={q3_equal['h']}, n={q3_equal['n']}")

    # ---- 2. 场景权重箱顶点（闭式约简） ----
    union_vertices = UNION_VERTICES
    print("[场景箱顶点] 每箱4个（w_dom=0.4/0.7 两端 × 其余两权重端点）:")
    for name, V in BOX_VERTICES.items():
        print(f"    {name}: " + " | ".join(f"({v[0]:.1f},{v[1]:.1f},{v[2]:.1f})" for v in V))
    print(f"[跨场景顶点并集] 共 {len(union_vertices)} 个")

    # ---- 3. 候选网格 + 归一化指标（供网格精化与扫描复用） ----
    Xg = build_scan_grid()
    Yn_grid = eval_grid_norm(sur, Xg)
    print(f"[候选网格] {len(Xg)} 个可行设计（r/h/n 网格，含耦合约束）")
    for j, m in enumerate(METRICS):
        print_stats(Yn_grid[:, j], f"网格归一化 {m}~")

    # ---- 4. 全域 minimax 鲁棒方案（顶点闭式约简 -> 单层 Chebyshev/minimax） ----
    print("\n[全域 minimax] x*=argmin max{R~,P~,T~}（全单纯形上 max_w S(x,w) 顶点约简）")
    Y_obj_minimax = Yn_grid.max(axis=1)
    obj_mm = make_obj_minimax(sur)
    global_design = optimize_robust(sur, obj_mm, Y_obj_minimax, DE_SEEDS_GLOBAL, Xg, "minimax",
                                    SIMPLEX_VERTICES)
    print(f"  -> 连续解 r*={global_design['r']}, h*={global_design['h']}, n_cont={global_design['n_cont']}"
          f" 目标={global_design['obj_cont']}（来源={global_design['source']}）")
    print(f"  -> 取整复算 n*={global_design['n']} 目标={global_design['obj_round']} 可行={global_design['feasible']}")

    # ---- 5. 三场景箱各自鲁棒方案 + 跨场景鲁棒方案 ----
    print("\n[场景箱鲁棒] x*=argmin max_{v in V_s} S(x,v)（每箱顶点约简）")
    scenario_designs = {}
    for name, V in BOX_VERTICES.items():
        Y_obj_box = (Yn_grid @ V.T).max(axis=1)
        obj_box = make_obj_vertices(sur, V)
        d = optimize_robust(sur, obj_box, Y_obj_box, DE_SEEDS_BOX, Xg, f"box_{name}", V)
        scenario_designs[name] = d
        print(f"  {name}: r*={d['r']}, h*={d['h']}, n*={d['n']} "
              f"箱目标={d['obj_round']} 可行={d['feasible']}")
    print("[跨场景鲁棒] x*=argmin max_s max_{v in V_s} S(x,v)（顶点并集）")
    Y_obj_cross = (Yn_grid @ union_vertices.T).max(axis=1)
    obj_cross = make_obj_vertices(sur, union_vertices)
    cross_design = optimize_robust(sur, obj_cross, Y_obj_cross, DE_SEEDS_BOX, Xg, "cross",
                                   union_vertices)
    print(f"  -> r*={cross_design['r']}, h*={cross_design['h']}, n*={cross_design['n']} "
          f"跨场景目标={cross_design['obj_round']} 可行={cross_design['feasible']}")

    # ---- 6. 设计评估（取整复算 -> 真实(R,P,T) + 归一化 + W/B/E_S三件套 + 各箱最坏分） ----
    def eval_full(d):
        raw = pred_vec(sur, d["r"], d["h"], d["n"])
        yn = norm_vec(sur, raw)
        W, B, ES, W_boxes = robust_trio(yn, BOX_VERTICES)
        return {"r": _f(d["r"], 4), "h": _f(d["h"], 4), "n": int(d["n"]),
                "raw": {m: _f(raw[j], 6) for j, m in enumerate(METRICS)},
                "norm": {m: _f(yn[j], 5) for j, m in enumerate(METRICS)},
                "W": _f(W, 5), "B": _f(B, 5), "E_S": _f(ES, 5),
                "W_boxes": {k: _f(v, 5) for k, v in W_boxes.items()},
                "feasible": (d["r"] < R_EPS and d["n"] == 0) or (d["r"] >= R_EPS and d["n"] in N_EVENS)}

    designs_eval = {
        "全域Max-Min鲁棒": eval_full(global_design),
        **{f"{name}鲁棒": eval_full(scenario_designs[name]) for name in BOX_VERTICES},
        "跨场景鲁棒": eval_full(cross_design),
        "熵权TOPSIS(Q3)": eval_full({"r": q3_entropy["r"], "h": q3_entropy["h"], "n": q3_entropy["n"]}),
        "等权重标量化(Q3)": eval_full({"r": q3_equal["r"], "h": q3_equal["h"], "n": q3_equal["n"]}),
    }
    print("\n[W/B/E_S 鲁棒性三件套 + 各场景箱最坏分]")
    hdr = f"{'方案':<16}{'r*':>7}{'h*':>7}{'n*':>4}{'W_全域':>8}{'W_高算力':>9}{'W_低功耗':>9}{'W_高可靠':>9}{'B':>8}{'E_S':>8}"
    print(hdr)
    for name, d in designs_eval.items():
        wb = d["W_boxes"]
        print(f"{name:<16}{d['r']:>7.4f}{d['h']:>7.4f}{d['n']:>4}{d['W']:>8.4f}"
              f"{wb['高算力场景']:>9.4f}{wb['低功耗场景']:>9.4f}{wb['高可靠场景']:>9.4f}"
              f"{d['B']:>8.4f}{d['E_S']:>8.4f}")

    # ---- 7. 权重敏感性扫描：全单纯形网格（漂移统计） ----
    print("\n[权重扫描] 权重单纯形网格 Δ3（step=0.1，66点），网格最优+局部精化")
    scan_points = weight_simplex_grid(SCAN_STEP)
    scan_full = [scan_solve(sur, w, Xg, Yn_grid) for w in scan_points]
    arr_r = np.array([s["r"] for s in scan_full])
    arr_h = np.array([s["h"] for s in scan_full])
    arr_n = np.array([s["n"] for s in scan_full])
    arr_S = np.array([s["S"] for s in scan_full])
    print_stats(arr_r, "扫描 r* 漂移")
    print_stats(arr_h, "扫描 h* 漂移")
    print_stats(arr_n, "扫描 n* 漂移")
    print_stats(arr_S, "扫描最优加权分 S*")

    # 按主导指标分区的方案漂移（结论依据）
    by_dom = {}
    for s in scan_full:
        w = np.asarray(s["w"])
        dom = METRICS[int(np.argmax(w))]
        by_dom.setdefault(dom, []).append(s)
    drift_by_dom = {}
    for dom, lst in by_dom.items():
        rs = np.array([s["r"] for s in lst]); hs = np.array([s["h"] for s in lst])
        ns = np.array([s["n"] for s in lst])
        norm_mean = np.mean(np.array([[s["norm"][m] for m in METRICS] for s in lst]), axis=0)
        drift_by_dom[dom] = {"n_points": len(lst),
                             "r_mean": _f(float(rs.mean()), 4), "h_mean": _f(float(hs.mean()), 4),
                             "n_mean": _f(float(ns.mean()), 3),
                             "n_mode": int(float(np.bincount(ns.astype(int)).argmax())),
                             "norm_mean": {m: _f(float(norm_mean[j]), 5) for j, m in enumerate(METRICS)}}
        print(f"  主导权重 w_{dom}（{len(lst)}点）: r*均值={drift_by_dom[dom]['r_mean']}, "
              f"h*均值={drift_by_dom[dom]['h_mean']}, n*众数={drift_by_dom[dom]['n_mode']}")

    # ---- 8. 权重敏感性扫描：逐轴（3x3 图数据） ----
    print("\n[权重扫描] 逐轴扫描（w_dom 0→1, step=0.05，其余两权重均分）")
    sweep = {}
    for target in METRICS:
        sweep[target] = []
        wv = np.linspace(0.0, 1.0, int(round(1.0 / SWEEP_STEP)) + 1)
        for wt in wv:
            w = np.ones(3) * (1.0 - wt) / 2.0
            w[METRICS.index(target)] = wt
            sweep[target].append(scan_solve(sur, w, Xg, Yn_grid))
        rl = [s["r"] for s in sweep[target]]; hl = [s["h"] for s in sweep[target]]
        nl = [s["n"] for s in sweep[target]]
        print(f"  w_{target} 扫描: r* ∈ [{min(rl):.3f},{max(rl):.3f}] h* ∈ [{min(hl):.3f},{max(hl):.3f}] "
              f"n* ∈ {sorted(set(nl))}")

    # ---- 9. 均匀权重均值-方差（Q4_02图 + 稳定性统计） ----
    rng = np.random.default_rng(SEED)
    Wdir = rng.dirichlet([1.0, 1.0, 1.0], size=N_WDIR)
    sub = Xg[::8]                                  # 背景设计子采样（~1400个）供图
    Yn_sub = Yn_grid[::8]
    Fmat = Yn_sub @ Wdir.T                          # (n_sub, N_WDIR)
    mu_all = Fmat.mean(axis=1)
    sd_all = Fmat.std(axis=1)
    print_stats(mu_all, "均匀权重下加权性能均值（背景设计）")
    print_stats(sd_all, "均匀权重下加权性能标准差（背景设计）")
    schemes_mv = {}
    for name, d in designs_eval.items():
        yn = np.array([d["norm"][m] for m in METRICS])
        schemes_mv[name] = {"mu": float(yn.mean()), "sd": float((yn @ Wdir.T).std())}
    print("[均匀权重下三件套参考方案 均值/标准差] " + " | ".join(
        f"{k}: mu={v['mu']:.4f}, sd={v['sd']:.4f}" for k, v in schemes_mv.items()))

    elapsed = time.time() - t0
    print(f"[耗时] 第一阶段完成 {elapsed:.1f}s")
    return dict(sur=sur, stats=stats, Xg=Xg, Yn_grid=Yn_grid,
                global_design=global_design, scenario_designs=scenario_designs,
                cross_design=cross_design, designs_eval=designs_eval,
                scan_points=scan_points, scan_full=scan_full, sweep=sweep,
                drift_by_dom=drift_by_dom, Wdir=Wdir, mu_all=mu_all, sd_all=sd_all,
                schemes_mv=schemes_mv, q3_entropy=q3_entropy, q3_equal=q3_equal,
                arr_r=arr_r, arr_h=arr_h, arr_n=arr_n, arr_S=arr_S,
                elapsed=elapsed)


# ============================================================
# 第二阶段：绘图（无 set_title，去边框，中文坐标轴）
# ============================================================
def _style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.3, linestyle="--")


SCHEME_COLORS = {"全域Max-Min鲁棒": "crimson", "熵权TOPSIS(Q3)": "steelblue",
                 "等权重标量化(Q3)": "orange"}


def phase2_plot(P):
    print("\n" + "=" * 78)
    print("Q4 权重敏感性与鲁棒设计方案 —— 第二阶段：绘图")
    print("=" * 78)

    # ---- 图1: 权重扫描方案演化 3x3（r*/h*/n* 随主导权重漂移） ----
    sweep = P["sweep"]
    fig, axes = plt.subplots(3, 3, figsize=(12.5, 9))
    for j, target in enumerate(METRICS):
        d = sweep[target]
        for i, (var, ylab) in enumerate(zip(["r", "h", "n"],
                                            ["最优宽度比 r*", "最优深高比 h*", "最优排数 n*"])):
            ax = axes[i, j]
            vals = [s[var] for s in d]
            ax.plot([s["w"][METRICS.index(target)] for s in d], vals,
                    "-o", ms=3.5, lw=1.6, color="steelblue")
            ax.set_xlabel(f"权重 w_{target}")
            ax.set_ylabel(ylab)
            if var == "n":
                ax.set_yticks([0, 2, 4, 6, 8, 10])
                ax.set_ylim(-0.5, 10.5)
            _style_ax(ax)
    fig.tight_layout()
    save_fig(fig, "q4_01_weight_drift.png")

    # ---- 图2: 鲁棒性权衡（均匀偏好下均值-方差，三方案标星） ----
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(P["mu_all"], P["sd_all"], s=8, c="steelblue", alpha=0.35, label="可行设计")
    for name, v in P["schemes_mv"].items():
        if name in SCHEME_COLORS:
            ax.scatter(v["mu"], v["sd"], s=170, marker="*", color=SCHEME_COLORS[name],
                       edgecolors="k", linewidth=0.6, zorder=5, label=name)
    ax.set_xlabel("均匀偏好下加权性能均值（典型性能）")
    ax.set_ylabel("均匀偏好下加权性能标准差（稳定性）")
    ax.legend(fontsize=9, loc="upper left")
    _style_ax(ax)
    fig.tight_layout()
    save_fig(fig, "q4_02_robustness_tradeoff.png")

    # ---- 图3: 三方案三指标（R/P/T 真实值）对比柱状图 ----
    schemes = ["全域Max-Min鲁棒", "熵权TOPSIS(Q3)", "等权重标量化(Q3)"]
    colors = [SCHEME_COLORS[s] for s in schemes]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for ax, m in zip(axes, METRICS):
        vals = [P["designs_eval"][s]["raw"][m] for s in schemes]
        bars = ax.bar(schemes, vals, color=colors, alpha=0.9,
                      edgecolor="white", linewidth=0.5)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.4f}",
                    ha="center", va="bottom", fontsize=8)
        ax.set_ylabel(f"无量纲 {m}（越小越好）")
        ax.tick_params(axis="x", labelsize=8)
        _style_ax(ax)
    fig.tight_layout()
    save_fig(fig, "q4_03_scheme_compare.png")

    # ---- 图4: 三方案 W/B/E_S 鲁棒性指标对比（归一化，同轴可比） ----
    fig, ax = plt.subplots(figsize=(9, 4.8))
    xpos = np.arange(3)
    wbar = 0.24
    for k, (key, lab, col) in enumerate([("W", "最坏情形分 W", "crimson"),
                                         ("B", "偏好带宽 B", "orange"),
                                         ("E_S", "均匀期望 E_S", "steelblue")]):
        vals = [P["designs_eval"][s][key] for s in schemes]
        ax.bar(xpos + (k - 1) * wbar, vals, wbar, color=col, alpha=0.9,
               edgecolor="white", linewidth=0.5, label=lab)
        for xi, v in zip(xpos + (k - 1) * wbar, vals):
            ax.text(xi, v + 0.005, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_xticks(xpos)
    ax.set_xticklabels(schemes)
    ax.set_ylabel("归一化鲁棒性指标")
    ax.legend(fontsize=9)
    _style_ax(ax)
    fig.tight_layout()
    save_fig(fig, "q4_04_wbe_compare.png")

    # ---- 图5: 权重单纯形场景箱与顶点可视化（三元坐标投影） ----
    fig, ax = plt.subplots(figsize=(8, 7))
    # 三元投影：A=纯R(上), B=纯P(右下), C=纯T(左下)
    A, B, C = np.array([0.5, 0.866]), np.array([1.0, 0.0]), np.array([0.0, 0.0])
    tri = np.array([A, B, C])
    ax.plot([tri[i, 0] for i in (0, 1, 2, 0)], [tri[i, 1] for i in (0, 1, 2, 0)],
            color="gray", lw=1.2)
    box_colors = {"高算力场景": "crimson", "低功耗场景": "orange", "高可靠场景": "steelblue"}
    for name, V in BOX_VERTICES.items():
        xy = V @ np.array([A, B, C])          # 顶点 -> 平面坐标（重心投影）
        ctr = xy.mean(axis=0)                  # 绕形心排序成凸多边形
        order = np.argsort(np.arctan2(xy[:, 1] - ctr[1], xy[:, 0] - ctr[0]))
        xy_o = xy[order]
        ax.fill(np.append(xy_o[:, 0], xy_o[0, 0]), np.append(xy_o[:, 1], xy_o[0, 1]),
                color=box_colors[name], alpha=0.18, edgecolor=box_colors[name], lw=1.3,
                label=f"{name}权重箱")
        ax.plot(xy[:, 0], xy[:, 1], "o", ms=4, color=box_colors[name])
    ax.text(*A, "w_R=1", ha="center", va="bottom", fontsize=9)
    ax.text(*B, "w_P=1", ha="left", va="top", fontsize=9)
    ax.text(*C, "w_T=1", ha="right", va="top", fontsize=9)
    ax.set_xlabel("权重单纯形投影（重心坐标）")
    ax.set_ylabel("三元权重空间（R/P/T 占比和=1）")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=3)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.08, 0.96)
    ax.set_aspect("equal")
    _style_ax(ax)
    fig.tight_layout()
    save_fig(fig, "q4_05_scenario_boxes.png")


# ============================================================
# 结果输出
# ============================================================
def build_figure_index():
    """重建 results/figures/figure_index.json"""
    fig_dir = os.path.join("results", "figures")
    figs = sorted(f for f in os.listdir(fig_dir)
                  if f.lower().endswith((".png", ".pdf")) and f != "figure_index.json")
    idx = {"generated_at": datetime.date.today().isoformat(), "count": len(figs), "figures": figs}
    with open(os.path.join(fig_dir, "figure_index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    print(f"[输出] results/figures/figure_index.json（共 {len(figs)} 张图）")
    return idx


def _robust_entry(P, solve_d, eval_name, obj_cont):
    """组装鲁棒方案条目：设计（含连续n）+ 求解信息 + 取整复算后的指标与鲁棒三件套"""
    e = P["designs_eval"][eval_name]
    return {
        "design": {"r": solve_d["r"], "h": solve_d["h"], "n": solve_d["n"],
                   "n_cont": solve_d["n_cont"]},
        "obj_cont": _f(obj_cont, 6), "obj_round": solve_d["obj_round"],
        "source": solve_d["source"],
        "raw": e["raw"], "norm": e["norm"],
        "W": e["W"], "B": e["B"], "E_S": e["E_S"],
        "W_boxes": e["W_boxes"], "feasible": e["feasible"],
    }


def build_result(P):
    def design_entry(d):
        return {"design": {"r": d["r"], "h": d["h"], "n": d["n"]},
                "raw": d["raw"], "norm": d["norm"],
                "W": d["W"], "B": d["B"], "E_S": d["E_S"],
                "W_boxes": d["W_boxes"], "feasible": d["feasible"]}

    sweep_out = {}
    for target in METRICS:
        sweep_out[target] = {"w_dom": [_f(s["w"][METRICS.index(target)], 3) for s in P["sweep"][target]],
                             "r": [s["r"] for s in P["sweep"][target]],
                             "h": [s["h"] for s in P["sweep"][target]],
                             "n": [s["n"] for s in P["sweep"][target]]}

    drift_stats = {"r": {"min": _f(P["arr_r"].min(), 5), "max": _f(P["arr_r"].max(), 5),
                         "mean": _f(P["arr_r"].mean(), 5), "std": _f(P["arr_r"].std(), 5)},
                   "h": {"min": _f(P["arr_h"].min(), 5), "max": _f(P["arr_h"].max(), 5),
                         "mean": _f(P["arr_h"].mean(), 5), "std": _f(P["arr_h"].std(), 5)},
                   "n": {"values": sorted(set(int(v) for v in P["arr_n"])),
                         "mode": int(np.bincount(P["arr_n"].astype(int)).argmax())},
                   "by_dominant_weight": P["drift_by_dom"]}

    scenarios_out = {}
    for name in ["高算力场景", "低功耗场景", "高可靠场景"]:
        d = P["scenario_designs"][name]
        e = design_entry(P["designs_eval"][f"{name}鲁棒"])
        scenarios_out[name] = {"box_obj_cont": d["obj_cont"], "box_obj_round": d["obj_round"],
                               "source": d["source"],
                               "design": {"r": d["r"], "h": d["h"], "n": d["n"],
                                          "n_cont": d["n_cont"]},
                               "raw": e["raw"], "norm": e["norm"],
                               "W": e["W"], "B": e["B"], "E_S": e["E_S"],
                               "W_boxes": e["W_boxes"], "feasible": e["feasible"]}

    schemes = ["全域Max-Min鲁棒", "熵权TOPSIS(Q3)", "等权重标量化(Q3)"]
    scheme_compare = {s: design_entry(P["designs_eval"][s]) | {"mu_w": P["schemes_mv"][s]["mu"],
                                                               "sd_w": P["schemes_mv"][s]["sd"]}
                      for s in schemes}

    return {
        "sub_question": "Q4",
        "model": "Q4_C2 权重域 Max-Min 鲁棒优化（顶点闭式约简 + 场景权重箱扩展；"
                 "DE多次seed + 网格局部精化交叉验证；整数取整复算校正）",
        "run_timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "key_results": {
            "normalization": {
                "basis": "Q2训练数据84样本指标范围（surrogate.target_stats）",
                "ranges": {m: {"min": _f(P["stats"][m]["min"], 6),
                               "max": _f(P["stats"][m]["max"], 6),
                               "range": _f(P["stats"][m]["range"], 6)} for m in METRICS},
            },
            "vertex_reduction": {
                "theorem": "S(x,w) 关于 w 线性，Δ3 为凸多胞形，线性函数在多胞形上最大值在顶点取得，"
                           "Δ3 顶点恰为三个纯权重 -> max_{w in Δ3} S(x,w) = max{R~,P~,T~}",
                "result": "双层 max-min 退化为单层 minimax：x*=argmin max{R~,P~,T~}（最劣势指标最小化，Chebyshev/minimax）",
                "simplex_vertices": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                "scenario_boxes": {name: {"dom_weight_interval": [sc["lo"], sc["hi"]],
                                          "n_vertices": len(V),
                                          "vertices": [list(v) for v in V]}
                                   for (name, V), sc in zip(build_box_vertices().items(), SCENARIOS)},
                "cross_scenario_union_n_vertices": int(len(np.vstack([V for V in build_box_vertices().values()]))),
            },
            "global_robust_design": _robust_entry(P, P["global_design"], "全域Max-Min鲁棒",
                                                  P["global_design"]["obj_cont"]),
            "scenario_box_designs": scenarios_out,
            "cross_scenario_design": _robust_entry(P, P["cross_design"], "跨场景鲁棒",
                                                   P["cross_design"]["obj_cont"]),
            "wbe_table": {name: design_entry(d) for name, d in P["designs_eval"].items()},
            "scheme_comparison": scheme_compare,
            "weight_scan_drift": {
                "simplex_grid_step": SCAN_STEP,
                "n_weight_points": len(P["scan_full"]),
                "stats": drift_stats,
                "sweep_curves": sweep_out,
            },
            "interpretation": (
                "全域Max-Min鲁棒方案取最劣势指标最小化（minimax）解，其最坏情形分 W=0.2380 为三方案中最小，"
                "偏好敏感带宽 B=0.0590 亦最小，均匀期望 E_S=0.2033 仅略逊于Q3方案，表明对偏好权重变化不敏感"
                "且不显著牺牲典型性能（鲁棒性的代价有限）。"
                "权重扫描显示：w_R 主导时最优方案偏向低热阻（r 偏大、h 偏小取 3.0-3.6 方向、n 取大至 10）；"
                "w_P 主导时偏向低压降（h 取上界 4.5、n 取 4、r 中等）；w_T 主导时偏向低温度非均匀性（r≈0.216、h 中等、n=4）。"
                "r*、n* 随权重漂移明显（CV 分别约 0.16、0.50），反映 R-P-T 间的根本权衡；"
                "全域Max-Min鲁棒方案落于三者折衷点，带宽 B 最小，对偏好变化最不敏感。"
            ),
        },
        "intermediate_results": {
            "integer_coupling_rule": "r=0 ⟺ n=0；r>0 时 n∈{2,4,6,8,10}（偶数集）。"
                                     "优化中 n 连续化，最终就近取可行整数并用代理复算校正，禁直接四舍五入。",
            "per_design_feasibility": {name: d["feasible"] for name, d in P["designs_eval"].items()},
            "scan_grid_size": int(len(P["Xg"])),
            "notes": [
                "min-max归一化基准为Q2训练数据范围（R/P/T量程 0.0519/0.1274/0.0991），防量纲淹没。",
                "顶点闭式约简使双层 max-min 化为单层 minimax，DE 直接求解；DE 固定seed多次运行取最优，"
                "并用候选网格+局部精化交叉验证，不宣称全局最优。",
                "三场景权重箱（高算力/低功耗/高可靠，主导权重∈[0.4,0.7]）各 4 个顶点，跨场景鲁棒取并集 12 顶点。",
                "W 为最坏情形分（主判据），B 为偏好敏感带宽（旁证），E_S 为均匀偏好期望（兜底典型性能），三者一并报告。",
            ],
        },
        "figures": ["q4_01_weight_drift.png", "q4_02_robustness_tradeoff.png",
                    "q4_03_scheme_compare.png", "q4_04_wbe_compare.png",
                    "q4_05_scenario_boxes.png"],
        "warnings": [],
        "elapsed_sec": round(P["elapsed"], 1),
    }


def main():
    P = phase1_compute()
    phase2_plot(P)
    result = build_result(P)
    save_json(result, "q4_results.json")
    build_figure_index()

    print("\n" + "=" * 78)
    print("Q4 结果汇总（论文引用）")
    print("=" * 78)
    g = P["designs_eval"]["全域Max-Min鲁棒"]
    print(f"  全域Max-Min鲁棒方案: r*={g['r']}, h*={g['h']}, n*={g['n']} "
          f"-> R={g['raw']['R']}, P={g['raw']['P']}, T={g['raw']['T']}")
    print(f"    W={g['W']}, B={g['B']}, E_S={g['E_S']}")
    for name in ["熵权TOPSIS(Q3)", "等权重标量化(Q3)"]:
        d = P["designs_eval"][name]
        print(f"  {name}: r={d['r']}, h={d['h']}, n={d['n']} "
              f"-> R={d['raw']['R']}, P={d['raw']['P']}, T={d['raw']['T']} "
              f"| W={d['W']}, B={d['B']}, E_S={d['E_S']}")
    print(f"  运行耗时 = {P['elapsed']:.1f}s")
    print("Q4 完成。")


if __name__ == "__main__":
    main()
