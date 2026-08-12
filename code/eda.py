"""
探索性数据分析（EDA）
功能：相关性热图、变量分布、试验设计识别、指标间关系
输入：problems/选题B/附件/附件2
输出：results/figures/eda_*.png, results/eda_summary.json
运行方式：python code/eda.py
"""
import json
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from data_loader import load_problem_b_data
from utils import save_fig, save_json, FIG_DIR, fix_chinese_font

sns.set_style("whitegrid")
fix_chinese_font()


def main():
    df = load_problem_b_data()
    summary = {}

    # 1. 变量统计
    desc = df.describe().round(4)
    summary["statistics"] = json.loads(desc.to_json())

    # 2. 试验设计识别：变量唯一取值组合
    r_levels = sorted(df["r"].unique().tolist())
    h_levels = sorted(df["h"].unique().tolist())
    n_levels = sorted(df["n"].unique().tolist())
    combos = df.groupby(["r", "h", "n"]).size()
    summary["design"] = {
        "r_levels": r_levels,
        "h_levels": h_levels,
        "n_levels": n_levels,
        "unique_combinations": int(len(combos)),
        "samples": int(len(df)),
        "notes": "近似空间填充设计；r=0时n=0(无针肋基线)",
    }

    # 3. 缺失/重复
    summary["quality"] = {"missing": int(df.isnull().sum().sum()),
                          "duplicates": int(df.duplicated().sum())}

    # 4. 相关性热图
    corr = df[["r", "h", "n", "R", "P", "T"]].corr()
    summary["correlation"] = json.loads(corr.round(4).to_json())
    fig, ax = plt.subplots(figsize=(8, 6.5))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                square=True, linewidths=0.5, ax=ax,
                cbar_kws={"shrink": 0.8})
    ax.set_title("")
    save_fig(fig, "eda_01_correlation.png")

    # 5. 指标分布（直方图+密度）
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, col in zip(axes, ["R", "P", "T"]):
        sns.histplot(df[col], kde=True, ax=ax, color="steelblue")
        ax.set_xlabel(col)
        ax.set_ylabel("频数")
    fig.tight_layout()
    save_fig(fig, "eda_02_metric_distributions.png")

    # 6. 成对关系（r/h/n 对 R/P/T）
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    for i, metric in enumerate(["R", "P", "T"]):
        for j, var in enumerate(["r", "h", "n"]):
            ax = axes[i, j]
            sns.scatterplot(data=df, x=var, y=metric, ax=ax, s=28, color="crimson", alpha=0.7)
            ax.set_xlabel(var)
            ax.set_ylabel(metric)
    fig.tight_layout()
    save_fig(fig, "eda_03_pairwise_trends.png")

    # 7. 样本-指标折线（观察数据平滑性/噪声）
    fig, ax = plt.subplots(figsize=(12, 4))
    for metric in ["R", "P", "T"]:
        ax.plot(df.index, df[metric], marker="o", ms=3, lw=1, label=metric)
    ax.set_xlabel("样本序号")
    ax.set_ylabel("无量纲值")
    ax.legend(ncol=3)
    save_fig(fig, "eda_04_metric_series.png")

    save_json(summary, "eda_summary.json")
    print("EDA完成")


if __name__ == "__main__":
    main()
