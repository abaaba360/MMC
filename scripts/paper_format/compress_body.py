# -*- coding: utf-8 -*-
"""正文压缩：行距/段距/图片尺寸。不动附录代码表（它们有显式 386 exact 行距）。
用法: python compress_body.py [LINE_FACTOR] [SPACE_FACTOR] [IMG_FACTOR]
"""
import sys, io, os, re, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Emu

SRC = r'D:\数模工作流\tmp\base_appendix.docx'      # 纯净底稿（附录已重建、未压缩）
OUT = r'D:\数模工作流\tmp\C题论文_国奖附录版.docx'     # 输出

LINE_FACTOR = float(sys.argv[1]) if len(sys.argv) > 1 else 0.86
SPACE_FACTOR = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
IMG_FACTOR = float(sys.argv[3]) if len(sys.argv) > 3 else 0.86

BODY_LINE_TW = int(round(360 * LINE_FACTOR))   # Normal 原 1.5 行 = 360 twips auto

_p_order = ['pStyle', 'keepNext', 'keepLines', 'pageBreakBefore', 'framePr', 'widowControl',
            'numPr', 'suppressLineNumbers', 'pBdr', 'shd', 'tabs', 'suppressAutoHyphens',
            'kinsoku', 'wordWrap', 'overflowPunct', 'topLinePunct', 'autoSpaceDE',
            'autoSpaceDN', 'bidi', 'adjustRightInd', 'snapToGrid', 'spacing', 'ind',
            'contextualSpacing', 'mirrorIndents', 'suppressOverlap', 'jc', 'textDirection',
            'textAlignment', 'textboxTightWrap', 'outlineLvl', 'divId', 'cnfStyle', 'rPr']


def ins_ordered(parent, child, order):
    tag = child.tag.split('}')[-1]
    try:
        idx = order.index(tag)
    except ValueError:
        parent.append(child)
        return child
    for ex in list(parent):
        et = ex.tag.split('}')[-1]
        try:
            ei = order.index(et)
        except ValueError:
            continue
        if ei > idx:
            ex.addprevious(child)
            return child
    parent.append(child)
    return child


def scale_spacing(sp, line_scale=None, space_scale=None):
    """按比例缩小 w:spacing 的 line/before/after"""
    changed = []
    if line_scale is not None:
        ln = sp.get(qn('w:line'))
        rule = sp.get(qn('w:lineRule'))
        if ln and rule == 'auto':
            nv = max(200, int(round(int(ln) * line_scale)))
            sp.set(qn('w:line'), str(nv))
            changed.append('line %s->%s' % (ln, nv))
    if space_scale is not None:
        for tag in ('w:before', 'w:after'):
            v = sp.get(qn(tag))
            if v is not None:
                nv = int(round(int(v) * space_scale))
                sp.set(qn(tag), str(nv))
                changed.append('%s %s->%s' % (tag[2:], v, nv))
        # beforeLines/afterLines
        for tag in ('w:beforeLines', 'w:afterLines'):
            v = sp.get(qn(tag))
            if v is not None:
                sp.set(qn(tag), str(max(0, int(round(int(v) * space_scale)))))
    return changed


def main():
    doc = Document(SRC)

    # 1) 找出「附录 B」锚点（其后表格不动）；以及第一个 Heading 1 之前的内容（摘要页，保持原间距）
    body = doc.element.body
    kids = list(body)
    anchor_i = None
    first_h1 = None
    for i, ch in enumerate(kids):
        if ch.tag == qn('w:p'):
            txt = ''.join(t.text or '' for t in ch.iter(qn('w:t')))
            if anchor_i is None and txt.strip().startswith('附录 B'):
                anchor_i = i
            pPr = ch.find(qn('w:pPr'))
            ps = pPr.find(qn('w:pStyle')) if pPr is not None else None
            if (first_h1 is None and ps is not None
                    and ps.get(qn('w:val')) in ('1', 'Heading1')):
                first_h1 = i
    print('附录B 锚点位置: %s / %d ; 第一个 Heading1: %s' % (anchor_i, len(kids), first_h1))
    protected = set()
    if anchor_i is not None:
        for ch in kids[anchor_i:]:
            if ch.tag == qn('w:tbl'):
                protected.add(id(ch))
    abstract = set()
    if first_h1 is not None:
        for ch in kids[:first_h1]:
            abstract.add(id(ch))

    # 2) 样式层：Normal 行距 + 各级标题段距
    for sname, lf, sf in (('Normal', LINE_FACTOR, None),
                          ('Heading 1', None, SPACE_FACTOR),
                          ('Heading 2', None, SPACE_FACTOR),
                          ('Heading 3', None, SPACE_FACTOR)):
        try:
            st = doc.styles[sname]
        except KeyError:
            continue
        pPr = st.element.find(qn('w:pPr'))
        if pPr is None:
            pPr = ins_ordered(st.element, OxmlElement('w:pPr'), ['pPr', 'rPr', 'tblPr'])
        sp = pPr.find(qn('w:spacing'))
        if sp is None:
            sp = ins_ordered(pPr, OxmlElement('w:spacing'), _p_order)
        if sname == 'Normal':
            sp.set(qn('w:line'), str(BODY_LINE_TW))
            sp.set(qn('w:lineRule'), 'auto')
            print('  Normal 行距 -> %d twips auto (%.2f 行)' % (BODY_LINE_TW, BODY_LINE_TW / 240))
        ch = scale_spacing(sp, space_scale=sf)
        if ch:
            print('  %s: %s' % (sname, ch))

    # 3) 段落级：缩放显式 spacing（跳过受保护表格内的段落）
    nlin = nsp = nasb = 0
    for ch in kids:
        if ch.tag == qn('w:tbl'):
            if id(ch) in protected:
                continue
            for p in ch.iter(qn('w:p')):
                pPr = p.find(qn('w:pPr'))
                sp = pPr.find(qn('w:spacing')) if pPr is not None else None
                if sp is not None:
                    r = scale_spacing(sp, line_scale=LINE_FACTOR, space_scale=SPACE_FACTOR)
                    if r:
                        nlin += 1
                else:
                    pass
        elif ch.tag == qn('w:p'):
            pPr = ch.find(qn('w:pPr'))
            # 摘要页（第一个 Heading1 之前）保持原样：不缩放，并显式写回原 1.5 倍行距
            if id(ch) in abstract:
                sp = pPr.find(qn('w:spacing')) if pPr is not None else None
                if sp is None:
                    if pPr is None:
                        pPr = ins_ordered(ch, OxmlElement('w:pPr'), _p_order)
                    sp = ins_ordered(pPr, OxmlElement('w:spacing'), _p_order)
                    sp.set(qn('w:line'), '360')
                    sp.set(qn('w:lineRule'), 'auto')
                nasb += 1
                continue
            style = None
            if pPr is not None:
                ps = pPr.find(qn('w:pStyle'))
                if ps is not None:
                    style = ps.get(qn('w:val'))
            if style and 'heading' in style.lower():
                sp = pPr.find(qn('w:spacing'))
                if sp is not None:
                    scale_spacing(sp, space_scale=SPACE_FACTOR)
                    nsp += 1
                continue
            sp = pPr.find(qn('w:spacing')) if pPr is not None else None
            if sp is not None:
                scale_spacing(sp, line_scale=LINE_FACTOR, space_scale=SPACE_FACTOR)
                nlin += 1
    print('  段落级 spacing 调整: 正文 %d 段, 标题 %d 段, 摘要页保留 %d 段' % (nlin, nsp, nasb))

    # 4) 图片缩放
    nimg = 0
    for sh in doc.inline_shapes:
        try:
            sh.width = Emu(int(sh.width * IMG_FACTOR))
            sh.height = Emu(int(sh.height * IMG_FACTOR))
            nimg += 1
        except Exception as e:
            print('  图片缩放失败', e)
    print('  图片缩放 %d 张 x %.2f' % (nimg, IMG_FACTOR))

    doc.save(OUT)
    print('已保存:', OUT, os.path.getsize(OUT))


main()
