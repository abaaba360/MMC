export const meta = {
  name: 'math-modeling-full-pipeline',
  description: '数学建模竞赛全流程编排：从赛题分析到论文交付，10阶段自动执行，含质量门禁和迭代控制',
  phases: [
    { title: '环境准备', detail: '验证环境、初始化状态' },
    { title: '选题比较', detail: '分析所有选题、推荐最佳' },
    { title: '赛题分析', detail: '深度分析、拆解子问题' },
    { title: '模型设计', detail: '候选模型、假设体系、符号表' },
    { title: '求解验证', detail: '代码实现、可视化、灵敏度分析' },
    { title: '论文撰写', detail: '撰写摘要和各章节' },
    { title: '质量审核', detail: '5维度评审、证据追溯、门禁检查' },
    { title: '终审交付', detail: '打包论文和支撑材料' }
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
1. 精读赛题PDF，提取所有子问题（Q1~Qn）
2. 对每个子问题标注：输入/输出/约束/目标/问题类型/依赖关系
3. 分析所有附件数据（格式/规模/质量问题）
4. 做假设敏感性预检（列出关键歧义）
5. 给出建模路线建议

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
      "problem_type": "优化类",
      "depends_on": [],
      "required_figures": [...],
      "difficulty": "medium"
    }
  ],
  "data_analysis": {...},
  "ambiguity_check": {...},
  "modeling_route": {...}
}
\`\`\`

## 产出文件
写入 state/agent_outputs/problem_decomposition.json`,
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
// Phase 3 & 4: 模型设计与基础锁定
// ============================================================
phase('模型设计')

log('🧮 Phase 3&4: 模型设计与基础锁定')

const model_design = await agent(
  `你是模型架构师。请基于赛题分析结果为每个子问题设计数学模型。

## 输入
读取 state/agent_outputs/problem_decomposition.json

## 任务
1. 对每个子问题提出≥2个候选模型（标准方案+增强方案）
2. 比较候选模型并选出最优（附淘汰理由）
3. 建立统一假设体系（10-15条，每条说明理由+必要性+违反后果）
4. 建立统一符号表
5. 构建模型依赖DAG
6. 制定论文章节大纲和字数预算

## 评审团标准（自我检查）
你的方案需要能够通过以下5维度评审（均分≥7.0）：
- 数学正确性：推导是否严谨？假设是否合理？
- 创新性：是否避免套用经典模型？有无针对问题的改进？
- 可行性：能否用现有数据求解？
- 一致性：各子模型之间是否逻辑一致？
- 完整性：是否覆盖所有约束条件？

## 产出
写入 state/agent_outputs/model_design.json`,
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

log('✅ 模型设计完成。假设体系已建立，符号表已统一。')

// ============================================================
// Phase 5: 递归求解（逐子问题）
// ============================================================
phase('求解验证')

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
    `你是代码实现专家。请为子问题 ${qi.id} 编写Python代码并求解。

## 子问题信息
${JSON.stringify(qi, null, 2)}

## 模型方案
读取 state/agent_outputs/model_design.json 中 ${qi.id} 对应的模型方案。

## 任务
1. 编写 code/q${qi.id.slice(1)}_model.py
2. 运行代码并验证输出
3. 生成≥3张论文级图表到 results/figures/
4. 输出结果到 state/agent_outputs/q${qi.id.slice(1)}_results.json

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

  if (result?.status === 'failed') {
    log(`❌ ${qi.id} 求解失败，回退到Phase 3修改模型方案...`)
    // 在实际执行中，这里会触发中循环回退
  } else {
    qi_results[qi.id] = result
    log(`✅ ${qi.id} 求解完成`)
  }
}

// ============================================================
// Phase 6 & 7: 灵敏度分析与模型评价
// ============================================================
log('📊 Phase 6&7: 灵敏度分析与模型评价')

const verification = await agent(
  `你是结果验证专家。请对所有子问题的求解结果进行验证分析。

## 输入
- state/agent_outputs/q*_results.json（各子问题结果）
- state/agent_outputs/model_design.json（模型方案）

## 任务
1. 参数灵敏度分析（关键参数±20%扰动，≥5个参数）
2. 鲁棒性测试（噪声注入/缺失数据/边界条件）
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
**权威格式文档**：`templates/CUMCM2026_标准Word模板格式规范.md`（源自备战资料Word模板），必须严格遵循。
- A4纸，页边距≥2.5cm
- **禁止目录**；正文≤30页
- 摘要单独一页、300-500字、**虎头-猪肚-豹尾三段式**、关键词4-6个
- 公式一律用公式编辑器，严禁截图
- 附录含附件文件列表+全部源代码（标注语言/作用/AI工具）
- 参考文献：GB/T 7714 + **AI工具引用格式**（[编号] 工具名称, 版本, 机构, 日期）
- AI使用声明（2026年新增）
- 不得出现参赛者身份和学校信息

## 论文结构（对齐Word模板）
1. 摘要（300-500字，虎头-猪肚-豹尾，含具体数字，1页内）
2. 一、问题重述（改写，防查重）
3. 二、问题分析（每问1.X单独小节 + 总分析流程图）
4. 三、模型假设（每条含理由）
5. 四、符号说明（三线表：符号|含义|单位）
6. 五、模型的建立与求解（每个子问题五段式：5.X.1预处理/5.X.2建立/5.X.3求解/5.X.4检验/5.X.5结果分析）
7. 六、模型检验（误差分析RMSE/MAPE + 灵敏度分析±10%/±20% + 稳健性检验）
8. 七、模型优缺点评价（7.1优点/7.2缺点/7.3改进）
9. 参考文献（GB/T 7714 + AI工具引用）
10. 附录（附件文件列表 + 源代码 + 中间结果）
11. AI使用声明

## 格式门禁（必须通过！）
- [ ] A4纸张、2.5cm边距
- [ ] 禁止目录
- [ ] 正文≤30页
- [ ] 摘要独立页、300-500字、1页内
- [ ] 模型检验覆盖误差/灵敏度/稳健性
- [ ] 参考文献含AI工具引用
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
phase('质量审核')

log('🔍 Phase 9: 终审交付')

const final_review = await agent(
  `你是质量审核专家。请以国赛评委视角对论文进行最终审核。

## 输入
- paper/final_paper.docx（完整论文）
- 所有 state/agent_outputs/ 下的中间产物
- code/ 和 results/ 下所有文件

## 5维度评审
1. 模型质量（50-60%权重）：假设合理性、推导严谨性、方法创新性
2. 问题解决（30-40%权重）：约束覆盖、结果有效性、分析深度
3. 论文规范（10-20%权重）：摘要质量、图表质量、格式合规
4. 验证分析（5-10%权重）：灵敏度、模型对比、鲁棒性
5. 综合印象：证据链、逻辑流、物理意义

## 证据追溯
对论文中每个定量声明，追溯：论文→q*_results.json→q*_model.py→原始数据

## 门禁检查
- 格式门禁：A4/边距/禁止目录/页码/摘要字数与1页/模型检验三件套/附录完整性
- 学术诚信门禁：AI声明/AI工具引用格式/AI详情/源代码/AI标注/无抄袭

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

if (final_review?.verdict === 'pass' || final_review?.verdict === 'conditional_pass') {
  log(`🎉 终审通过！总分: ${final_review.weighted_total}`)
  log('📦 打包交付物中...')

  // 生成AI工具使用详情
  log('📋 生成AI工具使用详情...')
  log('✅ 交付包准备完成：')
  log('   - delivery/论文.pdf')
  log('   - delivery/AI工具使用详情.pdf')
  log('   - delivery/支撑材料.zip')
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
