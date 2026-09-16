# -*- coding: utf-8 -*-
"""将单个 markdown 章节转换为国赛格式 Word (.docx)。

关键处理（避免乱码、公式原生）：
1. $...$  内联公式 → Word 原生 OMML 公式（latex2mathml → MML2OMML.XSL → m:oMath）
2. $$...$$ 块级公式 → 居中 OMML 公式（m:oMathPara）
3. **表N 标题** + 管道表格 → 三线表（表题黑体居中置表上方）
4. ![图题](相对路径) → 居中图片 + 黑体图题置图下方
5. Unicode 上标字符（⁰-⁹ ⁺ ⁻）→ Word 真正的上标格式
6. Unicode 下标字符（₀-₉）→ Word 真正的下标格式
7. ~ 区间号 → 全角 ～（中文规范）
8. **加粗** 段 → 加粗 run
9. # 标题 → 黑体；#/## 居中，### 起左对齐

用法：
    python scripts/md_section_to_docx.py <输入.md> [输出.docx]
"""
import os
import re
import sys
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import latex2mathml.converter as latex2mathml
from lxml import etree

MML2OMML_XSL = "C:/Program Files/Microsoft Office/root/Office16/MML2OMML.XSL"

SUPER_MAP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
             "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁺": "+", "⁻": "-"}
SUB_MAP = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5",
           "₆": "6", "₇": "7", "₈": "8", "₉": "9"}

_XSLT = None


def get_xslt():
    global _XSLT
    if _XSLT is None:
        _XSLT = etree.XSLT(etree.parse(MML2OMML_XSL))
    return _XSLT


def latex_to_omml(latex, display="inline"):
    """LaTeX → OMML 根元素。display='block' 返回 m:oMathPara，inline 返回 m:oMath。"""
    mathml = latex2mathml.convert(latex, display=display)
    mml_root = etree.fromstring(mathml.encode("utf-8"))
    result = get_xslt()(mml_root)
    return result.getroot()


def set_font(run, east_font="宋体", size=12):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), east_font)


def add_plain(p, s, size=12, italic=False, bold=False):
    """普通文本，拆出 Unicode 上/下标字符为独立 run。"""
    buf = ""
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch in SUPER_MAP or ch in SUB_MAP:
            if buf:
                r = p.add_run(buf)
                set_font(r, "宋体", size)
                r.italic, r.bold = italic, bold
                buf = ""
            is_sup = ch in SUPER_MAP
            base = SUPER_MAP.get(ch) or SUB_MAP.get(ch)
            r = p.add_run(base)
            set_font(r, "宋体", size)
            r.italic, r.bold = italic, bold
            r.font.superscript = is_sup
            r.font.subscript = not is_sup
        else:
            buf += ch
        i += 1
    if buf:
        r = p.add_run(buf)
        set_font(r, "宋体", size)
        r.italic, r.bold = italic, bold


def add_math_inline(p, latex, size=12):
    """内联 $...$ → OMML <m:oMath>，追加到段落末尾（保持顺序）。"""
    try:
        omml = latex_to_omml(latex, display="inline")
        p._p.append(omml)
    except Exception as e:
        # 转换失败兜底：西文斜体，绝不残留 $ 等标记
        if latex.strip():
            r = p.add_run(latex.strip())
            set_font(r, "Times New Roman", size)
            r.italic = True


def add_field_number(p):
    """在段落末尾插入公式编号 (N)：AUTONUM 域代码，Word 打开时自动连续编号。"""
    def _r():
        return OxmlElement('w:r')
    r0 = _r()
    t0 = OxmlElement('w:t'); t0.text = '('
    r0.append(t0); p._p.append(r0)
    rb = _r(); fb = OxmlElement('w:fldChar'); fb.set(qn('w:fldCharType'), 'begin'); fb.set(qn('w:dirty'), 'true'); rb.append(fb)
    p._p.append(rb)
    ri = _r(); it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = ' AUTONUM '; ri.append(it)
    p._p.append(ri)
    rs = _r(); fs = OxmlElement('w:fldChar'); fs.set(qn('w:fldCharType'), 'separate'); rs.append(fs)
    p._p.append(rs)
    rv = _r(); tv = OxmlElement('w:t'); tv.text = '1'; rv.append(tv)
    p._p.append(rv)
    re_ = _r(); fe = OxmlElement('w:fldChar'); fe.set(qn('w:fldCharType'), 'end'); re_.append(fe)
    p._p.append(re_)
    r1 = _r()
    t1 = OxmlElement('w:t'); t1.text = ')'
    r1.append(t1); p._p.append(r1)


def add_math_block(doc, latex, size=12):
    """块级 $$...$$ → 公式行：公式居中 + 编号右对齐（AUTONUM 自动编号，对齐模板规范）。"""
    from docx.enum.text import WD_TAB_ALIGNMENT
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    # 内容区宽16cm：中心制表位8cm使公式居中，右侧制表位16cm使编号右对齐
    pf.tab_stops.add_tab_stop(Cm(8.0), WD_TAB_ALIGNMENT.CENTER)
    pf.tab_stops.add_tab_stop(Cm(16.0), WD_TAB_ALIGNMENT.RIGHT)
    # 跳到中心制表位 → 公式（内联 oMath）
    rt = p.add_run(); rt._element.append(OxmlElement('w:tab'))
    try:
        omml = latex_to_omml(latex, display="inline")
        p._p.append(omml)
    except Exception as e:
        if latex.strip():
            r = p.add_run(latex.strip())
            set_font(r, "Times New Roman", size)
            r.italic = True
    # 跳到右侧制表位 → 编号 (N)
    r2 = p.add_run(); r2._element.append(OxmlElement('w:tab'))
    add_field_number(p)
    return p


def add_runs(p, text, size=12):
    """按 $...$ 与 **...** 分词后逐段渲染（含内联公式）。"""
    pattern = re.compile(r"(\$[^$]+\$|\*\*[^*]+\*\*)")
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            add_plain(p, text[pos:m.start()], size)
        tok = m.group(1)
        if tok.startswith("$"):
            add_math_inline(p, tok[1:-1], size)
        else:  # **加粗**
            add_plain(p, tok[2:-2], size, bold=True)
        pos = m.end()
    if pos < len(text):
        add_plain(p, text[pos:], size)


def is_table_sep(line):
    return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", line)) and "-" in line


def add_table(doc, rows, caption=None, size=12):
    if caption:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format
        pf.space_before = Pt(6)
        pf.space_after = Pt(2)
        pf.line_spacing = 1.2
        add_runs(p, caption, 10.5)
        for r in p.runs:
            r.bold = True
            rPr = r._element.get_or_add_rPr()
            rFonts = rPr.get_or_add_rFonts()
            rFonts.set(qn("w:eastAsia"), "黑体")
    header = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    ncol = len(header)
    nrow = len(rows) - 1
    table = doc.add_table(rows=nrow + 1, cols=ncol)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(header):
        cell = table.rows[0].cells[j]
        cell.text = ""
        add_runs(cell.paragraphs[0], h, 10.5)
        for r in cell.paragraphs[0].runs:
            r.bold = True
            rPr = r._element.get_or_add_rPr()
            rFonts = rPr.get_or_add_rFonts()
            rFonts.set(qn("w:eastAsia"), "宋体")
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, row in enumerate(rows[1:], start=1):
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        for j in range(ncol):
            val = cells[j] if j < len(cells) else ""
            cell = table.rows[i].cells[j]
            cell.text = ""
            add_runs(cell.paragraphs[0], val, 10.5)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    # 三线表：上粗线、表头下细线、下粗线
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for tag in ("top", "bottom"):
        el = OxmlElement(f"w:{tag}")
        el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "12")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    for tag in ("left", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{tag}")
        el.set(qn("w:val"), "none")
        borders.append(el)
    tblPr.append(borders)
    for cell in table.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = OxmlElement("w:tcBorders")
        b = OxmlElement("w:bottom")
        b.set(qn("w:val"), "single"); b.set(qn("w:sz"), "6"); b.set(qn("w:color"), "000000")
        tcBorders.append(b)
        tcPr.append(tcBorders)


def add_figure(doc, caption, path, base_dir):
    if not os.path.isabs(path):
        cand = os.path.normpath(os.path.join(base_dir, path))
        if os.path.exists(cand):
            path = cand
    if not os.path.exists(path):
        print(f"⚠️ 图片不存在: {path}")
        return False
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before = Pt(6)
    run = p.add_run()
    run.add_picture(path, width=Cm(13.5))
    if caption:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cpf = cp.paragraph_format
        cpf.space_after = Pt(8)
        cpf.line_spacing = 1.2
        add_runs(cp, caption, 10.5)
        for r in cp.runs:
            r.bold = False
            rPr = r._element.get_or_add_rPr()
            rFonts = rPr.get_or_add_rFonts()
            rFonts.set(qn("w:eastAsia"), "黑体")
    return True


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".docx"
    base_dir = os.path.dirname(os.path.abspath(src))

    with open(src, encoding="utf-8") as f:
        lines = f.read().split("\n")

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.5)
    sec.left_margin = sec.right_margin = Cm(2.5)
    style = doc.styles["Normal"]
    style.font.size = Pt(12)
    style.font.name = "宋体"
    rpr = style.element.get_or_add_rPr()
    rFonts = rpr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), "宋体")

    pending_caption = None
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue

        # 表题行：**表N ...**
        mcap = re.match(r"^\*\*表\s*([0-9]+)\s*(.*)\*\*$", s)
        if mcap and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            pending_caption = f"表{mcap.group(1)} {mcap.group(2)}".strip()
            i += 1
            continue

        # 管道表格
        if s.startswith("|") and i + 1 < len(lines) and is_table_sep(lines[i + 1]):
            rows = [s]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            add_table(doc, rows, caption=pending_caption)
            pending_caption = None
            continue

        # 图片
        mimg = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", s)
        if mimg:
            add_figure(doc, mimg.group(1).strip(), mimg.group(2).strip(), base_dir)
            i += 1
            continue

        # 标题
        hm = re.match(r"^(#{1,4})\s+(.+)$", s)
        if hm:
            level = len(hm.group(1))
            text = hm.group(2).strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if level <= 2 else WD_ALIGN_PARAGRAPH.LEFT
            pf = p.paragraph_format
            pf.space_before = Pt(12 if level == 1 else 8)
            pf.space_after = Pt(8 if level == 1 else 6)
            size = {1: 16, 2: 14, 3: 12}.get(level, 12)
            add_plain(p, text, size, bold=True)
            for r in p.runs:
                rPr = r._element.get_or_add_rPr()
                rFonts = rPr.get_or_add_rFonts()
                rFonts.set(qn("w:eastAsia"), "黑体")
            i += 1
            continue

        # 块级公式 $$...$$
        if s.startswith("$$"):
            if s.endswith("$$") and len(s) > 4:
                inner = s[2:-2].strip()
                add_math_block(doc, inner)
                i += 1
            else:
                buf = [s[2:]]
                i += 1
                while i < len(lines) and not lines[i].strip().endswith("$$"):
                    buf.append(lines[i].strip())
                    i += 1
                if i < len(lines):
                    buf.append(lines[i].strip()[:-2])
                    i += 1
                add_math_block(doc, "\n".join(buf))
            continue

        # 普通段落
        s = s.replace("~", "～")
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0.74)
        pf.line_spacing = 1.5
        pf.space_after = Pt(6)
        add_runs(p, s)
        i += 1

    # 声明 m 命名空间，保证 Word 正确识别 OMML 公式
    from docx.oxml import parse_xml
    root = doc.element
    nsmap = root.nsmap
    if "http://schemas.openxmlformats.org/officeDocument/2006/math" not in nsmap.values():
        # 直接向根元素声明命名空间
        root.set(qn("xmlns:m"), "http://schemas.openxmlformats.org/officeDocument/2006/math")

    doc.save(out)
    print(f"✅ 已生成: {out} ({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main()
