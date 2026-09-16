# -*- coding: utf-8 -*-
"""A题：按Word模板五段式重构5.2/5.3子节标题 + 全文交叉引用更新。
- 5.2: 7子节 -> 5段（删2标题，合并内容）
- 5.3: 7子节 -> 5段（删2标题 + 移动[193-196]块到[205]后 + 删[192]标题）
- 5.1/5.2/5.3 主标题统一为模板格式 "5.X 问题X模型的建立与求解"
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

path = r'd:\数模工作流\delivery\A题_智能评估\A题_数学建模论文智能评估_摘要参考文献版.docx'
doc = Document(path)
body = doc.element.body
els = list(body)
print('总元素数:', len(els))

def ptext(p):
    return ''.join(t.text or '' for t in p.iter(qn('w:t')))

def set_heading(p, num, title):
    """run0=编号前缀, run1=标题文本；保留两者rPr，删多余run"""
    runs = p.findall(qn('w:r'))
    assert len(runs) >= 2, '标题run不足: %r' % ptext(p)[:30]
    t0 = runs[0].find(qn('w:t'))
    t1 = runs[1].find(qn('w:t'))
    assert t0 is not None and t1 is not None, 'run缺w:t: %r' % ptext(p)[:30]
    t0.text = num
    t1.text = title
    for r in runs[2:]:
        p.remove(r)

RENAME = {
    64: ('5.1 ', '问题一模型的建立与求解'),
    113: ('5.2 ', '问题二模型的建立与求解'),
    160: ('5.3 ', '问题三模型的建立与求解'),
    115: ('5.2.1 ', '数据预处理'),
    128: ('5.2.2 ', '关联分析模型的建立'),
    138: ('5.2.3 ', '预测模型的建立与求解'),
    151: ('5.2.4 ', '模型的检验'),
    157: ('5.2.5 ', '结果的分析'),
    162: ('5.3.1 ', '数据预处理'),
    169: ('5.3.2 ', '人工智能辅助程度评估模型的建立'),
    187: ('5.3.3 ', '稳健优化模型的建立与求解'),
    197: ('5.3.4 ', '模型的检验'),
    203: ('5.3.5 ', '结果的分析'),
}
for idx, (num, title) in RENAME.items():
    set_heading(els[idx], num, title)
    print('改标题[%d]: %s%s' % (idx, num, title))

# 删除多余标题（内容保留、并入前节）
for idx in [123, 145, 179, 192]:
    el = els[idx]
    print('删标题[%d]: %r' % (idx, ptext(el)[:30]))
    body.remove(el)

# 移动块[193-196]到元素205之后（使5.3.5 = 结果分析prose + 具体修改方案表）
anchor = els[205]
block = [els[i] for i in range(193, 197)]
for el in reversed(block):
    anchor.addnext(el)
print('已移动[193-196]到[205]后')

# 交叉引用替换（段落内逐w:t节点）
def replace_in_para(p, old, new):
    cnt = 0
    for t in p.iter(qn('w:t')):
        if t.text and old in t.text:
            t.text = t.text.replace(old, new)
            cnt += 1
    return cnt

XREF = {
    210: [('5.2.6', '5.2.4')],
    212: [('5.3.6', '5.3.4')],
    217: [('5.2.3', '5.2.2')],
    220: [('5.2.6', '5.2.4')],
    222: [('5.3.4', '5.3.3')],
}
for idx, pairs in XREF.items():
    for old, new in pairs:
        n = replace_in_para(els[idx], old, new)
        print('元素%d: %s→%s 替换%d处' % (idx, old, new, n))

doc.save(path)
print('已保存:', path)

# ---------- 校验 ----------
doc2 = Document(path)
els2 = list(doc2.element.body)
for i in [64, 113, 115, 123, 128, 138, 145, 151, 157, 160, 162, 169, 179, 187, 192, 197, 203]:
    t = ''.join(x.text or '' for x in els2[i].iter(qn('w:t')))
    print('[%d] %r' % (i, t[:55]))
