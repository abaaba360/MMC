# -*- coding: utf-8 -*-
"""B题：将边际均值公式 M_r/M_h/M_n 与总均值 M 嵌入为 OMML 公式"""
import sys, io, shutil, os, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

path = r"delivery\B题_芯片散热优化\B题_高性能芯片热管理系统优化_摘要参考文献版.docx"
bak = r"delivery\B题_芯片散热优化\B题_高性能芯片热管理系统优化_摘要参考文献版_公式修改前备份.docx"
shutil.copy2(path, bak)
os.chmod(bak, 0o666)
print('已备份 ->', bak)

NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

def R(t):
    return ('<m:r><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'
            '<m:t>%s</m:t></m:r>') % t

def SUB(base, sub):
    return '<m:sSub><m:e>%s</m:e><m:sub>%s</m:sub></m:sSub>' % (R(base), R(sub))

def FRAC(n, d):
    return '<m:f><m:num>%s</m:num><m:den>%s</m:den></m:f>' % (R(n), R(d))

def NARY(sub, sup, e):
    sup_x = '<m:sup>%s</m:sup>' % R(sup) if sup else '<m:sup/>'
    return ('<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="subSup"/>'
            '<m:grow m:val="1"/></m:naryPr><m:sub>%s</m:sub>%s<m:e>%s</m:e></m:nary>') % (R(sub), sup_x, e)

def build_omath(body):
    return etree.fromstring('<m:oMath %s>%s</m:oMath>' % (NS, body))

def build_omathpara(body):
    return etree.fromstring('<m:oMathPara %s><m:oMathParaPr><m:jc m:val="center"/></m:oMathParaPr>'
                            '<m:oMath>%s</m:oMath></m:oMathPara>' % (NS, body))

YIJK = SUB('Y', 'ijk')

def margin(sub_sym, arg, denom, s1, s2, lim1, lim2):
    """M_sub(arg) = (1/denom) Σ_{lim1}^{s1} Σ_{lim2}^{s2} Y_ijk"""
    return (SUB('M', sub_sym) + R('(' + arg + ')') + R('=') + FRAC('1', denom)
            + NARY(lim1, s1, NARY(lim2, s2, YIJK)))

F1 = margin('r', 'i', '20', '4', '5', 'j=1', 'k=1')   # M_r(i)=(1/20)Σ_{j=1}^{4}Σ_{k=1}^{5}Y_ijk
F2 = margin('h', 'j', '20', '4', '5', 'i=1', 'k=1')   # M_h(j)=(1/20)Σ_{i=1}^{4}Σ_{k=1}^{5}Y_ijk
F3 = margin('n', 'k', '16', '4', '4', 'i=1', 'j=1')   # M_n(k)=(1/16)Σ_{i=1}^{4}Σ_{j=1}^{4}Y_ijk
F4 = (R('M') + R('=') + FRAC('1', '80')
      + NARY('i', '', NARY('j', '', NARY('k', '', YIJK))))  # M=(1/80)Σ_iΣ_jΣ_k Y_ijk

doc = Document(path)
body = doc.element.body
els = list(body)

# ---------- 1. [67] 段落内 "总体均值M=...Yijk" -> inline oMath ----------
p67 = els[67]
runs67 = p67.findall(qn('w:r'))
texts67 = [(r.find(qn('w:t')).text or '') if r.find(qn('w:t')) is not None else '' for r in runs67]
start = next(i for i, t in enumerate(texts67) if t == 'M')
end = next(i for i in range(start, len(texts67)) if texts67[i] == 'ijk')
assert ''.join(texts67[start:end + 1]) == 'M=(1/80)ΣiΣjΣkYijk', texts67[start:end+1]
anchor = runs67[start - 1]
omath4 = build_omath(F4)
anchor.addnext(omath4)
for i in range(start, end + 1):
    p67.remove(runs67[i])
print('[67] 总体均值公式已转为行内OMML')

# ---------- 2. [68][69][70] 整段替换为 oMathPara ----------
for idx, bodyf in ((68, F1), (69, F2), (70, F3)):
    p = els[idx]
    for r in p.findall(qn('w:r')):
        p.remove(r)
    ppr = p.find(qn('w:pPr'))
    omp = build_omathpara(bodyf)
    if ppr is not None:
        ppr.addnext(omp)
    else:
        p.insert(0, omp)
print('[68][69][70] 三个边际均值公式已转为OMML')

doc.save(path)
print('已保存:', path)

# ---------- 校验 ----------
doc2 = Document(path)
els2 = list(doc2.element.body)
for idx in (67, 68, 69, 70):
    om = len(list(els2[idx].iter(qn('m:oMath'))))
    mt = ''.join(t.text or '' for t in els2[idx].iter(qn('m:t')))
    wt = ''.join(t.text or '' for t in els2[idx].iter(qn('w:t')))
    print('[%d] oMath=%d mText=%r' % (idx, om, mt))
    if wt.strip():
        print('     残留wText=%r' % wt[:60])
