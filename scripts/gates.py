"""
数学建模工作流 — 质量门禁脚本集
包含：逻辑合约、证据、格式、学术诚信门禁与状态管理
用法：python scripts/gates.py [preflight|logic|qgate|evidence|format|integrity|all]
"""
import json
import os
import sys
import hashlib
import zipfile
from html import escape
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

PREFLIGHT_REQUIRED_FILES = [
    "AGENTS.md",
    ".agents/skills/master-controller/SKILL.md",
    ".agents/skills/analyst/SKILL.md",
    ".agents/skills/modeler/SKILL.md",
    ".agents/skills/coder/SKILL.md",
    ".agents/skills/verifier/SKILL.md",
    ".agents/skills/writer/SKILL.md",
    ".agents/skills/reviewer/SKILL.md",
    "references/2026最新资料吸收与正式赛题执行规范.md",
    "references/2026_AI工具使用详情模板填写规范.md",
]

AI_STAGE_NAMES = (
    "赛题理解与问题分析", "模型假设与符号定义", "模型建立与算法设计",
    "模型求解与编程实现", "结果分析与模型检验", "论文撰写与文字润色",
    "其他辅助环节（文献、数据、图表等）",
)
AI_PROMPT_MODES = (
    "网页对话框交互", "代码编辑器内嵌AI", "上传文件或数据对话",
    "AI智能体工作流（多步自动执行）", "其他方式",
)
AI_OUTPUT_CATEGORIES = (
    "建模思路与方法建议", "公式推导与理论参考", "代码编写与调试",
    "结果分析与模型评价", "论文核心论述（摘要、结论等）", "其他内容",
)
AI_TEAM_LED_ITEMS = (
    "模型结构与创新点", "公式推导与求解步骤", "程序逻辑与参数设置",
    "结果分析与论文核心论述", "论文撰写与图表制作等",
)
AI_DISPOSITIONS = {"direct_adopt", "modified_adopt", "rejected"}


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


def log_ai_usage(tool_name, tool_version, stage, purpose, prompt_summary, process_summary,
                 adopted=True, modified=False, verification_method="", verification_result="",
                 use_mode="", response_core="", disposition="", modification_details="",
                 rejection_reason="", evidence_paths=None, is_representative=False,
                 sensitive_data_redacted=True):
    """记录AI使用情况"""
    ledger_file = STATE_DIR / "ai_usage_ledger.json"
    ledger_file.parent.mkdir(parents=True, exist_ok=True)

    if ledger_file.exists():
        with open(ledger_file, "r", encoding="utf-8") as f:
            ledger = json.load(f)
    else:
        ledger = {"records": [], "total_interactions": 0}

    if not disposition:
        disposition = "rejected" if not adopted else ("modified_adopt" if modified else "direct_adopt")
    record = {
        "id": ledger["total_interactions"] + 1,
        "timestamp": datetime.now().isoformat(),
        "tool_name": tool_name,
        "tool_version": tool_version,
        "version": tool_version,
        "stage": stage,
        "purpose": purpose,
        "use_mode": use_mode,
        "prompt_summary": prompt_summary,
        "process_summary": process_summary,
        "response_core": response_core,
        "disposition": disposition,
        "adopted": adopted,
        "modified": modified,
        "rejected": not adopted,
        "modification_details": modification_details,
        "rejection_reason": rejection_reason,
        "verification_method": verification_method,
        "verification_result": verification_result,
        "evidence_paths": evidence_paths or [],
        "is_representative": bool(is_representative),
        "sensitive_data_redacted": bool(sensitive_data_redacted),
    }
    ledger["records"].append(record)
    ledger["total_interactions"] += 1

    with open(ledger_file, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_json_path(data, path):
    """解析仅含对象键和数组下标的简单JSONPath，如 $.key_results.items[0].value。"""
    if not isinstance(path, str) or not path.startswith("$."):
        raise ValueError("JSONPath必须以$.开头")
    current = data
    for part in path[2:].split("."):
        while "[" in part:
            key, rest = part.split("[", 1)
            if key:
                current = current[key]
            index_text, part = rest.split("]", 1)
            current = current[int(index_text)]
        if part:
            current = current[part]
    return current


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preflight_gate():
    """验证主Agent已加载当前版本的全部必读Skill与规则，防止使用旧记忆开题。"""
    print("\n" + "="*60)
    print("📚 Skill启动预检：最新规则与Agent定义")
    print("="*60)
    issues = []
    manifest_path = OUTPUT_DIR / "skill_preflight.json"
    if not manifest_path.exists():
        issues.append("缺少 skill_preflight.json；主Agent尚未完成最新Skill启动预读")
        print("❌ Skill启动预检未通过")
        return False, issues
    try:
        manifest = _load_json(manifest_path)
    except (json.JSONDecodeError, OSError) as exc:
        return False, [f"skill_preflight.json 无法读取: {exc}"]

    if manifest.get("acknowledged") is not True:
        issues.append("缺少 acknowledged=true")
    if manifest.get("main_agent_read_complete") is not True:
        issues.append("主Agent未确认亲自完整读取")
    if manifest.get("formal_mode") is not True:
        issues.append("formal_mode必须为true")
    if manifest.get("competition_year") != 2026:
        issues.append("competition_year必须为2026")
    checked_at = manifest.get("official_rules_checked_at")
    try:
        checked_time = datetime.fromisoformat(checked_at)
        current_time = datetime.now(checked_time.tzinfo) if checked_time.tzinfo else datetime.now()
        age_days = (current_time - checked_time).total_seconds() / 86400
        if age_days < -1 or age_days > 7:
            issues.append("官方规则核对时间距当前超过7天或位于未来")
    except (TypeError, ValueError):
        issues.append("official_rules_checked_at必须是ISO时间")

    records = {}
    for record in manifest.get("files", []):
        rel = str(record.get("path", "")).replace("\\", "/")
        if rel.startswith("./"):
            rel = rel[2:]
        if rel:
            records[rel.lower()] = record
    for rel in PREFLIGHT_REQUIRED_FILES:
        path = WORK_DIR / Path(rel)
        key = rel.replace("\\", "/").lower()
        if not path.exists():
            issues.append(f"必读文件不存在: {rel}")
            continue
        record = records.get(key)
        if not record:
            issues.append(f"预检清单缺少: {rel}")
            continue
        if record.get("read_complete") is not True:
            issues.append(f"未完整读取: {rel}")
        actual_hash = _sha256_file(path)
        if str(record.get("sha256", "")).lower() != actual_hash:
            issues.append(f"文件已变化，必须重新读取: {rel}")

    if issues:
        print(f"❌ Skill启动预检未通过：{len(issues)} 个问题")
        for issue in issues:
            print(f"  - {issue}")
        return False, issues
    print("✅ 最新Skill与规则已由主Agent完整加载，文件哈希有效")
    return True, []


def logic_gate():
    """S2G/S3G/S4G：正式编码前验证题目契约、模型生长和最小原型。"""
    print("\n" + "="*60)
    print("🧭 逻辑合约门禁：题目→结构→模型→原型")
    print("="*60)
    issues = []
    preflight_ok, preflight_issues = preflight_gate()
    if not preflight_ok:
        issues.extend(f"启动预检: {issue}" for issue in preflight_issues)
    required = {
        "requirement_ledger.json": ["requirements"],
        "model_growth_map.json": ["sub_questions"],
        "model_route_decision.json": ["decisions"],
        "user_model_selection.json": ["selections", "confirmed_by_team"],
        "argument_map.json": ["sub_questions"],
        "interface_contracts.json": ["interfaces"],
        "prototype_review.json": ["status"],
    }
    loaded = {}
    for name, keys in required.items():
        path = OUTPUT_DIR / name
        if not path.exists():
            issues.append(f"缺少 {name}")
            continue
        try:
            loaded[name] = _load_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"{name} 无法读取: {exc}")
            continue
        missing = [key for key in keys if key not in loaded[name]]
        if missing:
            issues.append(f"{name} 缺少字段: {missing}")

    ledger = loaded.get("requirement_ledger.json", {})
    requirements = ledger.get("requirements", [])
    if not requirements:
        issues.append("requirement_ledger没有题目要求")
    for item in requirements:
        for key in ("requirement_id", "source_clause", "required_output", "acceptance_test"):
            if not item.get(key):
                issues.append(f"题目要求缺少{key}: {item.get('requirement_id', '<unknown>')}")

    prototype = loaded.get("prototype_review.json", {})
    if prototype and prototype.get("status") != "passed":
        issues.append("最小原型尚未通过")
    if prototype and prototype.get("hard_issues"):
        issues.append("最小原型仍有未关闭的硬问题")

    growth_items = loaded.get("model_growth_map.json", {}).get("sub_questions", [])
    if not growth_items:
        issues.append("model_growth_map没有子问题")
    for item in growth_items:
        qid = item.get("sub_question_id", "<unknown>")
        if not item.get("central_mechanism"):
            issues.append(f"{qid} 缺少中心机制")
        signals = item.get("problem_signals", [])
        if not signals:
            issues.append(f"{qid} 缺少题干事实→数学结构→模型部件")
        for signal in signals:
            for key in ("observation", "mathematical_implication", "model_component"):
                if not signal.get(key):
                    issues.append(f"{qid} 的problem_signal缺少 {key}")

    route_items = loaded.get("model_route_decision.json", {}).get("decisions", [])
    if not route_items:
        issues.append("model_route_decision没有路线决策")
    route_fields = ("sub_question_id", "selected", "baseline", "why_not_simpler",
                    "identifiability_check", "falsification_test", "failure_trigger",
                    "solver", "time_complexity", "ablation_plan", "elimination_rationale")
    for item in route_items:
        qid = item.get("sub_question_id", "<unknown>")
        for key in route_fields:
            if not item.get(key):
                issues.append(f"{qid} 路线决策缺少 {key}")

    selection = loaded.get("user_model_selection.json", {})
    if selection and selection.get("confirmed_by_team") is not True:
        issues.append("候选模型尚未由团队确认")
    if selection and not selection.get("confirmed_at"):
        issues.append("团队模型选择缺少 confirmed_at")
    selected_qids = {item.get("sub_question_id") for item in selection.get("selections", [])}
    route_qids = {item.get("sub_question_id") for item in route_items}
    if route_qids and selected_qids != route_qids:
        issues.append(f"团队确认覆盖与路线决策不一致: selected={selected_qids}, routes={route_qids}")

    argument_items = loaded.get("argument_map.json", {}).get("sub_questions", [])
    argument_fields = ("sub_question_id", "requirement_ids", "claims", "model_propositions",
                       "expected_evidence", "validation", "conclusion_boundary")
    if not argument_items:
        issues.append("argument_map没有子问题论证骨架")
    for item in argument_items:
        qid = item.get("sub_question_id", "<unknown>")
        for key in argument_fields:
            if not item.get(key):
                issues.append(f"{qid} 论证骨架缺少 {key}")

    interfaces = loaded.get("interface_contracts.json", {}).get("interfaces", [])
    for item in interfaces:
        iid = item.get("interface_id", "<unknown>")
        for key in ("interface_id", "upstream", "downstream", "fields", "status"):
            if not item.get(key):
                issues.append(f"接口 {iid} 缺少 {key}")
        if item.get("status") != "passed":
            issues.append(f"接口 {iid} 尚未通过")
        for field in item.get("fields", []):
            for key in ("name", "unit", "dtype_or_shape", "valid_range", "semantics"):
                if key not in field or field.get(key) in (None, ""):
                    issues.append(f"接口 {iid} 字段缺少 {key}")

    if issues:
        print(f"❌ 逻辑合约门禁未通过：{len(issues)} 个问题")
        for issue in issues:
            print(f"  - {issue}")
        return False, issues
    print("✅ 逻辑合约门禁通过")
    return True, []


# ============================================================
# L1 证据门禁
# ============================================================
def evidence_gate():
    """验证requirement→claim→结果→代码→数据→图表/验证的追溯链。"""
    print("\n" + "="*60)
    print("🔍 L1 证据门禁：验证论文声明可追溯性")
    print("="*60)

    issues = []

    result_files = list(OUTPUT_DIR.glob("q*_results.json"))
    if not result_files:
        issues.append("未找到任何子问题结果文件 (q*_results.json)")
        print("❌ 未找到 q*_results.json")
        return False, issues

    claim_files = list(OUTPUT_DIR.glob("q*_claim_registry.json"))
    if not claim_files:
        issues.append("缺少 q*_claim_registry.json，不能证明论文声明可追溯")
    print(f"📊 找到 {len(result_files)} 个结果文件，{len(claim_files)} 个声明登记表")

    result_by_q = {}
    for path in result_files:
        try:
            data = _load_json(path)
            qid = str(data.get("sub_question") or path.stem.split("_")[0]).upper()
            result_by_q[qid] = (path, data)
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"{path.name} 无法读取: {exc}")

    registry_qids = set()

    for registry_path in claim_files:
        try:
            registry = _load_json(registry_path)
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"{registry_path.name} 无法读取: {exc}")
            continue
        claims = registry.get("claims", [])
        if not claims:
            issues.append(f"{registry_path.name} 没有claims")
            continue
        qid = str(registry.get("sub_question") or registry_path.stem.split("_")[0]).upper()
        registry_qids.add(qid)
        result_entry = result_by_q.get(qid)
        if not result_entry:
            issues.append(f"{registry_path.name} 找不到对应结果文件")
            continue
        _, result_data = result_entry
        for claim in claims:
            cid = claim.get("claim_id", "<unknown>")
            for key in ("requirement_id", "result_json_path", "code_symbol", "unit", "validation_test", "status"):
                if not claim.get(key):
                    issues.append(f"{cid} 缺少 {key}")
            if claim.get("status") != "verified":
                issues.append(f"{cid} 尚未验证")
            try:
                value = _resolve_json_path(result_data, claim.get("result_json_path", ""))
                if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
                    issues.append(f"{cid} 指向NaN/Inf")
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                issues.append(f"{cid} 结果路径无效: {exc}")
            symbol = claim.get("code_symbol", "")
            code_matches = []
            for code_path in CODE_DIR.rglob("*"):
                if code_path.suffix.lower() not in {".py", ".m", ".r", ".jl", ".ipynb"}:
                    continue
                try:
                    if symbol and symbol in code_path.read_text(encoding="utf-8", errors="ignore"):
                        code_matches.append(code_path)
                except OSError:
                    pass
            if symbol and not code_matches:
                issues.append(f"{cid} 在源代码中找不到符号 {symbol}")
            if not claim.get("raw_input_hashes"):
                issues.append(f"{cid} 缺少原始输入哈希")
            figure = claim.get("figure_or_table")
            if figure and not any(p.stem == Path(str(figure)).stem for p in RESULTS_DIR.rglob("*")):
                issues.append(f"{cid} 绑定的图表不存在: {figure}")

    for qid in result_by_q:
        if qid not in registry_qids:
            issues.append(f"{qid} 有结果文件但缺少对应声明登记表")

    if issues:
        print(f"\n❌ 证据门禁未通过：{len(issues)} 个问题")
        for i in issues:
            print(f"  - {i}")
        return False, issues
    else:
        print("\n✅ 证据门禁通过：所有已登记声明的追溯字段和目标均有效。")
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
        # 终审优先检查实际交付文件；尚未打包时才退回paper/中的候选稿。
        delivery_dir = WORK_DIR / "delivery"
        delivery_candidates = []
        if delivery_dir.exists():
            delivery_candidates = sorted(
                p for p in delivery_dir.iterdir()
                if p.is_file() and p.suffix.lower() in {".pdf", ".docx"}
                and p.name != "AI工具使用详情.pdf"
            )
        docx_candidates = sorted(PAPER_DIR.glob("*.docx"))
        pdf_candidates = sorted(PAPER_DIR.glob("*.pdf"))

        if len(delivery_candidates) == 1:
            paper_path = delivery_candidates[0]
        elif len(delivery_candidates) > 1:
            issues.append("delivery/中有多份电子论文候选，必须只保留PDF或Word一种格式")
            return False, issues
        elif docx_candidates:
            paper_path = docx_candidates[0]
        elif pdf_candidates:
            paper_path = pdf_candidates[0]
        else:
            issues.append("未找到可提交论文文件（paper/目录下无.docx/.pdf）")
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
    if file_size > 20 * 1024 * 1024:
        issues.append(f"电子论文超过20MB限制 ({file_size / 1024 / 1024:.2f}MB)")

    print(f"   文件大小: {file_size / 1024:.1f} KB")

    # 所有无法直接从二进制文件可靠判断的项目，都必须由渲染/人工复核产出可审计元数据；
    # 缺字段不能按“提醒”放行。
    metadata_file = OUTPUT_DIR / "paper_metadata.json"
    if metadata_file.exists():
        try:
            meta = _load_json(metadata_file)
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"paper_metadata.json 无法读取: {exc}")
            meta = {}
        print(f"\n📊 论文元数据:")
        print(f"   正文页数（含AI声明和参考文献）: {meta.get('body_page_count', 'N/A')}")
        print(f"   摘要页数: {meta.get('abstract_page_count', 'N/A')}")
        print(f"   摘要字数: {meta.get('abstract_word_count', 'N/A')}")
        print(f"   图表数: {meta.get('figure_count', 'N/A')}图/{meta.get('table_count', 'N/A')}表")
        print(f"   参考文献: {meta.get('reference_count', 'N/A')}条")
        if not isinstance(meta.get("body_page_count"), int):
            issues.append("缺少正文页数 body_page_count（口径须含AI声明和参考文献，不含附录）")
        elif meta["body_page_count"] > 30:
            issues.append(f"正文超过30页限制 ({meta['body_page_count']}页)")
        if meta.get("abstract_page_count") != 1:
            issues.append(f"摘要专用页必须恰为1页，当前为 {meta.get('abstract_page_count', 'N/A')}")

        required_true = {
            "a4_verified": "A4纸张",
            "margins_verified": "页边距要求",
            "toc_absent": "无目录",
            "abstract_page_only": "第一页仅含题目、摘要、关键词",
            "ai_declaration_before_references": "AI声明位于参考文献之前",
            "appendix_source_complete": "附录含文件清单和完整源代码",
            "anonymity_verified": "全文及文档属性匿名",
            "render_review_passed": "最终PDF/Word逐页渲染复核",
        }
        for key, label in required_true.items():
            if meta.get(key) is not True:
                issues.append(f"{label}未提供通过证据 ({key}=true)")
    else:
        issues.append("缺少论文元数据文件 paper_metadata.json")
        print("❌ 缺少 paper_metadata.json，不能证明最终渲染稿合规")

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
def _validate_ai_records_and_summary(ledger):
    """按官方字段和队伍采用的细化模板检查真实AI台账与人工确认汇总。"""
    issues = []
    records = ledger.get("records", [])
    record_ids = set()
    for record in records:
        rid = record.get("id", "<unknown>")
        record_ids.add(rid)
        version = record.get("tool_version") or record.get("version")
        required_values = {
            "tool_name": record.get("tool_name"), "tool_version": version,
            "stage": record.get("stage"), "purpose": record.get("purpose"),
            "use_mode": record.get("use_mode"), "prompt_summary": record.get("prompt_summary"),
            "process_summary": record.get("process_summary"), "response_core": record.get("response_core"),
            "disposition": record.get("disposition"),
        }
        for key, value in required_values.items():
            if not value:
                issues.append(f"AI记录 {rid} 缺少 {key}")
        if version and str(version).strip() in {"最新版", "最新", "latest", "Latest"}:
            issues.append(f"AI记录 {rid} 的版本描述不精确")
        if record.get("stage") and record.get("stage") not in AI_STAGE_NAMES:
            issues.append(f"AI记录 {rid} 的stage不属于七类规定环节")
        if record.get("use_mode") and record.get("use_mode") not in AI_PROMPT_MODES:
            issues.append(f"AI记录 {rid} 的use_mode不属于五类交互方式")
        if record.get("disposition") and record.get("disposition") not in AI_DISPOSITIONS:
            issues.append(f"AI记录 {rid} 的disposition无效")
        if record.get("disposition") == "modified_adopt" and not record.get("modification_details"):
            issues.append(f"AI记录 {rid} 修改后采纳但缺少 modification_details")
        if record.get("disposition") == "rejected" and not record.get("rejection_reason"):
            issues.append(f"AI记录 {rid} 未采纳但缺少 rejection_reason")
        polishing_only = "语言润色" in str(record.get("purpose", "")) and "论文核心" not in str(record.get("purpose", ""))
        if record.get("disposition") in {"direct_adopt", "modified_adopt"} and not polishing_only:
            if not record.get("verification_method"):
                issues.append(f"AI记录 {rid} 已采纳但缺少 verification_method")
            if not record.get("verification_result"):
                issues.append(f"AI记录 {rid} 已采纳但缺少 verification_result")
        if record.get("sensitive_data_redacted") is not True:
            issues.append(f"AI记录 {rid} 未确认敏感信息已脱敏")

    summary_file = OUTPUT_DIR / "ai_usage_summary.json"
    if not summary_file.exists():
        issues.append("缺少 ai_usage_summary.json（七环节、交互方式、采纳核验和人工主导确认未汇总）")
        return issues, None
    try:
        summary = _load_json(summary_file)
    except (json.JSONDecodeError, OSError) as exc:
        issues.append(f"ai_usage_summary.json 无法读取: {exc}")
        return issues, None

    inventory = summary.get("tool_inventory")
    if not isinstance(inventory, list) or not inventory:
        issues.append("ai_usage_summary.tool_inventory 缺失或为空")
    else:
        for index, item in enumerate(inventory, 1):
            if not isinstance(item, dict):
                issues.append(f"tool_inventory 第{index}项必须为对象")
                continue
            for field in ("tool_name", "tool_version", "main_purpose"):
                if not item.get(field):
                    issues.append(f"tool_inventory 第{index}项缺少 {field}")
            if str(item.get("tool_version", "")).strip() in {"最新版", "最新", "latest", "Latest"}:
                issues.append(f"tool_inventory 第{index}项版本描述不精确")
    for section, labels, fields in (
        ("stage_matrix", AI_STAGE_NAMES, ("used", "purpose", "tools")),
        ("prompt_modes", AI_PROMPT_MODES, ("used", "description")),
        ("output_categories", AI_OUTPUT_CATEGORIES, ("adoption_and_modification", "verification_method")),
        ("team_led_confirmation", AI_TEAM_LED_ITEMS, ("team_led", "contribution")),
    ):
        value = summary.get(section)
        if not isinstance(value, dict):
            issues.append(f"ai_usage_summary.{section} 必须为对象")
            continue
        for label in labels:
            item = value.get(label)
            if not isinstance(item, dict):
                issues.append(f"ai_usage_summary.{section} 缺少“{label}”")
                continue
            for field in fields:
                if field not in item or item.get(field) in (None, ""):
                    issues.append(f"ai_usage_summary.{section}[{label}] 缺少 {field}")

    truth = summary.get("truthfulness_confirmation")
    if not isinstance(truth, dict) or truth.get("confirmed_by_team") is not True or not truth.get("confirmed_at"):
        issues.append("真实性确认必须由队伍明确完成并记录 confirmed_at")
    representative_ids = summary.get("representative_record_ids")
    if not isinstance(representative_ids, list) or not 2 <= len(representative_ids) <= 3:
        issues.append("representative_record_ids 必须包含2至3个典型交互ID")
    else:
        if len(set(representative_ids)) != len(representative_ids):
            issues.append("representative_record_ids 不得重复")
        unknown = [rid for rid in representative_ids if rid not in record_ids]
        if unknown:
            issues.append(f"典型交互ID不在真实台账中: {unknown}")
    return issues, summary


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
        if "AI工具使用声明" not in content:
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
    ledger = {}
    if ledger_file.exists():
        try:
            ledger = _load_json(ledger_file)
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"AI使用记录无法读取: {exc}")
        total = ledger.get("total_interactions", 0)
        records = len(ledger.get("records", []))
        print(f"📋 AI使用记录: {total} 次交互, {records} 条记录")
        if total == 0:
            issues.append("AI使用记录为空（可能遗漏记录）")
            print("❌ AI使用记录为空")
        if total != records:
            issues.append(f"AI记录计数不一致: total_interactions={total}, records={records}")
        detail_issues, _ = _validate_ai_records_and_summary(ledger)
        issues.extend(detail_issues)

    else:
        issues.append("缺少AI使用记录文件 ai_usage_ledger.json")
        print("❌ 缺少AI使用记录")

    # 3. 检查源代码完整性
    code_suffixes = {".py", ".m", ".r", ".jl", ".ipynb"}
    code_files = [p for p in CODE_DIR.rglob("*") if p.is_file() and p.suffix.lower() in code_suffixes]
    if not code_files:
        issues.append("源代码目录为空")
        print("❌ 代码目录为空")
    else:
        total_lines = 0
        for cf in code_files:
            with open(cf, "r", encoding="utf-8", errors="ignore") as f:
                total_lines += len(f.readlines())
        print(f"💻 源代码: {len(code_files)} 个文件, {total_lines} 行")
        support_packages = list((WORK_DIR / "delivery").glob("*.zip")) + list((WORK_DIR / "delivery").glob("*.rar"))
        if not support_packages:
            issues.append("缺少支撑材料ZIP/RAR")
        elif len(support_packages) != 1:
            issues.append(f"支撑材料应为单个ZIP或RAR，当前找到 {len(support_packages)} 个")
        for package in support_packages:
            if package.stat().st_size > 20 * 1024 * 1024:
                issues.append(f"支撑材料超过20MB: {package.name}")
            if package.suffix.lower() == ".zip":
                try:
                    with zipfile.ZipFile(package) as archive:
                        names = [name.replace("\\", "/") for name in archive.namelist() if not name.endswith("/")]
                    archived_basenames = {Path(name).name.lower() for name in names}
                    # 提交包只需包含建模、求解、核验和复现所必需的源程序；论文排版、
                    # 内部审计、备份构建等工作流脚本不属于竞赛要求的“建模所用源程序”。
                    required_code = {"q1.py", "q2.py", "q3.py", "q4.py", "check.py", "run_all.py"}
                    missing_code = sorted(required_code - archived_basenames)
                    if missing_code:
                        issues.append(f"支撑材料缺少源代码: {missing_code}")
                    has_run_guide = any(Path(name).name.lower().startswith("readme") for name in names) or \
                        "代码运行说明.txt" in archived_basenames
                    if not has_run_guide:
                        issues.append("支撑材料缺少README或代码运行说明.txt")
                    if not any(Path(name).stem.lower() in {"run_all", "main"} for name in names):
                        issues.append("支撑材料缺少统一运行入口 run_all/main")
                    if ledger.get("total_interactions", 0) > 0 and "ai工具使用详情.pdf" not in archived_basenames:
                        issues.append("使用了AI但支撑材料内缺少精确文件名 AI工具使用详情.pdf")
                    unexpected_papers = [name for name in names if Path(name).suffix.lower() in {".docx", ".pdf"}
                                         and Path(name).name.lower() != "ai工具使用详情.pdf"]
                    if unexpected_papers:
                        issues.append(f"支撑材料混入论文或旧稿: {unexpected_papers}")
                except (zipfile.BadZipFile, OSError) as exc:
                    issues.append(f"支撑材料ZIP无法读取: {exc}")

    delivery_dir = WORK_DIR / "delivery"
    # Word在文档打开期间会生成“~$*.docx”所有者锁文件；它们不是提交论文，
    # 不能计入电子论文数量，否则仅预览论文也会导致诚信门禁误报。
    submission_papers = [p for p in delivery_dir.iterdir() if p.is_file()
                         and p.suffix.lower() in {".pdf", ".docx"}
                         and not p.name.startswith("~$")
                         and p.name != "AI工具使用详情.pdf"] if delivery_dir.exists() else []
    if len(submission_papers) != 1:
        issues.append(f"delivery中应恰有一个电子论文PDF或Word，当前找到 {len(submission_papers)} 个")
    for submission in submission_papers:
        if submission.stat().st_size > 20 * 1024 * 1024:
            issues.append(f"电子论文超过20MB: {submission.name}")

    # 4. 不适合靠字符串扫描判断的项目，必须有可审计的提交复核记录。
    audit_file = OUTPUT_DIR / "submission_audit.json"
    if not audit_file.exists():
        issues.append("缺少 submission_audit.json，匿名性、数据引用和支撑材料完整性不能放行")
    else:
        try:
            audit = _load_json(audit_file)
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"submission_audit.json 无法读取: {exc}")
            audit = {}
        audit_fields = {
            "official_ai_declaration_text_verified": "AI声明采用当年官方二选一文本",
            "data_sources_verified": "数据来源可追溯",
            "data_citations_verified": "外部数据和文献已正确引用",
            "support_code_complete": "支撑材料含全部可运行代码",
            "ai_detail_in_support_verified": "AI工具使用详情.pdf已放入支撑材料（未使用AI时亦须明确记为true）",
            "paper_text_anonymized": "论文正文匿名",
            "document_properties_anonymized": "文件属性匿名",
            "support_paths_anonymized": "支撑材料路径、文件名、代码和注释匿名",
        }
        for key, label in audit_fields.items():
            if audit.get(key) is not True:
                issues.append(f"{label}未提供通过证据 ({key}=true)")

    if issues:
        print(f"\n❌ 学术诚信门禁未通过：{len(issues)} 个问题")
        for i in issues:
            print(f"  - {i}")
        return False, issues
    else:
        print("\n✅ 学术诚信门禁通过！")
    return True, []


def q_gate(qid):
    """逐题硬门禁：某一问通过后，其下游问题才允许开始。"""
    qid = str(qid).upper()
    if not qid.startswith("Q"):
        qid = f"Q{qid}"
    slug = qid.lower()
    print("\n" + "="*60)
    print(f"🚦 {qid} 逐题门禁")
    print("="*60)
    issues = []
    paths = {
        "result": OUTPUT_DIR / f"{slug}_results.json",
        "claims": OUTPUT_DIR / f"{slug}_claim_registry.json",
        "verification": OUTPUT_DIR / f"{slug}_verification.json",
    }
    data = {}
    for label, path in paths.items():
        if not path.exists():
            issues.append(f"缺少 {path.name}")
            continue
        try:
            data[label] = _load_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"{path.name} 无法读取: {exc}")
    result = data.get("result", {})
    if result and result.get("status") != "success":
        issues.append(f"求解状态不是success: {result.get('status')}")
    claims = data.get("claims", {}).get("claims", [])
    if not claims:
        issues.append("声明登记表为空")
    for claim in claims:
        if claim.get("status") != "verified":
            issues.append(f"声明 {claim.get('claim_id', '<unknown>')} 未验证")
    verification = data.get("verification", {})
    if verification and verification.get("status") != "passed":
        issues.append(f"验证状态不是passed: {verification.get('status')}")
    coverage = verification.get("requirement_coverage")
    if coverage not in (1, 1.0, 100, "100%"):
        issues.append(f"题目要求覆盖率不是100%: {coverage}")
    if verification and verification.get("interface_status") != "passed":
        issues.append("与上下游接口契约未通过")
    if issues:
        print(f"❌ {qid} 未通过：{len(issues)} 个问题")
        for issue in issues:
            print(f"  - {issue}")
        return False, issues
    print(f"✅ {qid} 通过，可解锁依赖它的子问题")
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

    # 正式编码前的逻辑合约门禁
    passed, issues = logic_gate()
    results["logic_gate"] = {"passed": passed, "issues": issues}

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
    """根据真实ledger和队伍确认汇总生成指定文件名的AI工具使用详情PDF。"""
    ledger_file = STATE_DIR / "ai_usage_ledger.json"
    if not ledger_file.exists():
        print("❌ 缺少AI使用记录，无法生成报告")
        return False

    with open(ledger_file, "r", encoding="utf-8") as f:
        ledger = json.load(f)

    records = ledger.get("records", [])
    if not records:
        print("❌ AI使用记录为空，不能生成详情")
        return False
    validation_issues, summary = _validate_ai_records_and_summary(ledger)
    if validation_issues:
        print("❌ AI使用详情数据不完整：")
        for issue in validation_issues:
            print(f"  - {issue}")
        return False
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    except ImportError:
        print("❌ 缺少reportlab，无法生成AI工具使用详情.pdf")
        return False

    report_file = WORK_DIR / "state" / "submission_staging" / "AI工具使用详情.pdf"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    normal = ParagraphStyle("Chinese", parent=styles["BodyText"], fontName="STSong-Light", fontSize=9, leading=14)
    title = ParagraphStyle("ChineseTitle", parent=normal, fontSize=18, leading=24, alignment=TA_CENTER, spaceAfter=14)
    heading = ParagraphStyle("ChineseHeading", parent=normal, fontSize=13, leading=18, spaceBefore=10, spaceAfter=6)
    doc = SimpleDocTemplate(str(report_file), pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    def para(value):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), normal)

    def make_table(rows, widths, header=True):
        data = [[para(cell) for cell in row] for row in rows]
        table = Table(data, colWidths=widths, repeatRows=1 if header else 0)
        commands = [
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        if header:
            commands += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EDF5"))]
        table.setStyle(TableStyle(commands))
        return table

    story = [Paragraph("2026 全国大学生数学建模竞赛", title),
             Paragraph("AI 工具使用详情说明", title),
             Paragraph(f"竞赛：全国大学生数学建模竞赛 2026", normal),
             Paragraph(f"记录数：{len(records)}；生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}", normal),
             Spacer(1, 10)]
    tool_rows = [["序号", "AI工具名称", "版本/型号", "主要用途"]]
    for index, item in enumerate(summary["tool_inventory"], 1):
        tool_rows.append([index, item.get("tool_name", ""), item.get("tool_version", ""), item.get("main_purpose", "")])
    story += [Paragraph("一、所用AI工具名称、版本或型号", heading),
              make_table(tool_rows, [1.2*cm, 4.0*cm, 4.0*cm, 7.0*cm])]

    stage_rows = [["论文写作环节", "是否使用", "使用目的", "使用工具"]]
    for label in AI_STAGE_NAMES:
        item = summary["stage_matrix"][label]
        tools = item.get("tools", [])
        stage_rows.append([label, "是" if item["used"] else "否", item["purpose"], "、".join(tools) if isinstance(tools, list) else tools])
    story += [Paragraph("二、具体使用目的和环节", heading),
              make_table(stage_rows, [4.0*cm, 1.7*cm, 7.0*cm, 3.5*cm])]

    mode_rows = [["提示方式", "是否使用", "简要说明"]]
    for label in AI_PROMPT_MODES:
        item = summary["prompt_modes"][label]
        mode_rows.append([label, "是" if item["used"] else "否", item["description"]])
    story += [Paragraph("三、主要提示方式与使用过程说明", heading),
              make_table(mode_rows, [5.0*cm, 2.0*cm, 9.2*cm])]

    records_by_id = {record["id"]: record for record in records}
    for index, rid in enumerate(summary["representative_record_ids"], 1):
        record = records_by_id[rid]
        story.append(Paragraph(f"典型交互示例{index}", heading))
        disposition_text = {
            "direct_adopt": "直接采纳", "modified_adopt": "修改后采纳", "rejected": "未采纳"
        }.get(record.get("disposition"), record.get("disposition", ""))
        treatment = disposition_text
        if record.get("modification_details"):
            treatment += f"；修改说明：{record['modification_details']}"
        if record.get("rejection_reason"):
            treatment += f"；未采纳原因：{record['rejection_reason']}"
        rows = [
            ["项目", "填写内容"],
            ["对应环节", record.get("stage", "")],
            ["使用工具及版本", f"{record.get('tool_name', '')} {record.get('tool_version') or record.get('version', '')}"],
            ["交互时间", record.get("timestamp", "")],
            ["交互方式", record.get("use_mode", "")],
            ["本队提示词", record.get("prompt_summary", "")],
            ["AI回复核心内容", record.get("response_core", "")],
            ["使用过程", record.get("process_summary", "")],
            ["本队处理方式", treatment],
            ["人工核验方式", record.get("verification_method") or "纯语言润色/未采纳，不适用"],
            ["核验结果", record.get("verification_result") or "纯语言润色/未采纳，不适用"],
        ]
        story.append(make_table(rows, [3.3*cm, 12.9*cm]))

    category_rows = [["AI输出内容类别", "采纳与修改情况", "人工核验方式"]]
    for label in AI_OUTPUT_CATEGORIES:
        item = summary["output_categories"][label]
        category_rows.append([label, item["adoption_and_modification"], item["verification_method"]])
    story += [Paragraph("四、对AI输出的采纳、人工修改和核验的主要情况", heading),
              make_table(category_rows, [4.5*cm, 6.2*cm, 5.5*cm])]

    led_rows = [["核心环节", "是否本队主导", "本队贡献说明"]]
    for label in AI_TEAM_LED_ITEMS:
        item = summary["team_led_confirmation"][label]
        led_rows.append([label, "是" if item["team_led"] else "否", item["contribution"]])
    truth = summary["truthfulness_confirmation"]
    truth_text = truth.get("statement") or (
        "以上AI工具使用情况真实完整，无隐瞒、无虚假陈述。核心建模与分析由本队主导完成，"
        "所有AI输出内容（语言润色除外）均经过人工审查与核实。如有不实，本队愿承担相应责任。"
    )
    story += [Paragraph("五、核心环节人工主导确认", heading),
              make_table(led_rows, [5.0*cm, 2.5*cm, 8.7*cm]), Spacer(1, 10),
              Paragraph(f"本队确认（确认时间：{escape(str(truth['confirmed_at']))}）：{escape(truth_text)}", normal)]
    doc.build(story)

    print(f"✅ AI工具使用详情已生成: {report_file}")
    return True


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/gates.py [preflight|logic|qgate Q1|evidence|format|integrity|all|ai-report|state]")
        print("  preflight - 校验主Agent已完整加载当前Skill和规则")
        print("  logic     - 运行正式编码前逻辑合约门禁")
        print("  qgate Q1  - 运行指定子问题逐题门禁")
        print("  evidence  - 运行证据门禁")
        print("  format    - 运行格式门禁")
        print("  integrity - 运行学术诚信门禁")
        print("  all       - 运行全部门禁")
        print("  ai-report - 生成AI工具使用详情")
        print("  state     - 初始化或查看状态")
        sys.exit(1)

    cmd = sys.argv[1]

    exit_ok = True
    if cmd == "preflight":
        exit_ok = preflight_gate()[0]
    elif cmd == "logic":
        exit_ok = logic_gate()[0]
    elif cmd == "qgate":
        if len(sys.argv) < 3:
            print("用法: python scripts/gates.py qgate Q1")
            sys.exit(1)
        exit_ok = q_gate(sys.argv[2])[0]
    elif cmd == "evidence":
        exit_ok = evidence_gate()[0]
    elif cmd == "format":
        paper_path = sys.argv[2] if len(sys.argv) > 2 else None
        exit_ok = format_gate(paper_path)[0]
    elif cmd == "integrity":
        exit_ok = integrity_gate()[0]
    elif cmd == "all":
        paper_path = sys.argv[2] if len(sys.argv) > 2 else None
        exit_ok = run_all_gates(paper_path)
    elif cmd == "ai-report":
        exit_ok = generate_ai_report()
    elif cmd == "state":
        state = load_state()
        if state:
            print(json.dumps(state, ensure_ascii=False, indent=2))
        else:
            print("决策日志不存在")
    else:
        print(f"未知命令: {cmd}")
        exit_ok = False
    if not exit_ok:
        sys.exit(2)
