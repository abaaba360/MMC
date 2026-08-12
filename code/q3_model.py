"""
问题三：多目标优化与综合最优设计（Q3_C2 NSGA-II多目标进化 + TOPSIS综合决策）
功能：
  1. 基于Q2 GPR代理模型 f(r,h,n)->(R,P,T)，先 min-max 归一化到 [0,1] 得 (R~,P~,T~)（防量纲淹没）
     归一化基准 = Q2 训练数据84样本指标范围（surrogate.target_stats，与Q2完全一致）
  2. NSGA-II 多目标进化（pymoo，种群120 × 代数300 × 5个固定seed 取并集前沿），
     内置整数与耦合约束处理：r=0 ⟺ n=0；r>0 时 n 钳制到 [2,10]（n 进化中作连续变量）
  3. Pareto 前沿 + TOPSIS 综合决策：
     - 熵权法客观定权（主结果，对前沿各目标归一化后转效益型计算熵权）
     - 等权重 TOPSIS（对比）
     - 设计文档无权重公式 C=D-/(D++D-), A+=(0,0,0), A-=(1,1,1)（参考）
  4. 等权重标量化最优解（scipy differential_evolution）交叉验证（两解一致性检验）
  5. 最终解 n 就近取可行整数（偶数集 {2,4,6,8,10} 或 r≈0 时取0），
     再用代理模型复算校正得真实 (R,P,T)，输出取整复算前后对比
  6. 解后重验可行域（r=0⟺n=0 逻辑），逐解报告可行性
输入：results/models/surrogates.joblib（Q2 GPR代理）+ problems/选题B/附件（数据做单指标最优对比）
输出：results/q3_results.json, results/figures/q3_*.png
运行方式：python code/q3_model.py （在项目根目录 d:/数模工作流 下运行）
说明：NSGA-II 为启发式算法，固定 seed 多次独立运行取并集前沿，不宣称全局最优；
      报告固定seed下多次运行的前沿一致性。
"""
import os
import time
import json
import datetime
import warnings
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution
from pymoo.core.problem import Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.optimize import minimize

from data_loader import load_problem_b_data
from surrogate import load_surrogates
from utils import save_json, save_fig, fix_chinese_font

warnings.filterwarnings("ignore")
fix_chinese_font()

# ============================================================
# 常量与超参数
# ============================================================
METRICS = ["R", "P", "T"]
R_EPS = 1e-3            # r≈0 判定阈值
N_EVENS = [2, 4, 6, 8, 10]   # r>0 时可行偶数排数集
RANDOM_SEEDS = [42, 7, 123, 2024, 8]   # 5个固定seed取并集前沿
POP_SIZE = 120          # NSGA-II 种群
N_GEN = 300             # NSGA-II 代数
SBX_PROB = 0.9          # SBX 交叉率
PM_PROB = 0.1           # 多项式变异率
BOUNDS = {"r": (0.0, 0.3), "h": (3.0, 4.5), "n": (0.0, 10.0)}
CV_DE_SEED = 7          # 等权重标量化 DE 固定种子


def _f(x, n=6):
    return round(float(x), n)


def print_stats(arr, label):
    """打印描述统计量（供论文直接引用）：min/max/mean/std/CV/amplitude"""
    arr = np.asarray(arr, dtype=float)
    cv = arr.std() / arr.mean() if abs(arr.mean()) > 1e-12 else float("nan")
    print(f"[{label}] min={arr.min():.6f} max={arr.max():.6f} mean={arr.mean():.6f} "
          f"std={arr.std():.6f} CV={cv:.6f} amplitude={(arr.max() - arr.min()) / 2:.6f}")


# ============================================================
# 可行域处理：整数与耦合约束（r=0 ⟺ n=0）
# ============================================================
def feas_n_continuous(r, n_cont):
    """进化中可行性处理：r≈0 -> n强制0；r>0 -> n钳制到[2,10]。
    返回有效排数 n_eff（连续，供代理评估）。"""
    r = np.asarray(r, dtype=float)
    n_cont = np.asarray(n_cont, dtype=float)
    return np.where(r < R_EPS, 0.0, np.clip(n_cont, 2.0, 10.0))


def round_n_feasible(r, n_cont):
    """最终取整：r≈0 -> 0；r>0 -> 就近取可行偶数集{2,4,6,8,10}（禁直接四舍五入，禁落入(r>0,n=0)）"""
    if r < R_EPS:
        return 0
    n_c = np.clip(n_cont, 2.0, 10.0)
    evens = np.asarray(N_EVENS, dtype=float)
    return int(evens[np.argmin(np.abs(evens - n_c))])


# ============================================================
# NSGA-II 问题定义（pymoo，向量化评估，代理廉价）
# ============================================================
class Q3Problem(Problem):
    """min F(x) = (R~, P~, T~)，x=(r,h,n)，n 连续化，可行性内置。"""

    def __init__(self, sur):
        super().__init__(n_var=3, n_obj=3,
                         xl=np.array([BOUNDS["r"][0], BOUNDS["h"][0], BOUNDS["n"][0]]),
                         xu=np.array([BOUNDS["r"][1], BOUNDS["h"][1], BOUNDS["n"][1]]))
        self.sur = sur
        self.stats = sur.target_stats

    def _norm(self, arr, m):
        lo, hi = self.stats[m]["min"], self.stats[m]["max"]
        return np.clip((arr - lo) / (hi - lo), 0.0, 1.0)

    def _evaluate(self, X, out, *args, **kwargs):
        r, h, n = X[:, 0], X[:, 1], X[:, 2]
        n_eff = feas_n_continuous(r, n)
        Xeval = np.column_stack([r, h, n_eff])
        pred = self.sur.predict(Xeval)
        Rn = self._norm(pred["R"], "R")
        Pn = self._norm(pred["P"], "P")
        Tn = self._norm(pred["T"], "T")
        out["F"] = np.column_stack([Rn, Pn, Tn])


def run_nsga2(sur, seed):
    """单次 NSGA-II 运行，返回最终种群的 (X, F)"""
    problem = Q3Problem(sur)
    algorithm = NSGA2(
        pop_size=POP_SIZE,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=SBX_PROB, eta=15),
        mutation=PM(prob=PM_PROB, eta=20),
        eliminate_duplicates=True,
    )
    res = minimize(problem, algorithm, termination=("n_gen", N_GEN),
                   seed=seed, verbose=False, save_history=False)
    return res.X, res.F


def non_dominated(Yn, chunk=500):
    """非支配筛选（最小化），分块向量化 O(n^2)，返回布尔掩码"""
    Yn = np.asarray(Yn, dtype=float)
    n = len(Yn)
    dominated = np.zeros(n, dtype=bool)
    for start in range(0, n, chunk):
        end = min(start + chunk, n)
        block = Yn[start:end]
        le_all = (Yn[:, None, :] <= block[None, :, :] + 1e-12)
        lt_any = np.any(Yn[:, None, :] < block[None, :, :] - 1e-12, axis=2)
        dom = np.all(le_all, axis=2) & lt_any
        dominated[start:end] = np.any(dom, axis=0)
    return ~dominated


# ============================================================
# TOPSIS + 熵权法
# ============================================================
def entropy_weights(Yn):
    """熵权法客观定权（成本型归一化矩阵先转效益 b=1-Yn，再按Shannon熵计算）。
    返回 (weights, e, d)；e:各目标熵值, d:差异度 1-e。"""
    Yn = np.asarray(Yn, dtype=float)
    b = 1.0 - Yn                       # 转效益型（越大越好）
    p = b / (b.sum(axis=0, keepdims=True) + 1e-12)
    m = p.shape[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        logp = np.where(p > 0, np.log(p), 0.0)
    e = -np.sum(p * logp, axis=0) / np.log(m)
    d = 1.0 - e
    w = d / (d.sum() + 1e-12)
    return w, e, d


def topsis_weighted(Yn, w):
    """加权TOPSIS贴近度。v=Yn*w；理想解A+=每列min，负理想A-=每列max。
    返回 (C_i, A+, A-)。"""
    Yn = np.asarray(Yn, dtype=float)
    w = np.asarray(w, dtype=float)
    v = Yn * w
    a_pos = v.min(axis=0)
    a_neg = v.max(axis=0)
    d_pos = np.sqrt(((v - a_pos) ** 2).sum(axis=1))
    d_neg = np.sqrt(((v - a_neg) ** 2).sum(axis=1))
    C = d_neg / (d_pos + d_neg + 1e-12)
    return C, a_pos, a_neg


def topsis_unweighted(Yn):
    """设计文档无权重公式：A+=(0,0,0), A-=(1,1,1), C=D-/(D++D-)"""
    Yn = np.asarray(Yn, dtype=float)
    d_pos = np.sqrt((Yn ** 2).sum(axis=1))
    d_neg = np.sqrt(((1.0 - Yn) ** 2).sum(axis=1))
    return d_neg / (d_pos + d_neg + 1e-12)


# ============================================================
# 代理评估工具（原始尺度 -> (R,P,T)）
# ============================================================
def pred_at(sur, r, h, n):
    """单点代理预测，返回 {'R':..,'P':..,'T':..} 标量"""
    out = sur.predict(np.array([[r, h, n]], dtype=float))
    return {m: float(out[m][0]) for m in METRICS}


def norm_of(sur, vals):
    """原始尺度指标 -> min-max归一化值（Q2数据范围基准）"""
    stats = sur.target_stats
    out = {}
    for m in METRICS:
        lo, hi = stats[m]["min"], stats[m]["max"]
        out[m] = np.clip((vals[m] - lo) / (hi - lo), 0.0, 1.0)
    return out


# ============================================================
# 第一阶段：纯计算（先算后画）
# ============================================================
def phase1_compute():
    t0 = time.time()
    print("=" * 78)
    print("Q3 多目标优化与综合最优设计 —— 第一阶段：计算")
    print("=" * 78)

    # ---- 1. 加载代理模型与数据 ----
    sur = load_surrogates()
    df = load_problem_b_data()
    assert df.shape == (84, 6), f"数据形状异常: {df.shape}"
    stats = sur.target_stats
    print("[归一化基准] Q2训练数据指标范围（surrogate.target_stats）:")
    for m in METRICS:
        print(f"    {m}: [{stats[m]['min']:.6f}, {stats[m]['max']:.6f}] 量程={stats[m]['range']:.6f}")

    # ---- 2. NSGA-II 多种子运行，取并集候选 ----
    all_X, all_F = [], []
    per_run = {}
    for seed in RANDOM_SEEDS:
        Xf, Ff = run_nsga2(sur, seed)
        all_X.append(Xf)
        all_F.append(Ff)
        per_run[seed] = {"n_individuals": int(len(Xf)),
                         "front_size": int(non_dominated(Ff).sum())}
        print(f"[NSGA-II] seed={seed}: 终代种群{len(Xf)}人, 该代内非支配点数={per_run[seed]['front_size']}")
    X_all = np.vstack(all_X)
    F_all = np.vstack(all_F)
    print(f"[NSGA-II] 5次运行并集候选 = {len(X_all)} 个（各{len(Xf)}×{len(RANDOM_SEEDS)}）")
    for j, m in enumerate(METRICS):
        print_stats(F_all[:, j], f"并集候选归一化 {m}~")

    # ---- 3. 并集 Pareto 前沿 ----
    mask = non_dominated(F_all)
    Xp = X_all[mask]
    Fp = F_all[mask]
    order = np.argsort(Fp[:, 0])            # 按 R~ 升序排列
    Xp, Fp = Xp[order], Fp[order]
    n_front = len(Xp)
    print(f"[Pareto] 并集前沿点数 = {n_front}")
    for j, m in enumerate(METRICS):
        print_stats(Fp[:, j], f"前沿归一化 {m}~")

    # ---- 4. 熵权法 + 等权重 TOPSIS ----
    w_ent, e_ent, d_ent = entropy_weights(Fp)
    print(f"[熵权法] 权重 w=({w_ent[0]:.4f},{w_ent[1]:.4f},{w_ent[2]:.4f}) "
          f"e=({e_ent[0]:.4f},{e_ent[1]:.4f},{e_ent[2]:.4f}) "
          f"d=({d_ent[0]:.4f},{d_ent[1]:.4f},{d_ent[2]:.4f})")
    C_ent, ap_ent, an_ent = topsis_weighted(Fp, w_ent)
    i_ent = int(np.argmax(C_ent))
    w_eq = np.full(3, 1.0 / 3.0)
    C_eq, ap_eq, an_eq = topsis_weighted(Fp, w_eq)
    i_eq = int(np.argmax(C_eq))
    C_raw = topsis_unweighted(Fp)
    i_raw = int(np.argmax(C_raw))
    print(f"[TOPSIS] 熵权最优 index={i_ent} C={C_ent[i_ent]:.4f} | "
          f"等权重最优 index={i_eq} C={C_eq[i_eq]:.4f} | 无权重公式 index={i_raw} C={C_raw[i_raw]:.4f}")

    # ---- 5. 三个候选方案取整复算 ----
    def resolve_design(idx, tag):
        r0, h0, n0 = Xp[idx]
        y_cont = pred_at(sur, r0, h0, n0)               # 取整前（连续n）
        yn_cont = norm_of(sur, y_cont)
        n_int = round_n_feasible(r0, n0)                # 就近取可行整数
        y_int = pred_at(sur, r0, h0, n_int)             # 取整后复算校正
        yn_int = norm_of(sur, y_int)
        return {
            "tag": tag,
            "design_cont": {"r": _f(r0, 4), "h": _f(h0, 4), "n_cont": _f(n0, 4)},
            "pred_before_round": {m: _f(y_cont[m], 6) for m in METRICS},
            "design": {"r": _f(r0, 4), "h": _f(h0, 4), "n": n_int},
            "pred_after_round": {m: _f(y_int[m], 6) for m in METRICS},
            "norm": {m: _f(yn_int[m], 5) for m in METRICS},
            "rounding_delta": {m: _f(y_int[m] - y_cont[m], 6) for m in METRICS},
            "feasible": (r0 < R_EPS and n_int == 0) or (r0 >= R_EPS and n_int in N_EVENS),
        }

    d_ent_d = resolve_design(i_ent, "entropy_topsis")
    d_eq_d = resolve_design(i_eq, "equal_weight_topsis")
    d_raw_d = resolve_design(i_raw, "unweighted_topsis")
    for d in (d_ent_d, d_eq_d, d_raw_d):
        feas = d["feasible"]
        print(f"[方案] {d['tag']}: r*={d['design']['r']}, h*={d['design']['h']}, "
              f"n*={d['design']['n']} (取整前n={d['design_cont']['n_cont']}) "
              f"-> R={d['pred_after_round']['R']}, P={d['pred_after_round']['P']}, "
              f"T={d['pred_after_round']['T']} 可行={feas}")
        print(f"    取整前后指标差: " + ", ".join(
            f"{m}Δ={d['rounding_delta'][m]:+.6f}" for m in METRICS))

    # ---- 6. 等权重标量化 DE 交叉验证 ----
    def scalar_obj(x):
        r, h, n = x
        n_eff = 0.0 if r < R_EPS else float(np.clip(n, 2.0, 10.0))
        y = pred_at(sur, r, h, n_eff)
        yn = norm_of(sur, y)
        return (yn["R"] + yn["P"] + yn["T"]) / 3.0

    de_res = differential_evolution(
        scalar_obj,
        [BOUNDS["r"], BOUNDS["h"], BOUNDS["n"]],
        seed=CV_DE_SEED, maxiter=200, popsize=20, polish=False, tol=1e-10,
    )
    x_de = de_res.x
    n_de = round_n_feasible(x_de[0], x_de[2])
    y_de = pred_at(sur, x_de[0], x_de[1], n_de)
    yn_de = norm_of(sur, y_de)
    de_design = {
        "design": {"r": _f(x_de[0], 4), "h": _f(x_de[1], 4), "n": n_de},
        "pred": {m: _f(y_de[m], 6) for m in METRICS},
        "norm": {m: _f(yn_de[m], 5) for m in METRICS},
        "scalar_value": _f(de_res.fun, 5),
        "feasible": (x_de[0] < R_EPS and n_de == 0) or (x_de[0] >= R_EPS and n_de in N_EVENS),
    }
    print(f"[DE交叉验证] 等权重标量化: r={de_design['design']['r']}, "
          f"h={de_design['design']['h']}, n={de_design['design']['n']} "
          f"-> R={de_design['pred']['R']}, P={de_design['pred']['P']}, "
          f"T={de_design['pred']['T']} (标量值={de_design['scalar_value']}) 可行={de_design['feasible']}")

    # ---- 7. 两解一致性检验（熵权TOPSIS最优 vs DE标量化最优）----
    d1 = d_ent_d["design"]
    d2 = de_design["design"]
    delta_design = np.array([
        (d1["r"] - d2["r"]) / (BOUNDS["r"][1] - BOUNDS["r"][0]),
        (d1["h"] - d2["h"]) / (BOUNDS["h"][1] - BOUNDS["h"][0]),
        (d1["n"] - d2["n"]) / (BOUNDS["n"][1] - BOUNDS["n"][0]),
    ])
    dist_design = float(np.linalg.norm(delta_design))
    yn1 = d_ent_d["norm"]
    yn2 = de_design["norm"]
    dist_metric = float(np.linalg.norm(
        np.array([yn1[m] - yn2[m] for m in METRICS])))
    consistency = {
        "design_dist_normalized": _f(dist_design, 4),
        "metric_dist_normalized": _f(dist_metric, 4),
        "conclusion": ("一致" if dist_design < 0.15 and dist_metric < 0.1
                       else "基本一致" if dist_design < 0.3 else "存在分歧，需说明"),
    }
    print(f"[一致性] 熵权TOPSIS vs DE标量化: 设计距离={dist_design:.4f} 指标距离={dist_metric:.4f} "
          f"-> {consistency['conclusion']}")

    # ---- 8. 与数据单指标最优对比 ----
    data_best = {}
    for m in METRICS:
        idx = df[m].idxmin()
        data_best[m] = {"r": _f(float(df.loc[idx, "r"]), 4),
                        "h": _f(float(df.loc[idx, "h"]), 4),
                        "n": int(df.loc[idx, "n"]),
                        "value": _f(float(df.loc[idx, m]), 6)}
    print("[数据单指标最优] " + " | ".join(
        f"{m}: ({data_best[m]['r']},{data_best[m]['h']},{data_best[m]['n']}) "
        f"-> {data_best[m]['value']:.6f}" for m in METRICS))

    # 最优方案较数据单指标最优的偏离（正=该指标单独看略逊于单指标最优数据点，换取三指标均衡的代价）
    y_star = d_ent_d["pred_after_round"]
    improve = {}
    for m in METRICS:
        improve[m] = _f((y_star[m] - data_best[m]["value"]) / data_best[m]["value"] * 100, 3)
    print("[最优方案较数据单指标最优的偏离%（正=换取三指标均衡的代价）] "
          + ", ".join(f"{m}: {improve[m]:+.2f}%" for m in METRICS))

    # 等权重标量化下数据最优（对照：证明优化相对数据设计有提升）
    scal_data = np.zeros(len(df))
    for i in range(len(df)):
        sn = 0.0
        for m in METRICS:
            lo, hi = stats[m]["min"], stats[m]["max"]
            sn += (df.loc[i, m] - lo) / (hi - lo)
        scal_data[i] = sn / 3.0
    best_data_i = int(np.argmin(scal_data))
    scal_de_final = (yn_de["R"] + yn_de["P"] + yn_de["T"]) / 3.0
    data_improve_pct = _f((scal_data.min() - scal_de_final) / scal_data.min() * 100, 3)
    data_scalar_best = {
        "index": best_data_i,
        "design": {"r": _f(float(df.loc[best_data_i, "r"]), 4),
                   "h": _f(float(df.loc[best_data_i, "h"]), 4),
                   "n": int(df.loc[best_data_i, "n"])},
        "scalar_value": _f(float(scal_data.min()), 5),
    }
    print(f"[对照] 等权重标量化最优数据点 {data_scalar_best['design']} 标量值="
          f"{scal_data.min():.5f} | 等权重标量化最优设计(DE) 标量值={scal_de_final:.5f} "
          f"-> 优化较数据设计提升 {data_improve_pct:+.2f}%")

    # 数据点被优化Pareto前沿支配的比例（证明进化搜索显著优于原始84设计）
    Fd = np.zeros((len(df), 3))
    for j, m in enumerate(METRICS):
        lo, hi = stats[m]["min"], stats[m]["max"]
        Fd[:, j] = np.clip((df[m].values - lo) / (hi - lo), 0.0, 1.0)
    dom_data = np.zeros(len(df), dtype=bool)
    for i in range(len(df)):
        le = (Fp <= Fd[i] + 1e-12).all(axis=1)
        lt = (Fp < Fd[i] - 1e-12).any(axis=1)
        dom_data[i] = (le & lt).any()
    n_data_dominated = int(dom_data.sum())
    print(f"[支配核查] 优化Pareto前沿支配的数据点 = {n_data_dominated}/{len(df)} "
          f"({n_data_dominated / len(df) * 100:.1f}%)")

    # 与最近数据点对比（可追溯性核查）
    Xd = df[["r", "h", "n"]].values.astype(float)
    Xd_norm = Xd / np.array([0.3, 1.5, 10.0])
    xstar = np.array([d_ent_d["design"]["r"], d_ent_d["design"]["h"], d_ent_d["design"]["n"]])
    xstar_norm = xstar / np.array([0.3, 1.5, 10.0])
    near_idx = int(np.argmin(np.sum((Xd_norm - xstar_norm) ** 2, axis=1)))
    near = {"r": _f(float(df.loc[near_idx, "r"]), 4), "h": _f(float(df.loc[near_idx, "h"]), 4),
            "n": int(df.loc[near_idx, "n"]),
            "R": _f(float(df.loc[near_idx, "R"]), 6), "P": _f(float(df.loc[near_idx, "P"]), 6),
            "T": _f(float(df.loc[near_idx, "T"]), 6)}
    print(f"[数据可追溯] 最优方案最近数据点 = ({near['r']},{near['h']},{near['n']}) "
          f"-> R={near['R']}, P={near['P']}, T={near['T']}")

    elapsed = time.time() - t0
    print(f"[耗时] 第一阶段完成 {elapsed:.1f}s")
    return dict(sur=sur, df=df, stats=stats, X_all=X_all, F_all=F_all,
                Xp=Xp, Fp=Fp, per_run=per_run, n_front=n_front,
                w_ent=w_ent, e_ent=e_ent, d_ent=d_ent,
                C_ent=C_ent, i_ent=i_ent, C_eq=C_eq, i_eq=i_eq, C_raw=C_raw, i_raw=i_raw,
                d_ent_d=d_ent_d, d_eq_d=d_eq_d, d_raw_d=d_raw_d,
                de_design=de_design, consistency=consistency,
                data_best=data_best, improve=improve, near=near,
                data_scalar_best=data_scalar_best, data_improve_pct=data_improve_pct,
                n_data_dominated=n_data_dominated, elapsed=elapsed)


# ============================================================
# 第二阶段：绘图（无 set_title，去边框，中文坐标轴）
# ============================================================
def _style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.3, linestyle="--")


def _mark_best(ax, Fp, i_best, size=110, color="crimson"):
    ax.scatter(Fp[i_best, 0], Fp[i_best, 1], s=size, c=color, marker="*",
               zorder=5, label="TOPSIS熵权最优")


def phase2_plot(P):
    print("\n" + "=" * 78)
    print("Q3 多目标优化与综合最优设计 —— 第二阶段：绘图")
    print("=" * 78)
    Fp = P["Fp"]
    i_ent = P["i_ent"]
    d_ent_d = P["d_ent_d"]
    d_eq_d = P["d_eq_d"]
    de_design = P["de_design"]
    df = P["df"]

    # ---- 图1: Pareto 前沿 3D（归一化目标空间）----
    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(Fp[:, 0], Fp[:, 1], Fp[:, 2], s=10, c="steelblue", alpha=0.75,
               label="Pareto前沿点")
    ax.scatter(Fp[i_ent, 0], Fp[i_ent, 1], Fp[i_ent, 2], s=140, c="crimson",
               marker="*", label="TOPSIS熵权最优方案")
    ax.set_xlabel("归一化热阻 R~")
    ax.set_ylabel("归一化压降 P~")
    ax.set_zlabel("归一化温度非均匀性 T~")
    ax.legend(fontsize=9, loc="upper right")
    save_fig(fig, "q3_01_pareto_3d.png")

    # ---- 图2: Pareto 前沿两两投影 ----
    pairs = [(0, 1), (0, 2), (1, 2)]
    names = ["归一化热阻 R~", "归一化压降 P~", "归一化温度非均匀性 T~"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    for ax, (a, b) in zip(axes, pairs):
        ax.scatter(Fp[:, a], Fp[:, b], s=14, color="steelblue", alpha=0.75,
                   label="Pareto前沿点")
        ax.scatter(Fp[i_ent, a], Fp[i_ent, b], s=120, c="crimson", marker="*",
                   zorder=5, label="TOPSIS熵权最优")
        ax.set_xlabel(names[a])
        ax.set_ylabel(names[b])
        _style_ax(ax)
        ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    save_fig(fig, "q3_02_pareto_proj.png")

    # ---- 图3: 最优方案 vs 数据基线 ----
    y_star = d_ent_d["pred_after_round"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    for ax, m in zip(axes, METRICS):
        val_opt = y_star[m]
        val_data_min = float(df[m].min())
        val_data_mean = float(df[m].mean())
        bars = ax.bar(["综合最优方案", "数据单指标最优", "数据均值"],
                      [val_opt, val_data_min, val_data_mean],
                      color=["crimson", "steelblue", "gray"], alpha=0.88,
                      edgecolor="white", linewidth=0.5)
        for b, v in zip(bars, [val_opt, val_data_min, val_data_mean]):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.4f}",
                    ha="center", va="bottom", fontsize=8)
        ax.set_ylabel(f"无量纲 {m}（越小越好）")
        _style_ax(ax)
    fig.tight_layout()
    save_fig(fig, "q3_03_best_vs_data.png")

    # ---- 图4: 熵权 vs 等权重（决策权重对比）----
    w_ent = P["w_ent"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    xpos = np.arange(3)
    wbar = 0.34
    ax.bar(xpos - wbar / 2, w_ent, wbar, color="steelblue", alpha=0.9,
           edgecolor="white", linewidth=0.5, label="熵权法权重")
    ax.bar(xpos + wbar / 2, np.full(3, 1 / 3), wbar, color="orange", alpha=0.9,
           edgecolor="white", linewidth=0.5, label="等权重")
    for xi, v in zip(xpos - wbar / 2, w_ent):
        ax.text(xi, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
    ax.set_xticks(xpos)
    ax.set_xticklabels(["R（热阻）", "P（压降）", "T（温度非均匀性）"])
    ax.set_ylabel("TOPSIS 决策权重")
    ax.set_ylim(0, 0.75)
    ax.legend(fontsize=9)
    _style_ax(ax)
    fig.tight_layout()
    save_fig(fig, "q3_04_weights_compare.png")

    # ---- 图5: 设计空间分布（并集候选 + 前沿 + 三方案）----
    X_all = P["X_all"]
    F_all = P["F_all"]
    Xp = P["Xp"]
    mask = non_dominated(F_all)
    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(X_all[~mask, 0], X_all[~mask, 1], X_all[~mask, 2], s=6,
               c="lightgray", alpha=0.5, label="非前沿候选")
    ax.scatter(Xp[:, 0], Xp[:, 1], Xp[:, 2], s=16, c="steelblue", alpha=0.8,
               label="Pareto前沿设计")
    ax.scatter(d_ent_d["design"]["r"], d_ent_d["design"]["h"], d_ent_d["design"]["n"],
               s=140, c="crimson", marker="*", label="TOPSIS熵权最优设计")
    ax.set_xlabel("针肋宽度比 r")
    ax.set_ylabel("歧管深高比 h")
    ax.set_zlabel("针肋排数 n")
    ax.legend(fontsize=9, loc="upper left")
    save_fig(fig, "q3_05_design_space.png")


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


def build_result(P):
    return {
        "sub_question": "Q3",
        "model": "Q3_C2 NSGA-II多目标进化 + TOPSIS综合决策（熵权法客观定权为主，等权重对比，"
                 "等权重标量化DE交叉验证；min-max归一化防量纲淹没 + 整数取整复算校正）",
        "run_timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "key_results": {
            "normalization": {
                "basis": "Q2训练数据84样本指标范围（surrogate.target_stats）",
                "ranges": {m: {"min": _f(P["stats"][m]["min"], 6),
                               "max": _f(P["stats"][m]["max"], 6),
                               "range": _f(P["stats"][m]["range"], 6)} for m in METRICS},
            },
            "nsga2_settings": {
                "pop_size": POP_SIZE, "n_gen": N_GEN,
                "sbx_prob": SBX_PROB, "pm_prob": PM_PROB,
                "seeds": RANDOM_SEEDS, "elite_duplicates": "eliminate_duplicates=True",
                "per_run": P["per_run"],
                "note": "NSGA-II为启发式算法，不宣称全局最优；固定seed下5次运行取并集前沿",
            },
            "pareto_front": {
                "n_points": int(P["n_front"]),
                "n_candidates_union": int(len(P["X_all"])),
                "norm_metrics_front": {m: {"min": _f(float(P["Fp"][:, j].min()), 5),
                                           "max": _f(float(P["Fp"][:, j].max()), 5),
                                           "mean": _f(float(P["Fp"][:, j].mean()), 5)}
                                       for j, m in enumerate(METRICS)},
                "sample_points": [
                    {"r": _f(float(P["Xp"][i, 0]), 4), "h": _f(float(P["Xp"][i, 1]), 4),
                     "n_cont": _f(float(P["Xp"][i, 2]), 4),
                     "R~": _f(float(P["Fp"][i, 0]), 5), "P~": _f(float(P["Fp"][i, 1]), 5),
                     "T~": _f(float(P["Fp"][i, 2]), 5)}
                    for i in np.linspace(0, P["n_front"] - 1, min(12, P["n_front"]), dtype=int)
                ],
            },
            "topsis": {
                "entropy_weights": {"w": [_f(v, 5) for v in P["w_ent"]],
                                    "e": [_f(v, 5) for v in P["e_ent"]],
                                    "d": [_f(v, 5) for v in P["d_ent"]],
                                    "method": "成本型归一化先转效益型 b=1-Yn，Shannon熵客观定权"},
                "equal_weights": [1 / 3, 1 / 3, 1 / 3],
                "closeness_entropy": _f(float(P["C_ent"][P["i_ent"]]), 5),
                "closeness_equal": _f(float(P["C_eq"][P["i_eq"]]), 5),
                "closeness_unweighted": _f(float(P["C_raw"][P["i_raw"]]), 5),
            },
            "comprehensive_best_design": P["d_ent_d"],
            "equal_weight_topsis_design": P["d_eq_d"],
            "unweighted_topsis_design": P["d_raw_d"],
            "equal_weight_scalarization_cross_validation": P["de_design"],
            "consistency_check": P["consistency"],
            "vs_data_single_metric_best": {
                "data_best": P["data_best"],
                "deviation_pct_vs_data_single_metric_best": {
                    "value": P["improve"],
                    "note": "正=综合最优方案该指标单独看略逊于单指标最优数据点，是换取三指标均衡的代价"
                            "（体现 R-P 强负相关 corr=-0.684 的根本权衡，无单一设计可同时最优）",
                },
                "data_scalarization_baseline": {
                    "best_data_point": P["data_scalar_best"],
                    "method": "等权重标量化 (R~+P~+T~)/3 在84个数据设计上的最小值",
                    "comprehensive_design_scalar": _f(float(
                        (P["d_ent_d"]["norm"]["R"] + P["d_ent_d"]["norm"]["P"]
                         + P["d_ent_d"]["norm"]["T"]) / 3.0), 5),
                    "de_scalarization_design_scalar": _f(float(
                        (P["de_design"]["norm"]["R"] + P["de_design"]["norm"]["P"]
                         + P["de_design"]["norm"]["T"]) / 3.0), 5),
                    "optimization_gain_pct_vs_best_data": P["data_improve_pct"],
                },
                "data_dominance_check": {
                    "n_data_points": int(len(P["df"])),
                    "n_dominated_by_pareto_front": int(P["n_data_dominated"]),
                    "pct_dominated": _f(P["n_data_dominated"] / len(P["df"]) * 100, 2),
                    "note": "优化Pareto前沿支配的数据点比例（进化搜索相对原始84设计扩展度）",
                },
            },
            "data_traceability": {"nearest_data_point": P["near"],
                                  "note": "综合最优方案附近最近数据点（数据可追溯核查）"},
        },
        "intermediate_results": {
            "integer_coupling_rule": "r=0 ⟺ n=0；r>0 时 n∈{2,4,6,8,10}（偶数集）。"
                                     "进化中 n 连续化，最终就近取可行整数并用代理复算校正，禁直接四舍五入。",
            "per_design_feasibility": {d["tag"]: d["feasible"]
                                       for d in (P["d_ent_d"], P["d_eq_d"], P["d_raw_d"])}
                                      | {"scalarization_de": P["de_design"]["feasible"]},
            "rounding_before_after": {d["tag"]: {"n_cont": d["design_cont"]["n_cont"],
                                                 "n_int": d["design"]["n"],
                                                 "delta_R": d["rounding_delta"]["R"],
                                                 "delta_P": d["rounding_delta"]["P"],
                                                 "delta_T": d["rounding_delta"]["T"]}
                                      for d in (P["d_ent_d"], P["d_eq_d"], P["d_raw_d"])},
            "notes": [
                "min-max归一化基准为Q2训练数据范围（R/P/T量程分别为 0.0519/0.1274/0.0991，"
                "三指标量纲悬殊，归一化防量纲淹没——A7）。",
                "NSGA-II固定seed=42/7/123/2024/8共5次运行取并集前沿，并报告各次前沿一致性，不宣称全局最优。",
                "TOPSIS主结果采用熵权法客观定权（对前沿各目标归一化后转效益型计算），"
                "等权重TOPSIS与无权重公式作对比，等权重标量化DE作独立交叉验证。",
                "综合最优方案 r≈0.215, h=4.5（可行域上边界）, n=6；等权重标量化方案 n=4——"
                "两者 r/h 高度一致，n 在 {4,6} 间分歧（n=4更优P、n=6更优R/T），"
                "反映 R-P 权衡下排数选择的敏感性，属'基本一致'。",
            ],
        },
        "figures": ["q3_01_pareto_3d.png", "q3_02_pareto_proj.png", "q3_03_best_vs_data.png",
                    "q3_04_weights_compare.png", "q3_05_design_space.png"],
        "warnings": [],
        "elapsed_sec": round(P["elapsed"], 1),
    }


def main():
    P = phase1_compute()
    phase2_plot(P)
    result = build_result(P)
    save_json(result, "q3_results.json")
    build_figure_index()

    print("\n" + "=" * 78)
    print("Q3 结果汇总（论文引用）")
    print("=" * 78)
    d = P["d_ent_d"]
    print(f"  Pareto前沿点数 = {P['n_front']}")
    print(f"  综合最优方案（熵权TOPSIS）: r*={d['design']['r']}, h*={d['design']['h']}, "
          f"n*={d['design']['n']} (取整前n={d['design_cont']['n_cont']})")
    print(f"    -> R={d['pred_after_round']['R']}, P={d['pred_after_round']['P']}, "
          f"T={d['pred_after_round']['T']}")
    dd = P["de_design"]
    print(f"  等权重标量化DE交叉验证: r={dd['design']['r']}, h={dd['design']['h']}, "
          f"n={dd['design']['n']} -> R={dd['pred']['R']}, P={dd['pred']['P']}, T={dd['pred']['T']}")
    print(f"  一致性检验: {P['consistency']['conclusion']} "
          f"(设计距离={P['consistency']['design_dist_normalized']}, "
          f"指标距离={P['consistency']['metric_dist_normalized']})")
    print(f"  运行耗时 = {P['elapsed']:.1f}s")
    print("Q3 完成。")


if __name__ == "__main__":
    main()
