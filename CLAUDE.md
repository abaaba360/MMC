# CLAUDE.md

本项目是**数学建模竞赛多Agent协作工作流**。通过总控Agent编排6个专业Agent，实现从赛题分析到论文交付的全流程自动化。

## 项目概述

- **目标竞赛**: 2026年全国大学生数学建模竞赛 (CUMCM)
- **工作模式**: 总控Agent (Master Controller) 编排 → 6个专业Agent分工协作
- **质量保障**: 3层门禁 (证据/格式/学术诚信) + 5人评审团 + 3级迭代循环

## Agent体系

| Agent | 文件 | 职责 |
|-------|------|------|
| **Master Controller** | `.claude/skills/master-controller/SKILL.md` | 总调度：任务派发、进度管理、质量门禁、迭代控制 |
| **Analyst** | `.claude/skills/analyst/SKILL.md` | 赛题分析：选题比较、子问题拆解、数据理解 |
| **Modeler** | `.claude/skills/modeler/SKILL.md` | 模型设计：候选模型、假设体系、符号表 |
| **Coder** | `.claude/skills/coder/SKILL.md` | 代码实现：Python代码、图表生成 |
| **Verifier** | `.claude/skills/verifier/SKILL.md` | 求解验证：灵敏度分析、模型对比评价 |
| **Writer** | `.claude/skills/writer/SKILL.md` | 论文撰写：摘要、各章节、格式排版 |
| **Reviewer** | `.claude/skills/reviewer/SKILL.md` | 质量审核：5维度评审、证据追溯、门禁检查 |

## 常用命令

### 初始化
```bash
python scripts/init.py        # 初始化项目结构
python scripts/init.py B      # 初始化并指定预选赛题
```

### 质量门禁
```bash
python scripts/gates.py evidence     # 证据门禁
python scripts/gates.py format       # 格式门禁
python scripts/gates.py integrity    # 学术诚信门禁
python scripts/gates.py all          # 全部门禁检查
python scripts/gates.py ai-report    # 生成AI工具使用详情
python scripts/gates.py state        # 查看当前工作流状态
```

### 使用工作流
在Claude Code中加载技能后：
- "开始数学建模工作流" — 启动全流程
- "加载 master-controller skill" — 手动加载总控Agent
- "运行质量门禁检查" — 手动触发门禁

## 工作流10阶段

```
Phase 0: 环境准备    Phase 1: 选题比较    Phase 2: 赛题分析
Phase 3: 模型设计    Phase 4: 基础锁定    Phase 5: 递归求解
Phase 6: 灵敏度分析  Phase 7: 模型评价    Phase 8: 论文撰写
Phase 9: 终审交付
```

## 目录结构

```
d:\数模工作流\
├── .claude/skills/        # Agent定义（SKILL.md）
├── .claude/workflows/     # 工作流编排脚本
├── skills/                # GitHub技能包（MathModelAgent、Mrite-main等）
├── scripts/               # 工具脚本（门禁、初始化）
├── state/                 # 运行时状态（decision_log.json等）
├── problems/              # 赛题数据
├── code/                  # 生成的代码
├── results/               # 运行结果和图表
├── paper/                 # 论文产出
├── delivery/              # 最终交付物
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
- 论文: A4纸, 2.5cm边距, 正文≤30页, 摘要300-500字
- 评分权重: 模型质量50-60% > 问题解决30-40% > 论文规范10-20% > 验证5-10%
- 鼓励创新，反对套路化、形式化

## 参考资源与借鉴（2026-08-09）

- **`references/2026国赛备战资料/`**：5个备战文件（3天速成书籍PDF、1小时速通扫描版PDF、标准Word论文模板、常见题型及算法汇总docx、流程图PPT），可直接查阅
- **`skills/Mrite-main/`**：完整数学建模Skill副本（读题→求解→论文→编译），其 `Skill/CLAUDE.md` 含战备级论文LaTeX规范，是 writer/coder skill 高级规范区块的出处
- **`skills/MathModelAgent/`**：深度review（2026-08-12）后吸收4项高价值规范：coder 新增「非数据图自检清单」「scipy/优化求解防错细则」，writer 新增「写作前图表规划」「正文禁工作流内部名称」。其 `_references/math_modeling_norms.md`（456行题型防错知识库）可作 analyst 参考；**不采纳**Typst双引擎、drawio工具链、美赛专项规范（本项目LaTeX+Word、matplotlib、国赛）
- **`scripts/md_to_latex.py`**：图片引用改为**同名矢量PDF优先**、无则退回PNG（2026-08-12），LaTeX输出更清晰
- **`templates/MriteThesis/`**：Mrite完整可编译LaTeX模板（format.cls + 思源宋体 + 14个章节tex），与 `templates/CUMCMThesis/` 并存的备选排版方案
- **`templates/求解计划模板.md`**：六章求解计划模板（总体方向/求解思路/输出标准/操作步骤/文件清单/异常预案），Phase 4 生成 `求解/求解计划.md` 时使用
- **`templates/CUMCM2026_标准Word模板格式规范.md`**：**论文排版唯一权威依据**，由 `references/2026国赛备战资料/2026数学建模国赛标准论文Word模板.doc` 提取。含：禁止目录、摘要虎头-猪肚-豹尾三段式、五、模型建立与求解五段式(5.X.1~5.X.5)、六、模型检验三件套、七、模型优缺点评价、参考文献AI工具引用格式等。writer skill、full-pipeline.js Phase 8、gates.py 格式门禁均已对齐此规范
- **已借鉴进skill的高价值规范**（不采纳Mrite的全自动禁止交互、≤900字摘要，保留本项目人工确认点与官方300-500字）：
  - writer：摘要类型弹性分配+固定句式、统一longtable表格（列宽公式1.04−0.04N）、9框流程图模板、算法对比表格式、模型建立三段式（每步6-7公式）、参考文献标签规范、排版优化循环
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
对Claude Code说：
> "加载 master-controller skill，读取 state/decision_log.json 恢复状态，继续数学建模工作流。当前处于 Phase 0 环境准备完成，待进入 Phase 1 选题比较。"

或直接说：
> "用选题B开始数学建模工作流的端到端测试。"
