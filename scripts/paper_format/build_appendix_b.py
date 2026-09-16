# -*- coding: utf-8 -*-
"""生成国奖样式的附录B代码块（供 docx 构建使用）
产出 tmp/appendix_b.json : [ {name, title, lines:[{no, text, spans:[(txt,color)]}]} ]
"""
import sys, io, os, json, re, keyword, tokenize
from io import StringIO
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC = r'D:\数模工作流\tmp\code_src'

# 国奖实测配色
C_KW = '006EB8'    # 关键字 蓝
C_CMT = '009900'   # 注释 绿
C_STR = '008470'   # 字符串 青
C_TXT = '000000'   # 普通 黑

PLAN = [
    ('q1_model.py', '问题一：确定性MILP主模型与LP连续松弛对照', [(1, 13), (35, 94)]),
    ('q2_model.py', '问题二：严格0时两阶段随机MILP', [(1, 45), (48, 194)]),
    ('q3_model.py', '问题三：0/6/12/18滚动更新的确定性MILP-MPC', [(1, 31), (52, 109)]),
    ('q4_model.py', '问题四：实时波动电价下的因果Q4-2/Q4-3与信息基准', [(1, 41), (43, 171)]),
    ('common_milp.py', '四问共用的能量平衡与储能调度MILP骨架', [(1, 16), (18, 164)]),
    ('data_loader.py', '问题一附件数据读取与单位转换', [(1, 30)]),
    ('formal_data_loader.py', '全年数据读取、字段校验与单位转换', [(1, 22), (24, 87)]),
    ('causal_forecasts.py', '因果日前净负荷预测与整日残差情景生成',
     [(1, 21), (23, 28), (36, 50), (101, 136), (147, 189), (252, 271)]),
    ('q34_helpers.py', '问题三、四共用的滚动更新与调整结算',
     [(1, 30), (85, 123), (232, 346)]),
    ('verify_results.py', '四问约束与费用的独立复核', [(1, 15), (18, 51), (81, 104)]),
    ('export_result_workbooks.py', '计算结果工作簿导出', [(1, 17), (76, 106)]),
    ('export_matlab_visual_data.py', 'MATLAB绘图数据导出', [(1, 13), (15, 59)]),
    ('run_all.py', '统一核验与完整复算入口', [(1, 33), (36, 78)]),
    ('plot_q1_dispatch_matlab_preview.m', '问题一调度、储能动作与SOC轨迹',
     [(1, 4), (19, 35), (37, 85), (88, 111)]),
    ('plot_c_paper_figures_matlab.m', '问题二至问题四证据图',
     [(1, 3), (11, 19), (83, 101), (103, 125), (127, 148), (152, 161)]),
]


def hl_python(src: str):
    """按 token 的列位置重建整行 —— 保留 token 之间的空格与行首缩进"""
    lines = src.split('\n')
    n = len(lines)
    spans = {}
    try:
        toks = list(tokenize.generate_tokens(StringIO(src).readline))
    except Exception:
        toks = []
    for tok in toks:
        ttype, tstr, (sr, sc), (er, ec), _ = tok
        if ttype in (tokenize.ENCODING, tokenize.ENDMARKER):
            continue
        if ttype == tokenize.COMMENT:
            col = C_CMT
        elif ttype == tokenize.STRING:
            col = C_STR
        elif ttype == tokenize.NAME and keyword.iskeyword(tstr):
            col = C_KW
        else:
            col = C_TXT
        if sr == er:
            spans.setdefault(sr, []).append((sc, ec, col))
        else:
            parts = tstr.split('\n')
            for k, part in enumerate(parts):
                r = sr + k
                if k == 0:
                    spans.setdefault(r, []).append((sc, sc + len(part), col))
                else:
                    spans.setdefault(r, []).append((0, len(part), col))
    out = {}
    for ln in range(1, n + 1):
        line = lines[ln - 1].rstrip('\r')
        sp = sorted(spans.get(ln, []), key=lambda x: (x[0], x[1]))
        res = []
        cur = 0
        for a, b, col in sp:
            a = max(a, cur)
            if a > cur:
                res.append((line[cur:a], C_TXT))
            if b > a:
                res.append((line[a:b], col))
            cur = max(cur, b)
        if cur < len(line):
            res.append((line[cur:], C_TXT))
        if not res:
            res = [(line, C_TXT)]
        assert ''.join(s for s, _ in res) == line, \
            'Python 着色丢字符 第%d行: %r -> %r' % (ln, line, ''.join(s for s, _ in res))
        out[ln] = res
    return out


MATLAB_KW = {'function', 'if', 'elseif', 'else', 'end', 'for', 'while', 'break', 'continue',
             'return', 'switch', 'case', 'otherwise', 'try', 'catch', 'global', 'clear',
             'close', 'clc', 'true', 'false', 'nan'}


def _split_matlab_comment(line: str):
    """把一行切成 (代码段, 注释段)。注释段含前导 %，无注释则为空串。"""
    in_s = False
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == "'":
            # 处理 '' 转义（连续两个单引号算一个转义）
            if in_s and i + 1 < n and line[i + 1] == "'":
                i += 2
                continue
            in_s = not in_s
        elif ch == '%' and not in_s:
            return line[:i], line[i:]
        i += 1
    return line, ''


def hl_matlab_line(line: str):
    """MATLAB 逐行着色。严格保证 ''.join(spans) == line（无损）。"""
    code, cmt = _split_matlab_comment(line)
    spans = []

    def flush(buf):
        if buf:
            spans.append((buf, C_TXT))
        return ''

    buf = ''
    j = 0
    n = len(code)
    while j < n:
        ch = code[j]
        if ch == "'":
            # 字符串字面量：从 j 开始，找到配对的结束引号
            buf = flush(buf)
            k = j + 1
            while k < n:
                if code[k] == "'":
                    if k + 1 < n and code[k + 1] == "'":
                        k += 2          # '' 转义，继续
                        continue
                    break               # 真正的结束引号
                k += 1
            end = min(k + 1, n)
            spans.append((code[j:end], C_STR))
            j = end
            continue
        if ch.isalpha() or ch == '_':
            k = j
            while k < n and (code[k].isalnum() or code[k] == '_'):
                k += 1
            buf = flush(buf)                      # ← 关键：先吐出缓冲，保证顺序
            word = code[j:k]
            spans.append((word, C_KW if word in MATLAB_KW else C_TXT))
            j = k
            continue
        buf += ch
        j += 1
    flush(buf)
    if cmt:
        spans.append((cmt, C_CMT))
    if not spans:
        spans = [(line, C_TXT)]
    # 无损自检
    assert ''.join(s for s, _ in spans) == line, \
        'MATLAB 着色丢字符: %r -> %r' % (line, ''.join(s for s, _ in spans))
    return spans


def build():
    items = []
    total = 0
    report = []
    for name, title, segs in PLAN:
        path = os.path.join(SRC, name)
        raw = open(path, encoding='utf-8', errors='replace').read()
        if not raw.endswith('\n'):
            raw += '\n'
        src_lines = raw.split('\n')          # 保留末尾空串
        is_py = name.endswith('.py')
        hl = hl_python(raw) if is_py else None

        kept = []      # (orig_no, text, spans)
        prev_end = None
        for (a, b) in segs:
            if prev_end is not None and a > prev_end + 1:
                kept.append((None, '# ……', [('# ……', C_CMT)]))
            for ln in range(a, min(b, len(src_lines)) + 1):
                text = src_lines[ln - 1].rstrip('\r')
                if is_py:
                    sp = hl.get(ln) or [(text, C_TXT)]
                else:
                    sp = hl_matlab_line(text)
                kept.append((ln, text, sp))
            prev_end = b
        items.append({'name': name, 'title': title, 'lines': kept})
        total += len(kept)
        report.append('%-40s 摘录 %4d 行' % (name, len(kept)))

    json.dump(items, open(r'D:\数模工作流\tmp\appendix_b.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n'.join(report))
    print('-' * 50)
    print('合计 %d 个文件，%d 行' % (len(items), total))
    # 最长行
    mx = max((len(t), it['name']) for it in items for _, t, _ in it['lines'])
    print('最长行 %d 字符（%s）' % mx)
    print('预计页数 ≈ %.0f 页（37行/页）+ 文件标题' % (total / 37))


build()
