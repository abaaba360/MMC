# AGENTS.md

本项目是**数学建模竞赛多Agent协作工作流**。通过总控Agent编排6个专业Agent，实现从赛题分析到论文交付的全流程自动化。

## 项目概述

- **目标竞赛**: 2026年全国大学生数学建模竞赛 (CUMCM)
- **工作模式**: 总控Agent (Master Controller) 编排 → 6个专业Agent分工协作
- **质量保障**: 3层门禁 (证据/格式/学术诚信) + 5人评审团 + 3级迭代循环

## Agent体系

| Agent | 文件 | 职责 |
|-------|------|------|
| **Master Controller** | `.agents/skills/master-controller/SKILL.md` | 总调度：任务派发、进度管理、质量门禁、迭代控制 |
| **Analyst** | `.agents/skills/analyst/SKILL.md` | 赛题分析：选题比较、子问题拆解、数据理解 |
| **Modeler** | `.agents/skills/modeler/SKILL.md` | 模型设计：候选模型、假设体系、符号表 |
| **Coder** | `.agents/skills/coder/SKILL.md` | 代码实现：Python代码、图表生成 |
| **Verifier** | `.agents/skills/verifier/SKILL.md` | 求解验证：灵敏度分析、模型对比评价 |
| **Writer** | `.agents/skills/writer/SKILL.md` | 论文撰写：摘要、各章节、格式排版 |
| **Reviewer** | `.agents/skills/reviewer/SKILL.md` | 质量审核：5维度评审、证据追溯、门禁检查 |

## 常用命令

### 初始化
```bash
python scripts/init.py        # 初始化项目结构
python scripts/init.py B      # 初始化并指定预选赛题
```

### 质量门禁
```bash
python scripts/gates.py preflight    # 校验最新Skill已完整加载且哈希未过期
python scripts/gates.py logic        # 正式编码前：要求→模型生长→论证骨架→最小原型
python scripts/gates.py qgate Q1     # 逐题门禁；通过后才解锁依赖问题
python scripts/gates.py evidence     # 证据门禁
python scripts/gates.py format       # 格式门禁
python scripts/gates.py integrity    # 学术诚信门禁
python scripts/gates.py all          # 全部门禁检查
python scripts/gates.py ai-report    # 从真实台账生成暂存的AI工具使用详情PDF，随后收入支撑材料
python scripts/gates.py state        # 查看当前工作流状态
```

### 使用工作流
在Codex中加载技能后：
- "开始数学建模工作流" — 启动全流程
- "加载 master-controller skill" — 手动加载总控Agent
- "运行质量门禁检查" — 手动触发门禁

### 题目归档（多题隔离）
```bash
python scripts/archive_problem.py A          # 归档当前产出到 archive/选题A_日期/
python scripts/archive_problem.py B 20260812 # 指定题目和日期
python scripts/archive_problem.py A --reset  # 归档后清空共享目录，准备跑下一题
```
**⚠️ 跑新题前必须先归档上一题**：`paper/`、`results/`、`code/`、`state/agent_outputs/`、`delivery/` 是**多题共享目录**，新题的 Writer/Coder 会用同名文件覆盖上一题产出。归档脚本会把当前产出完整快照到 `archive/选题X_日期/`，避免覆盖丢失。

## 工作流10阶段

### 正式赛题启动硬要求

收到正式赛题后，主Agent必须先完整读取最新 `master-controller` 与 analyst/modeler/coder/verifier/writer/reviewer 六个专业 Skill，以及 `references/2026最新资料吸收与正式赛题执行规范.md`。随后生成 `state/agent_outputs/skill_preflight.json`，记录各文件SHA-256、读取完成标记和官方规则核对时间，并运行 `python scripts/gates.py preflight`。预检未通过不得进入选题、分析、建模或编码阶段；禁止仅凭对话记忆或旧版Skill继续工作。

```
Phase 0: 环境准备    Phase 1: 选题比较    Phase 2: 赛题分析
Phase 3: 模型设计    Phase 4: 基础锁定    Phase 5: 递归求解
Phase 6: 灵敏度分析  Phase 7: 模型评价    Phase 8: 论文撰写
Phase 9: 终审交付
```

## 目录结构

```
d:\数模工作流\
├── .agents/skills/       # 当前Codex使用的Agent定义（SKILL.md）
├── .claude/skills/       # 同步副本
├── .claude/workflows/    # 工作流编排脚本
├── skills/                # GitHub技能包（MathModelAgent、Mrite-main等）
├── scripts/               # 工具脚本（门禁、初始化）
├── state/                 # 运行时状态（decision_log.json等）
├── problems/              # 赛题数据
├── code/                  # 生成的代码
├── results/               # 运行结果和图表
├── paper/                 # 论文产出
├── delivery/              # 最终交付物
├── archive/               # 各题归档产出（选题A_日期/、选题B_日期/，防覆盖）
├── references/            # 参考资料（2026国赛备战资料等）
└── templates/             # 论文模板（CUMCMThesis / MriteThesis / 求解计划模板）
```

## 关键技术决策

1. **不重新发明轮子**: 基于成熟的GitHub项目 (MathModelAgent + MathModel-Skill + math-modeling-skills) 构建
2. **JSON作为真值源**: 所有Agent通过 `state/decision_log.json` 交换状态，不依赖对话记忆
3. **证据追溯链**: 论文声明 → q*_results.json → q*_model.py → 原始数据，确保每个数字可追溯
4. **三层迭代**: 内循环(Agent自检) → 中循环(阶段回退) → 外循环(全局一致性)
5. **AI使用追溯**: 符合2026年国赛新规，全程记录AI交互并生成《AI工具使用详情》

## 2026年国赛关键规则

- AI工具使用**必须**提交详情报告（缺失则取消评奖资格）
- 电子论文第一页为摘要专用页，原则上≤1页；正文（含AI声明和参考文献）≤30页；A4纸、页边距≥2.5cm；禁止目录
- AI工具使用声明置于参考文献之前；使用AI时支撑材料必须含 `AI工具使用详情.pdf`
- 电子论文与支撑材料分别≤20MB；全包匿名；论文不含承诺书/编号页
- 评分权重: 模型质量50-60% > 问题解决30-40% > 论文规范10-20% > 验证5-10%
- 鼓励创新，反对套路化、形式化

## 参考资源与借鉴（2026-08-09）

- **`references/2026国赛备战资料/`**：5个备战文件（3天速成书籍PDF、1小时速通扫描版PDF、标准Word论文模板、常见题型及算法汇总docx、流程图PPT），可直接查阅
- **`最新资料/` 与 `references/2026最新资料吸收与正式赛题执行规范.md`（2026-09-09）**：正式赛题最高优先级资料。已吸收2026参赛规则、北京赛区提交要求、AI规定、2022-2025优秀论文/代码/支撑材料和官方讲评；冲突时按“全国现行文件 > 赛区通知 > 校内说明 > 历史模板/论文”执行。新增题目契约、模型生长、最小原型、逐问声明闭环和精准失效机制。
- **`references/2026_AI工具使用详情模板填写规范.md`（2026-09-10）**：根据队伍提供的公众号正文和4张模板原图整理的操作性填写规范，覆盖工具清单、七环节矩阵、五类交互方式、2至3个典型交互、六类采纳核验汇总、五项人工主导确认与真实性声明；它不是官方文件，冲突时服从上述优先级。
- **`skills/Mrite-main/`**：完整数学建模Skill副本（读题→求解→论文→编译），其 `Skill/AGENTS.md` 含战备级论文LaTeX规范，是 writer/coder skill 高级规范区块的出处
- **`skills/MathModelAgent/`**：深度review（2026-08-12）后吸收4项高价值规范：coder 新增「非数据图自检清单」「scipy/优化求解防错细则」，writer 新增「写作前图表规划」「正文禁工作流内部名称」。其 `_references/math_modeling_norms.md`（456行题型防错知识库）可作 analyst 参考；**不采纳**Typst双引擎、drawio工具链、美赛专项规范（本项目LaTeX+Word、matplotlib、国赛）
- **`scripts/md_to_latex.py`**：图片引用改为**同名矢量PDF优先**、无则退回PNG（2026-08-12），LaTeX输出更清晰
- **`templates/MriteThesis/`**：Mrite完整可编译LaTeX模板（format.cls + 思源宋体 + 14个章节tex），与 `templates/CUMCMThesis/` 并存的备选排版方案
- **`templates/求解计划模板.md`**：六章求解计划模板（总体方向/求解思路/输出标准/操作步骤/文件清单/异常预案），Phase 4 生成 `求解/求解计划.md` 时使用
- **`templates/CUMCM2026_标准Word模板格式规范.md`**：由备战Word模板提取的排版基线；当年官方通知/章程和官方模板优先。已修正正文页数口径、摘要单页、AI声明顺序、附录代码双份提交，并移除固定流程图、公式数和检验套件等模板化要求；writer skill、full-pipeline.js Phase 8、gates.py 门禁均已对齐
- **已借鉴进skill的高价值规范**（不采纳Mrite的全自动禁止交互和固定摘要字数；摘要以最终单页渲染为硬门禁）：
  - writer：摘要信息闭环、统一longtable表格、按论证需要选用流程图与算法对比表、模型生长链表述、参考文献标签规范、排版优化循环；不再规定固定框数、图数或公式数
  - coder：两阶段执行（先算后画）、统计量输出（min/max/mean/std/CV/amplitude）、跨平台中文字体、图内不画set_title、灵敏度分析前置

## 当前状态（2026-08-04）

### ✅ 已完成
- 项目目录结构完整搭建
- 7个Agent定义文件全部编写（master-controller + 6个专业Agent）
- 工作流编排脚本 full-pipeline.js（10阶段）
- 质量门禁脚本 gates.py（3层门禁 + AI报告生成）
- 初始化脚本 init.py
- 3个GitHub技能包克隆到 skills/（MathModelAgent, MathModel-Skill, math-modeling-skills）
- LaTeX模板克隆到 templates/CUMCMThesis/（含承诺书+编号页）
- 论文模板和格式规范参考文档
- 状态文件和AI使用记录已初始化
- Python环境验证通过（numpy, scipy, pandas, matplotlib）

### 📋 待办
1. **✅ 端到端测试完成** (2026-08-04): 选题B全10阶段跑通，全部门禁通过，交付物在 delivery/
2. **官方文档**: 内容已转为 md 参考文件，PDF原件可在浏览器手动下载放入 templates/：
   - 格式规范PDF: http://dxs.moe.gov.cn/zx/a/hd_sxjm_gsyw/260702/2046411.shtml
   - AI使用规定: https://dxs.moe.gov.cn/zx/a/hd_sxjm_gsyw/250904/2017973.shtml
3. **✅ 国奖论文收集**: 已收录5篇到 templates/award_papers/（B060×72页, B157×67页, A196×97页, C132×138页, C023×45页），脚本 scripts/download_paper_images.py 可复用
4. **MCP服务器**: 按需安装 lit-mcp、mma-mcp、pandas-mcp-server
5. **Word模板**: 等官方发布2026版后放入 templates/
6. **图片识图管道**: scripts/parse_images.py（智谱GLM-4V-Flash）已就绪，填入API Key后可解析 award_papers 截图供参考
7. **✅ 备战资料与Mrite吸收** (2026-08-09): 备战资料→references/；Mrite→skills/Mrite-main/；MriteThesis模板已修复Menlo字体并编译通过（Error=0）；求解计划模板已建；writer/coder skill已补高级规范
8. **✅ 论文格式对齐Word标准模板** (2026-08-09): 从备战资料Word模板提取格式规范→`templates/CUMCM2026_标准Word模板格式规范.md`；writer skill、full-pipeline.js Phase 8、gates.py 格式门禁均已对齐（禁止目录/虎头猪肚豹尾摘要/五段式建模/检验三件套/AI工具引用）
9. **✅ B题按新格式重跑完成** (2026-08-09): 复用已有求解结果，按Word模板格式重写论文（复用结果→Writer重写→md_to_docx生成Word→md_to_latex编译PDF 24页Error=0），全部门禁通过；交付物在 delivery/（final_paper.docx/pdf/tex + 论文_芯片散热优化.md）；gates.py诚信门禁文件名约定修正为09_ai_declaration.md

### 🚀 启动方式（新对话中）
对Codex说：
> "加载 master-controller skill，读取 state/decision_log.json 恢复状态，继续数学建模工作流。当前处于 Phase 0 环境准备完成，待进入 Phase 1 选题比较。"

或直接说：
> "用选题B开始数学建模工作流的端到端测试。"
