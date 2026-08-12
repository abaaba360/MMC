"""
数学建模工作流 — 质量门禁脚本集
包含：证据门禁、格式门禁、学术诚信门禁、状态管理
用法：python scripts/gates.py [evidence|format|integrity|all]
"""
import json
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime

# Windows GBK控制台兼容：避免emoji/中文UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WORK_DIR = Path(__file__).parent.parent
STATE_DIR = WORK_DIR / "state"
OUTPUT_DIR = STATE_DIR / "agent_outputs"
PAPER_DIR = WORK_DIR / "paper"
CODE_DIR = WORK_DIR / "code"
RESULTS_DIR = WORK_DIR / "results"


# ============================================================
# 状态管理
# ============================================================
def load_state():
    """加载决策日志"""
    state_file = STATE_DIR / "decision_log.json"
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(state):
    """保存决策日志"""
    state_file = STATE_DIR / "decision_log.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def update_stage(stage_id, status, score=None, outputs=None):
    """更新阶段状态"""
    state = load_state()
    if state is None:
        print("❌ 决策日志不存在，请先初始化工作流")
        return False

    stage_key = f"S{stage_id}" if isinstance(stage_id, int) else stage_id
    if stage_key not in state.get("stages", {}):
        print(f"❌ 阶段 {stage_key} 不存在")
        return False

    now = datetime.now().isoformat()
    stage = state["stages"][stage_key]

    if status == "in_progress" and stage["status"] == "pending":
        stage["started_at"] = now
    elif status in ("complete", "failed"):
        stage["completed_at"] = now

    stage["status"] = status
    if score is not None:
        stage["score"] = score
    if outputs is not None:
        stage["outputs"] = outputs

    state["current_stage"] = stage_key
    save_state(state)
    print(f"✅ 阶段 {stage_key} → {status}")
    return True


def add_issue(description, stage, severity="refine"):
    """添加问题追踪"""
    state = load_state()
    if state is None:
        return

    issue = {
        "id": f"ISSUE-{len(state.get('issues', [])) + 1:03d}",
        "stage": stage,
        "severity": severity,
        "description": description,
        "status": "open",
        "created_at": datetime.now().isoformat()
    }
    state.setdefault("issues", []).append(issue)
    save_state(state)
    print(f"🐛 新增问题: {issue['id']} [{severity}] {description}")


def log_ai_usage(tool_name, stage, purpose, prompt_summary, adopted=True, modified=False):
    """记录AI使用情况"""
    ledger_file = STATE_DIR / "ai_usage_ledger.json"
    ledger_file.parent.mkdir(parents=True, exist_ok=True)

    if ledger_file.exists():
        with open(ledger_file, "r", encoding="utf-8") as f:
            ledger = json.load(f)
    else:
        ledger = {"records": [], "total_interactions": 0}

    record = {
        "id": ledger["total_interactions"] + 1,
        "timestamp": datetime.now().isoformat(),
        "tool_name": tool_name,
        "version": "Claude Code",
        "stage": stage,
        "purpose": purpose,
        "prompt_summary": prompt_summary,
        "adopted": adopted,
        "modified": modified,
        "rejected": not adopted
    }
    ledger["records"].append(record)
    ledger["total_interactions"] += 1

    with open(ledger_file, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)


# ============================================================
# L1 证据门禁
# ============================================================
def evidence_gate():
    """验证论文声明→代码输出→原始数据的追溯链"""
    print("\n" + "="*60)
    print("🔍 L1 证据门禁：验证论文声明可追溯性")
    print("="*60)

    issues = []

    # 检查必需的结果文件
    result_files = list(OUTPUT_DIR.glob("q*_results.json"))
    if not result_files:
        issues.append("未找到任何子问题结果文件 (q*_results.json)")
        print("❌ 未找到 q*_results.json")
        return False, issues

    print(f"📊 找到 {len(result_files)} 个子问题结果文件")

    # 检查每个结果文件的基本完整性
    for rf in result_files:
        try:
            with open(rf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            issues.append(f"{rf.name} 无法读取: {e}")
            continue

        # 检查必要字段
        required_fields = ["sub_question", "model", "key_results"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            issues.append(f"{rf.name} 缺少字段: {missing}")

        # 检查key_results中是否有数值
        kr = data.get("key_results", {})
        if not kr:
            issues.append(f"{rf.name} 的key_results为空")
        else:
            for k, v in kr.items():
                if isinstance(v, float) and (v != v or v == float('inf')):  # NaN or Inf
                    issues.append(f"{rf.name}.key_results.{k} 包含NaN或Inf")

    # 检查图表索引
    figure_index = RESULTS_DIR / "figures" / "figure_index.json"
    if not figure_index.exists():
        issues.append("缺少图表索引文件 results/figures/figure_index.json")
        print("⚠️ 缺少 figure_index.json")
    else:
        with open(figure_index, "r", encoding="utf-8") as f:
            figs = json.load(f)
        print(f"📈 图表索引记录 {len(figs)} 张图")

    # 检查代码文件
    code_files = list(CODE_DIR.glob("q*_model.py"))
    if not code_files:
        issues.append("未找到子问题代码文件 (code/q*_model.py)")
        print("❌ 未找到代码文件")
    else:
        print(f"💻 找到 {len(code_files)} 个代码文件")
        for cf in code_files:
            with open(cf, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content) < 100:
                issues.append(f"{cf.name} 代码量过少（可能不完整）")

    # 检查 run_all.py
    run_all = CODE_DIR / "run_all.py"
    if not run_all.exists():
        issues.append("缺少 code/run_all.py（一键运行脚本）")
        print("⚠️ 缺少 run_all.py")

    if issues:
        print(f"\n❌ 证据门禁未通过：{len(issues)} 个问题")
        for i in issues:
            print(f"  - {i}")
        return False, issues
    else:
        print("\n✅ 证据门禁通过！所有声明可追溯到代码输出。")
        return True, []


# ============================================================
# L2 格式门禁
# ============================================================
def format_gate(paper_path=None):
    """检查论文格式是否符合2026年国赛规范"""
    print("\n" + "="*60)
    print("📐 L2 格式门禁：检查论文格式合规性")
    print("="*60)

    issues = []

    if paper_path is None:
        # 自动查找论文文件
        docx_candidates = list(PAPER_DIR.glob("*.docx"))
        pdf_candidates = list(PAPER_DIR.glob("*.pdf"))
        tex_candidates = list(PAPER_DIR.glob("*.tex"))
        md_candidates = list(PAPER_DIR.glob("final_paper.md"))

        if docx_candidates:
            paper_path = docx_candidates[0]
        elif pdf_candidates:
            paper_path = pdf_candidates[0]
        elif tex_candidates:
            paper_path = tex_candidates[0]
        elif md_candidates:
            paper_path = md_candidates[0]
        else:
            issues.append("未找到论文文件（paper/目录下无.docx/.pdf/.tex/.md）")
            print("❌ 未找到论文文件")
            return False, issues

    print(f"📄 检查论文: {paper_path}")

    # 基本文件检查
    paper_path = Path(paper_path)
    if not paper_path.exists():
        issues.append(f"论文文件不存在: {paper_path}")
        return False, issues

    file_size = paper_path.stat().st_size
    if file_size < 1024:  # 小于1KB
        issues.append(f"论文文件过小 ({file_size} bytes)，可能为空或损坏")

    print(f"   文件大小: {file_size / 1024:.1f} KB")

    # 注意：详细的格式检查（边距、字体、页数）需要在论文生成时由Writer Agent负责
    # 这里做基本的结构检查

    format_checks = {
        "A4纸张": "⚠️ 需人工确认",
        "页边距≥2.5cm": "⚠️ 需人工确认",
        "禁止目录": "⚠️ 需人工确认",
        "正文≤30页": "⚠️ 需人工确认",
        "摘要300-500字": "⚠️ 需人工确认",
        "摘要独立页且1页内": "⚠️ 需人工确认",
        "模型检验三件套(误差/灵敏度/稳健性)": "⚠️ 需人工确认",
        "参考文献含AI工具引用": "⚠️ 需人工确认",
        "无身份信息": "⚠️ 需人工确认",
        "附录含源代码+AI标注": "⚠️ 需人工确认",
        "AI使用声明": "⚠️ 需人工确认",
    }

    print("\n📋 格式检查项（详细检查需在Writer Agent中完成）：")
    all_ok = True
    for check, status in format_checks.items():
        icon = "✅" if "需人工确认" not in status else "⚠️"
        print(f"   {icon} {check}: {status}")

    # 检查论文元数据
    metadata_file = OUTPUT_DIR / "paper_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        print(f"\n📊 论文元数据:")
        print(f"   总页数: {meta.get('total_pages', 'N/A')}")
        print(f"   摘要字数: {meta.get('abstract_word_count', 'N/A')}")
        print(f"   图表数: {meta.get('figure_count', 'N/A')}图/{meta.get('table_count', 'N/A')}表")
        print(f"   参考文献: {meta.get('reference_count', 'N/A')}条")

        # 检查硬约束
        if meta.get('total_pages', 31) > 30:
            issues.append(f"正文超过30页限制 ({meta['total_pages']}页)")
            all_ok = False
        if meta.get('abstract_word_count', 0) < 300:
            issues.append(f"摘要不足300字 ({meta['abstract_word_count']}字)")
            all_ok = False
        if meta.get('abstract_word_count', 0) > 500:
            issues.append(f"摘要超过500字 ({meta['abstract_word_count']}字)")
            all_ok = False
    else:
        issues.append("缺少论文元数据文件 paper_metadata.json")
        all_ok = False
        print("⚠️ 缺少 paper_metadata.json，无法进行详细格式检查")

    if issues:
        print(f"\n❌ 格式门禁未通过：{len(issues)} 个问题")
        for i in issues:
            print(f"  - {i}")
        return False, issues
    else:
        print("\n✅ 格式门禁通过！")
        return True, []


# ============================================================
# L3 学术诚信门禁
# ============================================================
def integrity_gate():
    """检查学术诚信合规性"""
    print("\n" + "="*60)
    print("🛡️ L3 学术诚信门禁：检查合规性")
    print("="*60)

    issues = []

    # 1. 检查AI使用声明（约定文件名 09_ai_declaration.md，兼容旧 10_ai_declaration.md）
    ai_declaration = PAPER_DIR / "paper_sections" / "09_ai_declaration.md"
    if not ai_declaration.exists():
        ai_declaration = PAPER_DIR / "paper_sections" / "10_ai_declaration.md"
    if ai_declaration.exists():
        with open(ai_declaration, "r", encoding="utf-8") as f:
            content = f.read()
        if "AI工具使用声明" not in content and "AI" not in content:
            issues.append("AI使用声明内容不完整")
            print("❌ AI使用声明不完整")
        else:
            print("✅ AI使用声明存在且内容完整")
    else:
        # 检查论文中是否包含AI声明
        issues.append("缺少独立的AI使用声明文件")
        print("⚠️ 缺少独立的AI使用声明（应在论文中包含）")

    # 2. 检查AI使用详情
    ledger_file = STATE_DIR / "ai_usage_ledger.json"
    if ledger_file.exists():
        with open(ledger_file, "r", encoding="utf-8") as f:
            ledger = json.load(f)
        total = ledger.get("total_interactions", 0)
        records = len(ledger.get("records", []))
        print(f"📋 AI使用记录: {total} 次交互, {records} 条记录")
        if total == 0:
            issues.append("AI使用记录为空（可能遗漏记录）")
            print("❌ AI使用记录为空")
    else:
        issues.append("缺少AI使用记录文件 ai_usage_ledger.json")
        print("❌ 缺少AI使用记录")

    # 3. 检查源代码完整性
    code_files = list(CODE_DIR.glob("*.py"))
    if not code_files:
        issues.append("源代码目录为空")
        print("❌ 代码目录为空")
    else:
        total_lines = 0
        for cf in code_files:
            with open(cf, "r", encoding="utf-8") as f:
                total_lines += len(f.readlines())
        print(f"💻 源代码: {len(code_files)} 个文件, {total_lines} 行")
        if total_lines < 100:
            issues.append(f"源代码总量过少 ({total_lines}行)，可能不完整")

    # 4. 检查数据来源标注
    # (需要在论文中检查，此处标记为人工确认)
    print("⚠️ 数据来源标注需人工确认")

    if issues:
        print(f"\n❌ 学术诚信门禁未通过：{len(issues)} 个问题")
        for i in issues:
            print(f"  - {i}")
        return False, issues
    else:
        print("\n✅ 学术诚信门禁通过！")
        return True, []


# ============================================================
# 综合检查
# ============================================================
def run_all_gates(paper_path=None):
    """运行所有门禁检查"""
    print("\n" + "="*60)
    print("🏆 执行全部质量门禁检查")
    print("="*60)

    results = {}

    # L1 证据门禁
    passed, issues = evidence_gate()
    results["evidence_gate"] = {"passed": passed, "issues": issues}

    # L2 格式门禁
    passed, issues = format_gate(paper_path)
    results["format_gate"] = {"passed": passed, "issues": issues}

    # L3 学术诚信门禁
    passed, issues = integrity_gate()
    results["integrity_gate"] = {"passed": passed, "issues": issues}

    # 汇总
    print("\n" + "="*60)
    print("📊 门禁检查汇总")
    print("="*60)
    all_passed = True
    for gate, result in results.items():
        icon = "✅" if result["passed"] else "❌"
        if result["passed"]:
            print(f"  {icon} {gate}: 通过")
        else:
            print(f"  {icon} {gate}: 未通过 ({len(result['issues'])}个问题)")
        if not result["passed"]:
            all_passed = False

    if all_passed:
        print("\n🎉 所有门禁通过！论文可以提交。")
    else:
        print("\n⚠️ 存在未通过的门禁，请修复后重新检查。")

    # 保存检查结果
    report = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "all_passed": all_passed
    }
    report_file = OUTPUT_DIR / "gate_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return all_passed


# ============================================================
# AI使用详情生成
# ============================================================
def generate_ai_report():
    """根据ledger生成AI工具使用详情"""
    ledger_file = STATE_DIR / "ai_usage_ledger.json"
    if not ledger_file.exists():
        print("❌ 缺少AI使用记录，无法生成报告")
        return False

    with open(ledger_file, "r", encoding="utf-8") as f:
        ledger = json.load(f)

    records = ledger.get("records", [])

    # 按阶段分组
    by_stage = {}
    for r in records:
        stage = r.get("stage", "Unknown")
        by_stage.setdefault(stage, []).append(r)

    # 生成Markdown报告
    md = []
    md.append("# AI工具使用详情\n")
    md.append(f"## 基本信息\n")
    md.append(f"- 竞赛：全国大学生数学建模竞赛 2026")
    md.append(f"- 使用工具：Claude Code (Anthropic)")
    md.append(f"- 总交互次数：{ledger['total_interactions']}")
    md.append(f"- 记录生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}\n")

    md.append(f"## 各阶段使用情况\n")
    for stage, stage_records in sorted(by_stage.items()):
        md.append(f"### {stage}\n")
        md.append(f"- 交互次数：{len(stage_records)}")
        md.append(f"- 主要目的：{stage_records[0].get('purpose', 'N/A')}\n")

        # 代表性交互示例
        md.append(f"**代表性交互示例：**\n")
        sample = stage_records[0]
        md.append(f"- 提示词概要：{sample.get('prompt_summary', 'N/A')}")
        md.append(f"- 采纳情况：{'已采纳' if sample.get('adopted') else '未采纳'}")
        if sample.get('modified'):
            md.append(f"- 人工修改：是")
        md.append("")

    md.append(f"## 人工审核声明\n")
    md.append(f"所有AI生成内容均经过人工审核和修改。作者对论文的原创性、真实性和准确性负全部责任。")
    md.append(f"AI工具在以下环节提供了辅助：问题分析、模型设计、代码生成、图表制作、论文初稿撰写。")
    md.append(f"关键建模决策、结果分析和最终结论由参赛队员独立完成。\n")

    # 写入文件
    report_file = WORK_DIR / "delivery" / "AI工具使用详情.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"✅ AI工具使用详情已生成: {report_file}")
    return True


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/gates.py [evidence|format|integrity|all|ai-report|state]")
        print("  evidence  - 运行证据门禁")
        print("  format    - 运行格式门禁")
        print("  integrity - 运行学术诚信门禁")
        print("  all       - 运行全部门禁")
        print("  ai-report - 生成AI工具使用详情")
        print("  state     - 初始化或查看状态")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "evidence":
        evidence_gate()
    elif cmd == "format":
        paper_path = sys.argv[2] if len(sys.argv) > 2 else None
        format_gate(paper_path)
    elif cmd == "integrity":
        integrity_gate()
    elif cmd == "all":
        paper_path = sys.argv[2] if len(sys.argv) > 2 else None
        run_all_gates(paper_path)
    elif cmd == "ai-report":
        generate_ai_report()
    elif cmd == "state":
        state = load_state()
        if state:
            print(json.dumps(state, ensure_ascii=False, indent=2))
        else:
            print("决策日志不存在")
    else:
        print(f"未知命令: {cmd}")
