# -*- coding: utf-8 -*-
"""A题：重写参考文献（10条，全部URL已逐一核对）+ 修正AI声明引用编号 [12]->[10]"""
import sys, io, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

path = r'd:\数模工作流\delivery\A题_智能评估\A题_数学建模论文智能评估_摘要参考文献版.docx'
doc = Document(path)
body = doc.element.body
els = list(body)

ai_note = els[248]   # "本次使用的人工智能工具已在参考文献[12]中列出。"
ref_title = els[250] # 参考文献 标题
ref_tpl = els[251]   # 旧参考文献[1]段落模板
old_refs = [els[i] for i in range(251, 263)]

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

# ---------- 1. AI声明 [12] -> [10] ----------
ai_text = ''.join(t.text or '' for t in ai_note.iter(qn('w:t')))
assert '参考文献[12]' in ai_text, repr(ai_text)
set_text(ai_note, ai_text.replace('参考文献[12]', '参考文献[10]'))
print('AI声明已更新: %r' % ai_text.replace('参考文献[12]', '参考文献[10]'))

# ---------- 2. 重写参考文献（10条，GB/T 7714-2015，附已核对网址） ----------
REFS = [
    "[1] Saaty T L. Decision making with the analytic hierarchy process[J]. International Journal of Services Sciences, 2008, 1(1): 83-98. https://doi.org/10.1504/IJSSCI.2008.017590",
    "[2] Shannon C E. A mathematical theory of communication[J]. The Bell System Technical Journal, 1948, 27(3): 379-423. https://doi.org/10.1002/j.1538-7305.1948.tb01338.x",
    "[3] Hoerl A E, Kennard R W. Ridge regression: biased estimation for nonorthogonal problems[J]. Technometrics, 1970, 12(1): 55-67. https://doi.org/10.1080/00401706.1970.10488634",
    "[4] Fisher W D. On grouping for maximum homogeneity[J]. Journal of the American Statistical Association, 1958, 53(284): 789-798. https://doi.org/10.1080/01621459.1958.10501479",
    "[5] Hubert L, Arabie P. Comparing partitions[J]. Journal of Classification, 1985, 2(1): 193-218. https://doi.org/10.1007/BF01908075",
    "[6] Spearman C. The proof and measurement of association between two things[J]. The American Journal of Psychology, 1904, 15(1): 72-101. https://doi.org/10.2307/1412159",
    "[7] Benjamini Y, Hochberg Y. Controlling the false discovery rate: a practical and powerful approach to multiple testing[J]. Journal of the Royal Statistical Society: Series B, 1995, 57(1): 289-300. https://doi.org/10.1111/j.2517-6161.1995.tb02031.x",
    "[8] 中华人民共和国国务院. 新一代人工智能发展规划[R]. 北京, 2017. https://www.gov.cn/zhengce/content/2017-07/20/content_5211996.htm",
    "[9] Efron B, Tibshirani R J. An introduction to the bootstrap[M]. New York: Chapman & Hall, 1993. https://doi.org/10.1201/9780429246593",
    "[10] Claude Code, Opus 5, Anthropic, 2026-08-21. (AI工具，使用声明见附录D)",
]

template = copy.deepcopy(ref_tpl)
for rp in old_refs:
    body.remove(rp)
prev = ref_title
for text in REFS:
    np = copy.deepcopy(template)
    set_text(np, text)
    prev.addnext(np)
    prev = np
print('参考文献重写完成: %d条' % len(REFS))

doc.save(path)
print('已保存:', path)
