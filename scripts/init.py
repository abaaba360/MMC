"""
数学建模工作流 — 初始化脚本
为新选题创建所需的所有目录和状态文件
用法：python scripts/init.py [选题字母]
"""
import json
import os
import sys
import io
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

WORK_DIR = Path(__file__).parent.parent

REQUIRED_DIRS = [
    "state/agent_outputs",
    "code",
    "results/figures",
    "results/tables",
    "paper/paper_sections",
    "delivery",
    "templates"
]


def init_project(problem_letter=None):
    """初始化项目结构"""
    print("=" * 60)
    print("🔧 数学建模工作流 — 项目初始化")
    print("=" * 60)

    # 1. 创建目录结构
    print("\n📁 创建目录结构...")
    for d in REQUIRED_DIRS:
        path = WORK_DIR / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {d}/")

    # 2. 初始化决策日志
    print("\n📋 初始化决策日志...")
    state_file = WORK_DIR / "state" / "decision_log.json"
    state = {
        "metadata": {
            "competition": "CUMCM_2026",
            "problem": problem_letter,
            "mode": "standard",
            "start_time": datetime.now().isoformat(),
            "pipeline_version": "1.0.0"
        },
        "stages": {
            f"S{i}": {"status": "pending" if i > 0 else "in_progress",
                       "score": None, "outputs": [],
                       "started_at": datetime.now().isoformat() if i == 0 else None,
                       "completed_at": None}
            for i in range(10)
        },
        "current_stage": "S0",
        "sub_questions": {},
        "assumptions": {"locked": False, "items": []},
        "symbols": {"locked": False, "items": []},
        "issues": [],
        "review_results": {},
        "rollback_history": []
    }

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"   ✅ state/decision_log.json")

    # 3. 初始化AI使用记录
    print("\n📝 初始化AI使用记录...")
    ledger_file = WORK_DIR / "state" / "ai_usage_ledger.json"
    ledger = {
        "records": [],
        "total_interactions": 0,
        "tool_name": "Claude Code",
        "version": "Anthropic Claude",
        "started_at": datetime.now().isoformat()
    }
    with open(ledger_file, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
    print(f"   ✅ state/ai_usage_ledger.json")

    # 4. 扫描选题
    print("\n🔍 扫描选题...")
    problems_dir = WORK_DIR / "problems"
    if problems_dir.exists():
        for p in sorted(problems_dir.iterdir()):
            if p.is_dir():
                pdfs = list(p.glob("*.pdf"))
                print(f"   📄 {p.name}: {len(pdfs)} 个PDF文件")
    else:
        print("   ⚠️ problems/ 目录不存在，请将赛题数据放入该目录")

    # 5. 检查Python环境
    print("\n🐍 检查Python环境...")
    try:
        import numpy; print(f"   ✅ numpy {numpy.__version__}")
    except ImportError:
        print("   ❌ numpy 未安装")

    try:
        import scipy; print(f"   ✅ scipy {scipy.__version__}")
    except ImportError:
        print("   ❌ scipy 未安装")

    try:
        import pandas; print(f"   ✅ pandas {pandas.__version__}")
    except ImportError:
        print("   ❌ pandas 未安装")

    try:
        import matplotlib; print(f"   ✅ matplotlib {matplotlib.__version__}")
    except ImportError:
        print("   ❌ matplotlib 未安装")

    # 6. 总结
    print("\n" + "=" * 60)
    print("✅ 项目初始化完成！")
    print("=" * 60)
    print(f"""
下一步操作：
1. 将赛题数据放入 problems/ 目录（如已有则跳过）
2. 在Claude Code中说："开始数学建模工作流" 或加载 master-controller skill
3. Master Controller将自动引导你完成从选题到论文交付的全流程

状态文件: state/decision_log.json
AI使用记录: state/ai_usage_ledger.json
质量门禁: python scripts/gates.py all
    """)


if __name__ == "__main__":
    problem = sys.argv[1] if len(sys.argv) > 1 else None
    init_project(problem)
