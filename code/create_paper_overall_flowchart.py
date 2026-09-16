"""生成论文第二章使用的总体思路图。"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "figures" / "paper_overall_flowchart.png"


def box(ax, x, y, w, h, text, fc, ec, fontsize=10, weight="normal"):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.018,rounding_size=0.025",
        linewidth=1.5, facecolor=fc, edgecolor=ec,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, weight=weight, color="#1f2937", linespacing=1.35)
    return patch


def arrow(ax, x1, y1, x2, y2, color="#64748b", lw=1.5):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=12, linewidth=lw, color=color,
                                 connectionstyle="arc3,rad=0"))


def main():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(15.6, 8.0), dpi=220)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")

    # 公共输入与预处理
    box(ax, 0.5, 7.55, 2.2, 0.85, "赛题要求与附件1—4", "#e0f2fe", "#0369a1", 11, "bold")
    box(ax, 3.15, 7.55, 2.45, 0.85, "时间、单位与数据质量核查", "#ecfeff", "#0e7490", 10, "bold")
    box(ax, 6.05, 7.55, 2.5, 0.85, "定义购电、充放电与储电量", "#eef2ff", "#4338ca", 10, "bold")
    box(ax, 9.0, 7.55, 2.55, 0.85, "建立母线平衡与储能状态关系", "#f5f3ff", "#7c3aed", 10, "bold")
    box(ax, 12.0, 7.55, 3.05, 0.85, "识别各问的信息边界与结算规则", "#fdf2f8", "#be185d", 10, "bold")
    for a, b in [(2.7, 3.15), (5.6, 6.05), (8.55, 9.0), (11.55, 12.0)]:
        arrow(ax, a, 7.98, b, 7.98)

    rows = [
        (6.0, "问题一\n全天曲线已知", "144时段联立\n容量、功率与互斥约束", "确定性MILP", "单日最低费用计划", "#dcfce7", "#15803d"),
        (4.65, "问题二\n0时计划、事后揭示", "历史净负荷预测\n整日残差场景", "严格两阶段模型", "全天计划与紧急购电", "#fef3c7", "#b45309"),
        (3.30, "问题三\n四次光伏预报更新", "固定已执行动作\n更新预测与当前储电量", "滚动MILP", "调整计划与费用账本", "#f3e8ff", "#7e22ce"),
        (1.95, "问题四\n未来实时价格未知", "只用历史价格\n形成因果预测", "嵌入问题二、三", "在线费用与信息价值", "#ffe4e6", "#be123c"),
    ]
    for y, q, step, model, output, fc, ec in rows:
        box(ax, 0.8, y, 2.2, 0.88, q, fc, ec, 10, "bold")
        box(ax, 3.65, y, 3.0, 0.88, step, "#f8fafc", "#64748b", 9.5)
        box(ax, 7.35, y, 2.35, 0.88, model, "#eff6ff", "#2563eb", 10, "bold")
        box(ax, 10.45, y, 2.95, 0.88, output, "#f0fdfa", "#0f766e", 9.5)
        arrow(ax, 3.0, y + 0.44, 3.65, y + 0.44, ec)
        arrow(ax, 6.65, y + 0.44, 7.35, y + 0.44, ec)
        arrow(ax, 9.70, y + 0.44, 10.45, y + 0.44, ec)
        arrow(ax, 13.40, y + 0.44, 14.25, y + 0.44, ec)
        box(ax, 14.25, y, 1.15, 0.88, "结果表\n与图形", "#fff7ed", "#c2410c", 9, "bold")

    # 共同检验闭环
    box(ax, 3.1, 0.45, 3.0, 0.82, "约束残差与充放电互斥检验", "#f1f5f9", "#475569", 9.5, "bold")
    box(ax, 6.55, 0.45, 3.0, 0.82, "费用账本与跨日状态复算", "#f1f5f9", "#475569", 9.5, "bold")
    box(ax, 10.0, 0.45, 3.0, 0.82, "未来信息泄漏与模型对照", "#f1f5f9", "#475569", 9.5, "bold")
    arrow(ax, 6.1, 0.86, 6.55, 0.86)
    arrow(ax, 9.55, 0.86, 10.0, 0.86)
    for x in (14.82,):
        arrow(ax, x, 1.95, 12.95, 1.27, "#64748b")

    ax.text(0.8, 8.65, "公共数据与物理关系", fontsize=10.5, weight="bold", color="#334155")
    ax.text(0.8, 7.12, "四个问题依次形成完整求解闭环", fontsize=10.5, weight="bold", color="#334155")
    ax.text(0.8, 0.72, "统一验证", fontsize=10.5, weight="bold", color="#334155")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
