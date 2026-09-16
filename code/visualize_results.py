"""从已验证的明细结果生成论文图；不在绘图阶段重新求解模型。"""

from __future__ import annotations

from pathlib import Path
import json

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "results" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def setup_style() -> None:
    mpl.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 9.5,
        "axes.labelsize": 10,
        "legend.fontsize": 8.5,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "axes.linewidth": 0.8,
        "grid.alpha": 0.2,
        "grid.linewidth": 0.6,
        "savefig.dpi": 300,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def _save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIG_DIR / f"{stem}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(FIG_DIR / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_q1() -> None:
    frame = pd.read_csv(ROOT / "results" / "q1_detail.csv")
    hours = np.arange(len(frame)) / 6.0
    colors = {
        "load": "#243B53", "pv": "#F2B134", "grid": "#2F80ED",
        "charge": "#27AE60", "discharge": "#EB5757", "soc": "#7B2CBF",
        "price": "#52616B",
    }
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(7.35, 6.15), sharex=True,
                                         gridspec_kw={"height_ratios": [1.25, 0.9, 0.72], "hspace": 0.12})
    ax1.plot(hours, frame["load_kwh"] * 6, lw=1.7, color=colors["load"], label="负荷功率")
    ax1.fill_between(hours, 0, frame["pv_kwh"] * 6, color=colors["pv"], alpha=0.42, label="光伏功率")
    ax1.plot(hours, frame["grid_kwh"] * 6, lw=1.25, color=colors["grid"], label="计划购电功率")
    ax1.set_ylabel("功率 / kW")
    ax1.grid(axis="y")
    ax1.legend(ncol=3, loc="upper center", frameon=False)

    discharge_kw = frame["discharge_kwh"] * 6
    charge_kw = -frame["charge_kwh"] * 6
    ax2.fill_between(hours, 0, discharge_kw, color=colors["discharge"], alpha=0.52, label="储能放电")
    ax2.fill_between(hours, 0, charge_kw, color=colors["charge"], alpha=0.52, label="储能充电")
    ax2.set_ylabel("储能功率 / kW")
    ax2.grid(axis="y")
    ax2b = ax2.twinx()
    ax2b.plot(hours, frame["price_yuan_per_kwh"], color=colors["price"], lw=1.0,
              ls=":", label="分时电价")
    ax2b.set_ylabel("电价 / (元·kWh$^{-1}$)")
    handles, labels = ax2.get_legend_handles_labels()
    handles2, labels2 = ax2b.get_legend_handles_labels()
    ax2.legend(handles + handles2, labels + labels2, ncol=3, loc="upper center", frameon=False)

    ax3.plot(hours, frame["soc_end_kwh"], color=colors["soc"], lw=1.7, label="储电量")
    ax3.axhline(1200, color=colors["soc"], lw=0.7, ls="--", alpha=0.55, label="运行边界")
    ax3.axhline(10800, color=colors["soc"], lw=0.7, ls="--", alpha=0.55)
    ax3.fill_between(hours, 1200, 10800, color=colors["soc"], alpha=0.035)
    ax3.set_ylabel("储电量 / kWh")
    ax3.set_xlabel("时刻 / h")
    ax3.set_xlim(0, 24)
    ax3.set_xticks(np.arange(0, 25, 2))
    ax3.set_ylim(0, 12000)
    ax3.grid(axis="y")
    ax3.legend(ncol=2, loc="upper center", frameon=False)
    for ax in (ax1, ax2, ax2b, ax3):
        ax.spines["top"].set_visible(False)
    _save(fig, "q1_dispatch_and_soc")


def plot_model_growth() -> None:
    fig, ax = plt.subplots(figsize=(7.35, 4.55))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")
    rows = [
        (6.55, "由运行过程得到基本关系", "母线能量守恒  ·  储电量跨时段转移  ·  容量/功率/互斥", "#D9EAF7", "#1F4E78"),
        (4.85, "问题一：全天信息已知", "给定144时段参数  →  求单日最低费用计划", "#E8F3E8", "#2E7D32"),
        (3.15, "问题二：0时先计划、事后只应急", "计划先于实际曲线确定  →  两阶段决策与跨日储电量", "#FFF1D6", "#C77800"),
        (1.45, "问题三、四：新信息逐步到达", "仅重算未执行时段  →  滚动调整与信息价值评价", "#F3E8FA", "#7B2CBF"),
    ]
    for y, title, body, fill, edge in rows:
        box = FancyBboxPatch((0.65, y), 8.7, 1.05, boxstyle="round,pad=0.03,rounding_size=0.12",
                             linewidth=1.35, edgecolor=edge, facecolor=fill)
        ax.add_patch(box)
        ax.text(1.0, y + 0.7, title, fontsize=11, fontweight="bold", color=edge, va="center")
        ax.text(1.0, y + 0.3, body, fontsize=9.3, color="#263238", va="center")
    for y1, y2 in ((6.55, 5.9), (4.85, 4.2), (3.15, 2.5)):
        ax.add_patch(FancyArrowPatch((5.0, y1), (5.0, y2), arrowstyle="-|>", mutation_scale=13,
                                     linewidth=1.1, color="#607D8B"))
    _save(fig, "model_growth_route")


def plot_q2() -> None:
    z = np.load(ROOT / "results" / "q2_detail.npz", allow_pickle=True)
    dates = pd.to_datetime(z["dates"])
    start = int(z["official_start_index"][0])
    frame = pd.DataFrame({
        "date": dates[start:],
        "计划购电费": z["planned_cost_yuan"][start:],
        "紧急购电费": z["emergency_cost_yuan"][start:],
        "紧急购电量": z["actual_emergency_kwh"][start:].sum(axis=1),
    }).set_index("date")
    monthly = frame.resample("ME").sum()
    x = np.arange(len(monthly))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.35, 5.0), gridspec_kw={"hspace": 0.3})
    ax1.bar(x, monthly["计划购电费"] / 1e4, color="#4C78A8", label="计划购电费")
    ax1.bar(x, monthly["紧急购电费"] / 1e4, bottom=monthly["计划购电费"] / 1e4,
            color="#E45756", label="紧急购电费")
    ax1.set_ylabel("月费用 / 万元")
    ax1.legend(ncol=2, frameon=False)
    ax1.set_xticks(x, [f"{d.month}月" for d in monthly.index])
    ax1.grid(axis="y")
    ax2.bar(x, monthly["紧急购电量"] / 1e3, color="#F28E2B")
    ax2.set_ylabel("紧急购电量 / MWh")
    ax2.set_xticks(x, [f"{d.month}月" for d in monthly.index])
    ax2.grid(axis="y")
    for ax in (ax1, ax2):
        ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "q2_monthly_cost_and_emergency")

    chosen = ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]
    fig, axes = plt.subplots(2, 2, figsize=(7.35, 5.2), sharex=True)
    h = np.arange(144) / 6
    for ax, day in zip(axes.flat, chosen):
        i = int(np.flatnonzero(dates.strftime("%Y-%m-%d") == day)[0])
        ax.plot(h, z["actual_net_kwh"][i] * 6, color="#243B53", lw=1.35, label="实际净负荷")
        ax.plot(h, z["point_forecast_net_kwh"][i] * 6, color="#4C78A8", lw=1.1,
                ls="--", label="日前预测")
        ax.fill_between(h, 0, z["actual_emergency_kwh"][i] * 6,
                        color="#E45756", alpha=0.42, label="紧急购电")
        ax.text(0.02, 0.92, day, transform=ax.transAxes, fontsize=9, fontweight="bold")
        ax.grid(axis="y")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0, 0].set_ylabel("功率 / kW")
    axes[1, 0].set_ylabel("功率 / kW")
    axes[1, 0].set_xlabel("时刻 / h")
    axes[1, 1].set_xlabel("时刻 / h")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.01))
    fig.subplots_adjust(top=0.91)
    _save(fig, "q2_representative_days")


def plot_q3() -> None:
    report = json.loads((ROOT / "results" / "q3_results.json").read_text(encoding="utf-8"))
    order = ["0_only", "0_6", "0_6_12", "0_6_12_18"]
    labels = ["0时", "0/6时", "0/6/12时", "0/6/12/18时"]
    ab = report["update_ablation"]
    planned = np.array([ab[k]["planned_cost_yuan"] for k in order]) / 1e4
    adjust = np.array([ab[k]["adjustment_cost_yuan"] for k in order]) / 1e4
    emerg = np.array([ab[k]["emergency_cost_yuan"] for k in order]) / 1e4
    energy = np.array([ab[k]["emergency_energy_kwh"] for k in order]) / 1e3
    x = np.arange(4)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.35, 3.55), gridspec_kw={"wspace": 0.3})
    ax1.bar(x, planned, color="#4C78A8", label="初始计划费用")
    ax1.bar(x, adjust, bottom=planned, color="#72B7B2", label="调整净费用")
    ax1.bar(x, emerg, bottom=planned + adjust, color="#E45756", label="紧急购电费")
    ax1.set_ylabel("全年费用 / 万元")
    ax1.set_xticks(x, labels, rotation=16)
    ax1.legend(frameon=False, fontsize=7.6, ncol=3, loc="upper center",
               bbox_to_anchor=(0.5, 1.12))
    ax1.grid(axis="y")
    ax2.bar(x, energy, color=["#C9D6E4", "#94B6D2", "#5F95BE", "#2F6F9F"])
    ax2.set_ylabel("紧急购电量 / MWh")
    ax2.set_xticks(x, labels, rotation=16)
    ax2.grid(axis="y")
    for ax in (ax1, ax2):
        ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "q3_update_ablation")

    z = np.load(ROOT / "results" / "q3_detail.npz", allow_pickle=True)
    dates = pd.to_datetime(z["dates"])
    chosen = ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]
    fig, axes = plt.subplots(2, 2, figsize=(7.35, 5.25), sharex=True)
    h = np.arange(144) / 6
    for ax, day in zip(axes.flat, chosen):
        i = int(np.flatnonzero(dates.strftime("%Y-%m-%d") == day)[0])
        net = z["effective_grid"][i] + z["emergency"][i] + z["discharge"][i] \
              - z["charge"][i] - z["curtailment"][i]
        ax.plot(h, net * 6, color="#243B53", lw=1.25, label="实际净负荷")
        for oi, origin in enumerate((0, 36, 72, 108)):
            vals = z["load_forecasts"][i, oi] - z["pv_forecasts"][i, oi]
            ax.plot(h[origin:], vals[origin:] * 6, lw=0.9, alpha=0.74,
                    label=f"{origin//6}时预测")
        ax.fill_between(h, 0, z["emergency"][i] * 6, color="#E45756", alpha=0.34,
                        label="紧急购电")
        ax.text(0.02, 0.92, day, transform=ax.transAxes, fontsize=9, fontweight="bold")
        ax.grid(axis="y")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0, 0].set_ylabel("功率 / kW")
    axes[1, 0].set_ylabel("功率 / kW")
    axes[1, 0].set_xlabel("时刻 / h")
    axes[1, 1].set_xlabel("时刻 / h")
    handles, labels2 = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels2, ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.01))
    fig.subplots_adjust(top=0.88)
    _save(fig, "q3_forecast_updates")


def plot_q4() -> None:
    report = json.loads((ROOT / "results" / "q4_results.json").read_text(encoding="utf-8"))
    k = report["key_results"]
    strategies = ["因果在线", "完全价格信息", "全信息下界"]
    q42 = [k["q4_2_causal"]["total_cost_yuan"],
           k["q4_2_perfect_price"]["total_cost_yuan"],
           k["full_information_oracle_lower_bound"]["total_cost_yuan"]]
    q43 = [k["q4_3_causal"]["total_cost_yuan"],
           k["q4_3_perfect_price"]["total_cost_yuan"],
           k["full_information_oracle_lower_bound"]["total_cost_yuan"]]
    x = np.arange(3); width = 0.34
    fig, ax = plt.subplots(figsize=(7.35, 3.8))
    b1 = ax.bar(x - width/2, np.array(q42)/1e4, width, color="#4C78A8", label="问题4-2")
    b2 = ax.bar(x + width/2, np.array(q43)/1e4, width, color="#F28E2B", label="问题4-3")
    ax.set_xticks(x, strategies)
    ax.set_ylabel("正式期总费用 / 万元")
    ax.grid(axis="y")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=2, loc="upper right")
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.1f}",
                    ha="center", va="bottom", fontsize=8)
    _save(fig, "q4_information_value")


def main() -> None:
    setup_style()
    plot_model_growth()
    if (ROOT / "results" / "q1_detail.csv").exists():
        plot_q1()
    if (ROOT / "results" / "q2_detail.npz").exists():
        plot_q2()
    if (ROOT / "results" / "q3_detail.npz").exists():
        plot_q3()
    if (ROOT / "results" / "q4_detail.npz").exists():
        q4_dates = np.load(ROOT / "results" / "q4_detail.npz", allow_pickle=True)["dates"]
        if len(q4_dates) == 365:
            plot_q4()


if __name__ == "__main__":
    main()
