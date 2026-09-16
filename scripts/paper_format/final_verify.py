# -*- coding: utf-8 -*-
"""最终验收：页数口径、附录版式、匿名性、文件大小。"""
import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import fitz, numpy as np

PDF = r'D:\数模工作流\tmp\cur_gj.pdf'
d = fitz.open(PDF)
N = d.page_count
print('=' * 62)
print('【1】页数口径')
print('  PDF 总页数:', N)

def find_page(marks, start=0):
    for i in range(start, N):
        tt = d[i].get_text().replace(' ', '').replace('\u3000', '')
        if any(m in tt for m in marks):
            return i + 1
    return None

p_ai = find_page(['十二、AI工具使用声明', '十二、AI工具使用声明'])
p_ref = find_page(['十三、参考文献'])
p_app = find_page(['附录A支撑材料的文件列表', '附录A　支撑材料的文件列表'])
# 更稳：找附录A标题页
for i in range(N):
    tt = d[i].get_text()
    if re.search(r'附录\s*A\s*支撑材料的文件列表', tt):
        p_app = i + 1
        break
print('  AI工具使用声明 起始页:', p_ai)
print('  参考文献 起始页:', p_ref)
print('  附录A 起始页:', p_app, '(正文到此结束)')
print('  >>> 摘要页 = P1 (1 页)')
print('  >>> 正文 = P2..P%d = %d 页  (限 30)  %s' % (p_app, p_app - 1, 'PASS' if p_app - 1 <= 30 else 'FAIL'))
print('  >>> 附录 = P%d..P%d = %d 页 (页数不限)' % (p_app, N, N - p_app + 1))
print('  >>> 全文 = %d 页  (限 100)  %s' % (N, 'PASS' if N <= 100 else 'FAIL'))

print('\n【2】附录B 版式核对（抽 3 页）')
for pno in (p_app + 1, p_app + 12, N - 6):
    if pno - 1 >= N:
        continue
    pg = d[pno - 1]
    pix = pg.get_pixmap(dpi=300)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    rgb = a[:, :, :3].astype(int)
    g = rgb.mean(axis=2)
    sc = 300 / 72.0
    y0, y1 = int(85 * sc), int(770 * sc)
    dark = (g[y0:y1, :] < 230).mean(axis=0)
    v = [i for i in range(len(dark)) if dark[i] > 0.9]
    groups = []
    for i in v:
        if groups and i - groups[-1][-1] <= 3:
            groups[-1].append(i)
        else:
            groups.append([i])
    desc = []
    for gp in groups:
        c = gp[len(gp) // 2]
        col = tuple(rgb[int(400 * sc), c])
        desc.append('x=%.1f-%s' % (gp[0] / sc, col))
    td = pg.get_text('dict')
    nums = [s for b in td['blocks'] if b['type'] == 0 for l in b['lines'] for s in l['spans']
            if s['font'] == 'TimesNewRomanPSMT' and s['color'] == 0x7f807f]
    code = [s for b in td['blocks'] if b['type'] == 0 for l in b['lines'] for s in l['spans']
            if s['font'] == 'Consolas']
    sizes = sorted(set(round(s['size'], 1) for s in code))
    print('  P%d 竖线/色带: %s' % (pno, '; '.join(desc)))
    print('      灰行号 %d 个, 等宽代码 span %d 个, 代码字号 %s' % (len(nums), len(code), sizes))

print('\n【3】匿名性检查（全文关键词）')
BAD = ['承诺书', '编号专用页', '参赛队号', '学校', '赛区', '队员', '指导教师',
       '张三', '李四', '王五', '大学', '学院', '班']
hits = {}
for i in range(N):
    t = d[i].get_text()
    for b in BAD:
        if b in t:
            hits.setdefault(b, []).append(i + 1)
for b, ps in hits.items():
    print('  %-8s 出现于 P%s' % (b, ','.join(map(str, ps[:6]))))
if not hits:
    print('  未命中敏感词')
# 目录检查
toc = [i + 1 for i in range(min(6, N)) if '目录' in d[i].get_text()]
print('  目录页:', toc or '无（合规）')

print('\n【4】文件大小')
for f in [r'D:\数模工作流\tmp\C题论文_国奖附录版.docx', PDF]:
    print('  %-50s %.2f MB' % (os.path.basename(f), os.path.getsize(f) / 1048576))

print('\n【5】正文抽样页（确认无重叠/裁切）')
for pno in (2, 5, 9, 15, 25):
    if pno - 1 < N:
        print('  P%-3d 字符数=%d' % (pno, len([c for c in d[pno - 1].get_text() if not c.isspace()])))
