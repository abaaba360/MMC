"""Build the anonymous, minimal and reproducible C-problem support package.

The package intentionally excludes paper drafts, authoring utilities and machine-specific
paths.  It contains only runnable modelling/verification/plotting sources, verified outputs,
the AI-use report, and a concise run guide.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "state" / "submission_staging" / "support"
DELIVERY = ROOT / "delivery"
ZIP_PATH = DELIVERY / "支撑材料.zip"


SOURCE_MAP = {
    "q1_model.py": "Q1.py",
    "q2_model.py": "Q2.py",
    "q3_model.py": "Q3.py",
    "q4_model.py": "Q4.py",
    "common_milp.py": "common.py",
    "data_loader.py": "data_q1.py",
    "formal_data_loader.py": "data.py",
    "causal_forecasts.py": "forecast.py",
    "q34_helpers.py": "rolling.py",
    "verify_results.py": "check.py",
    "export_result_workbooks.py": "export.py",
    "export_matlab_visual_data.py": "export_matlab.py",
    "plot_c_paper_figures_matlab.m": "plot_figures.m",
    "plot_q1_dispatch_matlab_preview.m": "plot_q1.m",
}

IMPORT_REPLACEMENTS = {
    "common_milp": "common",
    "data_loader": "data_q1",
    "formal_data_loader": "data",
    "causal_forecasts": "forecast",
    "q34_helpers": "rolling",
    "q2_model": "Q2",
}

FIGURE_MAP = {
    "paper_overall_flowchart.png": "图2-1_总体建模流程.png",
    "q1_dispatch_matlab_awardstyle.png": "图6-1_典型日调度与储能状态.png",
    "q2_representative_days_matlab.png": "图7-1_代表日前预测与紧急购电.png",
    "q2_monthly_cost_emergency_matlab.png": "图7-2_月度费用与紧急购电量.png",
    "q2_soc_continuity_matlab.png": "图7-3_跨日储能状态连续性.png",
    "q3_update_ablation_matlab.png": "图8-1_预报更新频率对比.png",
    "q3_forecast_updates_matlab.png": "图8-2_滚动预测修正效果.png",
    "q4_information_value_matlab.png": "图9-1_不同信息条件费用对比.png",
}

RESULT_FILES = [
    "result1.xlsx", "result2.xlsx", "result3.xlsx", "result4-2.xlsx", "result4-3.xlsx",
    "q1_detail.csv", "q2_detail.npz",
    "q3_daily.csv", "q3_detail.npz", "q3_results.json", "q4_daily.csv",
    "q4_detail.npz", "q4_results.json",
]


def reset_stage() -> None:
    expected_parent = (ROOT / "state" / "submission_staging").resolve()
    if STAGE.resolve().parent != expected_parent:
        raise RuntimeError(f"Unsafe staging target: {STAGE}")
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / "results" / "matlab_plot_data").mkdir(parents=True)
    (STAGE / "figures").mkdir(parents=True)


def compact(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+(?=\n)", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip() + "\n"


def transform_python(name: str, text: str) -> str:
    text = text.replace("Path(__file__).resolve().parents[1]", "Path(__file__).resolve().parent")
    text = text.replace('ROOT / "problems" / "选题C_2026正式" / "附件"', 'ROOT / "附件"')
    text = text.replace('ROOT / "state" / "agent_outputs"', 'ROOT / "results"')
    text = text.replace('"problems/选题C_2026正式/附件/附件1.xlsx"', '"附件/附件1.xlsx"')
    text = text.replace("problems/选题C_2026正式/附件/", "附件/")
    text = text.replace('ROOT = Path(r"D:\\数模工作流")', 'ROOT = Path(__file__).resolve().parent')
    text = text.replace('TEMPLATE_DIR = ROOT / "problems" / "选题C_2026正式" / "附件" / "附件5"',
                        'TEMPLATE_DIR = ROOT / "附件" / "附件5"')
    for old, new in IMPORT_REPLACEMENTS.items():
        text = re.sub(rf"\bfrom {re.escape(old)}\b", f"from {new}", text)
        text = re.sub(rf"\bimport {re.escape(old)}\b", f"import {new}", text)
    if name == "q2_model.py":
        text = text.replace('STATE_DIR = ROOT / "results"', 'STATE_DIR = RESULTS_DIR')
    if name == "q3_model.py":
        text = text.replace('STATE_OUTPUTS = ROOT / "results"', 'STATE_OUTPUTS = RESULTS')
    if name == "q4_model.py":
        text = text.replace('STATE_OUTPUTS = ROOT / "results"', 'STATE_OUTPUTS = RESULTS')
    if name == "verify_results.py":
        text = text.replace("import numpy as np\n", "import numpy as np\nimport pandas as pd\n")
        text = text.replace(
            "def sha(path: Path) -> str:\n    h = hashlib.sha256(path.read_bytes()).hexdigest()\n    return h.upper()",
            "def sha(path: Path) -> str:\n    if not path.exists():\n        return '赛题原始附件未随支撑材料重复提交'\n    h = hashlib.sha256(path.read_bytes()).hexdigest()\n    return h.upper()",
        )
        old_q3 = '''    from rolling import load_c_data
    data = load_c_data(DATA)
    balance = g + data.pv_actual[:len(dates)] + d + r - data.load[:len(dates)] - c - w
    checks = {
        "365_days_present": len(dates) == 365,
        "official_window_334_days": int(np.sum(dates >= "2025-02-01")) == 334,
        "actual_balance_residual_le_1e-6": float(np.max(np.abs(balance))) <= 1e-6,'''
        new_q3 = '''    # 原始赛题附件按竞赛要求不重复打包；供需平衡以正式求解时保存的逐日最大残差复核。
    balance_residual = np.asarray(z["max_balance_residual"], dtype=float)
    checks = {
        "365_days_present": len(dates) == 365,
        "official_window_334_days": int(np.sum(dates >= "2025-02-01")) == 334,
        "actual_balance_residual_le_1e-6": float(np.max(np.abs(balance_residual))) <= 1e-6,'''
        text = text.replace(old_q3, new_q3)
        q1_func = '''\n\ndef verify_q1():
    detail = pd.read_csv(RESULTS / "q1_detail.csv")
    report = json.loads((RESULTS / "q1_results.json").read_text(encoding="utf-8"))
    balance = detail["grid_kwh"] + detail["pv_kwh"] + detail["discharge_kwh"] - detail["load_kwh"] - detail["charge_kwh"] - detail["curtailment_kwh"]
    soc_step = detail["soc_end_kwh"] - detail["soc_start_kwh"] - 0.9 * detail["charge_kwh"] + detail["discharge_kwh"] / 0.9
    checks = {
        "144_intervals_present": len(detail) == 144,
        "balance_residual_le_1e-6": float(np.max(np.abs(balance))) <= 1e-6,
        "soc_transition_residual_le_1e-6": float(np.max(np.abs(soc_step))) <= 1e-6,
        "soc_bounds": float(detail[["soc_start_kwh", "soc_end_kwh"]].min().min()) >= 1200 - 1e-6 and float(detail[["soc_start_kwh", "soc_end_kwh"]].max().max()) <= 10800 + 1e-6,
        "charge_discharge_mutex": int(np.sum((detail["charge_kwh"] > 1e-7) & (detail["discharge_kwh"] > 1e-7))) == 0,
        "objective_matches_json": abs(float((detail["price_yuan_per_kwh"] * detail["grid_kwh"]).sum()) - float(report["milp"]["objective_yuan"])) <= 1e-5,
    }
    write_json(STATE / "q1_verification.json", {"status": "passed" if all(checks.values()) else "failed", "checks": checks})
\n'''
        text = text.replace("\ndef verify_q2():", q1_func + "\ndef verify_q2():")
        text = text.replace("    verify_q2(); verify_q3(); verify_q4()", "    verify_q1(); verify_q2(); verify_q3(); verify_q4()")
    return compact(text)


def transform_matlab(name: str, text: str) -> str:
    text = text.replace("fileparts(fileparts(mfilename('fullpath')))", "fileparts(mfilename('fullpath'))")
    text = text.replace("D:/数模工作流/code/plot_q1_dispatch_matlab_preview.m", "plot_q1.m")
    replacements = {
        "q1_dispatch_matlab_awardstyle": "图6-1_典型日调度与储能状态",
        "q2_representative_days_matlab": "图7-1_代表日前预测与紧急购电",
        "q2_monthly_cost_emergency_matlab": "图7-2_月度费用与紧急购电量",
        "q2_soc_continuity_matlab": "图7-3_跨日储能状态连续性",
        "q3_update_ablation_matlab": "图8-1_预报更新频率对比",
        "q3_forecast_updates_matlab": "图8-2_滚动预测修正效果",
        "q4_information_value_matlab": "图9-1_不同信息条件费用对比",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return compact(text)


def write_sources() -> None:
    for src_name, out_name in SOURCE_MAP.items():
        src = ROOT / "code" / src_name
        text = src.read_text(encoding="utf-8")
        if src.suffix == ".py":
            text = transform_python(src_name, text)
        else:
            text = transform_matlab(src_name, text)
        (STAGE / out_name).write_text(text, encoding="utf-8")

    run_all = '''"""统一运行入口。评阅时建议先运行 --check；完整复算需要赛题附件。"""
from __future__ import annotations
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(script: str, *args: str) -> None:
    start = time.time()
    print(f"\\n>>> {script}", flush=True)
    result = subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT)
    if result.returncode:
        raise SystemExit(f"{script} 运行失败，退出码 {result.returncode}")
    print(f"完成，用时 {time.time()-start:.1f}s", flush=True)

def main() -> None:
    parser = argparse.ArgumentParser(description="2026 C题程序统一入口")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="核验压缩包内既有结果")
    group.add_argument("--full", action="store_true", help="利用附件1—5完整复算")
    args = parser.parse_args()
    if args.check or not args.full:
        run("check.py")
        return
    for script in ("Q1.py", "Q2.py"):
        run(script)
    for script in ("Q3.py", "Q4.py"):
        run(script, "--full")
    for script in ("check.py", "export.py", "export_matlab.py"):
        run(script)
    print("数值结果已生成。MATLAB图请运行 plot_q1.m 和 plot_figures.m。")

if __name__ == "__main__":
    main()
'''
    (STAGE / "run_all.py").write_text(run_all, encoding="utf-8")


def copy_results() -> None:
    result_dir = STAGE / "results"
    for name in RESULT_FILES:
        src = ROOT / "results" / name
        if not src.exists() and name.startswith("result") and name.endswith(".xlsx"):
            src = ROOT / "results" / "submission_results" / name
        if src.exists():
            shutil.copy2(src, result_dir / name)
    for q in ("q1_results.json", "q2_results.json"):
        src = ROOT / "state" / "agent_outputs" / q
        if src.exists():
            target = result_dir / q
            shutil.copy2(src, target)
            if q == "q1_results.json":
                text = target.read_text(encoding="utf-8").replace("problems/选题C_2026正式/附件/", "附件/")
                target.write_text(text, encoding="utf-8")
    for src in (ROOT / "results" / "matlab_plot_data").glob("*.csv"):
        shutil.copy2(src, result_dir / "matlab_plot_data" / src.name)


def copy_figures() -> None:
    for source_name, chinese_name in FIGURE_MAP.items():
        if source_name == "paper_overall_flowchart.png":
            src = ROOT / "results" / "figures" / source_name
        else:
            src = ROOT / "results" / "figures_matlab" / source_name
        if not src.exists():
            raise FileNotFoundError(src)
        shutil.copy2(src, STAGE / "figures" / chinese_name)


def write_meta() -> None:
    req = "numpy\npandas\nscipy\nopenpyxl\nmatplotlib\n"
    (STAGE / "requirements.txt").write_text(req, encoding="utf-8")
    guide = """2026 C题代码运行说明

一、目录说明
Q1.py—Q4.py分别对应四个问题；common.py、data.py、data_q1.py、forecast.py、rolling.py为公共模块；check.py用于独立核验；export.py回填附件5结果表；export_matlab.py导出绘图数据；plot_q1.m、plot_figures.m为MATLAB绘图程序。results存放可核验中间结果和最终结果，figures存放论文所用图片。

二、环境
Python 3.11及以上。安装依赖：python -m pip install -r requirements.txt。MATLAB建议R2022b及以上。

三、快速核验
解压后在本目录执行：python run_all.py --check。该命令直接核验压缩包内结果，不需要赛题原始附件。

四、完整复算
按照竞赛规定，支撑材料不重复提供赛题原始数据。请把赛题“附件”文件夹完整复制到本目录，使附件1.xlsx—附件4.xlsx及附件5模板保持原名，然后执行：python run_all.py --full。全年Q3、Q4滚动回测计算量较大，运行时间取决于计算机配置。

五、图表复现
数值复算后，在MATLAB当前文件夹设为本目录，依次运行 plot_q1.m 与 plot_figures.m。图片输出到 results/figures_matlab；压缩包内 figures 文件夹保存的是论文实际采用的中文命名版本。

六、一致性说明
论文中的费用、电量、SOC和信息价值数据均可由results内JSON、NPZ、CSV及五份结果工作簿交叉核验。程序及文件不含参赛者、学校、赛区或本机绝对路径信息。
"""
    (STAGE / "代码运行说明.txt").write_text(guide, encoding="utf-8")

    candidates = [
        DELIVERY / "AI工具使用详情.pdf",
        ROOT / "paper" / "AI工具使用详情.pdf",
        ROOT / "archive" / "提交前备份_20260912" / "AI工具使用详情_独立备份.pdf",
    ]
    ai_src = next((path for path in candidates if path.exists()), None)
    if ai_src is None:
        raise FileNotFoundError("AI工具使用详情.pdf")
    shutil.copy2(ai_src, STAGE / "AI工具使用详情.pdf")

def write_manifest() -> None:
    manifest = []
    for path in sorted(STAGE.rglob("*")):
        if path.is_file() and path.name != "文件清单.json":
            manifest.append({"file": path.relative_to(STAGE).as_posix(), "bytes": path.stat().st_size})
    (STAGE / "文件清单.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def scan_sensitive() -> None:
    forbidden = ["wxid_", "微信聊天记录", "D:\\数模工作流", "C:\\Users\\", "zhangfengyi"]
    hits = []
    for path in STAGE.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".py", ".m", ".txt", ".json", ".csv"}:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            for token in forbidden:
                if token.lower() in text.lower() or token.lower() in path.as_posix().lower():
                    hits.append(f"{path.relative_to(STAGE)}: {token}")
    if hits:
        raise RuntimeError("Sensitive paths remain:\n" + "\n".join(hits))


def build_zip() -> None:
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(STAGE).as_posix())
    if ZIP_PATH.stat().st_size > 20 * 1024 * 1024:
        raise RuntimeError(f"支撑材料超过20MB: {ZIP_PATH.stat().st_size}")


def main() -> None:
    reset_stage()
    write_sources()
    copy_results()
    copy_figures()
    write_meta()
    subprocess.run([sys.executable, "run_all.py", "--check"], cwd=STAGE, check=True)
    write_manifest()
    scan_sensitive()
    build_zip()
    print(f"stage={STAGE}")
    print(f"zip={ZIP_PATH}")
    print(f"bytes={ZIP_PATH.stat().st_size}")


if __name__ == "__main__":
    main()
