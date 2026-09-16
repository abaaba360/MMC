# -*- coding: utf-8 -*-
"""A题：将5.2/5.3的16个显示公式（式11-26）从Unicode纯文本转为OMML格式。
布局保持与5.1一致：tab居中 + oMath + tab + 右对齐公式号。
"""
import sys, io, copy, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

path = r'd:\数模工作流\delivery\A题_智能评估\A题_数学建模论文智能评估_摘要参考文献版.docx'
doc = Document(path)
body = doc.element.body
els = list(body)

NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

def R(t):
    return ('<m:r><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'
            '<m:t>%s</m:t></m:r>') % t

def _E(x):
    """把裸字符串包成 m:r；已是XML（以'<'开头）的原样返回。"""
    if isinstance(x, str) and x.startswith('<'):
        return x
    return R(x)

def SUB(base, sub):
    return '<m:sSub><m:e>%s</m:e><m:sub>%s</m:sub></m:sSub>' % (_E(base), _E(sub))

def SUP(base, sup):
    return '<m:sSup><m:e>%s</m:e><m:sup>%s</m:sup></m:sSup>' % (_E(base), _E(sup))

def SUBSUP(base, sub, sup):
    return ('<m:sSubSup><m:e>%s</m:e><m:sub>%s</m:sub><m:sup>%s</m:sup></m:sSubSup>'
            % (_E(base), _E(sub), _E(sup)))

def FRAC(num, den):
    return '<m:f><m:num>%s</m:num><m:den>%s</m:den></m:f>' % (_E(num), _E(den))

def NARY(chr_, sub, sup, e, lim='subSup'):
    sub_x = '<m:sub>%s</m:sub>' % _E(sub) if sub else '<m:sub/>'
    sup_x = '<m:sup>%s</m:sup>' % _E(sup) if sup else '<m:sup/>'
    return ('<m:nary><m:naryPr><m:chr m:val="%s"/><m:limLoc m:val="%s"/><m:grow m:val="1"/>'
            '</m:naryPr>%s%s<m:e>%s</m:e></m:nary>') % (chr_, lim, sub_x, sup_x, _E(e))

def RAD(e):
    return ('<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>%s</m:e></m:rad>') % _E(e)

def BAR(e):
    return '<m:bar><m:barPr><m:pos m:val="top"/></m:barPr><m:e>%s</m:e></m:bar>' % _E(e)

def ACC(e):
    return '<m:acc><m:accPr><m:chr m:val="&#770;"/></m:accPr><m:e>%s</m:e></m:acc>' % _E(e)

def D(beg, end, e):
    return ('<m:d><m:dPr><m:begChr m:val="%s"/><m:endChr m:val="%s"/></m:dPr>'
            '<m:e>%s</m:e></m:d>') % (beg, end, _E(e))

def build_omath(body):
    return etree.fromstring('<m:oMath %s>%s</m:oMath>' % (NS, body))

def ptext(p):
    return ''.join(t.text or '' for t in p.iter(qn('w:t')))

# ---------------- 各公式 ----------------
# 式(11) Qᵢ(core) = 100(0.30D₁ᵢ + 0.25D₃ᵢ + 0.08D₅ᵢ)/0.63
F11 = (SUB('Q', 'i') + R('(core)') + R('=') +
       FRAC(R('100') + D('(', ')', R('0.30') + SUB('D', '1i') + R('+') + R('0.25') + SUB('D', '3i')
             + R('+') + R('0.08') + SUB('D', '5i')), R('0.63')))

# 式(12) zᵢⱼ = [xᵢⱼ − x̄ⱼ(train,b)]/sⱼ(train,b)
F12 = (SUB('z', 'ij') + R('=') +
       FRAC(D('[', ']', SUB('x', 'ij') + R('−') + SUB(BAR('x'), 'j') + R('(train,b)')),
            SUB('s', 'j') + R('(train,b)')))

# 式(13) Yᵢ(−r) = 100·Σ_{k≠r} WₖDₖᵢ/(1−Wᵣ)
F13 = (SUB('Y', 'i') + R('(−r)') + R('=') + R('100') + R('·') +
       FRAC(NARY('∑', 'k≠r', '', SUB('W', 'k') + SUB('D', 'ki')),
            D('(', ')', R('1') + R('−') + SUB('W', 'r'))))

# 式(14) ρᵣⱼ = Corr{R(Xᵣⱼ), R[Y(−r)]}
F14 = (SUB('ρ', 'rj') + R('=') + R('Corr') +
       D('{', '}', R('R') + D('(', ')', SUB('X', 'rj')) + R(',') + R('R') + D('[', ']', SUB('Y', 'i') + R('(−r)'))))

# 式(15) (β̂₀,β̂)=arg min{Σ_{i∈train} Aᵢ[Qᵢ(core)−β₀−zᵢᵀβ]²+λ‖β‖₂²}
_BH0 = SUB(ACC(R('β')), '0')
_BH = ACC(R('β'))
F15 = D('(', ')', _BH0 + R(',') + _BH) + R('=') + R('arg') + R('min') + \
       D('{', '}', NARY('∑', 'i∈train', '',
            SUB('A', 'i') + SUP(D('[', ']',
                SUB('Q', 'i') + R('(core)') + R('−') + _BH0 + R('−') + SUBSUP('z', 'i', 'T') + R('β')), '2'))
          + R('+') + R('λ') + SUBSUP(D('‖', '‖', R('β')), '2', '2'))

# 式(16) πⱼ = (1/10)Σ_{β=1}^{10} Iⱼ⁽ᵇ⁾
F16 = (SUB('π', 'j') + R('=') + FRAC(R('1'), R('10')) +
       NARY('∑', 'β=1', '10', SUBSUP('I', 'j', '(b)')))

# 式(17) Aᵢ = 2rᵢcᵢ/(rᵢ+cᵢ),  0≤Aᵢ≤1
F17 = (SUB('A', 'i') + R('=') +
       FRAC(R('2') + SUB('r', 'i') + SUB('c', 'i'), D('(', ')', SUB('r', 'i') + R('+') + SUB('c', 'i')))
       + R(',') + R('0') + R('≤') + SUB('A', 'i') + R('≤') + R('1'))

# 式(18) Q̂ᵢ(adj)=Q̄(train)+Aᵢ[Q̂ᵢ−Q̄(train)]
_QH = ACC(R('Q'))
_QH_I = SUB(ACC(R('Q')), 'i')
_QB = BAR(R('Q'))
F18 = (_QH_I + R('(adj)') + R('=') + _QB + R('(train)') + R('+') + SUB('A', 'i') +
       D('[', ']', _QH_I + R('−') + _QB + R('(train)')))

# 式(19) RMSE=√{(1/10)Σ_{i=1}^{10}[Qᵢ(core)−Q̂ᵢ(adj)]²}
_BR = D('[', ']', SUB('Q', 'i') + R('(core)') + R('−') + _QH_I + R('(adj)'))
F19 = (R('RMSE') + R('=') +
       RAD(FRAC(R('1'), R('10')) + NARY('∑', 'i=1', '10', SUP(_BR, '2'))))

# 式(20) MAE=(1/10)Σ_{i=1}^{10}|Qᵢ(core)−Q̂ᵢ(adj)|
F20 = (R('MAE') + R('=') + FRAC(R('1'), R('10')) +
       NARY('∑', 'i=1', '10', D('|', '|', SUB('Q', 'i') + R('(core)') + R('−') + _QH_I + R('(adj)'))))

# 式(21) Sᵢ = 100Σ_{k=1}^{6}WₖDₖᵢ
F21 = (SUB('S', 'i') + R('=') + R('100') +
       NARY('∑', 'k=1', '6', SUB('W', 'k') + SUB('D', 'ki')))

# 式(22) zᵢₕ = |aᵢₕ−mₕ|/(1.4826MADₕ+ε)
F22 = (SUB('z', 'ih') + R('=') +
       FRAC(D('|', '|', SUB('a', 'ih') + R('−') + SUB('m', 'h')),
            D('(', ')', R('1.4826') + SUB('MAD', 'h') + R('+') + R('ε'))))

# 式(23) Tᵢ = Σₕvₕ·min(zᵢₕ,3)/3,   Σₕvₕ=1
F23 = (SUB('T', 'i') + R('=') +
       FRAC(NARY('∑', 'h', '', SUB('v', 'h') + R('·') + R('min') + D('(', ')', SUB('z', 'ih') + R(',') + R('3'))), R('3'))
       + R(',') + NARY('∑', 'h', '', SUB('v', 'h')) + R('=') + R('1'))

# 式(24) Gᵢ = (1/Pᵢ)Σ_{g=1}^{5}ωgNᵢg
F24 = (SUB('G', 'i') + R('=') + FRAC(R('1'), SUB('P', 'i')) +
       NARY('∑', 'g=1', '5', SUB('ω', 'g') + SUB('N', 'ig')))

# 式(25) maxᵤ min_{w∈Ω}{Sᵢ(u,w)−Sᵢ(0,w)}−λΣₖcᵢkuᵢk
F25 = (NARY('max', 'u', '',
       NARY('min', 'w∈Ω', '', D('{', '}', SUB('S', 'i') + R('(u,w)') + R('−') + SUB('S', 'i') + R('(0,w)')))
       + R('−') + R('λ') + NARY('∑', 'k', '', SUB('c', 'ik') + SUB('u', 'ik'))))

# 式(26) Iᵢ(q)=[min_{w∈Ω}Sᵢ(q,w), max_{w∈Ω}Sᵢ(q,w)],  q∈{保守,完整}
F26 = (SUB('I', 'i') + R('(q)') + R('=') +
       D('[', ']', NARY('min', 'w∈Ω', '', SUB('S', 'i') + R('(q,w)')) + R(',')
         + NARY('max', 'w∈Ω', '', SUB('S', 'i') + R('(q,w)')))
       + R(',') + R('q') + R('∈') + D('{', '}', R('保守') + R(',') + R('完整')))

FORMULAS = {118: F11, 126: F12, 130: F13, 132: F14, 140: F15, 143: F16, 147: F17,
            149: F18, 153: F19, 154: F20, 164: F21, 172: F22, 174: F23, 182: F24,
            189: F25, 191: F26}

def rebuild_formula(p, omath_body):
    """保留 pPr + [tab run] + oMath + [tab run] + 公式号。
    定位方式：取第1、第2个tab run，公式区 = 两者之间的全部run。
    """
    runs = p.findall(qn('w:r'))
    tab_idx = [i for i, r in enumerate(runs) if r.find(qn('w:tab')) is not None]
    assert len(tab_idx) >= 2, '元素tab不足: %r' % tab_idx
    a, b = tab_idx[0], tab_idx[1]
    ftext = ''.join((r.find(qn('w:t')).text or '') if r.find(qn('w:t')) is not None else ''
                    for r in runs[a + 1:b])
    assert ftext.strip(), '公式区为空'
    anchor = runs[a]  # 前导tab run（保留原格式）
    for r in runs[a + 1:b]:   # 移除公式run区
        p.remove(r)
    om = build_omath(omath_body)
    anchor.addnext(om)        # 插入oMath，紧随其后的是第二个tab run和公式号

for idx, bodyf in FORMULAS.items():
    p = els[idx]
    rebuild_formula(p, bodyf)
    print('[%d] 式已转OMML' % idx)

doc.save(path)
print('已保存:', path)

# ---------------- 校验 ----------------
doc2 = Document(path)
els2 = list(doc2.element.body)
for idx in sorted(FORMULAS):
    e = els2[idx]
    om = len(list(e.iter(qn('m:oMath'))))
    mt = ''.join(t.text or '' for t in e.iter(qn('m:t')))
    wt = ''.join(t.text or '' for t in e.iter(qn('w:t')))
    print('[%d] oMath=%d mText=%r 残留wText=%r' % (idx, om, mt[:60], wt[:20]))
