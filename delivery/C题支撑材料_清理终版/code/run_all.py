"""C题统一运行入口：求解、核验与结果导出。

用法：
    python run_all.py                 # 冒烟求解并核验
    python run_all.py --full          # 全年完整复算并核验
    python run_all.py --check         # 仅核验已有结果
    python run_all.py --stage solve   # 仅运行四问求解程序
    python run_all.py --stage export  # 仅导出结果工作簿与MATLAB数据
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"

SOLVE_STEPS = [
    ("q1_model.py", "问题一确定性调度"),
    ("q2_model.py", "问题二日前两阶段调度"),
    ("q3_model.py", "问题三滚动调度"),
    ("q4_model.py", "问题四实时价格策略"),
]
VERIFY_STEPS = [("verify_results.py", "四问独立数值复核")]
EXPORT_STEPS = [
    ("export_result_workbooks.py", "导出五份结果工作簿"),
    ("export_matlab_visual_data.py", "导出MATLAB绘图数据"),
]


def run_step(script: str, note: str, extra_args: list[str] | None = None) -> None:
    print(f"\n{'=' * 68}\n▶ {script} —— {note}\n{'=' * 68}", flush=True)
    started = time.time()
    result = subprocess.run(
        [sys.executable, script, *(extra_args or [])], cwd=CODE, check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"✖ {script} 失败（退出码 {result.returncode}）")
    print(f"✔ 完成，用时 {time.time() - started:.1f}s", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="C题模型复算与核验")
    parser.add_argument("--full", action="store_true", help="执行全年完整回测")
    parser.add_argument("--check", action="store_true", help="仅核验已有结果")
    parser.add_argument(
        "--stage", choices=["all", "solve", "verify", "export"], default="all"
    )
    args = parser.parse_args()

    (ROOT / "results").mkdir(parents=True, exist_ok=True)
    (ROOT / "state" / "agent_outputs").mkdir(parents=True, exist_ok=True)

    if args.check:
        for item in VERIFY_STEPS:
            run_step(*item)
        print("\n✅ 既有结果核验完成")
        return

    if args.stage in {"all", "solve"}:
        for script, note in SOLVE_STEPS:
            extra = ["--full"] if args.full and script in {"q3_model.py", "q4_model.py"} else []
            run_step(script, note, extra)

    if args.stage in {"all", "verify"}:
        for item in VERIFY_STEPS:
            run_step(*item)

    if args.stage in {"all", "export"}:
        for item in EXPORT_STEPS:
            run_step(*item)

    print("\n✅ 指定流程全部完成")


if __name__ == "__main__":
    main()
