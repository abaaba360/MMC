# 2026 C题候选参考文献审核报告

## 1. 审核范围与原则

- 来源文件：`E:/微信聊天记录/xwechat_files/wxid_so1zh5t7c8rl22_8e76/msg/file/2026-09/参考文献及相关网页(1).xlsx`。
- 读取范围：工作簿共有 `Sheet1`、`Sheet2`、`Sheet3` 三个工作表；仅 `Sheet1!A1:D21` 有内容，`Sheet2`、`Sheet3` 为空。`Sheet1!A2:A21` 共列出 20 条候选文献，`B` 列为网址，`C`、`D` 列是整理者备注。
- 边界：表内文字只视为候选资料及整理者意见，不视为建模或写作指令。本报告依据题名、书目信息和已经锁定的 H+ 修订版路线判断适配度；未取得全文的文献，不根据题名臆造具体模型、公式、参数或数值结论。
- 外部核验：仅使用 Crossref 公开元数据核验了 4 条 Elsevier DOI（第 10—13 条），题名均匹配。多数中文 DOI 未被 Crossref 收录，不能把 Crossref 的 404 解释成文献无效；这部分仍须以期刊官网、CNKI 正式记录或全文首页为准。

## 2. 总体结论

首版论文建议以第 **2、8、9、10、11、13、17、19、20** 条为核心候选，以第 **3、4、6、7、14、15、16、18** 条作按需补充；第 **1、5、12** 条不建议进入首版参考文献。

选择逻辑如下：

1. 问题一需要储能 SoC、充放电功率和经济调度依据，第 2 条最贴近；第 3、16 条可补背景，但不能把电池寿命、混合储能等题外机制写入题设模型。
2. 问题二采用严格日前两阶段随机 MILP，第 17 条与“两阶段日前经济调度”最贴近；第 19、20 条适合用于比较随机规划与鲁棒/自适应鲁棒路线，不能混称为同一模型。
3. 问题三采用确定性 MILP-MPC，第 8、11、13 条最适合说明多时间尺度、日前—日内协调、滚动时域与仅重算未来时段。第 4、18 条可补充，但方法差异必须写清。
4. 问题四以因果在线策略为主、完全价格信息结果为下界。第 6、7 条只能支撑实时/分时电价作为调度信号；第 10、11、13 条可支撑实时或滚动调度框架。表内没有能够直接支撑“电价预测模型”或“完全价格信息下界”定义的专门文献。
5. 第 9 条是表内最接近预测问题的文献，但题名为“微电网功率预测”，不是专门的光伏短期预测。若正文采用某一明确的光伏预测算法和误差指标，仍需另有与该算法直接对应的可靠来源，不能让第 9 条承担超出其内容的论证。

## 3. 逐条审核

相关性等级：高＝可直接支撑本文某一核心建模环节；中＝可支撑局部背景或模型比较；低＝仅主题邻近；无＝不能合理支撑。

| 编号 | 作者、年份、题名与来源 | URL | 相关性判断 | 正文可支撑位置 | 采用建议与限制 |
|---|---|---|---|---|---|
| 1 | 王小文，2025，《基于深度强化学习的智能微电网协同优化运行研究》，山东大学学位论文 | [CNKI](https://kns.cnki.net/kcms2/article/abstract?v=14XpHnsxtHF7F2RfFSqDhpHmkb34EwbnZ8n_soR3paCeobo-7tCXyQvi6F2A1CEvVjGHr_km51wsAE2zfoDIvOZvBz7tke__MU4Lxy6W-e67jB1MYmygBxzrNmFTq-bVMVKNy4qVPID0qsckM7aRWbKdFqmu-xNQ38q_vYSHyNxf7XjqtxBo8bHftllI65KF&uniplatform=NZKPT&language=CHS) | 微网高；储能中；其余低/无 | 至多用于引言的智能微网研究背景 | **不建议首版采用**。深度强化学习与 MILP、随机规划、MPC 主线不一致。 |
| 2 | 张亚琳，2025，《具有电池储能系统的微电网分布式经济调度方案与SoC均衡控制》，南开大学学位论文 | [CNKI](https://kns.cnki.net/kcms2/article/abstract?v=14XpHnsxtHHMVyB2QBAdkBtLhO3uuc78z62pW93-pe9Gmx3XW_5p1zsqil1qtabjqTIOnbiV0oQQ4NJyN7T92yqAeamK4i91Mleu1yk6Vp4IjEpMYEGKHgZ6V3WD70d_VjspRVYfXaLRaAHQONXXx5-t4GvtjlHn7VsPhMbIENfLnSMB4hVH9Q==&uniplatform=NZKPT&language=CHS) | 微网、储能调度高 | 问题一：SoC 递推、状态边界及储能经济调度背景 | **核心候选**。只引用共同的储能和 SoC 思想，不把分布式算法说成本文方法。 |
| 3 | 王志伟、郭亚森、银姣姣等，2026，《考虑储能电池寿命与新能源消纳的风光储微电网日前优化调度》，《山西电力》2026(4):50-59 | [CNKI](https://kns.cnki.net/kcms2/article/abstract?v=14XpHnsxtHHPBLEiM04PTe2uCnsjiFrjUwttf9ZOplm6dzdNDqNtr9QOW2a6Ev2E38e162Qzza-2iFSt65iENSKm-nFeoDcDdBVwsSqadI9SjhdkxIJ79iAuYbssFAHyQR6HXBM1uvudej-Kpq6HyUlRVvsd0MAHtFsHkCB7-oAZitixrbaXJQ==&uniplatform=NZKPT&language=CHS) | 日前储能调度高；新能源消纳中 | 问题一、二的日前风光储调度背景 | **补充候选**。表内无 DOI，定稿前核正式页码；本文若不计寿命成本，不引用其寿命结论。 |
| 4 | 王立舒、宋英宣、魏东辉等，2026，《计及调节优先级的微电网双时间尺度鲁棒滚动优化调度》，《电力系统及其自动化学报》网络首发:1-13 | [DOI](https://doi.org/10.19635/j.cnki.csu-epsa.001884) | 多时间尺度、滚动调度高；鲁棒优化中 | 问题三滚动调整的研究背景和模型评价 | **补充候选**。本文是确定性 MILP-MPC，不得写成采用该文鲁棒模型；网络首发信息需复核。 |
| 5 | 闵鹏、林峰、赵宇辉，2026，《基于深度强化学习的微电网优化调度策略研究》，《电气开关》64(4):50-53 | [CNKI](https://kns.cnki.net/kcms2/article/abstract?v=14XpHnsxtHEv-b9d3lMHH5edmRSTL1dHVQLtJ-cNG3eMMNtfxN7uXbYGDzGEQujquwG0VktT9OgzmXJ3tJCXWuIL2kRRE6ZiEX0sS3ibqpw05PmV5GTTxlJWu1v0OKp-T7yiVe-MQGEqvzxTcQEyW1FK6VwNWaHiA0HLUqfra3ju_5as0yBN5Q==&uniplatform=NZKPT&language=CHS) | 微网高；本文方法适配低 | 引言中智能方法列举 | **不建议首版采用**。与主路线不一致，且不能支撑问题三的 MPC。 |
| 6 | 胡美璇、周洪、胡文山等，2016，《一种面向微电网多自主体系统的实时电价算法》，《电力建设》37(3):8-16 | [DOI](https://doi.org/10.3969/j.issn.1000-7229.2016.03.002) | 实时电价高；价格预测无 | 问题四引言：实时价格作为供需协调信号 | **补充候选**。研究价格形成而非价格预测，不能支撑完全信息下界。 |
| 7 | 王凌云、王晓敏、胡兴媛等，2020，《基于多智能体微网的需求侧分时电价优化调度》，《信息与控制》49(4):429-435 | [DOI](https://doi.org/10.13976/j.cnki.xk.2020.9297) | 分时价格与调度高；预测无 | 问题四背景：价格信号改变调度决策 | **补充候选**。本文若不建模需求响应，不能引用其需求侧模型或结论。 |
| 8 | 李嘉伟、巨云涛、张璐等，2024，《基于分布鲁棒模型预测控制的微电网多时间尺度优化调度》，《电力工程技术》43(4):45-55 | [DOI](https://doi.org/10.12158/j.2096-3203.2024.04.005) | MPC、多时间尺度、储能调度高 | 问题三：随新信息滚动优化尚未执行时段的思想 | **核心候选**。只借鉴 MPC 结构，必须说明本文没有采用其分布鲁棒不确定集。 |
| 9 | 张理、王宝、贾健雄等，2025，《微电网功率预测与调度端到端协同优化方法》，《上海交通大学学报》59(6):720-731 | [DOI](https://doi.org/10.16183/j.cnki.jsjtu.2024.224) | 预测—调度耦合高；专门光伏预测中 | 问题二、三：预测误差经调度作用于运行成本的研究动机 | **核心候选**。未读全文前不引用网络结构、损失函数或数值结果；不能替代专门光伏预测文献。 |
| 10 | LIU C, QIN Y, ZHANG H，2020，Real-time scheduling strategy for microgrids considering operation interval division of DGs and batteries，*Global Energy Interconnection* 3(5):442-452 | [DOI](https://doi.org/10.1016/j.gloei.2020.11.004) | 实时调度、储能高 | 问题三、四：在线更新与因果可执行性 | **核心候选**。Crossref 题名核验通过；不能支撑题设特有的购电结算比例。 |
| 11 | OROZCO C, BORGHETTI A, DE SCHUTTER B 等，2022，Intra-day scheduling of a local energy community coordinated with day-ahead multistage decisions，*Sustainable Energy, Grids and Networks* 29:100573 | [DOI](https://doi.org/10.1016/j.segan.2021.100573) | 日前—日内、多阶段、滚动调度高 | 问题二与三衔接：日前承诺、日内更新、已执行决策不可回溯 | **核心候选**。Crossref 题名核验通过；local energy community 与题设微网存在场景差异。 |
| 12 | ZHONG W, LIU Y, YANG C 等，2022，Optimal energy management for multi-energy multi-microgrid networks considering carbon emission limitations，*Energy* 246:123428 | [DOI](https://doi.org/10.1016/j.energy.2022.123428) | 微网一般背景高；当前核心问题低 | 只能用于一般能量管理背景 | **不建议首版采用**。多能、多微网、碳约束均非题设主矛盾。Crossref 题名核验通过。 |
| 13 | ELKAZAZ M, SUMNER M, THOMAS D，2020，Energy management system for hybrid PV-wind-battery microgrid using convex programming, model predictive and rolling horizon predictive control with experimental validation，*International Journal of Electrical Power & Energy Systems* 115:105483 | [DOI](https://doi.org/10.1016/j.ijepes.2019.105483) | PV—储能微网、MPC、滚动时域高 | 问题三模型建立和可实施性讨论 | **核心候选**。Crossref 题名核验通过；其凸规划与本文含充放电互斥变量的 MILP 不能混称。 |
| 14 | 于天佑、罗承东、潘雪丽等，2026，《调压站微电网源荷双重不确定下的分布鲁棒优化调度》，《上海交通大学学报》网络首发 | [DOI](https://doi.org/10.16183/j.cnki.jsjtu.2026.029) | 源荷不确定性、分布鲁棒高 | 问题二的不确定性背景或鲁棒路线比较 | **补充候选**。不是随机场景期望模型的直接依据；网络首发信息和全文需复核。 |
| 15 | 周昆树，2024，《微电网环境下考虑源荷不确定性的储能经济优化调度研究》，合肥工业大学学位论文 | [CNKI](https://kns.cnki.net/kcms2/article/abstract?v=14XpHnsxtHE5HXzSz_LHKmf_w_asEn7Mkzx0772YT04khpcToLXbi0CX2fW_ysdN3DQa_0lkg5QTF5ZyO0qEH_tKTZYRVs0iv3wqwEQnKsTMq7fNYFm33ijryo6SSQf6n3iHIvzppLEBgSONhB6n_ce7yxTgfL_ZmsvbkuzQIBlq_GPomuSTSY9V_FWoFTcy&uniplatform=NZKPT&language=CHS) | 储能、源荷不确定性高 | 问题二：源荷误差进入经济调度的动机 | **补充候选**。关键方法优先用同行评议期刊文献。 |
| 16 | 陈敬峰，2018，《含混合储能的独立型微电网系统控制与优化调度策略研究》，华南理工大学学位论文 | [CNKI](https://kns.cnki.net/kcms2/article/abstract?v=14XpHnsxtHH-lFwunwBMkx7ccS2VMkCYrTut_HtjTjciRCFcJ5uTY3j1Xzg3Ha1ShT-EukkFAjrsmOQ_KCW5Ysrzqfpp-Kg9FT0dwnBFAdBsrRXXdskbfJwr2Eg9vqU4z9lPpQFAFZuchA2Osrh7JF41AcV5nhYU_yAe1BKi07rNpLQOY0dqmlwKALZ4fbqP&uniplatform=NZKPT&language=CHS) | 储能微网高；场景匹配中 | 问题一：供需平衡与储能状态约束背景 | **补充候选**。独立型、混合储能与题设并网购电、单储能存在边界差异。 |
| 17 | 侯慧、王晴、薛梦雅等，2022，《计及源荷不确定性及需求响应的离网型微电网两阶段日前经济调度》，《电力系统保护与控制》50(13):73-85 | [DOI](https://doi.org/10.19783/j.cnki.pspc.211406) | 两阶段日前、不确定性、储能高 | 问题二：第一阶段计划、随机实现后第二阶段补救及期望成本结构 | **核心候选**。该文包含需求响应且为离网型；本文第二阶段只允许紧急购电，必须说明变量集合更窄。 |
| 18 | 徐钰涵，2023，《考虑源荷不确定性的微电网多时间尺度优化调度》，华南理工大学学位论文 | [CNKI](https://kns.cnki.net/kcms2/article/abstract?v=14XpHnsxtHGW-DScEJ4M9lMkM4WtMFZFGxNZuX_TW6Wypf11KkznxBH96f7ABP8ViHPxDAzmCgnBdPVusZdlg3o9NPBSUyczrA-2aY3Sj5FJuIYREN8bRADGanzZF7Cd3UObVq6wYuKHTvFqfgROuCyed9Tdra4pgg4z9MHSQyf9f8FhihRSg8e_804T16rI&uniplatform=NZKPT&language=CHS) | 多时间尺度、不确定性高 | 问题三多时标调整背景 | **补充候选**。未读全文前不能仅凭题名写成采用 MPC。 |
| 19 | 刘一欣、郭力、王成山，2018，《微电网两阶段鲁棒优化经济调度方法》，《中国电机工程学报》38(14):4013-4022,4307 | [DOI](https://doi.org/10.13334/j.0258-8013.pcsee.170500) | 两阶段、鲁棒调度高 | 问题二的模型比较和路线选择说明 | **核心候选**。鲁棒优化不等于随机规划，只能作为对照或两阶段结构参考。 |
| 20 | 王灿、张雪菲、凌凯等，2024，《基于区间概率不确定集的微电网两阶段自适应鲁棒优化调度》，《中国电机工程学报》44(5):1750-1764 | [DOI](https://doi.org/10.13334/j.0258-8013.pcsee.221968) | 两阶段、自适应鲁棒、不确定性高 | 问题二的模型比较与概率信息不完备讨论 | **核心候选**。若本文采用经验场景概率，不得声称采用区间概率不确定集。 |

## 4. 建议在首版论文中的引用布置

### 4.1 引言与问题背景

- 用第 2、13 条说明储能参与微网能量管理的作用。
- 用第 9 条说明预测质量与调度成本之间存在耦合关系。
- 问题四若需要交代价格机制，可选第 6 或第 7 条之一，避免同义堆叠。
- 不建议用第 1、5 条把“深度强化学习”写成综述重点，因为正文不采用该路线。

### 4.2 问题一：确定性储能经济调度

- 首选第 2 条支撑 SoC 状态约束和电池经济调度背景。
- 第 3 条只在讨论新能源消纳或储能运行权衡时补充；若模型没有电池衰减项，就不要引用寿命建模结论。
- 模型方程仍应从题目给出的供需关系、功率边界、容量边界和 90% 充/放电效率逐项推导，文献不能替代题设推导。

### 4.3 问题二：严格日前两阶段随机 MILP

- 第 17 条用于说明“日前决策—不确定性实现—补救决策”的两阶段结构。
- 第 19、20 条放在模型比较或模型评价中，解释为什么鲁棒/自适应鲁棒是可选路线，而本文依据题目所给数据和概率场景选择随机 MILP。
- 第 14、15 条最多作为源荷不确定性的补充材料。
- 必须明确本文第二阶段只允许 5 倍价格的紧急购电，不允许储能事后重调；这是由题目推导出的信息与决策边界，不是文献中的通用设定。

### 4.4 问题三：确定性 MILP-MPC

- 第 8、13 条说明滚动时域控制会在新信息到达后重新优化尚未执行时段。
- 第 11 条说明日前计划与日内决策的协调关系。
- 第 10 条补充实时调度的可执行性。
- 不引用第 8 条的分布鲁棒结论来包装本文确定性模型；减购按 50% 电价逐次结算、增购按 1.5 倍以及紧急购电按 5 倍，均应直接由题目规则推导。

### 4.5 问题四：因果在线价格策略与完全信息下界

- 第 6、7 条只能说明电价信号会影响微网调度。
- 第 10、11、13 条可以说明因果滚动策略的时间顺序：每个决策时点仅用已知信息更新未来决策。
- 表内没有专门的电价预测或完美信息价值文献，因此不要写“依据第 6 条预测未来电价”或“第 7 条证明完全信息下界”。完全价格信息解之所以构成价格信息下界，应由可行域包含关系和“信息更多不会使最优值变差”的数学论证给出。

## 5. GB/T 7714—2015 候选格式

以下格式按表内书目信息整理。正式使用前仍应核对学位层次、学位授予地、网络首发日期、卷期和页码；正文只保留实际引用过的条目。

1. 王小文. 基于深度强化学习的智能微电网协同优化运行研究[D]. 济南: 山东大学, 2025. DOI:10.27272/d.cnki.gshdu.2025.007849.
2. 张亚琳. 具有电池储能系统的微电网分布式经济调度方案与SoC均衡控制[D]. 天津: 南开大学, 2025. DOI:10.27254/d.cnki.gnkau.2025.000023.
3. 王志伟, 郭亚森, 银姣姣, 等. 考虑储能电池寿命与新能源消纳的风光储微电网日前优化调度[J]. 山西电力, 2026(4):50-59.
4. 王立舒, 宋英宣, 魏东辉, 等. 计及调节优先级的微电网双时间尺度鲁棒滚动优化调度[J/OL]. 电力系统及其自动化学报, 2026:1-13[2026-09-10]. DOI:10.19635/j.cnki.csu-epsa.001884.
5. 闵鹏, 林峰, 赵宇辉. 基于深度强化学习的微电网优化调度策略研究[J]. 电气开关, 2026, 64(4):50-53.
6. 胡美璇, 周洪, 胡文山, 等. 一种面向微电网多自主体系统的实时电价算法[J]. 电力建设, 2016, 37(3):8-16. DOI:10.3969/j.issn.1000-7229.2016.03.002.
7. 王凌云, 王晓敏, 胡兴媛, 等. 基于多智能体微网的需求侧分时电价优化调度[J]. 信息与控制, 2020, 49(4):429-435. DOI:10.13976/j.cnki.xk.2020.9297.
8. 李嘉伟, 巨云涛, 张璐, 等. 基于分布鲁棒模型预测控制的微电网多时间尺度优化调度[J]. 电力工程技术, 2024, 43(4):45-55. DOI:10.12158/j.2096-3203.2024.04.005.
9. 张理, 王宝, 贾健雄, 等. 微电网功率预测与调度端到端协同优化方法[J]. 上海交通大学学报, 2025, 59(6):720-731. DOI:10.16183/j.cnki.jsjtu.2024.224.
10. LIU C, QIN Y, ZHANG H. Real-time scheduling strategy for microgrids considering operation interval division of DGs and batteries[J]. Global Energy Interconnection, 2020, 3(5):442-452. DOI:10.1016/j.gloei.2020.11.004.
11. OROZCO C, BORGHETTI A, DE SCHUTTER B, et al. Intra-day scheduling of a local energy community coordinated with day-ahead multistage decisions[J]. Sustainable Energy, Grids and Networks, 2022, 29:100573. DOI:10.1016/j.segan.2021.100573.
12. ZHONG W, LIU Y, YANG C, et al. Optimal energy management for multi-energy multi-microgrid networks considering carbon emission limitations[J]. Energy, 2022, 246:123428. DOI:10.1016/j.energy.2022.123428.
13. ELKAZAZ M, SUMNER M, THOMAS D. Energy management system for hybrid PV-wind-battery microgrid using convex programming, model predictive and rolling horizon predictive control with experimental validation[J]. International Journal of Electrical Power & Energy Systems, 2020, 115:105483. DOI:10.1016/j.ijepes.2019.105483.
14. 于天佑, 罗承东, 潘雪丽, 等. 调压站微电网源荷双重不确定下的分布鲁棒优化调度[J/OL]. 上海交通大学学报, 2026[2026-09-10]. DOI:10.16183/j.cnki.jsjtu.2026.029.
15. 周昆树. 微电网环境下考虑源荷不确定性的储能经济优化调度研究[D]. 合肥: 合肥工业大学, 2024. DOI:10.27101/d.cnki.ghfgu.2024.000060.
16. 陈敬峰. 含混合储能的独立型微电网系统控制与优化调度策略研究[D]. 广州: 华南理工大学, 2018. DOI:10.27151/d.cnki.ghnlu.2018.000001.
17. 侯慧, 王晴, 薛梦雅, 等. 计及源荷不确定性及需求响应的离网型微电网两阶段日前经济调度[J]. 电力系统保护与控制, 2022, 50(13):73-85. DOI:10.19783/j.cnki.pspc.211406.
18. 徐钰涵. 考虑源荷不确定性的微电网多时间尺度优化调度[D]. 广州: 华南理工大学, 2023. DOI:10.27151/d.cnki.ghnlu.2023.004651.
19. 刘一欣, 郭力, 王成山. 微电网两阶段鲁棒优化经济调度方法[J]. 中国电机工程学报, 2018, 38(14):4013-4022, 4307. DOI:10.13334/j.0258-8013.pcsee.170500.
20. 王灿, 张雪菲, 凌凯, 等. 基于区间概率不确定集的微电网两阶段自适应鲁棒优化调度[J]. 中国电机工程学报, 2024, 44(5):1750-1764. DOI:10.13334/j.0258-8013.pcsee.221968.

## 6. 交付给 Writer/Reviewer 的硬性提醒

1. 参考文献表不是模型来源清单。正文每次引用都必须对应一句可被该文真实支持的陈述；不能只因题名相似就在公式后加编号。
2. 题目规则优先于文献惯例。90% 充/放电效率、禁止同时充放电、问题二第二阶段只允许紧急购电、问题三逐次调整结算、问题四的因果信息边界，都应从题面逐项推出。
3. “随机优化”“鲁棒优化”“分布鲁棒优化”不能互换。H+ 修订版采用何种模型，正文必须使用对应术语，并把其他路线放到比较或局限性部分。
4. 定稿前核对所有中文文献首页和 DOI；尤其是 2026 年网络首发/新刊条目。没有拿到全文的条目，不引用其定理、公式、参数和数值结论。
5. 首版以 8—12 条真正用到的高相关文献为宜，避免为了显得新而堆入深度强化学习、多能碳约束等题外文献。

逐条结构化字段、相关性分项评分和候选格式另见 `state/agent_outputs/reference_selection.json`。
