from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(r"D:\数模工作流")
PATH = ROOT / "state" / "ai_usage_ledger.json"
META = ROOT / "state" / "agent_outputs" / "paper_metadata.json"

ledger = json.loads(PATH.read_text(encoding="utf-8"))
records = ledger.setdefault("records", [])
record_id = "C-S8-20260912-015"
records = [r for r in records if r.get("id") != record_id]
records.append({
    "id": record_id,
    "timestamp": "2026-09-12T15:05:00+08:00",
    "tool_name": "OpenAI Codex",
    "tool_version": "GPT-5",
    "stage": "论文撰写与文字润色",
    "purpose": "以队伍最新Word为正文基准重排图表证据链与结果分析",
    "use_mode": "上传文件或数据对话",
    "prompt_summary": "队伍要求以最新Word文档为正文内容和结构基准，保留MATLAB真实结果图；每张图表分别设置图表前观察目的和紧随其后的局部解释，结果分析与检验改为独立的综合正文，并恢复完整摘要。",
    "process_summary": "逐项读取Word中的摘要、公式、14张表和7幅原图，保留原正文与71个Word公式对象；替换6张数据图并新增跨日SOC图，重新编排问题一至问题四的12张核心结果表和7张结果图，使每个对象形成前导—图表—解释的相邻结构；重写四个结果分析末节为回答题目、解释机制和验证可靠性的正文。",
    "response_core": "形成图表逐项解读版Word论文，摘要逐字保留最新原稿，所有MATLAB图由已验证结果驱动；正文含参考文献共29页，附录自第30页开始。",
    "disposition": "modified_adopt",
    "adopted": True,
    "modified": True,
    "rejected": False,
    "modification_details": "除图表前后局部解释、各问结果分析末节及必要的结果呈现衔接句外，其余内容以队伍提供的最新Word为基准保留。未使用生成式图片，未修改模型、公式、表格数据或数值结果。",
    "rejection_reason": "",
    "verification_method": "结构程序校验摘要逐字一致、14张表完整、71个Word公式对象不减少、全部核心图表均有相邻前导与后置解释；Microsoft Word导出113页PDF并逐页检查，重点放大正文第9至29页的图题、跨页长表和结果分析。",
    "verification_result": "29项结构检查全部通过；摘要独占第一页，正文含AI声明和参考文献至第29页，满足30页限制；8个内嵌图、14张表和71个公式对象完整，未发现图文堆砌、裁切、重叠、乱码或表格越界。",
    "evidence_paths": [
        "delivery/C题论文_光伏微网储能购电滚动优化_图表逐项解读版.docx",
        "code/rebuild_c_paper_figure_table_narrative.py",
        "code/validate_c_paper_figure_table_narrative.py",
        "state/agent_outputs/c_paper_figure_table_narrative_validation.json",
        "state/qa/c_paper_narrative_render_v1/",
        "results/figures_matlab/",
    ],
    "is_representative": True,
    "sensitive_data_redacted": True,
})
ledger["records"] = records
ledger["total_interactions"] = len(records)
PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

META.write_text(json.dumps({
    "total_pages": 113,
    "body_page_count": 29,
    "abstract_page_count": 1,
    "abstract_word_count": 911,
    "figure_count": 8,
    "table_count": 14,
    "omml_object_count": 71,
    "reference_count": 9,
    "format_check_passed": True,
    "figure_table_local_narrative_check_passed": True,
    "a4_verified": True,
    "margins_verified": True,
    "toc_absent": True,
    "abstract_page_only": True,
    "ai_declaration_before_references": True,
    "appendix_source_complete": True,
    "anonymity_verified": True,
    "render_review_passed": True,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{PATH} records={len(records)}")
print(META)
