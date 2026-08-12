# -*- coding: utf-8 -*-
"""将 paper/paper_sections/ 的markdown章节转换为国赛LaTeX论文

处理：标题(#/##/###)、加粗、行内公式、公式块、三线表、图片、列表
输出：paper/final_paper.tex（基于CUMCMThesis模板，需XeLaTeX编译）
"""
import os
import re

SEC_DIR = os.path.join("paper", "paper_sections")
OUT = os.path.join("paper", "final_paper.tex")

FIGURE_DIR = "../results/figures"


def convert_math_inline(line):
    """把markdown的 $...$ 保留（已是LaTeX公式），转义非公式文本特殊字符但不动公式"""
    parts = re.split(r"(\$\$?.+?\$\$?)", line)
    out = []
    for p in parts:
        if p.startswith("$"):
            out.append(p)  # 公式原样
        else:
            # 转义非公式文本中的LaTeX特殊字符（%是注释符，&是列分隔符等）
            p = p.replace("\\", r"\textbackslash ")
            p = p.replace("%", r"\%")
            p = p.replace("#", r"\#")
            p = p.replace("&", r"\&")
            p = p.replace("_", r"\_")
            out.append(p)
    return "".join(out)


def convert_bold(line):
    line = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", line)
    line = re.sub(r"`(.+?)`", r"\\texttt{\1}", line)
    return line


def split_intro(text):
    """拆出文档标题行与其余正文"""
    lines = text.split("\n")
    title = None
    body = []
    for ln in lines:
        if title is None and ln.startswith("# ") and not ln.startswith("## "):
            title = ln[2:].strip()
        else:
            body.append(ln)
    return title, body


def section_heading(line):
    """markdown标题 -> LaTeX section"""
    m = re.match(r"^(#{1,4})\s+(.+)$", line)
    if not m:
        return None
    level = len(m.group(1))
    txt = m.group(2).strip()
    # 去掉标题中的编号前缀（如"五、"、"5.1"），LaTeX自动编号
    txt = re.sub(r"^[一二三四五六七八九十]+、\s*", "", txt)
    txt = re.sub(r"^\d+(\.\d+)*\s*", "", txt)
    cmd = {1: "section", 2: "subsection", 3: "subsubsection", 4: "paragraph"}[level]
    return f"\\{cmd}{{{txt}}}"


def is_table_sep(line):
    return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", line)) and "-" in line


def convert_table(rows):
    """把表头+数据行转为三线表（单元格做LaTeX转义）"""
    header = rows[0]
    cells = [convert_bold(convert_math_inline(c.strip())) for c in header.strip().strip("|").split("|")]
    ncol = len(cells)
    colspec = "X" * ncol  # tabularx X列：自动分配宽度并支持换行
    out = []
    out.append("\\begin{table}[htbp]")
    out.append("\\centering")
    out.append("\\small")
    out.append(f"\\begin{{tabularx}}{{\\textwidth}}{{{colspec}}}")
    out.append("\\toprule")
    out.append(" & ".join(cells) + r" \\")
    out.append("\\midrule")
    for row in rows[1:]:
        cs = [convert_bold(convert_math_inline(c.strip())) for c in row.strip().strip("|").split("|")]
        # 补足列数
        cs = cs + [""] * (ncol - len(cs))
        out.append(" & ".join(cs) + r" \\")
    out.append("\\bottomrule")
    out.append("\\end{tabularx}")
    out.append("\\end{table}")
    return out


def strip_fig_prefix(caption):
    """去掉手动编号前缀 '图4-1 ' / '图 4-1 '，LaTeX 用 section-图 自动编号"""
    return re.sub(r"^图\s*\d+[\-–]?\s*", "", caption).strip()


def convert_figure(line):
    """markdown图片 -> LaTeX figure"""
    m = re.search(r"!\[(.*?)\]\((.+?)\)", line)
    if not m:
        return None
    caption = strip_fig_prefix(m.group(1))
    path = m.group(2).replace("..\\", "").replace("../", "")
    basename = os.path.basename(path)
    # 优先引用矢量 PDF（LaTeX 输出更清晰），同名 PDF 不存在时退回 PNG
    # FIGURE_DIR 相对 tex 输出位置（paper/），存在性检查须按真实项目路径解析
    name, _ = os.path.splitext(basename)
    real_pdf = os.path.abspath(
        os.path.join(SEC_DIR, "..", "..", "results", "figures", name + ".pdf"))
    if os.path.exists(real_pdf):
        basename = name + ".pdf"
    fig = os.path.join(FIGURE_DIR, basename)
    fig = fig.replace("\\", "/")
    return [
        "\\begin{figure}[htbp]",
        "\\centering",
        f"\\includegraphics[width=0.82\\textwidth]{{{fig}}}",
        f"\\caption{{{caption}}}",
        "\\end{figure}",
    ]


def convert_file(fname):
    with open(os.path.join(SEC_DIR, fname), encoding="utf-8") as f:
        text = f.read()
    if fname.startswith("00_"):
        title, body = split_intro(text)  # 摘要文件：首行是论文标题，需提取
    else:
        title = None
        body = text.split("\n")
    out = []
    if title and fname.startswith("00_"):
        out.append(f"\\begin{{abstract}}")
        for ln in body:
            ln = ln.strip()
            if ln.startswith("#"):
                continue  # 跳过 "## 摘要" 等标题（模板自带）
            if ln.startswith("**关键词**"):
                kw = ln.replace("**关键词**", "").strip()
                out.append(f"\\keywords{{{kw}}}")
            elif ln:
                out.append(convert_bold(convert_math_inline(ln)) + "\n\n")
        out.append("\\end{abstract}\n")
        return title, out

    i = 0
    lines = body
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        # 表格块
        if ln.strip().startswith("|") and i + 1 < len(lines) and is_table_sep(lines[i + 1]):
            rows = [ln]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.extend(convert_table(rows))
            continue
        # 图片
        fig = convert_figure(ln)
        if fig:
            out.extend(fig)
            i += 1
            continue
        # 标题
        h = section_heading(ln)
        if h:
            out.append(h)
            i += 1
            continue
        # 列表
        if re.match(r"^\s*[-*]\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]))
                i += 1
            out.append("\\begin{itemize}")
            for it in items:
                out.append("  \\item " + convert_bold(convert_math_inline(it)))
            out.append("\\end{itemize}")
            continue
        if re.match(r"^\s*\d+[\.、]\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+[\.、]\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+[\.、]\s+", "", lines[i]))
                i += 1
            out.append("\\begin{enumerate}")
            for it in items:
                out.append("  \\item " + convert_bold(convert_math_inline(it)))
            out.append("\\end{enumerate}")
            continue
        # 公式块
        if ln.startswith("$$"):
            if ln.strip().endswith("$$") and len(ln.strip()) > 4:
                # 单行公式 $$...$$（可能含\tag）
                inner = ln.strip()[2:-2].strip()
                out.append("\\begin{equation}")
                out.append(inner)
                out.append("\\end{equation}")
                i += 1
                continue
            # 多行公式块 $$ ... $$
            j = i + 1
            eqs = []
            while j < len(lines) and not lines[j].startswith("$$"):
                eqs.append(lines[j])
                j += 1
            out.append("\\begin{equation}")
            for e in eqs:
                out.append(e)
            out.append("\\end{equation}")
            i = j + 1
            continue
        # 普通段落
        para = []
        while i < len(lines) and lines[i].strip() and not (
            lines[i].strip().startswith("|") or lines[i].strip().startswith("#")
            or lines[i].strip().startswith("![")):
            para.append(lines[i].strip())
            i += 1
        out.append(convert_bold(convert_math_inline(" ".join(para))) + "\n")
    return title, out


def main():
    order = ["00_abstract.md", "01_problem_restatement.md", "02_problem_analysis.md",
             "03_assumptions.md", "04_symbols.md", "05_q1.md", "05_q2.md", "05_q3.md",
             "05_q4.md", "05_q5.md", "06_model_check.md", "07_evaluation.md",
             "08_references.md", "09_ai_declaration.md", "10_appendix.md"]
    header = r"""\documentclass[withoutpreface]{cumcmthesis}
\usepackage{url}
\usepackage{amsmath, amssymb}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{float}
\usepackage{chngcntr}
\counterwithin{figure}{section}
\counterwithin{table}{section}
\renewcommand\thefigure{\arabic{section}-\arabic{figure}}
\renewcommand\thetable{\arabic{section}-\arabic{table}}

\title{高性能芯片歧管式微通道热管理系统的多目标优化与鲁棒设计}
\tihao{B}
\baominghao{}
\schoolname{}
\membera{}
\memberb{}
\memberc{}
\supervisor{}
\yearinput{2026}
\monthinput{8}
\dayinput{4}

\begin{document}

\maketitle
"""
    footer = r"""
\end{document}
"""
    parts = [header]
    for fname in order:
        if not os.path.exists(os.path.join(SEC_DIR, fname)):
            continue
        title, blocks = convert_file(fname)
        parts.extend(blocks)
    parts.append(footer)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(f"final_paper.tex 已生成: {OUT} ({os.path.getsize(OUT)//1024} KB)")


if __name__ == "__main__":
    main()
