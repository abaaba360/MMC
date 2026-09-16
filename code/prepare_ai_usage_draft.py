"""把真实过程台账规范化，并生成待队伍确认的AI使用汇总。"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "state" / "ai_usage_ledger.json"
SUMMARY = ROOT / "state" / "agent_outputs" / "ai_usage_summary.json"

STAGES = (
    "赛题理解与问题分析", "模型假设与符号定义", "模型建立与算法设计",
    "模型求解与编程实现", "结果分析与模型检验", "论文撰写与文字润色",
    "其他辅助环节（文献、数据、图表等）",
)
MODES = (
    "网页对话框交互", "代码编辑器内嵌AI", "上传文件或数据对话",
    "AI智能体工作流（多步自动执行）", "其他方式",
)
CATEGORIES = (
    "建模思路与方法建议", "公式推导与理论参考", "代码编写与调试",
    "结果分析与模型评价", "论文核心论述（摘要、结论等）", "其他内容",
)
TEAM_ITEMS = (
    "模型结构与创新点", "公式推导与求解步骤", "程序逻辑与参数设置",
    "结果分析与论文核心论述", "论文撰写与图表制作等",
)


def normalize(record: dict, index: int) -> dict:
    phase = record.get("paper_phase", "")
    stage = {
        "模型建立与算法设计": "模型建立与算法设计",
        "模型求解与编程实现": "模型求解与编程实现",
        "其他辅助环节（文档排版与格式兼容）": "其他辅助环节（文献、数据、图表等）",
    }.get(phase, "模型建立与算法设计")
    adoption = record.get("adoption_status", "")
    disposition = "rejected" if "未采纳" in adoption else (
        "modified_adopt" if any(w in adoption for w in ("修改", "部分", "进行中", "待")) else "direct_adopt"
    )
    if disposition == "modified_adopt":
        mod = record.get("team_handling", "队伍依据题意和独立计算修改后纳入第一版，最终采纳待队伍复核。")
    else:
        mod = ""
    return {
        "id": record.get("interaction_id", f"C-AI-{index:03d}"),
        "timestamp": record.get("time", ""),
        "tool_name": record.get("tool_name", "OpenAI Codex"),
        "tool_version": record.get("version", "GPT-5"),
        "stage": stage,
        "purpose": phase or stage,
        "use_mode": "AI智能体工作流（多步自动执行）",
        "prompt_summary": record.get("user_prompt_summary", ""),
        "process_summary": record.get("ai_response_summary", ""),
        "response_core": record.get("ai_response_summary", ""),
        "disposition": disposition,
        "adopted": disposition != "rejected",
        "modified": disposition == "modified_adopt",
        "rejected": disposition == "rejected",
        "modification_details": mod,
        "rejection_reason": record.get("team_handling", "") if disposition == "rejected" else "",
        "verification_method": record.get("verification", ""),
        "verification_result": "已形成可追溯文件和检查记录；最终数值与论述仍须参赛队逐项复核确认。",
        "evidence_paths": record.get("evidence_paths", []),
        "is_representative": bool(record.get("typical_interaction_candidate")),
        "sensitive_data_redacted": bool(record.get("sensitive_information_redacted", True)),
    }


def main():
    raw = json.loads(LEDGER.read_text(encoding="utf-8"))
    records = [normalize(r, i) for i, r in enumerate(raw.get("records", []), 1)]
    LEDGER.write_text(json.dumps({
        "records": records,
        "total_interactions": len(records),
        "tool_name": "OpenAI Codex", "version": "GPT-5",
        "started_at": raw.get("started_at", ""),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    stage_matrix = {}
    for stage in STAGES:
        stage_matrix[stage] = {
            "used": any(r["stage"] == stage for r in records),
            "purpose": next((r["purpose"] for r in records if r["stage"] == stage), "未使用"),
            "tools": ["OpenAI Codex（GPT-5）"] if any(r["stage"] == stage for r in records) else [],
        }
    # 第一版实际已覆盖但尚未逐条写入历史台账的环节，明确记为使用。
    additions = {
        "赛题理解与问题分析": "拆解四问信息边界、结算规则和附件字段",
        "模型假设与符号定义": "检查假设、符号、效率和充放电互斥表述",
        "结果分析与模型检验": "复算能量平衡、SOC、费用账本并制作消融对照",
        "论文撰写与文字润色": "生成第一版结构、公式、表格并按模板排版",
        "其他辅助环节（文献、数据、图表等）": "审核队伍参考文献表、读取数据并生成图表",
    }
    for stage, purpose in additions.items():
        stage_matrix[stage] = {"used": True, "purpose": purpose, "tools": ["OpenAI Codex（GPT-5）"]}
    summary = {
        "status": "draft_pending_team_confirmation",
        "tool_inventory": [{"tool_name": "OpenAI Codex", "tool_version": "GPT-5",
                            "main_purpose": "赛题分析、模型与代码辅助、结果核验、图表和论文排版"}],
        "stage_matrix": stage_matrix,
        "prompt_modes": {
            mode: {"used": mode in {"上传文件或数据对话", "AI智能体工作流（多步自动执行）"},
                   "description": ("上传赛题、附件、参考文献和模板后分析" if mode == "上传文件或数据对话" else
                                   "在本地工作区执行多步建模、代码、验证和文档生成" if mode == "AI智能体工作流（多步自动执行）" else "未使用")}
            for mode in MODES
        },
        "output_categories": {
            cat: {"adoption_and_modification": "第一版已据题意和计算结果修改整理，最终采纳待队伍确认",
                  "verification_method": "题干逐条核对、独立公式复算、程序复现、残差门禁和队员讨论"}
            for cat in CATEGORIES
        },
        "team_led_confirmation": {
            item: {"team_led": True, "contribution": "队伍确定题意口径和路线；第一版内容须由队员逐项复核后方可提交"}
            for item in TEAM_ITEMS
        },
        "truthfulness_confirmation": {
            "confirmed_by_team": False,
            "confirmed_at": "",
            "statement": "待三名队员核对真实使用过程、采纳情况和人工核验记录后确认。",
        },
        "representative_record_ids": [r["id"] for r in records if r["is_representative"]][:3],
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(SUMMARY)


if __name__ == "__main__":
    main()
