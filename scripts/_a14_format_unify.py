# -*- coding: utf-8 -*-
"""A题论文格式统一脚本（按2026国赛标准Word模板(4)）。

统一规则（模板_4 实测 + 论文既有前端格式）：
- 题目[0]         ：黑体16pt加粗居中（保留不动）
- 摘要标题"摘 要"  ：黑体14pt加粗居中，bef=156 aft=156
- 章标题（一、…七、参考文献、附录、AI工具使用声明）：黑体14pt非加粗居中，bef=156 aft=156
- X.X级小标题     ：黑体12pt非加粗左，bef=156 aft=100
- X.X.X级小标题/附录A-D/使用情况/声明：黑体12pt非加粗左，bef=100 aft=60
- 正文            ：12pt 首行缩进482 两端对齐 行距360(auto) bef=0 aft=0
- 展示公式段       ：保留center/right制表位，jc=both 行距240(auto) bef=60 aft=60
- 图题/表题        ：10.5pt 居中 单倍行距 bef=0 aft=0
- 关键词行         ："关键词："标签黑体加粗，正文宋体；无缩进，两端对齐，行距360
- 参考文献         ：保持不变
- 颜色             ：全文仅黑色；如有非黑显式色则改为000000

用法：python scripts/_a14_format_unify.py <输入docx> <输出docx>
"""
import sys
import io
import re
import shutil
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def set_run_font(run, ea=None, ascii_=None, size_pt=None, bold=None):
    """对 w:r run 设置字体/字号/加粗（不影响 oMath 内 m:r）。"""
    rpr = run._r.get_or_add_rPr()
    if ea is not None or ascii_ is not None:
        rf = rpr.rFonts
        if rf is None:
            rf = rpr.get_or_add_rFonts()
        if ea is not None:
            rf.set(qn("w:eastAsia"), ea)
        if ascii_ is not None:
            rf.set(qn("w:ascii"), ascii_)
            rf.set(qn("w:hAnsi"), ascii_)
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    if bold is not None:
        run.font.bold = bold


def norm_color(run):
    """把 run 显式非黑颜色改为 000000；无显式色不动。返回是否修改。"""
    rpr = run._r.find(qn("w:rPr"))
    if rpr is None:
        return False
    c = rpr.find(qn("w:color"))
    if c is None:
        return False
    v = c.get(qn("w:val"))
    if v and v not in ("000000", "auto"):
        c.set(qn("w:val"), "000000")
        return True
    return False


def set_pf(p, fl=None, jc=None, line=None, bef=None, aft=None):
    """统一段落属性。fl: 'indent'=482首行缩进, 'none'=去首行缩进。line 为倍数(1.0/1.5/1.2等)。"""
    pf = p.paragraph_format
    if fl == "indent":
        pf.first_line_indent = Pt(24.1)  # 482 twips = 2字符(12pt)
    elif fl == "none":
        pf.first_line_indent = None
    if jc == "both":
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    elif jc == "center":
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif jc == "left":
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if line is not None:
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.line_spacing = line
    elif line is False:
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE  # 单倍，移除 line 元素
    if bef is not None:
        pf.space_before = Pt(bef / 20.0)
    if aft is not None:
        pf.space_after = Pt(aft / 20.0)


RE_CHAP = re.compile(r"^[一二三四五六七八九十]+、")
RE_SUB2 = re.compile(r"^\d+\.\d+\s")
RE_SUB3 = re.compile(r"^\d+\.\d+\.\d+\s")
RE_CAP = re.compile(r"^[图表]\d+-\d+\s")
RE_REF = re.compile(r"^\[\d+\]")
RE_APPENDIX = re.compile(r"^附录[ABCD]\s")
CHAP_NAMES = {"摘 要", "参考文献", "附录", "AI工具使用声明"}
SPECIAL_SUB = {"使用情况", "声明"}


def classify(p):
    """返回段落类别。"""
    t = p.text.strip()
    if not t:
        return "empty"
    if RE_CHAP.match(t) or t in CHAP_NAMES:
        return "chap" if t != "摘 要" else "abstract"
    if RE_CAP.match(t):
        return "caption"
    if RE_REF.match(t):
        return "ref"
    if RE_SUB2.match(t) or t in SPECIAL_SUB or RE_APPENDIX.match(t):
        return "sub2"
    if RE_SUB3.match(t):
        return "sub3"
    # 展示公式：含 oMath 且 段落正文仅是"（N）"或含center/right制表位
    if p._p.findall(qn("m:oMath")):
        has_tab = p._p.find(qn("w:pPr")) is not None and p._p.find(
            qn("w:pPr")).find(qn("w:tabs")) is not None
        plain = "".join(x.text or "" for x in p._p.iter(qn("w:t"))).strip()
        if has_tab or re.fullmatch(r"[（(]\d+[）)]", plain):
            return "formula"
        return "body"
    return "body"


def main():
    src, dst = sys.argv[1], sys.argv[2]
    doc = Document(src)
    stats = {"title": 0, "chap": 0, "abstract": 0, "sub2": 0, "sub3": 0,
             "caption": 0, "body": 0, "formula": 0, "ref": 0, "empty": 0,
             "color_fix": 0, "size_fix": 0, "keyword": 0}

    for idx, p in enumerate(doc.paragraphs):
        # 首段为论文题目：黑体16pt加粗居中（模板题目格式），不随正文处理
        if idx == 0 and p.text.strip():
            cls = "title"
        else:
            cls = classify(p)
        stats[cls] += 1

        if cls == "title":
            for r in p.runs:
                set_run_font(r, ea="黑体", ascii_="黑体", size_pt=16, bold=True)
            set_pf(p, fl="none", jc="center", line=None, bef=0, aft=0)
            _remove_line_spacing(p)
        elif cls == "chap":
            for r in p.runs:
                set_run_font(r, ea="黑体", ascii_="黑体", size_pt=14, bold=False)
            set_pf(p, fl="none", jc="center", line=1.0, bef=156, aft=156)
        elif cls == "abstract":
            for r in p.runs:
                set_run_font(r, ea="黑体", ascii_="黑体", size_pt=14, bold=True)
            set_pf(p, fl="none", jc="center", line=1.0, bef=156, aft=156)
        elif cls in ("sub2", "sub3"):
            bef, aft = (156, 100) if cls == "sub2" else (100, 60)
            for r in p.runs:
                set_run_font(r, ea="黑体", ascii_="黑体", size_pt=12, bold=False)
            set_pf(p, fl="none", jc="left", line=1.0, bef=bef, aft=aft)
        elif cls == "caption":
            for r in p.runs:
                set_run_font(r, size_pt=10.5)
                norm_color(r)
            set_pf(p, fl="none", jc="center", line=1.0, bef=0, aft=0)
        elif cls == "body":
            # 首行缩进482、两端对齐、单倍行距（对齐模板）、前后0
            set_pf(p, fl="indent", jc="both", line=None, bef=0, aft=0)
            _remove_line_spacing(p)
            for r in p.runs:
                # 消除异常显式字号：非12pt的都归为12pt
                rpr = r._r.find(qn("w:rPr"))
                sz = None
                if rpr is not None:
                    s = rpr.find(qn("w:sz"))
                    sz = s.get(qn("w:val")) if s is not None else None
                if sz is not None and sz != "24":
                    r.font.size = Pt(12)
                    stats["size_fix"] += 1
                if norm_color(r):
                    stats["color_fix"] += 1
            # 关键词行特殊处理
            if p.text.strip().startswith("关键词"):
                stats["keyword"] += 1
                set_pf(p, fl="none", jc="both", line=None, bef=0, aft=0)
                _remove_line_spacing(p)
                _split_keyword(p)
        elif cls == "formula":
            # 保留center/right制表位；统一 jc=both、行距240、bef=60 aft=60、无首行缩进
            set_pf(p, fl="none", jc="both", line=1.0, bef=60, aft=60)
            _ensure_formula_tabs(p)
        elif cls == "ref":
            pass  # 参考文献保持不变

    # 表格统一：单元格文本统一 10.5pt（五号）居中；无显式字号 → 10.5pt
    table_fix = 0
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        rpr = r._r.find(qn("w:rPr"))
                        sz = None
                        if rpr is not None:
                            s = rpr.find(qn("w:sz"))
                            sz = s.get(qn("w:val")) if s is not None else None
                        if sz is None or sz != "21":
                            r.font.size = Pt(10.5)
                            table_fix += 1
                        norm_color(r)
    print(f"表格单元格字号统一: {table_fix} 个run")

    doc.save(dst)
    print("== 段落分类统计 ==")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\n输出: {dst}")


def _ensure_formula_tabs(p):
    """确保展示公式段有 center/right 制表位（右位=页宽-右边距）。"""
    ppr = p._p.find(qn("w:pPr"))
    if ppr is None:
        return
    tabs = ppr.find(qn("w:tabs"))
    if tabs is not None:
        return
    from docx.oxml import OxmlElement
    t1 = OxmlElement("w:tab")
    t1.set(qn("w:val"), "center")
    t1.set(qn("w:pos"), "4535")
    t2 = OxmlElement("w:tab")
    t2.set(qn("w:val"), "right")
    t2.set(qn("w:pos"), "8901")
    tabsel = OxmlElement("w:tabs")
    tabsel.append(t1)
    tabsel.append(t2)
    ppr.insert(0, tabsel)


def _remove_line_spacing(p):
    """移除 w:spacing 的 w:line/w:lineRule 属性 → 单倍行距（对齐模板默认）。"""
    ppr = p._p.find(qn("w:pPr"))
    if ppr is None:
        return
    sp = ppr.find(qn("w:spacing"))
    if sp is None:
        return
    for a in ("w:line", "w:lineRule"):
        if sp.get(qn(a)) is not None:
            del sp.attrib[qn(a)]


def _split_keyword(p):
    """把"关键词："标签拆成黑体加粗run，其余宋体。"""
    if not p.runs:
        return
    r0 = p.runs[0]
    txt = r0.text
    i = txt.find("关键词：")
    if i < 0:
        return
    label = txt[: i + len("关键词：")]
    rest = txt[i + len("关键词："):]
    # 复制r0为新run，置于r0前，作为标签
    from docx.oxml import OxmlElement
    from copy import deepcopy
    new_r = deepcopy(r0._r)
    # 清空新run内所有w:t文本，写入标签
    for t in new_r.findall(qn("w:t")):
        t.text = ""
    if new_r.findall(qn("w:t")):
        new_r.findall(qn("w:t"))[0].text = label
    else:
        t = OxmlElement("w:t")
        t.text = label
        new_r.append(t)
    r0._r.addprevious(new_r)
    # 设置标签run为黑体加粗
    from docx.text.run import Run
    lab_run = Run(new_r, p)
    set_run_font(lab_run, ea="黑体", ascii_="黑体", bold=True)
    # 原run写入剩余文本，宋体非加粗
    r0.text = rest
    rpr = r0._r.find(qn("w:rPr"))
    if rpr is not None:
        rf = rpr.find(qn("w:rFonts"))
        if rf is not None:
            rf.set(qn("w:eastAsia"), "宋体")
            rf.set(qn("w:ascii"), "Times New Roman")
            rf.set(qn("w:hAnsi"), "Times New Roman")
    r0.font.bold = False


if __name__ == "__main__":
    main()
