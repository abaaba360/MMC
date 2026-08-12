# -*- coding: utf-8 -*-
"""从 final_paper.md 提取章节 → 重构为模板标准结构 → 写入 paper_sections/"""
import re, os

SEC = os.path.join('paper', 'paper_sections')
SRC = os.path.join('paper', 'final_paper.md')

text = open(SRC, encoding='utf-8').read()
lines = text.split('\n')

# ====== Find chapter boundaries ======
chapters = []
for i, line in enumerate(lines):
    m = re.match(r'^# (一|二|三|四|五|六|七|八|九|参考文献|AI|附录|高性能)', line)
    if m:
        chapters.append((i, line.strip()))

chapters.append((len(lines), ''))

# ====== Extract sections ======
sections = {}
for idx in range(len(chapters)-1):
    start = chapters[idx][0]
    end = chapters[idx+1][0]
    title = chapters[idx][1]

    if '高性能' in title:
        sections['00_abstract.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '一、' in title:
        sections['01_problem_restatement.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '二、' in title:
        sections['02_problem_analysis.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '三、' in title:
        sections['03_assumptions.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '四、' in title:
        sections['05_q1.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '五、' in title:
        sections['05_q2.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '六、' in title:
        sections['05_q3.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '七、' in title:
        sections['05_q4.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '八、' in title:
        sections['05_q5.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '九、' in title:
        sections['07_evaluation.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '参考' in title:
        sections['08_references.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif 'AI' in title:
        sections['09_ai_declaration.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'
    elif '附录' in title:
        sections['10_appendix.md'] = '\n'.join(lines[start:end]).rstrip() + '\n'

print("Extracted sections:")
for k in sorted(sections.keys()):
    print('  %s - %d chars' % (k, len(sections[k])))

# ====== Transform headings for Q1-Q5 ======
def restructure_q(content, old_chapter_num, new_sec, new_title, fig_map, tbl_map):
    new_lines = []

    for line in content.split('\n'):
        # Skip old top-level heading
        if re.match(r'^# [四五六七八]、', line):
            continue

        # Transform ## X.Y to ### 5.Z.Y
        m = re.match(r'^## (\d+)\.(\d+)\s+(.+)', line)
        if m:
            sub = int(m.group(2))
            title_text = m.group(3)
            new_lines.append('### %s.%d %s' % (new_sec, sub, title_text))
            continue

        new_lines.append(line)

    result = '\n'.join(new_lines)

    # Add section heading
    result = '## %s %s\n\n' % (new_sec, new_title) + result

    # Apply figure/table mappings with placeholder technique to avoid cascading
    # Step 1: replace all old refs with unique placeholders
    placeholders = {}
    for i, old_ref in enumerate(sorted(fig_map.keys(), key=len, reverse=True)):
        ph = '<<<FIG%d>>>' % i
        placeholders[ph] = fig_map[old_ref]
        result = result.replace(old_ref, ph)
    for i, old_ref in enumerate(sorted(tbl_map.keys(), key=len, reverse=True)):
        ph = '<<<TBL%d>>>' % i
        placeholders[ph] = tbl_map[old_ref]
        result = result.replace(old_ref, ph)
    # Step 2: replace placeholders with final values
    for ph, new_ref in placeholders.items():
        result = result.replace(ph, new_ref)

    # Clean excessive blank lines
    while '\n\n\n' in result:
        result = result.replace('\n\n\n', '\n\n')

    return result

# Per-file mappings
q1_figs = {'图4-1': '图5-1', '图4-2': '图5-2', '图4-3': '图5-3'}
q1_tbls = {'表4-1': '表5-1'}

q2_figs = {'图5-1': '图5-4', '图5-2': '图5-5', '图5-3': '图5-6',
           '图5-4': '图5-7', '图5-5': '图5-8'}
q2_tbls = {'表5-1': '表5-2'}

q3_figs = {'图6-1': '图5-9',  '图6-2': '图5-10', '图6-3': '图5-11',
           '图6-4': '图5-12'}
q3_tbls = {'表6-1': '表5-3'}

q4_figs = {'图7-1': '图5-13', '图7-2': '图5-14', '图7-3': '图5-15',
           '图7-4': '图5-16', '图7-5': '图5-17'}
q4_tbls = {'表7-1': '表5-4'}

q5_figs = {'图8-1': '图5-18', '图8-2': '图5-19', '图8-3': '图5-20',
           '图8-4': '图5-21'}
q5_tbls = {'表8-1': '表5-5'}

# Process Q1-Q5
sections['05_q1.md'] = restructure_q(sections['05_q1.md'], 4, '5.1',
    '问题一：机理建模与影响规律分析', q1_figs, q1_tbls)

sections['05_q2.md'] = restructure_q(sections['05_q2.md'], 5, '5.2',
    '问题二：GPR代理模型的建立与评估', q2_figs, q2_tbls)

sections['05_q3.md'] = restructure_q(sections['05_q3.md'], 6, '5.3',
    '问题三：多目标优化与综合最优设计', q3_figs, q3_tbls)

sections['05_q4.md'] = restructure_q(sections['05_q4.md'], 7, '5.4',
    '问题四：权重域鲁棒设计', q4_figs, q4_tbls)

sections['05_q5.md'] = restructure_q(sections['05_q5.md'], 8, '5.5',
    '问题五：敏感性分析与稳健性检验', q5_figs, q5_tbls)

# Add chapter heading to Q1
q1_body = sections['05_q1.md']
intro = ('本章针对五个子问题，依次建立机理模型（5.1节）、GPR代理模型（5.2节）、'
         '多目标优化模型（5.3节）、鲁棒设计模型（5.4节）与敏感性分析模型'
         '（5.5节），每节按“数据预处理—模型建立—模型求解—模型检验'
         '—结果分析”的五段式结构展开，给出完整的建模、求解、验证与结论。\n\n')
sections['05_q1.md'] = '# 五、模型建立与求解\n\n' + intro + q1_body

# Fix 07_evaluation.md: num 9 -> 7
eval_content = sections['07_evaluation.md']
eval_content = eval_content.replace('# 九、模型评价与推广', '# 七、模型优缺点评价')
eval_content = eval_content.replace('## 9.1', '## 7.1')
eval_content = eval_content.replace('## 9.2', '## 7.2')
eval_content = eval_content.replace('## 9.3', '## 7.3')
eval_content = eval_content.replace('## 9.4', '## 7.4')
sections['07_evaluation.md'] = eval_content

# Fix cross-references in Q files
for fname in list(sections.keys()):
    if fname.startswith('05_q'):
        content = sections[fname]
        content = content.replace('第六章', '5.3节')
        content = content.replace('第七章', '5.4节')
        content = content.replace('第八章', '5.5节')
        content = content.replace('第四章', '5.1节')
        content = content.replace('第五章', '5.2节')
        sections[fname] = content

# Also fix 00_abstract references to old chapter numbers
for fname in ['00_abstract.md']:
    if fname in sections:
        content = sections[fname]
        content = content.replace('第四章', '第五章')
        sections[fname] = content

# ====== Write all files ======
for fname, content in sections.items():
    path = os.path.join(SEC, fname)
    open(path, 'w', encoding='utf-8').write(content)
    print('Wrote %s (%d chars)' % (fname, len(content)))

# ====== Verify ======
print('\n===== Verification =====')
for fname in ['05_q1.md','05_q2.md','05_q3.md','05_q4.md','05_q5.md','07_evaluation.md']:
    path = os.path.join(SEC, fname)
    text = open(path, encoding='utf-8').read()
    hdrs = re.findall(r'^#{1,4} .+', text, re.MULTILINE)
    figs = sorted(set(re.findall(r'图\d+-\d+', text)))
    tbls = sorted(set(re.findall(r'表\d+-\d+', text)))
    old_figs = re.findall(r'图[4-8]-\d+', text)
    print('\n%s:' % fname)
    for h in hdrs[:7]: print('  ' + h[:70])
    print('  Figs:', figs)
    print('  Tbls:', tbls)
    if old_figs:
        print('  WARNING - old refs:', old_figs)

# Check no cross-file collisions
from collections import Counter
all_figs = Counter()
for fname in ['05_q1.md','05_q2.md','05_q3.md','05_q4.md','05_q5.md']:
    path = os.path.join(SEC, fname)
    text = open(path, encoding='utf-8').read()
    for fig in re.findall(r'图(\d+-\d+)', text):
        all_figs[fig] += 1
dups = [(k, c) for k, c in all_figs.items() if c > 1]
print('\nDuplicate fig numbers (cross-file):', dups[:20] if dups else 'None')
