"""根据真实台账生成《AI工具使用详情》待队伍核对版PDF。"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "delivery" / "AI工具使用详情_待队伍核对.pdf"
STAGES = (
    "赛题理解与问题分析", "模型假设与符号定义", "模型建立与算法设计",
    "模型求解与编程实现", "结果分析与模型检验", "论文撰写与文字润色",
    "其他辅助环节（文献、数据、图表等）",
)
MODES = ("网页对话框交互", "代码编辑器内嵌AI", "上传文件或数据对话",
         "AI智能体工作流（多步自动执行）", "其他方式")
CATS = ("建模思路与方法建议", "公式推导与理论参考", "代码编写与调试",
        "结果分析与模型评价", "论文核心论述（摘要、结论等）", "其他内容")
TEAM = ("模型结构与创新点", "公式推导与求解步骤", "程序逻辑与参数设置",
        "结果分析与论文核心论述", "论文撰写与图表制作等")


def main():
    ledger = json.loads((ROOT / "state/ai_usage_ledger.json").read_text(encoding="utf-8"))
    summary = json.loads((ROOT / "state/agent_outputs/ai_usage_summary.json").read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont("CN", r"C:\Windows\Fonts\simsun.ttc", subfontIndex=0))
    pdfmetrics.registerFont(TTFont("CNBold", r"C:\Windows\Fonts\simhei.ttf"))
    normal = ParagraphStyle("normal", fontName="CN", fontSize=9, leading=14, textColor=colors.HexColor("#263238"))
    title = ParagraphStyle("title", parent=normal, fontName="CNBold", fontSize=18, leading=26,
                           alignment=TA_CENTER, spaceAfter=8)
    h = ParagraphStyle("h", parent=normal, fontName="CNBold", fontSize=13, leading=19,
                       textColor=colors.HexColor("#1F4E78"), spaceBefore=10, spaceAfter=6)
    warn = ParagraphStyle("warn", parent=normal, fontName="CNBold", fontSize=10, leading=16,
                          textColor=colors.HexColor("#A64B00"), backColor=colors.HexColor("#FFF3D6"),
                          borderPadding=8, borderColor=colors.HexColor("#E6A23C"), borderWidth=0.8)

    def p(value, style=normal):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)

    def table(rows, widths):
        data = [[p(v) for v in row] for row in rows]
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#D9EAF7")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#1F4E78")),
            ("FONTNAME", (0,0), (-1,0), "CNBold"),
            ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#A7B8C5")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        return t

    story = [p("2026 全国大学生数学建模竞赛", title), p("AI 工具使用详情说明", title),
             Spacer(1, 5), p("待队伍核对版：不得直接作为最终支撑材料提交。请三名队员逐项核对真实工具、版本、交互、采纳修改与人工核验后再确认。", warn)]
    story += [p("一、所用AI工具名称、版本或型号", h), table([
        ["序号", "AI工具名称", "版本/型号", "主要用途"],
        *[[i, x["tool_name"], x["tool_version"], x["main_purpose"]]
          for i, x in enumerate(summary["tool_inventory"], 1)]
    ], [1.1*cm, 3.5*cm, 3.0*cm, 8.6*cm])]
    story += [p("二、具体使用目的和环节", h), table([
        ["论文写作环节", "是否使用", "使用目的", "使用工具"],
        *[[s, "是" if summary["stage_matrix"][s]["used"] else "否",
           summary["stage_matrix"][s]["purpose"], "、".join(summary["stage_matrix"][s]["tools"])] for s in STAGES]
    ], [4.1*cm, 1.5*cm, 7.1*cm, 3.5*cm])]
    story += [p("三、主要提示方式与使用过程说明", h), table([
        ["提示方式", "是否使用", "简要说明"],
        *[[m, "是" if summary["prompt_modes"][m]["used"] else "否",
           summary["prompt_modes"][m]["description"]] for m in MODES]
    ], [5.2*cm, 1.8*cm, 9.2*cm])]
    records = {r["id"]: r for r in ledger["records"]}
    for idx, rid in enumerate(summary["representative_record_ids"], 1):
        r = records[rid]
        story += [PageBreak(), p(f"典型交互示例 {idx}", h), table([
            ["项目", "填写内容"], ["对应环节", r["stage"]],
            ["使用工具及版本", f"{r['tool_name']} {r['tool_version']}"],
            ["交互时间", r["timestamp"]], ["交互方式", r["use_mode"]],
            ["本队提示词", r["prompt_summary"]], ["AI回复核心内容", r["response_core"]],
            ["使用过程", r["process_summary"]],
            ["本队处理方式", "修改后采纳；" + r.get("modification_details", "")],
            ["人工核验方式", r["verification_method"]], ["核验结果", r["verification_result"]],
        ], [3.3*cm, 12.9*cm])]
    story += [PageBreak(), p("四、AI输出的采纳、人工修改和核验", h), table([
        ["AI输出类别", "采纳与修改情况", "人工核验方式"],
        *[[c, summary["output_categories"][c]["adoption_and_modification"],
           summary["output_categories"][c]["verification_method"]] for c in CATS]
    ], [4.4*cm, 6.0*cm, 5.8*cm])]
    story += [p("五、核心环节人工主导确认", h), table([
        ["核心环节", "是否本队主导", "本队贡献说明"],
        *[[x, "待最终确认", summary["team_led_confirmation"][x]["contribution"]] for x in TEAM]
    ], [4.6*cm, 2.6*cm, 9.0*cm]), Spacer(1, 10),
        p("真实性确认：当前状态为待三名队员核对，尚未作出最终真实性承诺。确认后应删除本提示，将文件改名为“AI工具使用详情.pdf”，并与论文AI声明保持一致。", warn)]

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont("CNBold", 9)
        canvas.setFillColor(colors.HexColor("#B35A00"))
        canvas.drawString(2*cm, A4[1]-1.35*cm, "待队伍核对版")
        canvas.setFont("CN", 8)
        canvas.setFillColor(colors.HexColor("#607D8B"))
        canvas.drawCentredString(A4[0]/2, 1.3*cm, str(doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    print(OUT)


if __name__ == "__main__":
    main()
