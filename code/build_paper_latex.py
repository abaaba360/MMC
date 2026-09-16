"""把最终Markdown论文转换为符合CUMCM版式的XeLaTeX文稿。"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper" / "论文_C题_第一版.md"
OUTPUT = ROOT / "paper" / "C题论文_第一版.tex"
CODE_FILES = [
    "common_milp.py", "q1_model.py", "formal_data_loader.py",
    "causal_forecasts.py", "q2_model.py", "q34_helpers.py",
    "q3_model.py", "q4_model.py", "verify_results.py",
    "export_result_workbooks.py", "visualize_results.py",
]


def escape_text(value: str) -> str:
    parts = re.split(r"(\$[^$]+\$)", value)
    out = []
    for part in parts:
        if part.startswith("$") and part.endswith("$"):
            out.append(part)
            continue
        part = part.replace("\\", r"\textbackslash{}")
        for a, b in (("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_")):
            part = part.replace(a, b)
        part = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", part)
        part = re.sub(r"`(.+?)`", r"\\texttt{\1}", part)
        out.append(part)
    return "".join(out)


def table_to_tex(rows: list[str]) -> list[str]:
    cells = [[escape_text(c.strip()) for c in row.strip().strip("|").split("|")] for row in rows]
    n = len(cells[0])
    numeric = []
    for j in range(n):
        vals = [re.sub(r"\\textbf\{(.+?)\}", r"\1", r[j]) for r in cells[1:] if j < len(r)]
        numeric.append(bool(vals) and all(re.fullmatch(r"[-+0-9.,—\s]+", v or "—") for v in vals))
    spec = "@{}" + " ".join("r" if numeric[j] else "X" for j in range(n)) + "@{}"
    out = [r"\begin{table}[htbp]", r"\centering", r"\small",
           rf"\begin{{tabularx}}{{\textwidth}}{{{spec}}}", r"\toprule",
           " & ".join(cells[0]) + r" \\", r"\midrule"]
    for row in cells[1:]:
        row += [""] * (n - len(row))
        out.append(" & ".join(row[:n]) + r" \\")
    out += [r"\bottomrule", r"\end{tabularx}", r"\end{table}"]
    return out


def convert_body(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    in_appendix = False
    while i < len(lines):
        raw = lines[i].rstrip()
        text = raw.strip()
        if not text:
            i += 1
            continue
        if text.startswith("## 附录"):
            in_appendix = True
            break
        if text.startswith("## "):
            title = re.sub(r"^\d+\s*", "", text[3:].strip())
            if title in {"AI工具使用声明", "参考文献"}:
                out.append(rf"\section*{{{escape_text(title)}}}")
                out.append(rf"\addcontentsline{{toc}}{{section}}{{{escape_text(title)}}}")
            else:
                out.append(rf"\section{{{escape_text(title)}}}")
            i += 1
            continue
        if text.startswith("### "):
            title = re.sub(r"^\d+(?:\.\d+)*\s*", "", text[4:].strip())
            out.append(rf"\subsection{{{escape_text(title)}}}")
            i += 1
            continue
        if text.startswith("!["):
            m = re.match(r"!\[(.*?)\]\((.*?)\)", text)
            if m:
                caption = re.sub(r"^图\s*\d+(?:-\d+)?\s*", "", m.group(1)).strip()
                stem = Path(m.group(2)).stem
                fig = (ROOT / "results" / "figures" / f"{stem}.pdf").as_posix()
                out += [r"\begin{figure}[htbp]", r"\centering",
                        rf"\includegraphics[width=0.88\textwidth]{{{fig}}}",
                        rf"\caption{{{escape_text(caption)}}}", r"\end{figure}"]
            i += 1
            continue
        if text.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]):
            rows = [raw]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out += table_to_tex(rows)
            continue
        if text.startswith("$$"):
            eq = []
            if text.endswith("$$") and len(text) > 4:
                eq = [text[2:-2].strip()]
                i += 1
            else:
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("$$"):
                    eq.append(lines[i])
                    i += 1
                i += 1
            out += [r"\begin{equation}", *eq, r"\end{equation}"]
            continue
        if re.match(r"^\d+\.\s+", text):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            out.append(r"\begin{enumerate}[leftmargin=2.2em,itemsep=0.2em]")
            out += [rf"\item {escape_text(item)}" for item in items]
            out.append(r"\end{enumerate}")
            continue
        para = [text]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{2,3}\s|!\[|\||\$\$|\d+\.\s)", lines[i].strip()
        ):
            para.append(lines[i].strip())
            i += 1
        out.append(escape_text(" ".join(para)) + r"\par")
    return out


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = lines[0].removeprefix("# ").strip()
    abs_start = lines.index("## 摘要") + 1
    body_start = next(i for i, line in enumerate(lines) if line.startswith("## 1 "))
    abstract_lines = [line.strip() for line in lines[abs_start:body_start] if line.strip()]
    keyword_line = next(line for line in abstract_lines if line.startswith("**关键词"))
    abstract_text = "\n\n".join(line for line in abstract_lines if line != keyword_line)
    keywords = re.sub(r"^\*\*关键词：?\*\*\s*", "", keyword_line)
    body = convert_body(lines[body_start:])
    appendix = [r"\clearpage", r"\appendix", r"\section{完整源程序代码}",
                "本附录列出全部可运行源程序；同名文件同时收入支撑材料。"]
    for name in CODE_FILES:
        appendix += [rf"\subsection{{{escape_text(name)}}}",
                     rf"\lstinputlisting{{{(ROOT / 'code' / name).as_posix()}}}"]
    preamble = rf"""\documentclass[12pt,a4paper]{{ctexart}}
\usepackage[left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm]{{geometry}}
\usepackage{{fontspec,xeCJK,amsmath,amssymb,booktabs,tabularx,graphicx,float,caption,enumitem,listings,xcolor,fancyhdr,chngcntr}}
\setmainfont{{Times New Roman}}
\setCJKmainfont{{SimSun}}
\setCJKsansfont{{SimHei}}
\renewcommand\familydefault{{\rmdefault}}
\setlength{{\parindent}}{{2em}}
\setlength{{\parskip}}{{0pt}}
\linespread{{1.5}}
\setcounter{{secnumdepth}}{{3}}
\ctexset{{section={{format=\centering\bfseries\zihao{{3}},beforeskip=1.0em,afterskip=0.7em}},subsection={{format=\raggedright\bfseries\zihao{{4}},beforeskip=0.8em,afterskip=0.45em}}}}
\captionsetup{{font=small,labelsep=quad}}
\counterwithin{{figure}}{{section}}
\counterwithin{{table}}{{section}}
\renewcommand\thefigure{{\arabic{{section}}-\arabic{{figure}}}}
\renewcommand\thetable{{\arabic{{section}}-\arabic{{table}}}}
\pagestyle{{fancy}}\fancyhf{{}}\cfoot{{\thepage}}\renewcommand{{\headrulewidth}}{{0pt}}
\lstset{{basicstyle=\ttfamily\zihao{{-5}},breaklines=true,frame=single,numbers=left,numberstyle=\tiny,showstringspaces=false,tabsize=4,columns=fullflexible,keepspaces=true,keywordstyle=\color{{blue!55!black}},commentstyle=\color{{green!40!black}}}}
\begin{{document}}
\thispagestyle{{empty}}
\begin{{center}}\bfseries\zihao{{3}} {escape_text(title)}\end{{center}}
\vspace{{0.5em}}
\begin{{center}}\bfseries\zihao{{3}} 摘\quad 要\end{{center}}
\zihao{{-4}}
{escape_text(abstract_text)}

\vfill
\noindent\textbf{{关键词：}}{escape_text(keywords)}
\clearpage
\setcounter{{page}}{{1}}
"""
    OUTPUT.write_text(preamble + "\n".join(body + appendix) + "\n\\end{document}\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
