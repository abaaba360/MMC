# -*- coding: utf-8 -*-
"""
把正文里打包式引用拆成单独形式：
  [2,4-6] -> [2][4][5][6]
  [7-9]   -> [7][8][9]

理由：原文的连续范围在 GB/T 7714 下可解释为"含端点的整段"，但写"单独引用"时
仍可能被读者/评审看作打包引用。拆成逐条方括号最稳。
"""
import os, shutil, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn

SRC = r'D:\数模工作流\delivery\C题论文_国奖附录定稿.docx'
REPL = [
    ('[2,4-6]', '[2][4][5][6]'),
    ('[7-9]',   '[7][8][9]'),
]


def main():
    d = Document(SRC)
    n_para = n_run = 0
    for p in d.paragraphs:
        full = ''.join(r.text for r in p.runs)
        if any(old in full for old, _ in REPL):
            new_full = full
            for old, new in REPL:
                new_full = new_full.replace(old, new)
            if new_full != full:
                # 把所有文本合到第一个 run，重设字体（保留第一个 run 的格式）
                first = p.runs[0]
                first.text = new_full
                # 删掉多余 run
                for r in p.runs[1:]:
                    r._r.getparent().remove(r._r)
                n_para += 1
                n_run += 1
                print('  段落:', full[:60], '->', new_full[:60])

    # 表格里的也处理一下（按段落）
    for tbl in d.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    full = ''.join(r.text for r in p.runs)
                    if any(old in full for old, _ in REPL):
                        new_full = full
                        for old, new in REPL:
                            new_full = new_full.replace(old, new)
                        if new_full != full:
                            first = p.runs[0]
                            first.text = new_full
                            for r in p.runs[1:]:
                                r._r.getparent().remove(r._r)
                            n_para += 1
                            n_run += 1
    print(f'共改 {n_para} 个段落 / {n_run} 处')
    d.save(SRC)
    print('已保存:', SRC, os.path.getsize(SRC), 'bytes')


if __name__ == '__main__':
    main()