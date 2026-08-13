# -*- coding: utf-8 -*-
"""题目产出归档脚本：把当前一题的完整产出归档到 archive/选题X_日期/，避免多题共用目录互相覆盖。

用法：
    python scripts/archive_problem.py A          # 归档当前产出为 archive/选题A_20260813/
    python scripts/archive_problem.py B 20260812 # 指定题目和日期
    python scripts/archive_problem.py A --reset  # 归档后清空共享产出目录（准备跑下一题）

归档范围：paper/、results/、code/、state/agent_outputs/、delivery/ 五类目录的题相关文件。
公共文件（code/utils.py、data_loader.py、eda.py、scripts/ 等）也会一并快照，保证归档目录自包含可复现。
"""
import os
import re
import sys
import json
import shutil
import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

# 共享产出目录（会被归档快照）
SHARED_DIRS = ["paper", "results", "code", "state", "delivery"]


def detect_problem():
    """从 decision_log.json 检测当前题"""
    try:
        with open(os.path.join("state", "decision_log.json"), encoding="utf-8") as f:
            d = json.load(f)
        p = d.get("metadata", {}).get("problem", "")
        m = re.search(r"([A-D])", p or "")
        return m.group(1) if m else None
    except Exception:
        return None


def archive(problem, date_str=None, reset=False):
    problem = problem.upper()
    assert problem in "ABCD", f"题目必须是 A/B/C/D，收到 {problem}"

    date_str = date_str or datetime.datetime.now().strftime("%Y%m%d")
    archive_root = os.path.join("archive", f"选题{problem}_{date_str}")
    os.makedirs(archive_root, exist_ok=True)

    manifest = {"problem": f"选题{problem}", "date": date_str, "dirs": {}}

    for d in SHARED_DIRS:
        src = d
        if not os.path.isdir(src):
            continue
        dst = os.path.join(archive_root, d)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        # 只复制目录内容，跳过备份/临时子目录
        shutil.copytree(
            src, dst,
            ignore=shutil.ignore_patterns(
                "*.aux", "*.log", "*.out", "*.toc", "*.synctex*",
                "__pycache__", "*.pyc", ".git",
            ),
        )
        n_files = sum(len(fs) for _, _, fs in os.walk(dst))
        manifest["dirs"][d] = n_files
        print(f"  归档 {d}/ → {os.path.relpath(dst)} ({n_files} 个文件)")

    manifest_path = os.path.join(archive_root, "archive_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 归档完成：{archive_root}")
    print(f"   清单：{os.path.relpath(manifest_path)}")

    if reset:
        # 清空共享产出目录（保留目录结构）
        for d in SHARED_DIRS:
            src = d
            if os.path.isdir(src):
                for item in os.listdir(src):
                    p = os.path.join(src, item)
                    if os.path.isdir(p):
                        shutil.rmtree(p)
                    else:
                        os.remove(p)
        print("  已清空共享产出目录，可开始跑下一题")

    return archive_root


if __name__ == "__main__":
    args = sys.argv[1:]
    problem = args[0] if args else detect_problem()
    if not problem:
        print("用法: python scripts/archive_problem.py <A|B|C|D> [日期] [--reset]")
        print("  A/B/C/D 为题目；日期可选（默认今天）；--reset 归档后清空共享目录")
        sys.exit(1)

    date_str = args[1] if len(args) > 1 and not args[1].startswith("--") else None
    reset = "--reset" in args

    print(f"=== 归档选题{problem.upper()} 的产出 ===")
    archive(problem, date_str, reset)
