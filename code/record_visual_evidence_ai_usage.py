from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(r"D:\数模工作流")
PATH = ROOT / "state" / "ai_usage_ledger.json"
ledger = json.loads(PATH.read_text(encoding="utf-8"))
records = ledger.setdefault("records", [])
record_id = "C-S8-20260912-014"
records = [record for record in records if record.get("id") != record_id]
records.append(
    {
        "id": record_id,
        "timestamp": "2026-09-12T14:35:00+08:00",
        "tool_name": "OpenAI Codex",
        "tool_version": "GPT-5",
        "stage": "其他辅助环节（文献、数据、图表等）",
        "purpose": "按国奖论文证据链重构全篇图表并补充缺失证据",
        "use_mode": "AI智能体工作流（多步自动执行）",
        "prompt_summary": "队伍要求把国奖论文图表学习记录应用到C题全部问题；优化或删除现有图，并在论证缺少图形证据时补画；所有数据图尽量由本机MATLAB真实运行生成。",
        "process_summary": "先审计全文7图13表及其图前图后文字，为四问建立结论—证据计划；从已验证结果文件导出绘图数据，在MATLAB中统一重绘问题一至问题四的调度、预测、费用、消融和信息价值图，并新增全年跨日SOC连续性图；随后替换Word图片、重写图前引导与图后分析，统一三线表版式并逐页渲染检查。",
        "response_core": "形成图表论证增强版Word论文：6张数据图重绘、1张SOC证据图新增，图表均由真实结果驱动；问题四增加信息损失放大面板，问题三给出更新频率边际收益，问题二给出跨日SOC零连接残差。",
        "disposition": "modified_adopt",
        "adopted": True,
        "modified": True,
        "rejected": False,
        "modification_details": "未使用生成式图片。对不适合直接比较的计划购电曲线予以删除；趋势用图、精确时点用表，避免重复。绘图只读取既有验证结果，不在作图阶段重新求解或修改数值。",
        "rejection_reason": "",
        "verification_method": "MATLAB R2025a本机运行并同时导出600 dpi PNG、矢量PDF和可编辑FIG；Word原生引擎导出109页PDF，检查全部页面缩略图并逐页放大核对正文第9至26页；结构核对8个嵌入图、13张表和26个显示公式对象，运行证据、格式与诚信门禁。",
        "verification_result": "正文含AI声明和参考文献至物理第26页，满足不超过30页；图表无乱码、裁切或错位，三线表跨页表头正常；新增SOC图的跨日连接最大残差为0 kWh，全部图中文字与结果文件一致。",
        "evidence_paths": [
            "state/agent_outputs/c_paper_figure_table_evidence_plan.md",
            "code/export_matlab_visual_data.py",
            "code/plot_c_paper_figures_matlab.m",
            "code/plot_q1_dispatch_matlab_preview.m",
            "results/figures_matlab/",
            "code/enhance_c_paper_visual_evidence.py",
            "delivery/C题论文_光伏微网储能购电滚动优化_图表论证增强版.docx",
            "state/docx_render_qa/visual_enhanced_v1_word/",
        ],
        "is_representative": True,
        "sensitive_data_redacted": True,
    }
)
ledger["records"] = records
ledger["total_interactions"] = len(records)
PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{PATH} records={len(records)}")
