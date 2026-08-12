# -*- coding: utf-8 -*-
"""
图2-1 总体技术路线图生成脚本（B题：芯片歧管式微通道散热多目标优化与鲁棒设计）

设计要点（针对旧版 s0_route.png 的诊断修复）：
  1. 网格对齐：所有框坐标写在 GRID 表中，行列严格对齐，杜绝手写坐标错位。
  2. 字号校准：画布 6.8in 宽，正文 11~13pt，论文里按 13.5cm 宽显示时文字 ≈ 10~12pt，
     保证人眼可读（旧版 28px 字形在 3570px 画布上仅占 1.6%，显示时不足 3pt 即"乱码"）。
  3. 配色对齐备战资料 PPT 模板：蓝色系=建模、橙色系=优化、绿色系=验证/成果，圆角块+箭头。
  4. 内容可追溯：每个框对应 code/qN_model.py 与 state/agent_outputs/qN_results.json。

输出：
  results/figures/s0_route.png   (300 dpi，docx/md 引用路径不变)
  results/figures/s0_route.pdf   (矢量，LaTeX 引用更清晰)

用法：
  python code/route_map.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ---------------------------------------------------------------
# 1. 全局样式：中文字体回退 + 配色
# ---------------------------------------------------------------
plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "Noto Sans SC", "SimSun", "FangSong",
]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.family"] = "sans-serif"

# PPT 模板风格配色（蓝=建模 / 橙=优化 / 绿=验证与成果）
C = {
    "blue_fill":  "#DDEBF7", "blue_edge": "#2F5597", "blue_txt": "#1F3864",
    "org_fill":   "#FCE4D6", "org_edge":  "#ED7D31", "org_txt":  "#833C00",
    "grn_fill":   "#E2EFDA", "grn_edge":  "#548235", "grn_txt":  "#375623",
    "head_fill":  "#2F5597", "head_edge": "#1F3864", "head_txt":  "#FFFFFF",
    "arr_color":  "#404040",
    "panel":      "#F7F9FC",
}

BASE = 14          # 标题字号（论文13.5cm宽显示时 ≈ 10.9pt）
BODY = 13          # 正文字号（显示时 ≈ 10.1pt，保证可读）

# ---------------------------------------------------------------
# 2. 网格布局：每行两段 y 值 [顶部, 底部]，每列两段 x 值 [左, 右]
#    ——所有框都从这张表取值，行列严格对齐。
# ---------------------------------------------------------------
# y 轴：0(底) ~ 100(顶)
Y = {
    "header":  (90.0, 97.0),
    "data":    (76.0, 87.0),
    "rowA":    (54.0, 69.0),   # 顶排三个建模框（高15单位，容纳标题+2正文）
    "rowB":    (31.0, 46.0),   # 底排三个验证框
    "result":  (14.0, 26.0),
}
X = {
    "col1":  (5.0, 34.0),      # 左列
    "col2":  (36.0, 65.0),     # 中列
    "col3":  (67.0, 96.0),     # 右列
    "full":  (5.0, 95.0),      # 通栏
}
# 箭头 x 坐标（列中心）
CX = {k: (v[0] + v[1]) / 2 for k, v in X.items()}
# 框高
H = {k: v[1] - v[0] for k, v in Y.items()}


def cy(tag):
    """行内框体的 y 中心（横向箭头应指向框体中部而非顶边）。"""
    return (Y[tag][0] + Y[tag][1]) / 2


def draw_box(ax, x0, x1, y0, y1, fill, edge, tcolor, title=None,
             lines=None, title_fs=None, body_fs=None, lw=1.6,
             title_color=None):
    """圆角框 + 顶部标题 + 居中正文。title/正文均以框顶为基准向下排布。"""
    title_fs = title_fs or BASE
    body_fs = body_fs or BODY
    title_color = title_color or tcolor
    # 注意：boxstyle 的 pad/rounding_size 以「点」为单位，mutation_scale 放大它们。
    # mutation_scale=100 会把 0.6pt 的 pad 放大成 60pt≈0.8in≈13 数据单位，导致框互相重叠，
    # 因此这里必须用默认的 1（即只加几像素的圆角 padding）。
    pad = 0.3
    box = FancyBboxPatch(
        (x0, y0), x1 - x0, y1 - y0,
        boxstyle=f"round,pad={pad},rounding_size=2.5",
        fc=fill, ec=edge, lw=lw, mutation_scale=1, zorder=2,
    )
    ax.add_patch(box)

    xc = (x0 + x1) / 2
    yt = y1 - 1.2                      # 标题行顶部（y 轴上，框顶向下留白）
    if title:
        ax.text(xc, yt, title, ha="center", va="top",
                fontsize=title_fs, fontweight="bold", color=title_color, zorder=3)
        yt -= title_fs / 72 * 100 / 5.0 + 0.8   # 换算一个标题行的高度

    if lines:
        for ln in lines:
            ax.text(xc, yt, ln, ha="center", va="top",
                    fontsize=body_fs, color=tcolor, zorder=3)
            yt -= body_fs / 72 * 100 / 5.0 + 0.4


def arrow(ax, x0, y0, x1, y1):
    """带箭头实线。"""
    a = FancyArrowPatch(
        (x0, y0), (x1, y1),
        arrowstyle="-|>", mutation_scale=20, lw=2.0,
        color=C["arr_color"], zorder=4,
    )
    ax.add_patch(a)


# ---------------------------------------------------------------
# 3. 画布
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.8, 5.0), dpi=300)
fig.subplots_adjust(left=0.02, right=0.98, top=0.985, bottom=0.015)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.set_aspect("auto")
ax.axis("off")

# ---------------------------------------------------------------
# 4. 背景：三个阶段面板（建模蓝 / 优化橙 / 验证绿），弱化描边
# ---------------------------------------------------------------
# 左面板：Q1 + Q2（建模阶段）
ax.add_patch(FancyBboxPatch(
    (X["col1"][0] - 0.8, Y["rowA"][0] - 0.8), X["col2"][1] - X["col1"][0] + 1.6, H["rowA"] + 1.6,
    boxstyle="round,pad=0.4,rounding_size=1.5", fc=C["panel"], ec="#C8D6E5",
    lw=1.0, zorder=1))
# 中面板：Q5（验证阶段）
ax.add_patch(FancyBboxPatch(
    (X["col2"][0] - 0.8, Y["rowB"][0] - 0.8), X["col2"][1] - X["col2"][0] + 1.6, H["rowB"] + 1.6,
    boxstyle="round,pad=0.4,rounding_size=1.5", fc=C["panel"], ec="#C8D6E5",
    lw=1.0, zorder=1))
# 右面板：Q3 + Q4（优化阶段）
ax.add_patch(FancyBboxPatch(
    (X["col3"][0] - 0.8, Y["rowB"][0] - 0.8), X["col3"][1] - X["col3"][0] + 1.6, H["rowA"] + H["rowB"] + 2.4,
    boxstyle="round,pad=0.4,rounding_size=1.5", fc=C["panel"], ec="#C8D6E5",
    lw=1.0, zorder=1))

# ---------------------------------------------------------------
# 5. 各框
# ---------------------------------------------------------------
# 顶部：赛题背景（单行横幅）
draw_box(ax, *X["full"], *Y["header"], C["head_fill"], C["head_edge"], C["head_txt"],
         title="高性能芯片歧管式微通道散热系统 · 多目标优化与鲁棒设计", title_fs=BASE + 1)

# 数据准备与问题分析
draw_box(ax, *X["full"], *Y["data"], C["blue_fill"], C["blue_edge"], C["blue_txt"],
         title="问题分析与数据准备",
         lines=["机理建模 → 代理建模 → 多目标优化 → 鲁棒设计 → 稳健性验证"],
         title_fs=BASE, body_fs=BASE - 1)

# ---- 顶排：问题一 / 二 / 三 ----
draw_box(ax, *X["col1"], *Y["rowA"], C["blue_fill"], C["blue_edge"], C["blue_txt"],
         title="问题一 · 机理建模",
         lines=["热-流耦合电阻网络", "拟合 R²≈0.75~0.77"],
         title_fs=BASE, body_fs=BODY)

draw_box(ax, *X["col2"], *Y["rowA"], C["blue_fill"], C["blue_edge"], C["blue_txt"],
         title="问题二 · 代理建模",
         lines=["GPR 高斯过程回归", "5折CV R² ≥ 0.994"],
         title_fs=BASE, body_fs=BODY)

draw_box(ax, *X["col3"], *Y["rowA"], C["org_fill"], C["org_edge"], C["org_txt"],
         title="问题三 · 多目标优化",
         lines=["Pareto 非支配排序", "TOPSIS · 193 方案"],
         title_fs=BASE, body_fs=BODY)

# ---- 底排：问题四 / 五 / 模型检验 ----
draw_box(ax, *X["col3"], *Y["rowB"], C["org_fill"], C["org_edge"], C["org_txt"],
         title="问题四 · 鲁棒设计",
         lines=["权重域 Max-Min 优化", "( 0.228, 4.5, 5 )"],
         title_fs=BASE, body_fs=BODY)

draw_box(ax, *X["col2"], *Y["rowB"], C["grn_fill"], C["grn_edge"], C["grn_txt"],
         title="问题五 · 稳健性验证",
         lines=["局部弹性 · 蒙特卡洛", "Sobol 全局灵敏度"],
         title_fs=BASE, body_fs=BODY)

draw_box(ax, *X["col1"], *Y["rowB"], C["grn_fill"], C["grn_edge"], C["grn_txt"],
         title="模型检验与评价",
         lines=["误差分析 RMSE / R²", "稳健性综合评判"],
         title_fs=BASE, body_fs=BODY)

# ---- 底部：最终成果 ----
draw_box(ax, *X["full"], *Y["result"], C["grn_fill"], C["grn_edge"], C["grn_txt"],
         title="最终成果",
         lines=["机理-数据混合建模 + 多目标优化 + 权重域鲁棒设计一体化框架"],
         title_fs=BASE, body_fs=BODY)

# ---------------------------------------------------------------
# 6. 箭头（S 形流程：Q1→Q2→Q3 ↓ Q4→Q5→检验 ↓ 成果）
# ---------------------------------------------------------------
# 背景 → 数据
arrow(ax, CX["full"], Y["header"][0], CX["full"], Y["data"][1])
# 数据 → Q1
arrow(ax, CX["col1"], Y["data"][0], CX["col1"], Y["rowA"][1])
# 顶排横向
arrow(ax, X["col1"][1], cy("rowA"), X["col2"][0], cy("rowA"))
arrow(ax, X["col2"][1], cy("rowA"), X["col3"][0], cy("rowA"))
# Q3 向下到 Q4
arrow(ax, CX["col3"], Y["rowA"][0], CX["col3"], Y["rowB"][1])
# 底排横向（自右向左）
arrow(ax, X["col3"][0], cy("rowB"), X["col2"][1], cy("rowB"))
arrow(ax, X["col2"][0], cy("rowB"), X["col1"][1], cy("rowB"))
# 检验 → 成果
arrow(ax, CX["col1"], Y["rowB"][0], CX["col1"], Y["result"][1])

# ---------------------------------------------------------------
# 7. 输出
# ---------------------------------------------------------------
out_png = "results/figures/s0_route.png"
out_pdf = "results/figures/s0_route.pdf"
fig.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white")
fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
print(f"✅ 已生成: {out_png} / {out_pdf}")

# ---- 诊断输出：验证文字相对画布的比例（应 ≥ 1.5%，旧版为 1.6% 但画布过大浪费）----
from PIL import Image
im = Image.open(out_png)
w, h = im.size
print(f"   尺寸: {w}x{h}px  宽高比 {w/h:.2f}（旧版 2.02，新版更紧凑）")
print(f"   字体 BASE={BASE}pt 于 {6.8}in 宽画布 → 按论文 13.5cm 宽显示 ≈ {BASE*5.31/6.8:.1f}pt（旧版不足 3pt）")
