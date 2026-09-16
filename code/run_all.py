"""统一运行入口：按依赖顺序复现C题全部结果、图表与论文稿。

用法：
    python run_all.py            # 14日冒烟测试，全程数十秒
    python run_all.py --full     # 全年正式回测（Q3/Q4为长任务，约2-3小时）
    python run_all.py --stage solve    # 只跑求解与验证
    python run_all.py --stage paper    # 只跑回填与排版（需已有结果）

各阶段严格串行：后一步依赖前一步写出的 results/ 与 state/agent_outputs/ 文件。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"

# (模块, 说明, 是否仅在全年模式下作为长任务运行)
SOLVE_STEPS = [
    ("q1_model.py", "问题一：确定性MILP、LP下界与无储能基线"),
    ("q2_model.py", "问题二：严格日前两阶段随机MILP全年回测"),
    ("q3_model.py", "问题三：光伏预报更新频率消融与全年滚动回测"),
    ("q4_model.py", "问题四：因果价格策略、完全价格基准与全信息下界"),
]
VERIFY_STEPS = [
    ("verify_results.py", "独立数值复核并生成逐问声明登记表"),
    ("export_result_workbooks.py", "回填附件5要求的五份结果工作簿"),
    ("visualize_results.py", "从已验证明细生成论文图表"),
]
PAPER_STEPS = [
    ("finalize_paper_text.py", "把已验证结果回填进论文Markdown"),
    ("build_paper_docx.py", "生成Word稿"),
    ("build_paper_latex.py", "生成XeLaTeX源（另行编译PDF）"),
]


def run_step(script: str, note: str, extra_args: list[str]) -> None:
    print("\n" + "=" * 68)
    print(f"▶ {script}  ——  {note}")
    print("=" * 68, flush=True)
    started = time.time()
    result = subprocess.run(
        [sys.executable, script, *extra_args], cwd=CODE, check=False
    )
    elapsed = time.time() - started
    if result.returncode != 0:
        raise SystemExit(f"✖ {script} 失败（退出码 {result.returncode}），已中止")
    print(f"✔ {script} 完成，用时 {elapsed:.1f}s", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="C题全流程统一入口")
    parser.add_argument("--full", action="store_true", help="全年回测；缺省为14日冒烟测试")
    parser.add_argument(
        "--stage", choices=["all", "solve", "verify", "paper"], default="all",
        help="只运行指定阶段；paper阶段需已有全年结果",
    )
    args = parser.parse_args()

    if args.stage in ("all", "solve"):
        long_flag = ["--full"] if args.full else []
        for script, note in SOLVE_STEPS:
            # 仅 Q3/Q4 支持 --full；其余脚本按自身缺省运行。
            extra = long_flag if script in {"q3_model.py", "q4_model.py"} else []
            run_step(script, note, extra)
        if not args.full:
            print("\n⚠ 当前为14日冒烟测试。正式结果请运行：python run_all.py --full")

    if args.stage in ("all", "verify"):
        if not args.full and args.stage == "all":
            print("\n(i) 冒烟模式下跳过验证/回填/排版：正式结果需全年数据。")
            return
        for script, note in VERIFY_STEPS:
            run_step(script, note, [])

    if args.stage in ("all", "paper"):
        for script, note in PAPER_STEPS:
            run_step(script, note, [])

    print("\n✅ run_all 全部步骤完成")


if __name__ == "__main__":
    main()
