# 附录

## 附录A 附件文件列表

支撑材料包含以下文件。

| 文件 | 说明 |
|------|------|
| code/data_loader.py | 数据读取与预处理 |
| code/eda.py | 探索性数据分析 |
| code/surrogate.py | 代理模型通用封装（GPR/多项式/随机森林） |
| code/utils.py | 归一化/交叉验证等通用工具函数 |
| code/q1_model.py | 问题一：机理模型与影响规律 |
| code/q2_model.py | 问题二：GPR代理模型训练与评估 |
| code/q3_model.py | 问题三：NSGA-II多目标优化与TOPSIS决策 |
| code/q4_model.py | 问题四：权重扫描与Max-Min鲁棒优化 |
| code/q5_model.py | 问题五：局部弹性/蒙特卡洛/Sobol灵敏度分析 |
| code/q6_sensitivity.py | 灵敏度综合报告生成 |
| code/q6_verifier.py | 灵敏度结果独立复核 |
| code/route_map.py | 求解路线图绘制 |
| code/run_all.py | 一键运行脚本 |
| results/q1_results.json~q5_results.json | 各问求解结果 |
| results/models/surrogates.joblib | 训练好的GPR代理模型 |
| results/figures/*.png（*.pdf） | 论文图表 |

## 附录B 源代码清单

完整源代码位于 `code/` 目录，运行方式为 `python code/run_all.py`，可自动依次运行全部脚本。各脚本均含中文注释并固定随机种子，保证结果可复现。各文件作用及AI使用情况说明如下。

| 文件 | 作用 | 是否AI生成 |
|------|------|-----------|
| data_loader.py | 读取附件2，统一列名并做类型安全清洗 | 是（经人工审查修改） |
| eda.py | 探索性数据分析，生成相关性/分布图 | 是（经人工审查修改） |
| surrogate.py | GPR与多项式、随机森林代理模型通用封装 | 是（经人工审查修改） |
| utils.py | 标准化/归一化/交叉验证等工具函数 | 是（经人工审查修改） |
| q1_model.py | 问题一机理模型拟合与影响规律分析 | 是（经人工审查修改） |
| q2_model.py | 问题二GPR代理模型训练与5折/留一交叉验证 | 是（经人工审查修改） |
| q3_model.py | 问题三NSGA-II寻优、熵权TOPSIS与多路线交叉验证 | 是（经人工审查修改） |
| q4_model.py | 问题四权重扫描与Max-Min鲁棒优化 | 是（经人工审查修改） |
| q5_model.py | 问题五局部弹性/双源蒙特卡洛/Sobol分析 | 是（经人工审查修改） |
| q6_sensitivity.py | 生成灵敏度综合报告 | 是（经人工审查修改） |
| q6_verifier.py | 对灵敏度结论独立复核 | 是（经人工审查修改） |
| route_map.py | 绘制求解总技术路线图 | 是（经人工审查修改） |
| run_all.py | 一键依次运行全部脚本 | 是（经人工审查修改） |

## 附录C AI工具使用详情

《AI工具使用详情》（Markdown格式，随支撑材料一并提交）内容包括所用AI工具名称与版本、具体使用目的和环节、关键交互记录（重要提示词与回复）以及采纳和人工修改情况。本论文所用AI辅助工具已在参考文献[12]中列出。
