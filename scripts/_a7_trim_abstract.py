# -*- coding: utf-8 -*-
"""A题：摘要精简，使标题+摘要+关键词严格落在第1页（格式规范：摘要不超过一页）。
保持书7.3.3规则800-1000字（B题先例989字），仅删冗余连接词，不动量化结论。
同时对关键词段前距100->0。幂等：直接覆盖元素2-6文本。
"""
import sys, io, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

path = r'd:\数模工作流\delivery\A题_智能评估\A题_数学建模论文智能评估_摘要参考文献版.docx'
doc = Document(path)
body = doc.element.body
els = list(body)

def ptext(p):
    return ''.join(t.text or '' for t in p.iter(qn('w:t')))

def set_text(p, text):
    for r in p.findall(qn('w:r')):
        p.remove(r)
    r = OxmlElement('w:r')
    if rpr_tpl is not None:
        r.append(copy.deepcopy(rpr_tpl))
    t = OxmlElement('w:t'); t.set(qn('xml:space'), 'preserve'); t.text = text
    r.append(t)
    p.append(r)

# 取元素2第一run的rPr作模板（_a3_abstract.py已用该方式设定）
els2probe = els[2]
rpr_tpl = None
for r in els2probe.findall(qn('w:r')):
    rp = r.find(qn('w:rPr'))
    if rp is not None:
        rpr_tpl = copy.deepcopy(rp); break
assert rpr_tpl is not None, '元素2无rPr模板'

P1 = "针对数学建模论文质量评估需兼顾竞赛规范、文本可量化特征与评审主观性差异的问题，本文构建“双源组合赋权评分—无循环定义关联预测—证据化优化与稳健重评”的智能评估框架。附件1含30篇不同题型论文，附件2含10篇同题论文，附件3含3篇待诊断案例，均无权威评分与等级真值，以可复算的内部相对尺度为报告口径。"
P2 = "针对问题一，建立“6维度21指标”层次体系：一级主观权重由层次分析法对齐国赛评分权重框架，二级客观权重由熵权法确定，经组合赋权得综合得分，再用Fisher-Jenks自然断点分级。30篇分级为优秀1篇（71.54分）、良好1篇、中等2篇、及格6篇、不及格20篇；200次权重扰动下等级稳定率0.95、固定断点稳定率0.92，与纯AHP、纯熵权的排序相关0.966、0.890。"
P3 = "针对问题二，为避免循环论证，以D₁、D₃、D₅构造核心质量代理Qᵢ(core)（式(11)），预测变量只用D₂、D₄、D₆的11项特征，以删维相关Yᵢ(−r)（式(13)）检验单调关联并经Benjamini-Hochberg校正；探索性排序提示逻辑连接词密度、参考文献规范度与公式编号密度优先检验。建立带可靠性因子Aᵢ（式(17)）的加权岭回归，以嵌套留一（式(19)、(20)）给出误差协议；因附件2无核验特征矩阵且2-8需OCR复核，不移植旧稿误差数值，正式RMSE、MAE以统一正文提取后重算为准。"
P4 = "针对问题三，以来源证据+文本异常双通道评估AI辅助程度：三篇案例均缺少可核验来源材料而标记为U（无法核验），文本异常指数只用于确定复核优先级；建立G₁–G₅逻辑断层规则（式(24)）并逐篇定位修改，三篇共同问题是摘要（约911、833、946字）超300~500字区间且检验与结论证据链不足；以Ω上max-min（式(25)）在最不利权重下求解，输出保守、完整两情景区间Iᵢ(q)（式(26)），优化顺序为“先修矛盾、再补证据、后调规范”。"
P5 = "本文不编造数据：预测误差与优化后得分均按可复算口径报告，分级退化（ARI=0.068）与分级方法分歧（ARI=0.21）如实披露；模型经权重扰动、赋权替换、无循环定义与三重嵌套稳定性检验，结果稳健。该框架可迁移至学术论文、报告、申请书等文本质量评估，少量无标签样本下仍可给出可追溯的相对评分与改进建议。"

for txt in (P1, P2, P3, P4, P5):
    n = len(txt)
    assert 0 < n, '空段落!'
total = sum(len(x) for x in (P1,P2,P3,P4,P5))
print('精简后摘要总字数: %d' % total)
assert 800 <= total <= 1000, '越界: %d' % total

# 覆盖元素2-6（当前依次为P1-P5）
for i, txt in zip(range(2, 7), (P1, P2, P3, P4, P5)):
    set_text(els[i], txt)
print('已覆盖元素2-6')

# 关键词段前距 100 -> 0（元素7）
kw = els[7]
assert '关键词' in ptext(kw), '元素7不是关键词: %r' % ptext(kw)[:20]
pPr = kw.find(qn('w:pPr'))
sp = pPr.find(qn('w:spacing')) if pPr is not None else None
if sp is not None:
    sp.set(qn('w:before'), '0')
    print('关键词段前距 100 -> 0')
else:
    print('关键词无spacing节点，跳过')

doc.save(path)
print('已保存:', path)
