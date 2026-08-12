# -*- coding: utf-8 -*-
"""检查tex所有tabular的列数与colspec是否匹配"""
import re

tex = open("paper/final_paper.tex", encoding="utf-8").read()
blocks = re.findall(r"\\begin\{tabular\}\{(.*?)\}(.*?)\\end\{tabular\}", tex, re.S)
print("tabular数量:", len(blocks))
problems = 0
for bi, (spec, body) in enumerate(blocks):
    ncol = len(spec)
    for r in body.split("\n"):
        s = r.strip()
        if not s or s.startswith(("\\toprule", "\\midrule", "\\bottomrule")):
            continue
        if "&" not in s:
            continue
        ncells = s.count("&") + 1
        if ncells != ncol:
            problems += 1
            print(f"表{bi+1}: colspec={spec}({ncol}列) vs {ncells}格: {s[:60]}")
print("列数不匹配的表格行数:", problems)
