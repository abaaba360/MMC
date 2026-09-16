# -*- coding: utf-8 -*-
"""A题：正文插入上标引用编号（10条参考文献对应锚点）+ 处理整合严谨版残留的字面[2][5][10]"""
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

def make_sup_run(target, sup_text):
    sr = copy.deepcopy(target)
    st = sr.find(qn('w:t')); st.text = sup_text
    rPr = sr.find(qn('w:rPr'))
    if rPr is None:
        rPr = OxmlElement('w:rPr'); sr.insert(0, rPr)
    for tag in ('w:i', 'w:iCs'):
        e = rPr.find(qn(tag))
        if e is not None:
            rPr.remove(e)
    va = rPr.find(qn('w:vertAlign'))
    if va is None:
        va = OxmlElement('w:vertAlign'); rPr.append(va)
    va.set(qn('w:val'), 'superscript')
    return sr

def insert_superscript(p, anchor, sup_text):
    """在anchor文本结束后插入上标引用run（仅处理w:r文本run，保留OMML）"""
    runs = p.findall(qn('w:r'))
    texts = []
    for r in runs:
        t = r.find(qn('w:t'))
        texts.append(t.text if t is not None and t.text else '')
    full = ''.join(texts)
    pos = full.find(anchor)
    if pos < 0:
        raise ValueError('锚点未找到: %r in %r' % (anchor[:15], full[:60]))
    end = pos + len(anchor)
    acc = 0; target = None; in_off = 0
    for r, txt in zip(runs, texts):
        nxt = acc + len(txt)
        if nxt >= end:
            target = r; in_off = end - acc; break
        acc = nxt
    if target is None:
        raise ValueError('锚点超出段落末尾')
    t = target.find(qn('w:t'))
    full_text = t.text or ''
    if in_off > 0 and in_off < len(full_text):
        prefix, suffix = full_text[:in_off], full_text[in_off:]
        t.text = prefix
        nr = copy.deepcopy(target); nt = nr.find(qn('w:t')); nt.text = suffix
        sr = make_sup_run(target, sup_text)
        target.addnext(sr); sr.addnext(nr)
    elif in_off == 0:
        sr = make_sup_run(target, sup_text); target.addprevious(sr)
    else:
        sr = make_sup_run(target, sup_text); target.addnext(sr)

def replace_bracket_with_sup(p, bracket, sup_text):
    """把段落中字面 [x] 改为上标 sup_text（保留OMML）"""
    truns = []
    for r in p.findall(qn('w:r')):
        t = r.find(qn('w:t'))
        if t is not None and t.text:
            truns.append((r, t))
    full = ''.join(t.text for r, t in truns)
    start = full.find(bracket)
    if start < 0:
        raise ValueError('括号未找到: %r in %r' % (bracket, full[:60]))
    end = start + len(bracket)
    # 1) 从runs中删除括号字符
    acc = 0
    for r, t in truns:
        txt = t.text
        nxt = acc + len(txt)
        ov_s, ov_e = max(acc, start), min(nxt, end)
        if ov_s < ov_e:
            t.text = txt[:ov_s - acc] + txt[ov_e - acc:]
        acc = nxt
    # 2) 定位边界：上标插在原start处（删除后前缀长度仍为start）
    acc2 = 0; target = None; in_off = 0
    for r, t in truns:
        txt = t.text if t.text else ''
        nxt = acc2 + len(txt)
        if nxt >= start:
            target = r; in_off = start - acc2; break
        acc2 = nxt
    if target is None:
        raise ValueError('边界未定位')
    t = target.find(qn('w:t'))
    full_text = t.text or ''
    if in_off > 0 and in_off < len(full_text):
        prefix, suffix = full_text[:in_off], full_text[in_off:]
        t.text = prefix
        nr = copy.deepcopy(target); nt = nr.find(qn('w:t')); nt.text = suffix
        sr = make_sup_run(target, sup_text)
        target.addnext(sr); sr.addnext(nr)
    elif in_off == 0:
        sr = make_sup_run(target, sup_text); target.addprevious(sr)
    else:
        sr = make_sup_run(target, sup_text); target.addnext(sr)

# ---------- 1. 字面 [2] (熵权) 与 [5] (自然断点) 转上标；[10]（论文评价规范）删除 ----------
replace_bracket_with_sup(els[86], '[2]', '2')
print('  转换 [2] -> 上标2 @[86] 信息熵')
replace_bracket_with_sup(els[96], '[5]', '4')
print('  转换 [5] -> 上标4 @[96] Fisher-Jenks自然断点法')
# 步骤1 "对齐论文评价规范[10]"：移除括号，不引外部文献
els69 = els[69]
txt69 = ptext(els69)
if '[10]' in txt69:
    replace_bracket_with_sup(els69, '[10]', '')
    # 移除空上标run
    for r in els69.findall(qn('w:r')):
        t = r.find(qn('w:t'))
        if t is not None and (t.text or '') == '' and r.find(qn('w:rPr')) is not None \
           and r.find(qn('w:rPr')).find(qn('w:vertAlign')) is not None:
            els69.remove(r)
    print('  移除 [10] @[69] 论文评价规范（内部规范，不引文献）')
else:
    print('  [69] 无 [10]，跳过')

# ---------- 2. 上标引用 ----------
CITATIONS = [
    (9,  "教育评价与学术写作场景", "[8]"),   # 问题重述 新一代AI规划
    (23, "Bootstrap", "[9]"),                # 2.1 Bootstrap
    (28, "层次体系", "[1]"),                 # 2.2 层次分析法
    (34, "Bootstrap", "[9]"),                # 2.4 Bootstrap
    (31, "Spearman秩相关", "[6]"),           # 2.3 Spearman
    (81, "层次分析法", "[1]"),               # 5.1.2 步骤3 AHP
    (107, "调整兰德指数ARI", "[5]"),         # 5.1.4 ARI
    (131, "Spearman相关系数", "[6]"),        # 5.2.3 Spearman
    (133, "Benjamini-Hochberg方法", "[7]"),  # 5.2.3 FDR
    (139, "岭回归", "[3]"),                  # 5.2.4 岭回归
]
for idx, anchor, sup in CITATIONS:
    insert_superscript(els[idx], anchor, sup)
    print('  插入上标 %s @[%d] after %s...' % (sup, idx, anchor[:12]))

# 6.3(2) 的 Bootstrap 重采样 —— 按文本定位
for i, e in enumerate(els):
    if ptext(e).startswith('（2）预测模型三重稳健性'):
        insert_superscript(e, 'Bootstrap', '[9]')
        print('  插入上标 [9] @[%d] 6.3 Bootstrap重采样' % i)
        break

doc.save(path)
print('已保存:', path)

# ---------- 校验 ----------
doc2 = Document(path)
els2 = list(doc2.element.body)
n_sup = 0
for i, e in enumerate(els2):
    sups = [r for r in e.findall(qn('w:r')) if r.find(qn('w:rPr')) is not None
            and r.find(qn('w:rPr')).find(qn('w:vertAlign')) is not None]
    if sups:
        txts = [r.find(qn('w:t')).text or '' for r in sups]
        print('[%d] 上标: %s  ->  %s' % (i, ' '.join(txts), ptext(e)[:40]))
        n_sup += len(sups)
print('上标引用总数: %d' % n_sup)
