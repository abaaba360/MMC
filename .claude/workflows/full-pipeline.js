export const meta = {
  name: 'math-modeling-full-pipeline',
  description: '数学建模竞赛全流程编排：从赛题分析到论文交付，10阶段自动执行，含质量门禁和迭代控制',
  phases: [
    { title: '环境准备', detail: '验证环境、初始化状态' },
    { title: '选题比较', detail: '分析所有选题、推荐最佳' },
    { title: '赛题分析', detail: '深度分析、拆解子问题' },
    { title: '模型设计', detail: '候选模型、假设体系、符号表' },
    { title: '基础锁定', detail: '论证骨架、接口契约、最小原型' },
    { title: '递归求解', detail: '逐题编码、结果与声明登记' },
    { title: '灵敏度分析', detail: '扰动、边界与不确定性分析' },
    { title: '模型评价', detail: '基线、消融、适用范围与局限' },
    { title: '论文撰写', detail: '撰写摘要和各章节' },
    { title: '终审交付', detail: '质量审核、门禁检查和打包' }
  ]
}

// ============================================================
// 数学建模竞赛全流程编排脚本
// ============================================================

// 工作目录和状态文件路径
const WORK_DIR = 'd:\\数模工作流'
const STATE_FILE = 'state/decision_log.json'
const LEDGER_FILE = 'state/ai_usage_ledger.json'

// ============================================================
// Phase 0: 环境准备
// ============================================================
phase('环境准备')

log('🔧 Phase 0: 环境准备 — 验证环境和初始化状态')

log('📚 主Agent必须先完整读取AGENTS.md、最新总控与六个专业Skill、2026最新资料执行规范、2026_AI工具使用详情模板填写规范，生成skill_preflight.json并通过 python scripts/gates.py preflight；不得由Agent自行伪造read_complete。')

// 验证目录结构
const required_dirs = ['problems', 'state', 'state/agent_outputs', 'code', 'results/figures', 'results/tables', 'paper', 'delivery', 'templates']
for (const dir of required_dirs) {
  log(`  检查目录: ${dir}`)
}

// 初始化决策日志
const init_state = {
  metadata: {
    competition: 'CUMCM_2026',
    problem: null,
    mode: 'standard',
    start_time: null,
    pipeline_version: '1.0.0'
  },
  stages: {
    S0: { status: 'in_progress', score: null, outputs: [], started_at: null, completed_at: null },
    S1: { status: 'pending', score: null, outputs: [], started_at: null, completed_at: null },
    S2: { status: 'pending', score: null, outputs: [], started_at: null, completed_at: null },
    S3: { status: 'pending', score: null, outputs: [], started_at: null, completed_at: null },
    S4: { status: 'pending', score: null, outputs: [], started_at: null, completed_at: null },
    S5: { status: 'pending', score: null, outputs: [], started_at: null, completed_at: null },
    S6: { status: 'pending', score: null, outputs: [], started_at: null, completed_at: null },
    S7: { status: 'pending', score: null, outputs: [], started_at: null, completed_at: null },
    S8: { status: 'pending', score: null, outputs: [], started_at: null, completed_at: null },
    S9: { status: 'pending', score: null, outputs: [], started_at: null, completed_at: null }
  },
  current_stage: 'S0',
  sub_questions: {},
  assumptions: { locked: false, items: [] },
  symbols: { locked: false, items: [] },
  issues: [],
  review_results: {},
  rollback_history: []
}

log('✅ 环境准备完成。状态文件已初始化。')

// ============================================================
// Phase 1: 选题比较
// ============================================================
phase('选题比较')

log('📋 Phase 1: 选题比较 — 分析所有可选题目')

const problem_comparison = await agent(
  `你是赛题分析专家。请扫描 problems/ 目录下所有选题PDF，完成选题比较分析。

## 任务
1. 读取每个选题的PDF（选题A~D）
2. 对每题进行6维度评估（数据可得性/建模难度/创新潜力/求解可行性/时间需求/工具适配度）
3. 给出排序推荐，说明每题的核心优势和风险

## 产出
生成 state/agent_outputs/problem_comparison.json，包含所有选题的评估结果和排序推荐。

## 重要
评估完成后，向用户展示结果并等待用户确认选题。不要自行决定选题！`,
  { label: '选题比较分析', phase: '选题比较', schema: {
    type: 'object',
    properties: {
      rankings: { type: 'array', items: { type: 'object', properties: {
        problem_id: { type: 'string' },
        overall_score: { type: 'number' },
        summary: { type: 'string' },
        strengths: { type: 'array', items: { type: 'string' } },
        risks: { type: 'array', items: { type: 'string' } }
      }, required: ['problem_id', 'overall_score', 'summary'] } },
      recommendation: { type: 'string' }
    },
    required: ['rankings', 'recommendation']
  }}
)

log(`📊 选题分析完成。推荐：${problem_comparison?.recommendation || '请用户确认'}`)
log('⚠️ 请用户确认选题后继续...')

// ============================================================
// Phase 2: 赛题分析 (需要用户确认选题后执行)
// ============================================================
phase('赛题分析')

log('🔍 Phase 2: 赛题分析 — 深度分析选定赛题')

const decomposition = await agent(
  `你是赛题分析专家。请深度分析用户选定的赛题。

## 前置条件
用户已在Phase 1确认选题。请读取该选题的PDF和所有附件数据。

## 任务
1. 精读赛题PDF，把每一项显式或隐式要求编号为Qx-Rxx，并保留题干原句或准确定位
2. 对每个子问题标注：输入/输出/约束/目标/依赖关系/验收标准；“问题类型”只作诊断，不能直接映射算法
3. 分析所有附件数据（格式/规模/质量问题）
4. 做假设敏感性预检（列出关键歧义）
5. 建立数据契约：字段、单位、范围、缺失、主键、时间/空间口径和跨问接口
6. 给出建模路线建议，但本阶段不预选算法

## 产出格式
\`\`\`json
{
  "problem_id": "...",
  "sub_questions": [
    {
      "id": "Q1",
      "title": "...",
      "description": "...",
      "inputs": [...],
      "outputs": [...],
      "decision_variables": [...],
      "objectives": [...],
      "constraints": [...],
      "problem_type_diagnostic": "优化类",
      "depends_on": [],
      "requirement_ids": [...],
      "acceptance_tests": [...],
      "difficulty": "medium"
    }
  ],
  "data_analysis": {...},
  "ambiguity_check": {...},
  "modeling_route": {...}
}
\`\`\`

## 产出文件
写入：
- state/agent_outputs/problem_decomposition.json
- state/agent_outputs/requirement_ledger.json
- state/agent_outputs/data_contract.json`,
  { label: '赛题深度分析', phase: '赛题分析', schema: {
    type: 'object',
    properties: {
      sub_questions: { type: 'array' },
      data_analysis: { type: 'object' },
      modeling_route: { type: 'object' }
    },
    required: ['sub_questions']
  }}
)

log(`📝 赛题分析完成。识别到 ${decomposition?.sub_questions?.length || '?'} 个子问题。`)

// ============================================================
// Phase 3: 模型设计
// ============================================================
phase('模型设计')

log('🧮 Phase 3: 让模型从题目结构中生长')

const model_design = await agent(
  `你是模型架构师。请基于赛题分析结果为每个子问题设计数学模型。

## 输入
读取 state/agent_outputs/problem_decomposition.json

## 任务
1. 先按“题目事实→数学对象→机制/不变量→最小假设→方程/约束→求解器→验证器”形成模型生长链
2. 证据充分时提出2–4个候选；证据不足时不得为凑数量制造候选。候选必须含最简单可解释基线
3. 对每个候选说明触发它的题目证据、为什么更简单模型不够、可识别性、可证伪条件、复杂度与失败模式
4. 区分数学模型、估计器、求解算法和验证方法，禁止把算法名拼成模型
5. 比较候选并选出推荐路线，记录淘汰理由；复杂模块必须规划消融实验
6. 建立统一且最小的假设体系，每条说明依据、必要性、违反后果和检验方式
7. 建立统一符号表和模型依赖DAG

## 评审团标准（自我检查）
你的方案需要能够通过以下5维度评审（均分≥7.0）：
- 数学正确性：推导是否严谨？假设是否合理？
- 创新性：是否避免套用经典模型？有无针对问题的改进？
- 可行性：能否用现有数据求解？
- 一致性：各子模型之间是否逻辑一致？
- 完整性：是否覆盖所有约束条件？

## 产出
写入：
- state/agent_outputs/model_design.json
- state/agent_outputs/model_growth_map.json
- state/agent_outputs/model_route_decision.json`,
  { label: '模型方案设计', phase: '模型设计', schema: {
    type: 'object',
    properties: {
      candidates_per_qi: { type: 'object' },
      selected_models: { type: 'object' },
      assumptions: { type: 'array' },
      symbols: { type: 'array' },
      model_dag: { type: 'object' },
      paper_outline: { type: 'object' }
    },
    required: ['selected_models', 'assumptions', 'symbols']
  }}
)

log('✅ 候选路线及其题目依据已形成。')
log('⚠️ 请团队逐问确认候选路线；确认后写入 state/agent_outputs/user_model_selection.json。未确认不得进入Phase 4。')

// ============================================================
// Phase 4: 基础锁定——在全面编码前做一次低成本逻辑审查
// ============================================================
phase('基础锁定')
log('🔒 Phase 4: 论证骨架、接口契约、最小原型与影子论文')

const logic_lock = await agent(
  `你是建模方案审查专家。请在全面编码前锁定逻辑基础。

## 输入
读取 requirement_ledger.json、data_contract.json、model_growth_map.json、model_route_decision.json、user_model_selection.json；后者必须来自团队真实确认，Agent不得代填。

## 任务
1. 为每问建立“要求→假设→模型命题→待输出结论→证据→验证”的论证骨架
2. 定义跨问接口契约（字段、单位、形状、方向、允许范围、失败处理）
3. 只实现能验证关键可行性的最小原型，不做全面计算和美化绘图
4. 写影子论文：用短段落预演每个核心结论如何由结果和验证支撑
5. 审查是否存在孤儿算法、循环论证、不可识别参数、数据不可达或结论超出模型能力

## 产出
- state/agent_outputs/argument_map.json
- state/agent_outputs/interface_contracts.json
- state/agent_outputs/prototype_review.json

prototype_review.status 只有在所有硬问题关闭后才能为 passed。`,
  { label: '基础锁定审查', phase: '基础锁定', schema: {
    type: 'object', properties: {
      status: { type: 'string', enum: ['passed', 'revise', 'blocked'] },
      hard_issues: { type: 'array' },
      selected_route_confirmed: { type: 'boolean' }
    }, required: ['status', 'hard_issues', 'selected_route_confirmed']
  }}
)
if (logic_lock?.status !== 'passed') {
  throw new Error(`Phase 4逻辑合约未通过，禁止进入全面编码：${JSON.stringify(logic_lock?.hard_issues || [])}`)
}
log('✅ 最小原型与论证骨架通过；模型基础已锁定。')

// ============================================================
// Phase 5: 递归求解（逐子问题）
// ============================================================
phase('递归求解')

log('💻 Phase 5: 逐子问题求解、可视化、验证')

const sub_questions = decomposition?.sub_questions || []
const model_dag = model_design?.model_dag || {}

// 按DAG拓扑顺序排序子问题
const sorted_qi = topologicalSort(sub_questions, model_dag)
log(`求解顺序: ${sorted_qi.map(q => q.id).join(' → ')}`)

// 逐子问题求解
const qi_results = {}
for (const qi of sorted_qi) {
  log(`  🔨 求解 ${qi.id}: ${qi.title}`)

  const result = await agent(
    `你是代码实现专家。请严格按已通过的接口契约为子问题 ${qi.id} 编写代码并求解。

## 子问题信息
${JSON.stringify(qi, null, 2)}

## 模型方案
读取 model_route_decision.json、argument_map.json、interface_contracts.json 中 ${qi.id} 的已锁定方案。

## 任务
1. 编写 code/q${qi.id.slice(1)}_model.py
2. 运行代码并验证输出
3. 仅为实际声明生成必要的论文级图表；每张图必须绑定具体claim_id
4. 输出 q${qi.id.slice(1)}_results.json 和 q${qi.id.slice(1)}_claim_registry.json
5. 与最简单基线比较；复杂模块执行预先登记的消融实验

## 代码要求
- 可复现（固定随机种子）
- 数值稳定（检查NaN/Inf）
- 约束验证（assert所有约束条件）
- 输出包含关键中间过程

## 图表要求
- PDF矢量格式，≥300 DPI
- 中文坐标轴标签
- 图内不写大标题`,
    { label: `求解${qi.id}`, phase: '求解验证', schema: {
      type: 'object',
      properties: {
        status: { type: 'string', enum: ['success', 'failed', 'partial'] },
        key_results: { type: 'object' },
        figures_generated: { type: 'array', items: { type: 'string' } },
        warnings: { type: 'array', items: { type: 'string' } }
      },
      required: ['status', 'key_results']
    }}
  )

  if (result?.status !== 'success') {
    throw new Error(`${qi.id} 求解状态为 ${result?.status || 'unknown'}，禁止下游继续；只回退受影响的模型、接口与声明。`)
  }
  const qcheck = await agent(
    `你是结果验证专家。对 ${qi.id} 执行逐题门禁：核对全部requirement_id覆盖、接口契约、数值稳定性、约束、基线/消融和每条claim的结果路径。写入 state/agent_outputs/q${qi.id.slice(1)}_verification.json；只有全部通过时status=passed、requirement_coverage=1、interface_status=passed。`,
    { label: `${qi.id}逐题门禁`, phase: '递归求解', schema: { type: 'object', properties: {
      status: { type: 'string', enum: ['passed', 'revise', 'blocked'] },
      requirement_coverage: { type: 'number' }, interface_status: { type: 'string' }, issues: { type: 'array' }
    }, required: ['status', 'requirement_coverage', 'interface_status'] }}
  )
  if (qcheck?.status !== 'passed' || qcheck?.requirement_coverage !== 1 || qcheck?.interface_status !== 'passed') {
    throw new Error(`${qi.id}逐题门禁未通过，禁止解锁依赖问题。`)
  }
  qi_results[qi.id] = result
  log(`✅ ${qi.id} 求解和逐题验证完成`)
}

// ============================================================
// Phase 6 & 7: 灵敏度分析与模型评价
// ============================================================
phase('灵敏度分析')
log('📊 Phase 6: 灵敏度、稳健性和边界测试')

const verification = await agent(
  `你是结果验证专家。请对所有子问题的求解结果进行验证分析。

## 输入
- state/agent_outputs/q*_results.json（各子问题结果）
- state/agent_outputs/model_design.json（模型方案）

## 任务
1. 根据模型机制选取真正影响结论的参数和扰动范围，不机械规定参数数目
2. 按数据与模型适用条件设计噪声、缺失、边界或极端情景测试
3. 模型对比评测（与Phase 3的候选模型量化对比）
4. 模型优势分析（证据支撑）
5. 模型局限性（真实具体的不足，非套话）
6. 改进方向和推广条件

## 产出
写入 state/agent_outputs/sensitivity_report.json 和 state/agent_outputs/model_evaluation.md`,
  { label: '验证分析', phase: '求解验证', schema: {
    type: 'object',
    properties: {
      sensitivity_complete: { type: 'boolean' },
      model_comparison_complete: { type: 'boolean' },
      key_findings: { type: 'array', items: { type: 'string' } }
    },
    required: ['sensitivity_complete', 'model_comparison_complete']
  }}
)

log('✅ 验证分析完成。')
phase('模型评价')
log('📐 Phase 7: 基线、消融、适用范围与局限性评价已纳入验证报告。')

// ============================================================
// Phase 8: 论文撰写
// ============================================================
phase('论文撰写')

log('📝 Phase 8: 论文撰写')

const paper = await agent(
  `你是数学建模论文撰写专家。请根据所有前序产出撰写符合2026年国赛规范的完整论文。

## 输入
- state/agent_outputs/problem_decomposition.json
- state/agent_outputs/model_design.json
- state/agent_outputs/q*_results.json
- state/agent_outputs/sensitivity_report.json
- state/agent_outputs/model_evaluation.md
- results/figures/ 下所有图表

## 2026年国赛论文规范（对齐Word标准模板）
规则优先级：当年官方通知/章程 > 官方模板与官方评阅解读 > 本地规范 > 往届论文习惯。
- A4纸，页边距≥2.5cm
- **禁止目录**；正文主体+AI工具使用声明+参考文献合计≤30页，附录不计入
- 第一页为摘要专用页，只含标题、摘要、关键词，无英文翻译，原则上不超过1页；最终渲染页数是硬门禁
- 公式一律用公式编辑器，严禁截图
- AI工具使用声明采用2026官方二选一原文并置于参考文献之前；声明必须与真实台账和七环节汇总一致；AI使用详情PDF收入支撑材料，不作为第三个独立上传件
- 附录含支撑材料文件列表+全部可运行源代码；代码同时进入支撑材料
- 不得出现参赛者身份和学校信息

## 论文结构（对齐Word模板）
1. 摘要专用页（题目、摘要、关键词；含核心方法、关键结果和结论，最终1页内）
2. 一、问题重述（改写，防查重）
3. 二、问题分析（每问1.X单独小节 + 总分析流程图）
4. 三、模型假设（每条含理由）
5. 四、符号说明（三线表：符号|含义|单位）
6. 五、模型的建立与求解（每个子问题五段式：5.X.1预处理/5.X.2建立/5.X.3求解/5.X.4检验/5.X.5结果分析）
7. 六、模型检验（误差分析RMSE/MAPE + 灵敏度分析±10%/±20% + 稳健性检验）
8. 七、模型优缺点评价（7.1优点/7.2缺点/7.3改进）
9. AI工具使用声明（官方文本）
10. 参考文献
11. 附录（支撑材料文件列表 + 完整源代码 + 必要中间结果）

## 格式门禁（必须通过！）
- [ ] A4纸张、2.5cm边距
- [ ] 禁止目录
- [ ] 正文≤30页
- [ ] 摘要专用页经最终渲染确认恰为1页
- [ ] 模型检验覆盖误差/灵敏度/稳健性
- [ ] AI声明位于参考文献之前；AI详情由真实台账生成
- [ ] 所有图表被正文引用
- [ ] 所有数值可追溯到代码输出
- [ ] 无身份信息
- [ ] 附录源代码完整+AI标注

## 产出
1. paper/final_paper.docx（Word格式，符合国赛模板）
2. paper/paper_sections/（各章节源文件）`,
  { label: '论文撰写', phase: '论文撰写', schema: {
    type: 'object',
    properties: {
      total_pages: { type: 'number' },
      abstract_word_count: { type: 'number' },
      figure_count: { type: 'number' },
      format_gate_passed: { type: 'boolean' },
      evidence_gate_passed: { type: 'boolean' }
    },
    required: ['format_gate_passed', 'evidence_gate_passed']
  }}
)

log(`📄 论文撰写完成。${paper?.format_gate_passed ? '✅ 格式门禁通过' : '❌ 格式门禁未通过'}`)

// ============================================================
// Phase 9: 终审交付
// ============================================================
phase('终审交付')

log('🔍 Phase 9: 终审交付')

const final_review = await agent(
  `你是质量审核专家。请以国赛评委视角对论文进行最终审核。

## 输入
- paper/final_paper.docx（完整论文）
- 所有 state/agent_outputs/ 下的中间产物
- code/ 和 results/ 下所有文件

## 5维度评审
以官方主要标准审核：假设合理性、建模创造性、结果正确性、表述清晰度。内部量表仅用于查漏，不声称是官方权重。

## 证据追溯
对论文中每个定量声明，追溯：论文→q*_results.json→q*_model.py→原始数据

## 门禁检查
- 逻辑门禁：模型生长链、为什么不用更简单模型、可识别性、反证与结论边界
- 格式门禁：A4/边距/禁止目录/正文页数口径/摘要专用页/AI声明顺序/附录完整性/最终渲染
- 学术诚信门禁：真实AI台账；工具精确版本；七环节矩阵；五类交互方式；2至3个典型交互；六类采纳核验汇总；五项人工主导确认；队伍真实性确认；指定PDF/源代码双份提交/匿名性/引用与版权

## 通过条件
- 各维度≥满分的65%
- 加权总分≥70分
- 学术诚信门禁全部通过

## 产出
写入 state/agent_outputs/quality_report.json`,
  { label: '终审评审', phase: '质量审核', schema: {
    type: 'object',
    properties: {
      weighted_total: { type: 'number' },
      verdict: { type: 'string', enum: ['pass', 'conditional_pass', 'revise', 'block'] },
      format_gate_passed: { type: 'boolean' },
      integrity_gate_passed: { type: 'boolean' },
      issues: { type: 'array' }
    },
    required: ['weighted_total', 'verdict']
  }}
)

if (final_review?.verdict === 'pass') {
  log(`🎉 终审通过！总分: ${final_review.weighted_total}`)
  log('📦 打包交付物中...')

  const delivery_check = await agent(
    `你是最终交付管理员。不得改写论文结论，只完成可复现打包和机器检查。

1. 由队伍核对 state/agent_outputs/ai_usage_summary.json 中的七环节、五类交互方式、六类采纳核验、五项人工主导、真实性确认和2至3个典型交互ID；Agent不得代填确认。
2. 从真实 state/ai_usage_ledger.json 和已确认的 ai_usage_summary.json 生成 state/submission_staging/AI工具使用详情.pdf；缺字段、脱敏或核验记录时立即阻断，禁止补造。
3. 生成唯一的支撑材料ZIP/RAR，包含README、统一运行入口、全部代码、非题目原始数据、必要中间结果；使用AI时必须含精确文件名 AI工具使用详情.pdf。
4. delivery/ 最终只保留一份电子论文（PDF或Word之一）和一份支撑材料压缩包，不含身份信息，二者各≤20MB。
5. 运行 python scripts/gates.py all；只有退出码0时 status=passed。

返回门禁结果、两个最终文件名和SHA-256。`,
    { label: '最终打包与机器门禁', phase: '终审交付', schema: { type: 'object', properties: {
      status: { type: 'string', enum: ['passed', 'blocked'] },
      paper_file: { type: 'string' }, support_file: { type: 'string' }, hashes: { type: 'object' }, issues: { type: 'array' }
    }, required: ['status', 'paper_file', 'support_file', 'hashes'] }}
  )
  if (delivery_check?.status !== 'passed') {
    throw new Error(`最终机器门禁未通过：${JSON.stringify(delivery_check?.issues || [])}`)
  }
  log('✅ 交付包准备完成：')
  log(`   - ${delivery_check.paper_file}`)
  log(`   - ${delivery_check.support_file}（使用AI时内含AI工具使用详情.pdf）`)
} else {
  log(`⚠️ 终审未通过，需要退回修改。结论: ${final_review?.verdict}`)
  log('修改建议详见 state/agent_outputs/quality_report.json')
}

log('🏁 全流程完成！')

// ============================================================
// 辅助函数
// ============================================================
function topologicalSort(sub_questions, dag) {
  // 按DAG拓扑顺序排序子问题
  const sorted = []
  const visited = new Set()
  const temp = new Set()

  function visit(qi) {
    if (temp.has(qi.id)) throw new Error(`DAG contains cycle involving ${qi.id}`)
    if (visited.has(qi.id)) return
    temp.add(qi.id)
    const deps = dag[qi.id]?.depends_on || []
    for (const dep_id of deps) {
      const dep_qi = sub_questions.find(q => q.id === dep_id)
      if (dep_qi) visit(dep_qi)
    }
    temp.delete(qi.id)
    visited.add(qi.id)
    sorted.push(qi)
  }

  for (const qi of sub_questions) {
    if (!visited.has(qi.id)) visit(qi)
  }
  return sorted
}
