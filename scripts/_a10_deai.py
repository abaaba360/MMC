# -*- coding: utf-8 -*-
"""A题：去AI味——删除自指式结构宣言与填充衔接词，只保留必要表述。
- [63] 五章开头：删"针对三个子问题，"与"每节按...五段式结构展开，给出完整的建模、求解、验证与结论。"
- [97] 5.1.2结尾：删"综上所述，"与"接下来"
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn

path = r'd:\数模工作流\delivery\A题_智能评估\A题_数学建模论文智能评估_摘要参考文献版.docx'
doc = Document(path)
els = list(doc.element.body)

def ptext(p):
    return ''.join(t.text or '' for t in p.iter(qn('w:t')))

# [63] 五章开头
p = els[63]
runs = p.findall(qn('w:r'))
assert '本章针对三个子问题' in (runs[0].find(qn('w:t')).text or ''), ptext(p)[:30]
runs[0].find(qn('w:t')).text = '本章依次建立质量综合评价指标体系与自动评分模型（'
assert '节），每节按' in (runs[8].find(qn('w:t')).text or ''), 'run8异常: %r' % (runs[8].find(qn('w:t')).text or '')
runs[8].find(qn('w:t')).text = '节）。'
for r in runs[9:]:
    p.remove(r)
print('[63] 精简后: %r' % ptext(p))

# [97] 5.1.2结尾
p = els[97]
runs = p.findall(qn('w:r'))
t0 = runs[0].find(qn('w:t'))
assert '综上所述，本节建立了' in (t0.text or ''), 'run0异常: %r' % (t0.text or '')
t0.text = '本节建立'
t10 = runs[10].find(qn('w:t'))
assert '的评分模型，接下来基于' in (t10.text or ''), 'run10异常: %r' % (t10.text or '')
t10.text = '的评分模型，基于'
print('[97] 精简后: %r' % ptext(p))

doc.save(path)
print('已保存:', path)
