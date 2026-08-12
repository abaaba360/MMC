"""
问题二：代理模型构建与评估（Q2_C2 高斯过程回归主模型）
功能：
  1. 对 x=(r,h,n) 标准化（StandardScaler），对 y∈{R,P,T} 分别建独立 GPR（共享同一核结构）
  2. 核：Matern(5/2) ARD 各维独立 length_scale + ConstantKernel 幅度 + WhiteKernel 噪声
     超参经负对数边际似然 L-BFGS-B 优化，5 次随机重启（固定 seed，防局部最优）
  3. 双校验防过拟合：固定 seed 5折CV（R²/RMSE/MAE/RRMSE=RMSE/y_range）+ LOOCV 复核（84次）
     R 指标量程仅 7%，同时报 RRMSE 与 R²
  4. 基线对比：Q2_C1 岭正则化多项式（3次含交互，λ 由5折CV网格选择）+ Q2_C3 随机森林（树基线）
  5. 输出 GPR 预测方差 σ²(x)（供 Q5 认知不确定度传播）
  6. 保存代理模型 results/models/surrogates.joblib 供 Q3-Q5 复用
输入：problems/选题B/附件/附件2 xlsx（load_problem_b_data → df[r,h,n,R,P,T] 84行）
输出：results/q2_results.json, results/figures/q2_*.png, results/models/surrogates.joblib
运行方式：python code/q2_model.py （在项目根目录 d:/数模工作流 下运行）
说明：CV/LOOCV 折内 GPR 用 2 次随机重启以保证 LOOCV 84 次拟合总耗时可控(<5min)，
      最终全量模型用 5 次随机重启（对应论文 Q2_C2 设计）；折内评估偏保守，不夸大泛化性能。
"""
import os
import time
import json
import warnings
import datetime
import numpy as np
import matplotlib.pyplot as plt
from sklearn.exceptions import ConvergenceWarning
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, LeaveOneOut
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel

from data_loader import load_problem_b_data
from utils import save_json, save_fig, fix_chinese_font, rmse, r2_score, minmax_norm
from surrogate import Surrogates

warnings.filterwarnings("ignore", category=ConvergenceWarning)
fix_chinese_font()

RANDOM_STATE = 42
N_FOLDS = 5
METRICS = ["R", "P", "T"]
DIM_NAMES = ["r", "h", "n"]


# ============================================================
# 工具函数
# ============================================================
def print_stats(arr, label):
    """打印描述统计量（供论文直接引用）：min/max/mean/std/CV/amplitude"""
    arr = np.asarray(arr, dtype=float)
    cv = arr.std() / arr.mean() if abs(arr.mean()) > 1e-12 else float("nan")
    print(f"[{label}] min={arr.min():.6f} max={arr.max():.6f} mean={arr.mean():.6f} "
          f"std={arr.std():.6f} CV={cv:.6f} amplitude={(arr.max() - arr.min()) / 2:.6f}")


def _f(x, n=6):
    return round(float(x), n)


def _build_gpr(Xs, y, restarts):
    """构建并训练单个 GPR：ConstantKernel * Matern(5/2 ARD) + WhiteKernel"""
    kernel = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(
        length_scale=[0.3, 0.3, 0.3],
        length_scale_bounds=(1e-2, 1e2),
        nu=2.5,
    ) + WhiteKernel(noise_level=1e-5, noise_level_bounds=(1e-8, 1e-1))
    gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=restarts,
                                   normalize_y=True, random_state=RANDOM_STATE)
    gpr.fit(Xs, y)
    return gpr


def denorm(pred_n, lo, hi):
    return pred_n * (hi - lo) + lo


def eval_raw(y_true, y_pred, y_range):
    """原始尺度指标：R² / RMSE / MAE / RRMSE=RMSE/y_range"""
    r2 = r2_score(y_true, y_pred)
    rm = rmse(y_true, y_pred)
    mae = float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))))
    rrmse = rm / y_range if y_range > 1e-12 else float("nan")
    return r2, rm, mae, rrmse


def gpr_cv_eval(Xs, y_raw, lo, hi, n_folds=N_FOLDS, restarts=2):
    """GPR 5折CV，返回总体与每折指标（原始尺度）"""
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
    r2s, rms, maes, rrms = [], [], [], []
    for tr, te in kf.split(Xs):
        m = _build_gpr(Xs[tr], (y_raw[tr] - lo) / (hi - lo), restarts)
        pred_raw = denorm(m.predict(Xs[te]), lo, hi)
        r2, rm, mae, rrmse = eval_raw(y_raw[te], pred_raw, hi - lo)
        r2s.append(r2); rms.append(rm); maes.append(mae); rrms.append(rrmse)
    return {"fold_r2": r2s, "fold_rmse": rms, "fold_mae": maes, "fold_rrmse": rrms,
            "mean_r2": float(np.mean(r2s)), "mean_rmse": float(np.mean(rms)),
            "mean_mae": float(np.mean(maes)), "mean_rrmse": float(np.mean(rrms))}


def gpr_loocv_eval(Xs, y_raw, lo, hi, restarts=2):
    """GPR 留一交叉验证（84次），返回总体指标与逐样本预测/残差"""
    loo = LeaveOneOut()
    r2s, rms, maes, rrms = [], [], [], []
    pred_all = np.zeros_like(y_raw)
    for tr, te in loo.split(Xs):
        m = _build_gpr(Xs[tr], (y_raw[tr] - lo) / (hi - lo), restarts)
        pred_raw = denorm(m.predict(Xs[te]), lo, hi)
        pred_all[te] = pred_raw[0]
    yt = np.asarray(y_raw)
    r2, rm, mae, rrmse = eval_raw(yt, pred_all, hi - lo)
    return {"mean_r2": r2, "mean_rmse": rm, "mean_mae": mae, "mean_rrmse": rrmse,
            "pred_loocv": pred_all}


def poly_cv_select(Xs, y_raw, lo, hi, n_folds=N_FOLDS):
    """Q2_C1 岭正则化3次多项式（含交互），λ 由5折CV网格选择（最小化RMSE）"""
    poly = PolynomialFeatures(degree=3, include_bias=False)
    Xp = poly.fit_transform(Xs)
    alphas = np.logspace(-5, 2, 50)
    best_alpha, best_score = None, np.inf
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
    alpha_rmse = []
    for alpha in alphas:
        scores = []
        for tr, te in kf.split(Xs):
            m = Ridge(alpha=alpha).fit(Xp[tr], (y_raw[tr] - lo) / (hi - lo))
            pred_raw = denorm(m.predict(Xp[te]), lo, hi)
            scores.append(rmse(y_raw[te], pred_raw))
        ms = float(np.mean(scores))
        alpha_rmse.append(ms)
        if ms < best_score:
            best_score, best_alpha = ms, alpha
    # 用最优 λ 重新做5折CV，取各折指标
    r2s, rms, maes, rrms = [], [], [], []
    for tr, te in kf.split(Xs):
        m = Ridge(alpha=best_alpha).fit(Xp[tr], (y_raw[tr] - lo) / (hi - lo))
        pred_raw = denorm(m.predict(Xp[te]), lo, hi)
        r2, rm, mae, rrmse = eval_raw(y_raw[te], pred_raw, hi - lo)
        r2s.append(r2); rms.append(rm); maes.append(mae); rrms.append(rrmse)
    # 最优λ全量拟合
    final = Ridge(alpha=best_alpha).fit(Xp, (y_raw - lo) / (hi - lo))
    return {"best_alpha": float(best_alpha), "mean_r2": float(np.mean(r2s)),
            "mean_rmse": float(np.mean(rms)), "mean_mae": float(np.mean(maes)),
            "mean_rrmse": float(np.mean(rrms)), "fold_r2": r2s, "model": final,
            "poly": poly, "alpha_rmse_curve": alpha_rmse, "alphas": alphas.tolist()}


def rf_cv_eval(Xs, y_raw, lo, hi, n_folds=N_FOLDS):
    """Q2_C3 随机森林基线，5折CV（n_est=300, min_samples_leaf=4 防过拟合）"""
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
    r2s, rms, maes, rrms = [], [], [], []
    for tr, te in kf.split(Xs):
        m = RandomForestRegressor(n_estimators=300, min_samples_leaf=4,
                                  random_state=RANDOM_STATE, n_jobs=-1)
        m.fit(Xs[tr], (y_raw[tr] - lo) / (hi - lo))
        pred_raw = denorm(m.predict(Xs[te]), lo, hi)
        r2, rm, mae, rrmse = eval_raw(y_raw[te], pred_raw, hi - lo)
        r2s.append(r2); rms.append(rm); maes.append(mae); rrms.append(rrmse)
    return {"mean_r2": float(np.mean(r2s)), "mean_rmse": float(np.mean(rms)),
            "mean_mae": float(np.mean(maes)), "mean_rrmse": float(np.mean(rrms)),
            "fold_r2": r2s}


def ard_importance(gpr):
    """从 GPR 核超参提取 ARD 各维重要度（length_scale 倒数，归一化）"""
    k = gpr.kernel_
    ls = k.k1.k2.length_scale  # ConstantKernel * Matern
    imp = 1.0 / np.asarray(ls, dtype=float)
    imp = imp / imp.sum()
    return {"length_scales": list(ls), "importance": list(imp)}


def build_figure_index():
    """重建 results/figures/figure_index.json（含新增 q2_05）"""
    fig_dir = os.path.join("results", "figures")
    figs = sorted(f for f in os.listdir(fig_dir)
                  if f.lower().endswith((".png", ".pdf")) and f != "figure_index.json")
    idx = {"generated_at": datetime.date.today().isoformat(), "count": len(figs), "figures": figs}
    with open(os.path.join(fig_dir, "figure_index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    print(f"[输出] results/figures/figure_index.json（共 {len(figs)} 张图）")
    return idx


# ============================================================
# 第一阶段：纯计算（先算后画）
# ============================================================
def phase1_compute():
    t0 = time.time()
    print("=" * 78)
    print("Q2 代理模型构建与评估 —— 第一阶段：计算")
    print("=" * 78)

    # ---- 1. 数据读取与校验 ----
    df = load_problem_b_data()
    assert df.shape == (84, 6), f"数据形状异常: {df.shape}"
    assert set(df["r"].unique()) == {0, 0.1, 0.15, 0.2, 0.3}, "r取值异常"
    assert set(df["h"].unique()) == {3, 3.5, 4, 4.5}, "h取值异常"
    assert set(df["n"].unique()) == {0, 2, 4, 6, 8, 10}, "n取值异常"
    assert len(df[(df["r"] > 0) & (df["n"] == 0)]) == 0, "发现 (r>0,n=0) 非法组合"
    assert len(df[(df["r"] == 0) & (df["n"] > 0)]) == 0, "发现 (r=0,n>0) 非法组合"
    assert not df.isna().any().any(), "存在缺失值"
    print("[数据] 84样本结构化全因子网格校验通过；4基线(r=0,n=0) + 80有针肋")

    X = df[["r", "h", "n"]].values.astype(float)
    Y = df[["R", "P", "T"]].values
    print("[数据] 输入 (r,h,n) 与各指标统计：")
    for j, m in enumerate(METRICS):
        print_stats(Y[:, j], f"数据 {m}")

    # ---- 2. 预处理：x标准化 + y 0-1归一化 ----
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    target_stats = {}
    Yn = np.zeros_like(Y)
    for j, m in enumerate(METRICS):
        Yn[:, j], (lo, hi) = minmax_norm(Y[:, j])
        target_stats[m] = {"min": float(lo), "max": float(hi), "range": float(hi - lo)}
    print("[预处理] 输入 StandardScaler 完成；目标 min-max 0-1 归一化完成")
    for m in METRICS:
        print(f"    {m}: y范围={target_stats[m]['range']:.4f}")

    # ---- 3. GPR 主模型训练（全量，5次随机重启）----
    gpr = {}
    print("[GPR] 训练三个独立 GPR（Matern5/2 ARD，5次随机重启，固定seed）：")
    for j, m in enumerate(METRICS):
        gpr[m] = _build_gpr(Xs, Yn[:, j], restarts=5)
        print(f"  GPR[{m}] 最优核: {gpr[m].kernel_}")

    # ---- 4. 5折CV（折内2次重启，防耗时过久）----
    cv = {}
    print("[评估] GPR 5折CV（固定seed打乱）：")
    for j, m in enumerate(METRICS):
        cv[m] = gpr_cv_eval(Xs, Y[:, j], target_stats[m]["min"], target_stats[m]["max"],
                            restarts=2)
        print(f"  {m}: R^2={cv[m]['mean_r2']:.4f} RMSE={cv[m]['mean_rmse']:.5f} "
              f"MAE={cv[m]['mean_mae']:.5f} RRMSE={cv[m]['mean_rrmse']:.4f}")

    # ---- 5. LOOCV 复核（84次）----
    print("[评估] GPR 留一交叉验证（LOOCV 84次，折内2次重启）：")
    loocv = {}
    for j, m in enumerate(METRICS):
        loocv[m] = gpr_loocv_eval(Xs, Y[:, j], target_stats[m]["min"], target_stats[m]["max"])
        print(f"  {m}: R^2={loocv[m]['mean_r2']:.4f} RMSE={loocv[m]['mean_rmse']:.5f} "
              f"MAE={loocv[m]['mean_mae']:.5f} RRMSE={loocv[m]['mean_rrmse']:.4f}")

    # ---- 6. 基线对比：Q2_C1 岭多项式 + Q2_C3 随机森林 ----
    print("[基线] Q2_C1 岭正则化3次多项式（λ 5折CV网格选择）：")
    poly_res = {}
    for j, m in enumerate(METRICS):
        poly_res[m] = poly_cv_select(Xs, Y[:, j], target_stats[m]["min"], target_stats[m]["max"])
        print(f"  {m}: best λ={poly_res[m]['best_alpha']:.2e} R^2={poly_res[m]['mean_r2']:.4f} "
              f"RMSE={poly_res[m]['mean_rmse']:.5f}")

    print("[基线] Q2_C3 随机森林（n_est=300, min_leaf=4, 5折CV）：")
    rf_res = {}
    for j, m in enumerate(METRICS):
        rf_res[m] = rf_cv_eval(Xs, Y[:, j], target_stats[m]["min"], target_stats[m]["max"])
        print(f"  {m}: R^2={rf_res[m]['mean_r2']:.4f} RMSE={rf_res[m]['mean_rmse']:.5f}")

    # ---- 7. GPR 预测方差 σ²(x)（供Q5认知不确定度）----
    surrogates = Surrogates(gpr, scaler, target_stats,
                            meta={"model": "Q2_C2 GPR(Matern5/2 ARD)+WhiteKernel",
                                  "n_samples": len(df)})
    _, std_all = surrogates.predict(X, return_std=True)
    sig_stats = {}
    for m in METRICS:
        s = std_all[m]
        sig_stats[m] = {"min": float(s.min()), "max": float(s.max()),
                        "mean": float(s.mean()), "std": float(s.std()),
                        "cv": float(s.std() / s.mean()) if abs(s.mean()) > 1e-12 else None}
    print("[不确定度] GPR 在84训练点上预测标准差 σ(x) 统计：")
    for m in METRICS:
        print_stats(std_all[m], f"σ({m})")

    # ---- 8. ARD 特征重要度 ----
    ard = {}
    for m in METRICS:
        ard[m] = ard_importance(gpr[m])
        print(f"[ARD] {m} length_scales={ard[m]['length_scales']} 重要度={ard[m]['importance']}")

    # ---- 9. 代理模型保存 ----
    saved_path = surrogates.save("surrogates")
    print(f"[保存] 代理模型 -> {saved_path}")

    elapsed = time.time() - t0
    print(f"[耗时] 第一阶段完成 {elapsed:.1f}s")
    return dict(df=df, X=X, Y=Y, Xs=Xs, Yn=Yn, scaler=scaler, target_stats=target_stats,
                gpr=gpr, cv=cv, loocv=loocv, poly_res=poly_res, rf_res=rf_res,
                surrogates=surrogates, sig_stats=sig_stats, ard=ard,
                saved_path=saved_path, elapsed=elapsed)


# ============================================================
# 第二阶段：绘图（不画 set_title，去边框，中文坐标轴）
# ============================================================
def _style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.3, linestyle="--")


def phase2_plot(P):
    print("\n" + "=" * 78)
    print("Q2 代理模型构建与评估 —— 第二阶段：绘图")
    print("=" * 78)
    Y = P["Y"]
    df = P["df"]
    surrogates = P["surrogates"]

    # ---- 图1: GPR LOOCV 拟合散点 ----
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, m in zip(axes, METRICS):
        j = METRICS.index(m)
        pred = P["loocv"][m]["pred_loocv"]
        ax.scatter(Y[:, j], pred, s=25, alpha=0.7, color="steelblue",
                   label="LOOCV 预测样本")
        lo = min(Y[:, j].min(), pred.min())
        hi = max(Y[:, j].max(), pred.max())
        ax.plot([lo, hi], [lo, hi], "k--", lw=1)
        ax.set_xlabel(f"{m} 真实值")
        ax.set_ylabel(f"{m} LOOCV 预测值")
        ax.text(0.04, 0.88,
                f"R^2={P['loocv'][m]['mean_r2']:.3f}\nRRMSE={P['loocv'][m]['mean_rrmse']:.3f}",
                transform=ax.transAxes, fontsize=9)
        _style_ax(ax)
        ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    save_fig(fig, "q2_01_gpr_fit.png")

    # ---- 图2: 残差分析（散点 + 直方图）----
    fig, axes = plt.subplots(2, 3, figsize=(15, 6.6))
    for j, m in enumerate(METRICS):
        pred = P["loocv"][m]["pred_loocv"]
        resid = Y[:, j] - pred
        ax = axes[0, j]
        ax.scatter(pred, resid, s=25, alpha=0.7, color="crimson")
        ax.axhline(0, color="k", lw=0.8, ls="--")
        ax.set_xlabel(f"{m} 预测值")
        ax.set_ylabel("残差")
        ax.text(0.04, 0.88, f"RMSE={P['loocv'][m]['mean_rmse']:.4f}",
                transform=ax.transAxes, fontsize=9)
        _style_ax(ax)
        ax = axes[1, j]
        ax.hist(resid, bins=14, color="steelblue", edgecolor="white", alpha=0.85)
        ax.set_xlabel(f"{m} 残差")
        ax.set_ylabel("频数")
        _style_ax(ax)
        print_stats(resid, f"残差 {m}")
    fig.tight_layout()
    save_fig(fig, "q2_02_residuals.png")

    # ---- 图3: 模型对比（5折CV R² 与 RMSE）----
    models = ["GPR", "多项式(岭)", "随机森林"]
    colors = {"GPR": "steelblue", "多项式(岭)": "orange", "随机森林": "mediumseagreen"}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    x = np.arange(3)
    w = 0.26
    for mi, name in enumerate(models):
        if name == "GPR":
            r2s = [P["cv"][m]["mean_r2"] for m in METRICS]
            rms = [P["cv"][m]["mean_rmse"] for m in METRICS]
        elif name == "多项式(岭)":
            r2s = [P["poly_res"][m]["mean_r2"] for m in METRICS]
            rms = [P["poly_res"][m]["mean_rmse"] for m in METRICS]
        else:
            r2s = [P["rf_res"][m]["mean_r2"] for m in METRICS]
            rms = [P["rf_res"][m]["mean_rmse"] for m in METRICS]
        ax = axes[0]
        ax.bar(x + (mi - 1) * w, r2s, w, label=name, color=colors[name],
               edgecolor="white", linewidth=0.5)
        for xi, v in zip(x + (mi - 1) * w, r2s):
            ax.text(xi, v + 0.01, f"{v:.3f}", ha="center", fontsize=8)
        ax = axes[1]
        ax.bar(x + (mi - 1) * w, rms, w, label=name, color=colors[name],
               edgecolor="white", linewidth=0.5)
        for xi, v in zip(x + (mi - 1) * w, rms):
            ax.text(xi, v + 0.0006, f"{v:.4f}", ha="center", fontsize=8)
    axes[0].set_xticks(x); axes[0].set_xticklabels(METRICS)
    axes[0].set_ylabel("5折CV R^2")
    axes[0].set_ylim(0, 1.08)
    axes[0].legend(fontsize=8, loc="lower left")
    _style_ax(axes[0])
    axes[1].set_xticks(x); axes[1].set_xticklabels(METRICS)
    axes[1].set_ylabel("5折CV RMSE")
    axes[1].legend(fontsize=8, loc="upper left")
    _style_ax(axes[1])
    fig.tight_layout()
    save_fig(fig, "q2_03_model_compare.png")

    # ---- 图4: GPR 预测区间 σ²(x)（沿 h 扫描, r=0.15, n=6 固定）----
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    r0, n0 = 0.15, 6
    mask = (df["r"] == r0) & (df["n"] == n0)
    hs = np.linspace(3, 4.5, 60)
    Xg = np.column_stack([np.full(60, r0), hs, np.full(60, n0)])
    out, out_std = surrogates.predict(Xg, return_std=True)
    for ax, m in zip(axes, METRICS):
        ax.plot(hs, out[m], color="steelblue", lw=2, label="GPR 预测均值")
        ax.fill_between(hs, out[m] - 2 * out_std[m], out[m] + 2 * out_std[m],
                        color="steelblue", alpha=0.22, label="95% 预测区间(±2σ)")
        ax.scatter(df["h"][mask], df[m][mask], s=45, color="crimson", marker="s",
                   zorder=3, label="CFD 数据点")
        ax.set_xlabel("歧管深高比 h")
        ax.set_ylabel(f"无量纲 {m}")
        ax.text(0.03, 0.90, "r=0.15, n=6", transform=ax.transAxes, fontsize=9)
        _style_ax(ax)
        ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    save_fig(fig, "q2_04_gpr_uncertainty.png")

    # ---- 图5（补充）: ARD 各维特征重要度（length_scale 倒数归一化）----
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(3)
    w = 0.26
    for j, m in enumerate(METRICS):
        imp = P["ard"][m]["importance"]
        ax.bar(x + (j - 1) * w, imp, w, label=f"{m}", color=plt.cm.Set2(j),
               edgecolor="white", linewidth=0.5)
    ax.set_xticks(x); ax.set_xticklabels(["r", "h", "n"])
    ax.set_ylabel("ARD 归一化重要度")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=9)
    _style_ax(ax)
    fig.tight_layout()
    save_fig(fig, "q2_05_ard_importance.png")


# ============================================================
# 结果输出
# ============================================================
def _resid_stats(P):
    """LOOCV 残差描述统计（真实值 - LOOCV预测）"""
    out = {}
    for j, m in enumerate(METRICS):
        res = np.asarray(P["Y"][:, j], dtype=float) - np.asarray(P["loocv"][m]["pred_loocv"])
        out[m] = {"min": _f(float(res.min()), 6), "max": _f(float(res.max()), 6),
                  "mean": _f(float(res.mean()), 6), "std": _f(float(res.std()), 6)}
    return out


def build_result(P):
    result = {
        "sub_question": "Q2",
        "model": "Q2_C2 高斯过程回归（Matern 5/2 ARD 各维独立长度尺度 + ConstantKernel + WhiteKernel），"
                 "负对数边际似然 L-BFGS-B 优化，5次随机重启（固定seed=42），输入StandardScaler、目标min-max 0-1归一化",
        "baseline_models": {
            "Q2_C1": "岭正则化3次多项式（含交互），λ 由5折CV网格选择",
            "Q2_C3": "随机森林（n_estimators=300, min_samples_leaf=4）树基线",
        },
        "run_timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "input_data": {"n_samples": 84,
                       "r_values": [0, 0.1, 0.15, 0.2, 0.3],
                       "h_values": [3, 3.5, 4, 4.5],
                       "n_values": [0, 2, 4, 6, 8, 10],
                       "coupling_rule": "r=0 ⟺ n=0（4基线 + 80有针肋）",
                       "metric_ranges": {m: P["target_stats"][m]["range"] for m in METRICS}},
        "key_results": {
            "gpr_5fold_cv": {m: {"r2": _f(P["cv"][m]["mean_r2"], 4),
                                 "rmse": _f(P["cv"][m]["mean_rmse"], 6),
                                 "mae": _f(P["cv"][m]["mean_mae"], 6),
                                 "rrmse": _f(P["cv"][m]["mean_rrmse"], 4),
                                 "fold_r2": [_f(v, 4) for v in P["cv"][m]["fold_r2"]],
                                 "fold_rmse": [_f(v, 6) for v in P["cv"][m]["fold_rmse"]]}
                            for m in METRICS},
            "gpr_loocv": {m: {"r2": _f(P["loocv"][m]["mean_r2"], 4),
                              "rmse": _f(P["loocv"][m]["mean_rmse"], 6),
                              "mae": _f(P["loocv"][m]["mean_mae"], 6),
                              "rrmse": _f(P["loocv"][m]["mean_rrmse"], 4)}
                          for m in METRICS},
            "poly_5fold_cv": {m: {"best_lambda": _f(P["poly_res"][m]["best_alpha"], 6),
                                  "r2": _f(P["poly_res"][m]["mean_r2"], 4),
                                  "rmse": _f(P["poly_res"][m]["mean_rmse"], 6),
                                  "rrmse": _f(P["poly_res"][m]["mean_rrmse"], 4)}
                              for m in METRICS},
            "rf_5fold_cv": {m: {"r2": _f(P["rf_res"][m]["mean_r2"], 4),
                                "rmse": _f(P["rf_res"][m]["mean_rmse"], 6),
                                "rrmse": _f(P["rf_res"][m]["mean_rrmse"], 4)}
                            for m in METRICS},
            "improvement_gpr_vs_poly": {m: _f(P["cv"][m]["mean_r2"] - P["poly_res"][m]["mean_r2"], 4)
                                        for m in METRICS},
            "improvement_gpr_vs_rf": {m: _f(P["cv"][m]["mean_r2"] - P["rf_res"][m]["mean_r2"], 4)
                                      for m in METRICS},
            "kernel_hyperparams": {m: {"length_scales": P["ard"][m]["length_scales"],
                                       "importance": [_f(v, 4) for v in P["ard"][m]["importance"]]}
                                   for m in METRICS},
            "prediction_sigma_stats": P["sig_stats"],
            "saved_model": P["saved_path"],
        },
        "intermediate_results": {
            "residual_stats_loocv": _resid_stats(P),
            "ard_automatic_feature_selection": "length_scale越大该维重要度越低（自动特征选择）",
            "cv_restarts_note": "CV/LOOCV折内GPR用2次随机重启控制耗时，全量模型5次随机重启",
            "notes": "R指标量程仅约7%，同时报告RRMSE与R^2；GPR核心优势在于σ²(x)不确定度输出（多项式/随机森林无法提供），服务Q5认知不确定度传播",
        },
        "warnings": [],
        "elapsed_sec": round(P["elapsed"], 1),
    }
    return result


def main():
    P = phase1_compute()
    phase2_plot(P)
    result = build_result(P)
    save_json(result, "q2_results.json")
    build_figure_index()

    print("\n" + "=" * 78)
    print("Q2 结果汇总（论文引用）")
    print("=" * 78)
    for m in METRICS:
        print(f"  {m}: 5折CV R^2={P['cv'][m]['mean_r2']:.4f} RMSE={P['cv'][m]['mean_rmse']:.5f} "
              f"RRMSE={P['cv'][m]['mean_rrmse']:.4f}"
              f" | LOOCV R^2={P['loocv'][m]['mean_r2']:.4f}"
              f" | 多项式R^2={P['poly_res'][m]['mean_r2']:.4f}"
              f" | RF R^2={P['rf_res'][m]['mean_r2']:.4f}"
              f" | 较多项式提升={P['cv'][m]['mean_r2'] - P['poly_res'][m]['mean_r2']:+.4f}")
    print("Q2 完成。代理模型已保存，供 Q3-Q5 复用。")


if __name__ == "__main__":
    main()
