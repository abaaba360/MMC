# -*- coding: utf-8 -*-
"""A题终稿：六章起（六/七/声明/参考文献/附录）正文段落首行缩进统一482。
标题（章节/子标题/AI工具使用声明/使用情况/声明/参考文献/附录）、参考文献条目、表图标题保持无缩进。
"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = r'd:\数模工作流\delivery\A题_智能评估\终稿\A题_数学建模论文_终稿.docx'
doc = Document(OUT)
els = list(doc.element.body)

def pt(el):
    return ''.join(t.text or '' for t in el.iter(qn('w:t')))

HEAD_EXACT = {'AI工具使用声明', '使用情况', '声明', '参考文献', '附录'}
def is_heading(s):
    if s in HEAD_EXACT:
        return True
    if re.match(r'^[一二三四五六七八九十]+、', s):
        return True
    if re.match(r'^\d+(\.\d+)*\s+\S', s):
        return True
    if s.startswith('附录'):
        return True
    return False

def set_firstline(p, val='482'):
    ppr = p.find(qn('w:pPr'))
    if ppr is None:
        ppr = OxmlElement('w:pPr')
        p.insert(0, ppr)
    ind = ppr.find(qn('w:ind'))
    if ind is None:
        ind = OxmlElement('w:ind')
        ppr.append(ind)
    ind.set(qn('w:firstLine'), val)

# 定位六章起点
start = None
for i, el in enumerate(els):
    if el.tag == qn('w:p') and pt(el).strip() == '六、模型检验与结果分析':
        start = i
        break
assert start is not None, '未找到六章起点'
print('六章起点元素[%d]' % start)

fixed = []
for i in range(start, len(els)):
    el = els[i]
    if el.tag != qn('w:p'):
        continue
    t = pt(el).strip()
    if not t:
        continue
    if is_heading(t):
        continue
    if re.match(r'^\[\d+\]', t):
        continue
    if re.match(r'^[表图]\d', t):
        continue
    # 正文
    ppr = el.find(qn('w:pPr'))
    old = None
    if ppr is not None and ppr.find(qn('w:ind')) is not None:
        old = ppr.find(qn('w:ind')).get(qn('w:firstLine'))
    set_firstline(el, '482')
    fixed.append((i, old, t[:25]))

print('修正正文段落 %d 个：' % len(fixed))
for i, old, t in fixed:
    print('  [%d] %s -> 482  %r' % (i, old, t))

doc.save(OUT)
print('已保存:', OUT)
