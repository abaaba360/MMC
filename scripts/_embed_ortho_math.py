# -*- coding: utf-8 -*-
"""B题：将[74]正交分解公式组 与 [133]w向量/Σwj 转为行内OMML公式"""
import sys, io, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

path = r"delivery\B题_芯片散热优化\B题_高性能芯片热管理系统优化_摘要参考文献版.docx"
NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

def R(t):
    return ('<m:r><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'
            '<m:t>%s</m:t></m:r>') % t

def SUB(base, sub):
    return '<m:sSub><m:e>%s</m:e><m:sub>%s</m:sub></m:sSub>' % (R(base), R(sub))

def SUP(base_inner, sup):
    return '<m:sSup><m:e>%s</m:e><m:sup>%s</m:sup></m:sSup>' % (base_inner, R(sup))

def FRAC(n_inner, d_inner):
    return '<m:f><m:num>%s</m:num><m:den>%s</m:den></m:f>' % (n_inner, d_inner)

def NARY(sub, sup, e):
    sup_x = '<m:sup>%s</m:sup>' % R(sup) if sup else '<m:sup/>'
    return ('<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="subSup"/>'
            '<m:grow m:val="1"/></m:naryPr><m:sub>%s</m:sub>%s<m:e>%s</m:e></m:nary>') % (R(sub), sup_x, e)

def build_omath(body):
    return etree.fromstring('<m:oMath %s>%s</m:oMath>' % (NS, body))

YIJK = SUB('Y', 'ijk')

# ============ [74] 正交分解公式 ============
F_Mrh = SUB('M', 'rh') + R('(i,j)') + R('=') + FRAC(R('1'), R('5')) + NARY('k', '', YIJK)
F_Mrn = SUB('M', 'rn') + R('(i,k)') + R('=') + FRAC(R('1'), R('4')) + NARY('j', '', YIJK)
F_Mhn = SUB('M', 'hn') + R('(j,k)') + R('=') + FRAC(R('1'), R('4')) + NARY('i', '', YIJK)
F_SStotal = SUB('SS', 'total') + R('=') + NARY('i', '', NARY('j', '', NARY('k', '',
            SUP(R('(') + YIJK + R('−') + R('M') + R(')'), '2'))))
F_SSr = SUB('SS', 'r') + R('=') + R('20') + NARY('i', '', SUP(
            R('[') + SUB('M', 'r') + R('(i)') + R('−') + R('M') + R(']'), '2'))
F_SSrh = SUB('SS', 'rh') + R('=') + R('5') + NARY('i', '', NARY('j', '', SUP(
            R('[') + SUB('M', 'rh') + R('(i,j)') + R('−') + SUB('M', 'r') + R('(i)')
            + R('−') + SUB('M', 'h') + R('(j)') + R('+') + R('M') + R(']'), '2')))
F_SSrhn = SUB('SS', 'rhn') + R('=') + SUB('SS', 'total') + R('−') + SUB('SS', 'r') \
            + R('−') + SUB('SS', 'h') + R('−') + SUB('SS', 'n') + R('−') + SUB('SS', 'rh') \
            + R('−') + SUB('SS', 'rn') + R('−') + SUB('SS', 'hn')
F_eta = R('η(E)') + R('=') + FRAC(R('SS(E)'), SUB('SS', 'total')) + R('×') + R('100%')

P74 = [
    ('t', '正交分解中，令'), ('m', F_Mrh), ('t', '，'), ('m', F_Mrn), ('t', '，'), ('m', F_Mhn),
    ('t', '，且'), ('m', F_SStotal), ('t', '；'), ('m', F_SSr), ('t', '，'), ('m', F_SSrh),
    ('t', '，其余项同理；'), ('m', F_SSrhn),
    ('t', '。贡献率'), ('m', F_eta),
    ('t', '。因每个组合仅一个响应，三阶交互与随机误差不可分，故贡献率仅比较网格内各效应的相对大小，不作显著性检验。'),
]

# ============ [133] 固定极值 / w向量 / Σwj ============
def eq(sub_base, sub_sym, val):
    return SUB(sub_base, sub_sym) + R('=') + R(val)

F_W = R('w') + R('=') + R('(') + FRAC(R('1'), R('3')) + R(',') + FRAC(R('1'), R('3')) \
        + R(',') + FRAC(R('1'), R('3')) + R(')')
F_WJGE = SUB('w', 'j') + R('≥') + R('0')
F_SIGW = NARY('j', '', SUB('w', 'j')) + R('=') + R('1')
F_RHO = R('ρ') + R('=') + R('0.01')

P133 = [
    ('t', '固定观测极值为：'),
    ('m', eq('R', 'min', '0.721922')), ('t', '、'), ('m', eq('R', 'max', '0.773783')),
    ('t', '，'), ('m', eq('P', 'min', '0.076688')), ('t', '、'), ('m', eq('P', 'max', '0.204048')),
    ('t', '，'), ('m', eq('T', 'min', '0.774010')), ('t', '、'), ('m', eq('T', 'max', '0.873100')),
    ('t', '。取'), ('m', F_W), ('t', '，满足'), ('m', F_WJGE), ('t', '且'), ('m', F_SIGW),
    ('t', '；增广系数'), ('m', F_RHO), ('t', '。'),
]

doc = Document(path)
body = doc.element.body
els = list(body)

def rebuild(p, parts):
    """parts: [('t', text)|('m', body_xml)]; 用原段落首run作文字模板"""
    runs = p.findall(qn('w:r'))
    tpl = runs[0] if runs else None
    for r in runs:
        p.remove(r)
    if tpl is not None:
        # 从文档detach模板的引用，克隆成新run
        pass
    ppr = p.find(qn('w:pPr'))
    anchor = ppr if ppr is not None else p[0] if len(p) else None
    for kind, content in parts:
        if kind == 't':
            nr = copy.deepcopy(tpl) if tpl is not None else None
            if nr is None:
                nr = etree.SubElement(p, qn('w:r'))
            nt = nr.find(qn('w:t'))
            if nt is None:
                nt = etree.SubElement(nr, qn('w:t'))
            nt.text = content
            anchor.addnext(nr)
            anchor = nr
        else:
            om = build_omath(content)
            anchor.addnext(om)
            anchor = om

rebuild(els[74], P74)
print('[74] 正交分解公式组已转为OMML')
rebuild(els[133], P133)
print('[133] 极值/w向量/Σwj公式已转为OMML')

doc.save(path)
print('已保存:', path)

# ---------- 校验 ----------
doc2 = Document(path)
els2 = list(doc2.element.body)
for idx in (74, 133):
    om = len(list(els2[idx].iter(qn('m:oMath'))))
    mt = ''.join(t.text or '' for t in els2[idx].iter(qn('m:t')))
    print('[%d] oMath=%d mText=%r' % (idx, om, mt))
