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

    # 4. 初始化AI使用详情汇总骨架；真实性确认必须由队伍在终审前填写
    summary_file = WORK_DIR / "state" / "agent_outputs" / "ai_usage_summary.json"
    stages = (
        "赛题理解与问题分析", "模型假设与符号定义", "模型建立与算法设计",
        "模型求解与编程实现", "结果分析与模型检验", "论文撰写与文字润色",
        "其他辅助环节（文献、数据、图表等）",
    )
    modes = ("网页对话框交互", "代码编辑器内嵌AI", "上传文件或数据对话", "AI智能体工作流（多步自动执行）", "其他方式")
    categories = (
        "建模思路与方法建议", "公式推导与理论参考", "代码编写与调试",
        "结果分析与模型评价", "论文核心论述（摘要、结论等）", "其他内容",
    )
    team_led_items = (
        "模型结构与创新点", "公式推导与求解步骤", "程序逻辑与参数设置",
        "结果分析与论文核心论述", "论文撰写与图表制作等",
    )
    summary = {
        "tool_inventory": [],
        "stage_matrix": {name: {"used": False, "purpose": "未使用", "tools": []} for name in stages},
        "prompt_modes": {name: {"used": False, "description": "未使用"} for name in modes},
        "output_categories": {
            name: {"adoption_and_modification": "待根据真实台账汇总", "verification_method": "待核验"}
            for name in categories
        },
        "team_led_confirmation": {
            name: {"team_led": None, "contribution": "待队伍确认"} for name in team_led_items
        },
        "truthfulness_confirmation": {"confirmed_by_team": False, "confirmed_at": None, "statement": ""},
        "representative_record_ids": [],
    }
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"   ✅ state/agent_outputs/ai_usage_summary.json（待队伍终审确认）")

    # 5. 扫描选题
    print("\n🔍 扫描选题...")
    problems_dir = WORK_DIR / "problems"
    if problems_dir.exists():
        for p in sorted(problems_dir.iterdir()):
            if p.is_dir():
                pdfs = list(p.glob("*.pdf"))
                print(f"   📄 {p.name}: {len(pdfs)} 个PDF文件")
    else:
        print("   ⚠️ problems/ 目录不存在，请将赛题数据放入该目录")

    # 6. 检查Python环境
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
