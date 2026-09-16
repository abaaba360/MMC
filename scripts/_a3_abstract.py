# -*- coding: utf-8 -*-
"""A题：重写摘要（书7.3.3规范：800-1000字、黄金三段式虎头-猪肚-豹尾、全量化）+ 关键词"""
import sys, io, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

path = r'd:\数模工作流\delivery\A题_智能评估\A题_数学建模论文智能评估_摘要参考文献版.docx'
doc = Document(path)
body = doc.element.body
els = list(body)

abs_p1 = els[2]
abs_p2 = els[3]
abs_p3 = els[4]
kw_p   = els[5]
tpl_rpr = None
for r in abs_p1.findall(qn('w:r')):
    rpr = r.find(qn('w:rPr'))
    if rpr is not None:
        tpl_rpr = copy.deepcopy(rpr); break

def set_text(p, text):
    for r in p.findall(qn('w:r')):
        p.remove(r)
    r = OxmlElement('w:r')
    if tpl_rpr is not None:
        r.append(copy.deepcopy(tpl_rpr))
    t = OxmlElement('w:t'); t.set(qn('xml:space'), 'preserve'); t.text = text
    r.append(t)
    p.append(r)

P1 = "针对数学建模论文质量评估需兼顾竞赛规范、文本可量化特征与评审主观性差异的问题，本文构建“双源组合赋权评分—无循环定义关联预测—证据化优化与稳健重评”的智能评估框架。附件1含30篇不同题型论文，附件2含10篇同题论文，附件3含3篇待诊断案例，均无权威评分与等级真值，本文以可复算的内部相对尺度为报告口径。"
P2 = "针对问题一，建立“6维度21指标”层次体系：一级主观权重由层次分析法对齐国赛评分权重框架，二级客观权重由熵权法确定，经乘法合成与线性加权得综合得分，再用Fisher-Jenks自然断点分级。30篇分级为优秀1篇（71.54分）、良好1篇、中等2篇、及格6篇、不及格20篇；200次权重扰动下等级稳定率0.95、固定断点稳定率0.92，与纯AHP、纯熵权的排序相关0.966、0.890。"
P3 = "针对问题二，为避免循环论证，以D₁、D₃、D₅构造核心质量代理Qᵢ(core)（式(11)），预测变量只用D₂、D₄、D₆的11项文本特征，以删维相关Yᵢ(−r)（式(13)）检验单调关联并经Benjamini-Hochberg校正；探索性排序提示逻辑连接词密度、参考文献规范度与公式编号密度优先检验。建立带可靠性因子Aᵢ（式(17)）的加权岭回归，以嵌套留一（式(19)、(20)）给出误差协议；因附件无可核验的10×21特征矩阵且2-8需OCR复核，本文不移植旧稿误差数值，正式RMSE、MAE以统一正文提取后重算为准。"
P4 = "针对问题三，以“来源证据+文本异常”双通道评估AI辅助程度：三篇案例均缺少可核验来源材料而标记为U（无法核验），文本异常指数只用于确定复核优先级；建立G₁–G₅五类逻辑断层规则（式(24)）并逐篇定位修改，三篇共同问题是摘要（约911、833、946字）超300~500字区间且检验与结论证据链不足；以Ω上max-min（式(25)）在最不利权重下求解，输出保守、完整两情景区间Iᵢ(q)（式(26)），优化顺序为“先修矛盾、再补证据、后调规范”。"
P5 = "本文不编造数据：预测误差与优化后得分均按可复算口径报告，分级退化（ARI=0.068）与分级方法分歧（ARI=0.21）如实披露；模型经权重扰动、赋权方法替换、无循环定义与三重嵌套稳定性检验，结果稳健。该框架可迁移至学术论文、报告、申请书等文本对象的自动质量评估，在少量无标签样本条件下仍可给出可追溯、可复算的相对评分与改进建议。"
KEYWORDS = "关键词：论文质量评估；层次分析法；组合赋权；岭回归；无循环定义；稳健优化"

total = sum(len(p) for p in (P1, P2, P3, P4, P5))
print('摘要总字数: %d' % total)
assert 800 <= total <= 1000, '摘要字数不满足800-1000: %d' % total

template = copy.deepcopy(abs_p1)
set_text(abs_p1, P1)
cur = abs_p1
for txt in (P2, P3, P4):
    np = copy.deepcopy(template)
    set_text(np, txt)
    cur.addnext(np)
    cur = np
set_text(abs_p3, P5)
body.remove(abs_p2)

# 关键词
set_text(kw_p, KEYWORDS)

doc.save(path)
print('摘要重写完成 (%d字, 5段), 关键词已更新' % total)
