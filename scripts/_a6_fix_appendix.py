# -*- coding: utf-8 -*-
"""A题：修复两处过期附录引用。
1) 参考文献末尾追加 [11] GB/T 7714—2025（现行标准，2025-12-02发布、2026-07-01实施，
   全部代替已废止的GB/T 7714—2015；附录C表格中的"GB/T 7714合规度[11]"据此指向新标准）。
2) 附录D AI工具使用详情：[12]->[10]，日期 2026-08-13->2026-08-21（与参考文献[10]一致）。
幂等：已存在[11]或已修正时自动跳过。
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
    rPr = OxmlElement('w:rPr')
    rf = OxmlElement('w:rFonts'); rf.set(qn('w:cs'), 'Times New Roman'); rPr.append(rf)
    r.append(rPr)
    t = OxmlElement('w:t'); t.set(qn('xml:space'), 'preserve'); t.text = text
    r.append(t)
    p.append(r)

# ---------- 1. 追加 [11] GB/T 7714—2025 ----------
REFS = [ptext(e) for e in els]
if any(txt.startswith('[11]') for txt in REFS):
    print('已存在 [11]，跳过追加')
else:
    ref10 = None
    for i, e in enumerate(els):
        if ptext(e).startswith('[10] Claude Code'):
            ref10 = e
            ref10_idx = i
            break
    assert ref10 is not None, '未找到参考文献 [10] 段落'
    new11 = copy.deepcopy(ref10)
    set_text(new11, "[11] 信息与文献 参考文献著录规则: GB/T 7714—2025[S]. 北京: 中国标准出版社, 2025. "
                    "https://std.samr.gov.cn/gb/search/gbDetailed?id=4507EFE13D37CB6AE06397BE0A0A601F")
    ref10.addnext(new11)
    print('已追加 [11] GB/T 7714—2025 于段落 [%d] 之后' % ref10_idx)

# ---------- 2. 附录D: [12]->[10], 2026-08-13->2026-08-21 ----------
for i, e in enumerate(els):
    txt = ptext(e)
    if '[12]' in txt and 'AI辅助工具' in txt:
        new_txt = txt.replace('参考文献[12]', '参考文献[10]').replace('2026-08-13', '2026-08-21')
        set_text(e, new_txt)
        print('附录D 段落[%d] 已修正: [12]->[10], 2026-08-13->2026-08-21' % i)
        break
else:
    print('未找到含 [12] 的附录D段落（可能已修正）')

doc.save(path)
print('已保存:', path)

# ---------- 校验 ----------
doc2 = Document(path)
els2 = list(doc2.element.body)
refs = [ptext(e) for e in els2 if ptext(e).startswith('[')]
print('参考文献条目数: %d' % len(refs))
for r in refs:
    print('  ' + r[:75])
# 附录C表单元格 [11] 是否仍在
for i, e in enumerate(els2):
    if ptext(e).startswith('参考文献规范度引用密度'):
        print('附录C单元格[%d]: %s' % (i, ptext(e)))
for i, e in enumerate(els2):
    if ptext(e).startswith('《AI工具使用详情》'):
        print('附录D段落[%d] 含[10]: %s, 日期2026-08-21: %s' %
              (i, '[10]' in ptext(e), '2026-08-21' in ptext(e)))
