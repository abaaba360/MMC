# -*- coding: utf-8 -*-
"""A题终稿：六章起正文段落格式规范化。
- jc 统一 both（两端对齐，同5.x正文）
- 去除run显式 rFonts（黑体/微软雅黑等），继承默认样式（同5.x正文）
- 移除纯空run
标题、参考文献条目、表格保持原样。
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

start = None
for i, el in enumerate(els):
    if el.tag == qn('w:p') and pt(el).strip() == '六、模型检验与结果分析':
        start = i
        break

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
    # ---- 正文 ----
    changed = []
    # 1. jc=both
    ppr = el.find(qn('w:pPr'))
    if ppr is None:
        ppr = OxmlElement('w:pPr')
        el.insert(0, ppr)
    jc = ppr.find(qn('w:jc'))
    if jc is None:
        jc = OxmlElement('w:jc')
        ppr.append(jc)
    if jc.get(qn('w:val')) != 'both':
        changed.append('jc %s->both' % jc.get(qn('w:val')))
        jc.set(qn('w:val'), 'both')
    # 2. 去除run显式rFonts
    n_rf = 0
    for r in el.findall(qn('w:r')):
        rpr = r.find(qn('w:rPr'))
        if rpr is not None and rpr.find(qn('w:rFonts')) is not None:
            rpr.remove(rpr.find(qn('w:rFonts')))
            n_rf += 1
    if n_rf:
        changed.append('去rFonts x%d' % n_rf)
    # 3. 移除纯空run（无w:t、无drawing、无tab、无br、无symbol）
    for r in list(el.findall(qn('w:r'))):
        has_content = (
            r.find(qn('w:t')) is not None or
            r.find(qn('w:tab')) is not None or
            r.find(qn('w:br')) is not None or
            r.find(qn('w:drawing')) is not None or
            r.find(qn('w:pict')) is not None or
            r.find(qn('w:object')) is not None
        )
        if not has_content:
            el.remove(r)
            changed.append('去空run')
    if changed:
        fixed.append((i, ';'.join(changed), t[:20]))

print('规范化正文段落 %d 个：' % len(fixed))
for i, c, t in fixed:
    print('  [%d] %s  %r' % (i, c, t))

doc.save(OUT)
print('已保存:', OUT)
