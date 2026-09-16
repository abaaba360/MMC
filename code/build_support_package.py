"""打包C题支撑材料：代码、结果、图表、AI工具使用详情与README。"""

from __future__ import annotations

import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
RESULTS = ROOT / "results"
STATE_OUTPUTS = ROOT / "state" / "agent_outputs"
PAPER = ROOT / "paper"
DELIVERY = ROOT / "delivery"
AI_DETAIL = ROOT / "state" / "submission_staging" / "AI工具使用详情.pdf"
OUT = DELIVERY / "支撑材料.zip"

MAX_BYTES = 20 * 1024 * 1024

README = """# C题 支撑材料说明

**题目**：微网与外部电网电力调控策略（2026 高教社杯全国大学生数学建模竞赛 C 题）

## 一、目录结构

```
code/                      全部可运行源程序（见下表）
results/submission_results/ 附件5要求的五份结果工作簿 result1/2/3/4-2/4-3.xlsx
results/figures/           论文图表（矢量PDF + 位图PNG）
results/qN_results.json    各问关键结果与验证指标
results/qN_detail.npz      各问逐日/逐时段完整决策明细
results/qN_daily.csv       各问逐日汇总
paper/                     论文Markdown与Word稿
AI工具使用详情.pdf          按2026年国赛规定提交的AI工具使用详情
```

## 二、源程序清单

| 文件 | 作用 |
|---|---|
| `run_all.py` | 统一运行入口，按依赖顺序复现全部结果与论文稿 |
| `common_milp.py` | 确定性MILP统一骨架（母线平衡、SOC转移、容量/功率/互斥约束） |
| `formal_data_loader.py` | 附件1—4读取与单位转换 |
| `data_loader.py` | 附件读取辅助 |
| `q1_model.py` | 问题一：确定性MILP、LP连续松弛下界、无储能基线 |
| `prototype_q1.py` | 问题一最小原型（正式编码前的可行性验证） |
| `causal_forecasts.py` | 因果净负荷/价格预测、残差情景构造与月度选参 |
| `q2_model.py` | 问题二：严格日前两阶段随机MILP |
| `q34_helpers.py` | 问题三/四共用的因果预测、滚动结算与仿真 |
| `q3_model.py` | 问题三：预报更新频率消融与全年滚动回测 |
| `q4_model.py` | 问题四：因果价格策略、完全价格信息基准与全信息下界 |
| `verify_results.py` | 独立数值复核并生成逐问声明登记表 |
| `export_result_workbooks.py` | 回填附件5要求的五份结果工作簿 |
| `visualize_results.py` | 从已验证明细生成论文图表 |
| `finalize_paper_text.py` | 把已验证结果回填进论文Markdown |
| `build_paper_docx.py` | 生成Word稿 |
| `build_paper_latex.py` | 生成XeLaTeX源 |
| `build_support_package.py` | 打包本支撑材料 |
| `prepare_ai_usage_draft.py` | 从真实台账汇总AI使用信息 |
| `build_ai_report_draft.py` | 生成AI工具使用详情草稿 |
| `record_team_confirmation.py` | 记录参赛队真实性确认 |

## 三、运行方式

```bash
cd code
python run_all.py            # 14日冒烟测试，数十秒
python run_all.py --full     # 全年正式回测（Q3/Q4为长任务，约2-3小时）
python run_all.py --stage paper   # 已有结果时只重跑回填与排版
```

依赖：Python 3.11+，numpy、pandas、scipy、matplotlib、openpyxl、pulp、
reportlab、python-docx。原始数据须置于 `problems/选题C_2026正式/附件/`。

## 四、结果可追溯性

论文中每个关键数字均可追溯到 `results/qN_results.json` 的具体字段，
再到 `code/qN_model.py` 的求解函数，最后到附件1—4的原始数据；
`verify_results.py` 独立复算能量平衡、SOC转移、充放电互斥与费用账本。
"""


def collect_payload() -> list[tuple[Path, str]]:
    """返回 (源文件, 压缩包内路径) 列表。"""
    items: list[tuple[Path, str]] = []

    # 全部源程序：Python负责求解与文档复现，MATLAB负责论文数据图绘制。
    for suffix in ("*.py", "*.m"):
        for path in sorted(CODE.glob(suffix)):
            items.append((path, f"code/{path.name}"))

    # AI工具使用详情：规定文件名。
    if AI_DETAIL.exists():
        items.append((AI_DETAIL, "AI工具使用详情.pdf"))

    # 附件5结果工作簿。
    for path in sorted((RESULTS / "submission_results").glob("*.xlsx")):
        items.append((path, f"results/submission_results/{path.name}"))

    # 图表：矢量PDF与位图PNG成对保留。
    for path in sorted((RESULTS / "figures").iterdir()):
        if path.suffix.lower() in {".pdf", ".png"}:
            items.append((path, f"results/figures/{path.name}"))

    # MATLAB终稿图：位图用于Word，矢量PDF用于高质量排版，FIG便于队伍人工编辑。
    matlab_figures = RESULTS / "figures_matlab"
    if matlab_figures.exists():
        for path in sorted(matlab_figures.iterdir()):
            if path.suffix.lower() in {".pdf", ".png", ".fig"}:
                items.append((path, f"results/figures_matlab/{path.name}"))

    # 四问关键结果JSON。Q1/Q2历史程序写入state/agent_outputs，Q3/Q4另有
    # results副本；打包时统一归档到results/，并保证每问恰好一份。
    for question_no in range(1, 5):
        name = f"q{question_no}_results.json"
        candidates = (RESULTS / name, STATE_OUTPUTS / name)
        source = next((path for path in candidates if path.exists()), None)
        if source is None:
            raise FileNotFoundError(f"缺少{name}，无法形成四问完整证据链")
        items.append((source, f"results/{name}"))

    # 逐日汇总与逐时段决策明细。
    for pattern, sub in (("q*_daily.csv", ""),
                         ("q1_detail.csv", ""), ("q*_detail.npz", "")):
        for path in sorted(RESULTS.glob(pattern)):
            items.append((path, f"results/{sub}{path.name}"))

    # 论文正文与Word稿。
    for name in ("论文_C题_第一版.md", "C题论文_第一版.docx", "C题论文_第一版.tex"):
        path = PAPER / name
        if path.exists():
            items.append((path, f"paper/{name}"))

    return items


def main() -> None:
    DELIVERY.mkdir(parents=True, exist_ok=True)
    payload = collect_payload()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("README.md", README)
        for source, arcname in payload:
            archive.write(source, arcname)

    size = OUT.stat().st_size
    print(f"{OUT}")
    print(f"条目数: {len(payload) + 1}  大小: {size / 1024 / 1024:.2f} MB")
    if size > MAX_BYTES:
        raise SystemExit(f"✖ 支撑材料超过20MB限制 ({size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
