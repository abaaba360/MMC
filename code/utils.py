"""
公共工具函数
功能：matplotlib中文字体、结果JSON输出、指标归一化
运行方式：作为模块被其他脚本import
"""
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- 中文字体 ----
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 100


def fix_chinese_font():
    """seaborn等库会重置字体，调用后重新设置中文字体"""
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False

RESULTS_DIR = os.path.join("results")
FIG_DIR = os.path.join("results", "figures")
for _d in (RESULTS_DIR, FIG_DIR):
    os.makedirs(_d, exist_ok=True)


def save_json(data, name):
    """保存结果JSON到 results/（q{i}_results.json）"""
    path = os.path.join(RESULTS_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=float)
    print(f"[输出] {path}")
    return path


def save_fig(fig, name):
    """保存图表为PNG 300dpi"""
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[图表] {path}")
    return path


def minmax_norm(arr, eps=1e-12):
    """0-1归一化，返回归一化值和(min,max)"""
    arr = np.asarray(arr, dtype=float)
    lo, hi = arr.min(), arr.max()
    if hi - lo < eps:
        return np.zeros_like(arr), (lo, hi)
    return (arr - lo) / (hi - lo), (lo, hi)


def rmse(y, yhat):
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(yhat)) ** 2)))


def r2_score(y, yhat):
    y = np.asarray(y, dtype=float)
    yhat = np.asarray(yhat, dtype=float)
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return float(1 - ss_res / (ss_tot + 1e-12))
