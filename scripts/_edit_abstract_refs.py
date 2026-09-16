# -*- coding: utf-8 -*-
"""B题v2：重写摘要(7.3.3规范800-1000字三段式) + 正文上标引用编号 + 参考文献网址版"""
import sys, io, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

path = r"delivery\B题_芯片散热优化\B题_高性能芯片热管理系统优化_摘要参考文献版.docx"
doc = Document(path)
body = doc.element.body
els = list(body)

# ---------- 捕获元素引用 ----------
abs_p1 = els[3]
abs_p4 = els[4]
abs_p5 = els[5]
cite_paras = {9: els[9], 57: els[57], 61: els[61], 93: els[93], 98: els[98],
              100: els[100], 122: els[122], 170: els[170], 200: els[200], 206: els[206]}
ref_title = els[261]
ref_tpl = els[262]
old_refs = [els[i] for i in range(262, 269)]

# ---------- 工具函数 ----------
def set_abstract_text(p, text):
    """用*斜体*标记构建摘要段落run"""
    for r in p.findall(qn('w:r')):
        p.remove(r)
    parts = text.split('*')
    for k, part in enumerate(parts):
        if not part:
            continue
        is_ital = (k % 2 == 1)
        r = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        if is_ital:
            rf = OxmlElement('w:rFonts'); rf.set(qn('w:eastAsia'), 'Times New Roman'); rPr.append(rf)
            rPr.append(OxmlElement('w:i')); rPr.append(OxmlElement('w:iCs'))
        sz = OxmlElement('w:sz'); sz.set(qn('w:val'), '21'); rPr.append(sz)
        lang = OxmlElement('w:lang'); lang.set(qn('w:eastAsia'), 'zh-CN'); rPr.append(lang)
        r.append(rPr)
        t = OxmlElement('w:t'); t.text = part; r.append(t)
        p.append(r)

def insert_superscript(p, anchor, sup_text):
    """在anchor文本结束后插入上标引用run"""
    runs = p.findall(qn('w:r'))
    texts = []
    for r in runs:
        t = r.find(qn('w:t'))
        texts.append(t.text if t is not None and t.text else '')
    full = ''.join(texts)
    pos = full.find(anchor)
    if pos < 0:
        raise ValueError('锚点未找到: %r in %r' % (anchor[:15], full[:50]))
    end = pos + len(anchor)
    acc = 0; target = None; in_off = 0
    for r, txt in zip(runs, texts):
        nxt = acc + len(txt)
        if nxt >= end:
            target = r; in_off = end - acc; break
        acc = nxt
    if target is None:
        raise ValueError('锚点超出段落末尾')
    t = target.find(qn('w:t'))
    full_text = t.text or ''
    def make_sup():
        sr = copy.deepcopy(target)
        st = sr.find(qn('w:t')); st.text = sup_text
        rPr = sr.find(qn('w:rPr'))
        if rPr is None:
            rPr = OxmlElement('w:rPr'); sr.insert(0, rPr)
        for tag in ('w:i', 'w:iCs'):
            e = rPr.find(qn(tag))
            if e is not None:
                rPr.remove(e)
        va = rPr.find(qn('w:vertAlign'))
        if va is None:
            va = OxmlElement('w:vertAlign'); rPr.append(va)
        va.set(qn('w:val'), 'superscript')
        return sr
    if in_off > 0 and in_off < len(full_text):
        prefix, suffix = full_text[:in_off], full_text[in_off:]
        t.text = prefix
        nr = copy.deepcopy(target); nt = nr.find(qn('w:t')); nt.text = suffix
        sr = make_sup()
        target.addnext(sr); sr.addnext(nr)
    elif in_off == 0:
        sr = make_sup(); target.addprevious(sr)
    else:
        sr = make_sup(); target.addnext(sr)

def set_ref_text(p, text):
    for r in p.findall(qn('w:r')):
        p.remove(r)
    r = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    rf = OxmlElement('w:rFonts'); rf.set(qn('w:cs'), 'Times New Roman'); rPr.append(rf)
    r.append(rPr)
    t = OxmlElement('w:t'); t.text = text; r.append(t)
    p.append(r)

# ---------- 1. 重写摘要（7.3.3：虎头-猪肚-豹尾，总字数800-1000） ----------
ABSTRACT = [
    "针对芯片功率密度攀升带来的散热瓶颈，本文研究歧管式微通道热管理系统结构参数优化，分析针肋宽度比 *r*、歧管深高比 *h* 与排数 *n* 对无量纲热阻 *R*、压降 *P* 与温度非均匀性 *T* 的影响，构建“机理—代理—多目标—偏好—稳健性”框架。附件含4组无针肋基线与80组4×4×5全因子样本，并给出可核验方案。",
    "针对问题一，由能量与导热方程建机理约束，用边际均值与正交效应分解辨识效应：*r*=0.20层级*R*、*T*最优，*T*在16个切片一致率100%、*R*为95%；*h*增大使*P*由0.143255降至0.097196，*h*主效应占*P*变异38.892%，*r*-*n*交互贡献11.247%。",
    "针对问题二，用80个有针肋样本建立三次响应面（RSM3）主模型，用高斯过程回归（GPR）复核。随机5折下RSM3的*R*²为1.0000、0.9996、0.9997，GPR为0.9983、0.9990、0.9971，RMSE低至10⁻⁷~10⁻⁴；留一*n*层RSM3仍近1，留一*r*、*h*层显著下降，故仅用于插值。",
    "针对问题三，建立三目标与固定极差标准化优化模型，对84个观测方案Pareto筛选得12个非支配点，以等权增广切比雪夫准则选优：方案48（0.20,4.50,6）综合最优；网格细化后两模型差异0.565%、0.433%、1.123%，候选集中于*r*≈0.238、*h*=4.50、*n*=6。",
    "针对问题四，在完整权重单纯形上建立最小最大后悔模型，将双层优化约简为枚举。样本48最大后悔0.283276为84候选中最小；等权线性下样本64（0.20,4.50,4）最优，表明综合最优随偏好离散跳变，样本48对偏好最稳健。",
    "针对问题五，构造加工误差与工况波动情景模型：*P*对*h*敏感，RSM3与GPR弹性系数为-0.853、-0.902；5000次蒙特卡洛下*R*、*P*、*T*标准差为4.8%、10.5%、6.6%，*P*的5%~95%分位[-16.0%,+16.8%]，24组弹性方向一致。",
    "本文创新点包括：建立四级证据链严格区分可核验结论与情景假设；以随机5折与留一层级双重验证刻画外推边界；以最小最大后悔实现偏好鲁棒决策；在无真实公差分布时仅做有依据的误差传播。模型经随机5折、留一结构、双模型一致性与权重鲁棒性检验，结果一致。综上，推荐样本48（0.20,4.50,6）为兼顾三目标且偏好最稳健方案，该框架可推广至叶片冷却、换热器等“少量高成本仿真+多目标决策”问题。",
]

total_chars = sum(len(a.replace('*', '')) for a in ABSTRACT)
print('摘要总字数(不含*号): %d' % total_chars)
assert 800 <= total_chars <= 1000, '摘要字数不满足800-1000'

template_abs = copy.deepcopy(abs_p1)
set_abstract_text(abs_p1, ABSTRACT[0])
prev = abs_p1
for txt in ABSTRACT[1:6]:
    np = copy.deepcopy(template_abs)
    set_abstract_text(np, txt)
    prev.addnext(np)
    prev = np
set_abstract_text(abs_p4, ABSTRACT[6])
body.remove(abs_p5)

# ---------- 2. 插入上标引用 ----------
CITATIONS = [
    (9, "影响芯片性能与可靠性的关键约束", "[1]"),
    (9, "歧管式微通道液冷系统", "[2-4]"),
    (57, "动量方程和能量方程", "[5-7]"),
    (61, "边界层发展", "[5]"),
    (93, "交互效应与非线性弯曲", "[8]"),
    (98, "带极弱L₂正则的岭回归", "[9]"),
    (100, "Matérn—5/2核的乘积", "[10]"),
    (122, "方案上进行Pareto筛选", "[11]"),
    (170, "候选方案中取最小值", "[12]"),
    (200, "作蒙特卡洛抽样", "[13]"),
    (206, "次蒙特卡洛抽样", "[13]"),
]
for idx, anchor, sup in CITATIONS:
    insert_superscript(cite_paras[idx], anchor, sup)
    print('  插入上标 %s @[%d] after %s...' % (sup, idx, anchor[:12]))

# ---------- 3. 重写参考文献（附核验网址） ----------
REFS = [
    "[1] Zhang J, Sadiqbatcha S, Tan S X D. Hot-trim: thermal and reliability management for commercial multicore processors considering workload dependent hot spots[J]. IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, 2022, 42(7): 2290-2302. https://doi.org/10.1109/TCAD.2022.3216552",
    "[2] Tuckerman D B, Pease R F W. High-performance heat sinking for VLSI[J]. IEEE Electron Device Letters, 1981, 2(5): 126-129. https://doi.org/10.1109/EDL.1981.25367",
    "[3] Cang D, Dong Z, Lv S, et al. Design and intelligent optimization of TSV-based embedded microchannel heatsinks in 2.5D packaging[J]. International Journal of Heat and Mass Transfer, 2026, 255: 127908. https://doi.org/10.1016/j.ijheatmasstransfer.2025.127908",
    "[4] He W, Yin E, Zhou F, et al. Integrated manifold microchannels and near-junction cooling for enhanced thermal management in 3D heterogeneous packaging technology[J]. Energy, 2024, 305: 132263. https://doi.org/10.1016/j.energy.2024.132263",
    "[5] 杨世铭, 陶文铨. 传热学[M]. 4版. 北京: 高等教育出版社, 2006. ISBN 978-7-04-018918-6. https://xuanshu.hep.com.cn/front/book/findBookDetails?bookId=59ccffadba9eb884cf8187f8",
    "[6] 陶文铨. 数值传热学[M]. 2版. 西安: 西安交通大学出版社, 2001. ISBN 978-7-5605-1436-9. https://mfpe.xjtu.edu.cn/info/1032/1409.htm",
    "[7] Bergman T L, Lavine A S, Incropera F P, et al. Fundamentals of heat and mass transfer[M]. 7th ed. Hoboken: John Wiley & Sons, 2011. ISBN 978-0-470-50197-9. https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer%2C+7th+Edition-p-9780470501979",
    "[8] Box G E P, Wilson K B. On the experimental attainment of optimum conditions[J]. Journal of the Royal Statistical Society: Series B, 1951, 13(1): 1-45. https://doi.org/10.1111/j.2517-6161.1951.tb00067.x",
    "[9] Hoerl A E, Kennard R W. Ridge regression: biased estimation for nonorthogonal problems[J]. Technometrics, 1970, 12(1): 55-67. https://doi.org/10.1080/00401706.1970.10488634",
    "[10] Rasmussen C E, Williams C K I. Gaussian processes for machine learning[M]. Cambridge: MIT Press, 2006. ISBN 978-0-262-18253-9. https://direct.mit.edu/books/book/2320/gaussian-processes-for-machine-learning",
    "[11] Miettinen K. Nonlinear multiobjective optimization[M]. Boston: Kluwer Academic Publishers, 1999. ISBN 978-0-7923-8278-2. https://link.springer.com/book/10.1007/978-1-4615-5563-6",
    "[12] Savage L J. The theory of statistical decision[J]. Journal of the American Statistical Association, 1951, 46(253): 55-67. https://doi.org/10.1080/01621459.1951.10500768",
    "[13] Hammersley J M, Handscomb D C. Monte Carlo methods[M]. London: Methuen, 1964. ISBN 978-0-416-52340-9. https://openlibrary.org/show-records/ia:montecarlomethod0000hamm_k1u9",
]
template_ref = copy.deepcopy(ref_tpl)
for rp in old_refs:
    body.remove(rp)
prev = ref_title
for text in REFS:
    np = copy.deepcopy(template_ref)
    set_ref_text(np, text)
    prev.addnext(np)
    prev = np
print('参考文献重写完成: %d条' % len(REFS))

doc.save(path)
print('已保存:', path)
