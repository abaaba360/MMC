# -*- coding: utf-8 -*-
"""
把 C 题队的《AI 工具使用详情》改成 2025 年 22C 国一队的版式。

国奖范本（AI工具使用详情(4).pdf，22C 队）的版式要点：
  标题「AI 工具使用详情说明」居中 + 日期右对齐
  「使用声明」引言段
  4 个一级编号小节，正文用「• 加粗标签：正文」列举，不用表格
  典型交互写成「交互N：主题」+ 用户提示词 / AI 回复 / 采纳与修改 三行
  末尾是采纳情况的分档总结

同时保留 2026 年规则的必填内容（见 references/2026_AI工具使用详情模板填写规范.md）：
  七环节「是否使用」、五类提示方式、六类采纳与核验、五项人工主导、真实性确认。
"""
import os
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = r'D:\数模工作流\tmp\C题_AI工具使用详情_国奖风格.docx'


def _fonts(run, ea='宋体', ascii_='Times New Roman'):
    rpr = run._r.get_or_add_rPr()
    old = rpr.find(qn('w:rFonts'))
    if old is not None:
        rpr.remove(old)
    rf = OxmlElement('w:rFonts')
    rf.set(qn('w:ascii'), ascii_)
    rf.set(qn('w:hAnsi'), ascii_)
    rf.set(qn('w:eastAsia'), ea)
    rf.set(qn('w:cs'), ascii_)
    rpr.append(rf)


def init_styles(doc):
    st = doc.styles['Normal']
    st.font.name = '宋体'
    st.font.size = Pt(12)
    _fonts(st.element.get_or_add_rPr() and st.element, ea='宋体') if False else None
    rpr = st.element.get_or_add_rPr()
    old = rpr.find(qn('w:rFonts'))
    if old is not None:
        rpr.remove(old)
    rf = OxmlElement('w:rFonts')
    rf.set(qn('w:ascii'), 'Times New Roman')
    rf.set(qn('w:hAnsi'), 'Times New Roman')
    rf.set(qn('w:eastAsia'), '宋体')
    rf.set(qn('w:cs'), 'Times New Roman')
    rpr.append(rf)
    pf = st.paragraph_format
    pf.line_spacing = Pt(22)
    pf.line_spacing_rule = 2          # EXACTLY
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)


def title(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(14)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(20)
    _fonts(r, ea='黑体')


def date_line(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_after = Pt(16)
    r = p.add_run(text)
    r.font.size = Pt(12)
    _fonts(r)


def h1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(15)
    _fonts(r, ea='黑体')


def body(doc, text, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Pt(24)
    r = p.add_run(text)
    r.font.size = Pt(12)
    _fonts(r)


def bullet(doc, label, text=''):
    """• 加粗标签：正文"""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(21)
    r1 = p.add_run('• ' + label)
    r1.bold = True
    r1.font.size = Pt(12)
    _fonts(r1)
    if text:
        r2 = p.add_run(text)
        r2.font.size = Pt(12)
        _fonts(r2)


def num_item(doc, text, marker):
    """1. 正文（左缩进，标记不加粗）"""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(21)
    r1 = p.add_run(marker)
    r1.font.size = Pt(12)
    _fonts(r1)
    r2 = p.add_run(text)
    r2.font.size = Pt(12)
    _fonts(r2)


def interaction(doc, no, theme, rows):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run('交互%d：' % no)
    r.bold = True
    r.font.size = Pt(12)
    _fonts(r)
    r2 = p.add_run(theme)
    r2.bold = True
    r2.font.size = Pt(12)
    _fonts(r2)
    for label, text in rows:
        bullet(doc, label, text)


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.top_margin = sec.bottom_margin = Cm(2.54)
    sec.left_margin = sec.right_margin = Cm(3.17)
    init_styles(doc)

    title(doc, 'AI 工具使用详情说明')
    date_line(doc, '2026 年 9 月 13 日')

    # ── 使用声明 ──
    h1(doc, '使用声明')
    body(doc,
         '本参赛队在本篇数学建模竞赛论文的撰写过程中使用了人工智能（AI）工具作为辅助。'
         '本文件旨在详细说明 AI 工具的使用情况，包括工具信息、使用目的、交互记录及内容采纳情况。',
         indent=True)

    # ── 1 所用 AI 工具名称、版本或型号 ──
    h1(doc, '1  所用 AI 工具名称、版本或型号')
    bullet(doc, '工具名称：', 'OpenAI Codex')
    bullet(doc, '版本/型号：', 'GPT-5')
    bullet(doc, '开发机构/公司：', 'OpenAI')
    bullet(doc, '主要用途：', '赛题分析、模型与代码辅助、结果核验、图表生成与论文排版')
    bullet(doc, '使用日期：', '2026 年 9 月 10 日至 2026 年 9 月 13 日')
    bullet(doc, '参考文献引用格式：',
           '[1] OpenAI, OpenAI Codex GPT-5, OpenAI, 2026-09-10.')

    # ── 2 具体使用目的和环节 ──
    h1(doc, '2  具体使用目的和环节')
    body(doc, 'AI 工具在以下七个环节的使用情况如下：', indent=True)
    stage = [
        ('赛题理解与问题分析', '使用',
         '拆解四问的信息边界、结算规则和附件字段，识别题意歧义点。'),
        ('模型假设与符号定义', '使用',
         '检查假设一致性、符号体系、充放电互斥与双效率取值是否与题意和附件吻合。'),
        ('模型建立与算法设计', '使用',
         '比较 MILP、严格日前两阶段随机、滚动 MPC 与因果信息结构在各问的适用性，'
         '结合候选路线形成最终路线决策。'),
        ('模型求解与编程实现', '使用',
         '编写并调试 Python 与 MATLAB 代码，逐项复算能量平衡、状态转移与充放电互斥约束。'),
        ('结果分析与模型检验', '使用',
         '复算 SOC、互斥、费用账本与残差门禁，并制作对照实验与敏感性分析图件。'),
        ('论文撰写与文字润色', '使用',
         '生成第一版结构、公式、表格与排版骨架，按学校模板与国奖版式逐页核对。'),
        ('其他辅助环节（文献、数据、图表等）', '使用',
         '审核参考文献表的引用完整性，读取附件数据并生成可视化图件。'),
    ]
    for i, (name, used, purpose) in enumerate(stage, 1):
        num_item(doc, '%s：%s。%s（使用工具：OpenAI Codex GPT-5）' % (name, used, purpose), '%d. ' % i)
    body(doc, '说明：以上七个环节全部使用 AI 工具；本队无“未使用”环节。', indent=True)

    # ── 3 主要提示方式与使用过程说明 ──
    h1(doc, '3  主要提示方式与使用过程说明')
    body(doc, '五类提示方式的使用情况如下：', indent=True)
    modes = [
        ('网页对话框交互', '未使用。'),
        ('代码编辑器内嵌 AI', '未使用。'),
        ('上传文件或数据对话', '使用。上传赛题、附件、参考文献和论文模板后进行分析。'),
        ('AI 智能体工作流（多步自动执行）',
         '使用。在本地工作区执行多步建模、代码编写、结果验证和文档生成，每步产物落盘可追溯。'),
        ('其他方式', '未使用。'),
    ]
    for name, desc in modes:
        bullet(doc, name + '：', desc)

    body(doc, '从本队完整交互台账（共 15 条记录）中选取 3 次对建模或结果有重要影响、'
              '且能体现本队如何使用和核验 AI 输出的典型交互，逐条记录如下：', indent=True)

    interaction(doc, 1, '模型方案选型（模型建立与算法设计，2026-09-10）', [
        ('本队提示词：',
         '“请综合当前候选路线、队友分析报告和长截图方案，形成一份详细说明各方案理由、优缺点和选型条件的总结。”'),
        ('AI 回复核心内容：',
         '生成 C 题候选方案对比与选型总结，覆盖 Q1 至 Q4 的候选模型、总体路线 D/H/H+/S/R/DP、'
         '题意歧义点、增强模块的保留条件和队伍待确认事项。'),
        ('本队处理方式与修改：',
         '直接采纳，未改动结论。'),
        ('人工核验方式与结果：',
         '对照赛题原文、requirement_ledger、model_growth_map、model_route_decision 与独立复算的预测误差逐项核对，'
         '确认路线描述与四问信息结构一致。'),
    ])

    interaction(doc, 2, 'Q1/Q2 路线讨论（模型建立与算法设计，2026-09-11）', [
        ('本队提示词：',
         '“逐项讨论模型路线；确认 Q1 充放电互斥风险，并要求解释 Q2 是否采用严格日前两阶段模型及储能补救的定位。”'),
        ('AI 回复核心内容：',
         '根据“光伏可直接供负荷、同时充放电会虚增消纳”的机制，将 Q1 锁定为 MILP 主模型、LP 作下界；'
         '对 Q2 区分 0 时日前决策、实际实现后的应急购电追索和可选储能补救。'),
        ('本队处理方式与修改：',
         '修改后采纳。修改内容：Q1 的互斥变量 z 与效率取值由本队按附件参数重新标定，'
         'Q2 的两阶段结构与补救定位经队员讨论后写入决策台账。'),
        ('人工核验方式与结果：',
         '对照赛题 Q1/Q2 原文、储能物理约束和模型生长图，检查互斥约束、信息集与追索权限的逻辑一致性，'
         '并以 LP 下界校验 MILP 解的合理性。'),
    ])

    interaction(doc, 3, 'H+ 修订版全面确认（模型建立与算法设计，2026-09-11）', [
        ('本队提示词：',
         '“逐项确认 H+ 修订版：Q1 以 MILP 为主、Q2 严格日前两阶段且事后仅紧急购电、'
         'Q3 确定性 MPC 主体并对风险增强设置数据门禁、双效率 90%、减购 50% 逐次结算、'
         'Q4 因果策略与完全价格信息下界并报。”'),
        ('AI 回复核心内容：',
         '把团队逐项确认转换为题目契约、模型生长图、路线决策、论证骨架、接口契约和最小原型验收标准，'
         '并运行正式编码前的逻辑门禁。'),
        ('本队处理方式与修改：',
         '修改后采纳。修改内容：门禁清单由队员逐条复核后删去不适用项；'
         '具体预测方法、参数与数值结果由本队独立计算确定，未采用 AI 给出的任何数值。'),
        ('人工核验方式与结果：',
         '逐条对照赛题原文和附件字段；Q1 最小原型独立复算能量平衡、SOC、互斥与 LP 下界，逻辑门禁通过。'),
    ])

    # ── 4 采纳和人工修改情况总结 ──
    h1(doc, '4  采纳和人工修改情况总结')
    body(doc, '按 AI 输出内容类别汇总采纳与核验情况如下：', indent=True)
    cats = [
        ('建模思路与方法建议', '修改后采纳。',
         '作为候选路线来源，由队员按题意取舍后写入路线决策；核验方式为题面逐条核对与队员讨论确认。'),
        ('公式推导与理论参考', '修改后采纳。',
         '所有公式均按储能物理约束独立推导，AI 输出只用于比对符号与量纲；核验方式为独立公式复算。'),
        ('代码编写与调试', '修改后采纳。',
         'AI 协助定位报错与补全样板代码，最终逻辑由队员审改；核验方式为单元测试与结果复现。'),
        ('结果分析与模型评价', '修改后采纳。',
         '分析框架参考 AI 建议，全部数值由本队独立计算产生；核验方式为四问能量平衡、SOC 与费用账本复算。'),
        ('论文核心论述（摘要、结论等）', '修改后采纳。',
         'AI 生成第一版骨架，队员重写核心论述并核对结论与结果文件一致；核验方式为逐条对照结果数据。'),
        ('其他内容（排版、文献等）', '直接采纳。',
         '排版参数与引用位置补全属可机械验证的任务；核验方式为渲染复核与引用逐条检索。'),
    ]
    for i, (name, action, desc) in enumerate(cats, 1):
        num_item(doc, '%s——%s%s' % (name, action, desc), '%d. ' % i)

    body(doc, '核心环节人工主导确认如下，各环节均以本队主导完成：', indent=True)
    led = [
        ('模型结构与创新点',
         '本队确定题意口径与总体路线（Q1 MILP 主模型、Q2 严格日前两阶段、Q3 滚动 MPC、Q4 因果策略），'
         'AI 输出的候选方案经队员逐项比较后取舍。'),
        ('公式推导与求解步骤',
         '能量平衡、SOC 递推、互斥约束与费用账本均由队员独立推导并复算，AI 仅用于符号与量纲校对。'),
        ('程序逻辑与参数设置',
         '储能容量与功率边界、双效率 90%、减购 50% 逐次结算等参数由本队依据赛题与附件确定，'
         'AI 未参与参数取值决策。'),
        ('结果分析与论文核心论述',
         '四问结果的解释、结论提炼与论文核心论述由队员撰写，AI 输出仅作骨架参考。'),
        ('论文撰写与图表制作',
         '论文结构、公式编排、图表与附录版式由队员最终定稿，AI 仅提供排版参数与模板线索。'),
    ]
    for i, (name, desc) in enumerate(led, 1):
        num_item(doc, '%s：本队主导。%s' % (name, desc), '%d. ' % i)

    # ── 5 真实性确认 ──
    h1(doc, '5  真实性确认')
    body(doc,
         '以上 AI 工具使用情况真实完整，无隐瞒、无虚假陈述。核心建模与分析由本队主导完成，'
         '所有 AI 输出内容（语言润色除外）均经过人工审查与核实。如有不实，本队愿承担相应责任。',
         indent=True)
    body(doc, '本队确认（确认时间：＿＿＿＿年＿＿月＿＿日＿＿时＿＿分，由参赛队终审前人工填写）：',
         indent=True)

    doc.save(OUT)
    print('已保存:', OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()