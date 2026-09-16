# -*- coding: utf-8 -*-
"""A题终稿：将「六七章重写终稿」的新六/七块移植进「公式上下标修正版」，替换旧六/七块[202-235]。

- 新块来源：重写终稿 元素[215-255]，跳过[239]（AI使用表，声明区已存在同一表格）
- 标题统一：章节标题=黑体居中（克隆[62]五、），子标题=黑体编号+空格+标题（克隆[66]5.1.1）
- 正文统一：首行缩进482 twips，去除误加粗
- 数字一致性：新块0.948→0.95（对应5.1.4与q1结果0.95）、0.808→0.81、0.214→0.21（对应5.1.5与q1结果）
"""
import sys, io, copy, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DST = r'd:\数模工作流\delivery\A题_智能评估\终稿\A题_数学建模论文_公式上下标与上下限最终修正版.docx'
SRC = r'd:\数模工作流\delivery\A题_智能评估\终稿\A题_数学建模论文_六七章重写终稿.docx'
OUT = r'd:\数模工作流\delivery\A题_智能评估\终稿\A题_数学建模论文_终稿.docx'

doc = Document(DST)
body = doc.element.body
els = list(body)

def pt(el):
    return ''.join(t.text or '' for t in el.iter(qn('w:t')))

# ---------- 1. 删除旧六/七块 [202]-[235] ----------
for i in list(range(202, 236)):
    body.remove(els[i])
print('已删除旧块元素 34 个')

els2 = list(body)
anchor = els2[201]
assert pt(anchor).strip() == '', 'anchor非空段: %r' % pt(anchor)[:30]
print('anchor[201]为空段 ✓')

# ---------- 2. 标题模板 ----------
ch_h = copy.deepcopy(els2[62])   # 五、模型建立与求解（黑体居中）
assert pt(ch_h).startswith('五、')
sub_h = copy.deepcopy(els2[66])  # 5.1.1 数据预处理（黑体，run0编号+run1标题）
assert pt(sub_h).startswith('5.1.1')

def make_chapter(text):
    p = copy.deepcopy(ch_h)
    for r in list(p.findall(qn('w:r'))):
        p.remove(r)
    r = OxmlElement('w:r')
    rpr = OxmlElement('w:rPr')
    rf = OxmlElement('w:rFonts')
    for k in ('w:eastAsia', 'w:ascii', 'w:hAnsi'):
        rf.set(qn(k), '黑体')
    rpr.append(rf)
    r.append(rpr)
    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    t.text = text
    r.append(t)
    p.append(r)
    return p

def make_subheading(num, title):
    p = copy.deepcopy(sub_h)
    runs = p.findall(qn('w:r'))
    while len(runs) > 2:
        p.remove(runs.pop())
    runs[0].find(qn('w:t')).text = num
    runs[1].find(qn('w:t')).text = title
    return p

HEADMAP = {
    215: ('ch', '六、模型检验与结果分析'),
    217: ('sub', '6.1 ', '评分模型复现与误差分析'),
    221: ('sub', '6.2 ', '参数与方法敏感性'),
    226: ('sub', '6.3 ', '稳健性检验'),
    231: ('sub', '6.4 ', '检验结论与适用范围'),
    234: ('ch', '七、模型优缺点评价与推广'),
    235: ('sub', '7.1 ', '模型优点'),
    241: ('sub', '7.2 ', '模型局限'),
    246: ('sub', '7.3 ', '模型改进方向'),
    251: ('sub', '7.4 ', '推广与应用'),
}
NUMFIX = {
    222: [('0.948', '0.95')],
    224: [('0.808', '0.81'), ('0.214', '0.21')],
}

# ---------- 3. 组装新块段落 ----------
src_doc = Document(SRC)
src_els = list(src_doc.element.body)

new_paras = []
for i in range(215, 256):
    if i == 239:
        continue
    el = src_els[i]
    assert el.tag == qn('w:p'), '新块含非段落 at %d' % i
    if i in HEADMAP:
        h = HEADMAP[i]
        new_paras.append(make_chapter(h[1]) if h[0] == 'ch' else make_subheading(h[1], h[2]))
        continue
    p = copy.deepcopy(el)
    # 去除正文误加粗
    for r in p.findall(qn('w:r')):
        rpr = r.find(qn('w:rPr'))
        if rpr is not None and rpr.find(qn('w:b')) is not None:
            rpr.remove(rpr.find(qn('w:b')))
    # 首行缩进 482
    ppr = p.find(qn('w:pPr'))
    if ppr is None:
        ppr = OxmlElement('w:pPr')
        p.insert(0, ppr)
    ind = ppr.find(qn('w:ind'))
    if ind is None:
        ind = OxmlElement('w:ind')
        ppr.append(ind)
    ind.set(qn('w:firstLine'), '482')
    # 数字一致性
    if i in NUMFIX:
        for old, new in NUMFIX[i]:
            for t in p.iter(qn('w:t')):
                if t.text and old in t.text:
                    t.text = t.text.replace(old, new)
                    print('  数字修正: %s -> %s' % (old, new))
    new_paras.append(p)

# ---------- 4. 插入到 anchor 之后 ----------
for p in reversed(new_paras):
    anchor.addnext(p)
print('已插入新块段落 %d 个' % len(new_paras))

doc.save(OUT)
print('已保存:', OUT)
