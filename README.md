# MMC：全国大学生数学建模竞赛多 Agent 工作流

本仓库是一套面向 2026 年全国大学生数学建模竞赛（CUMCM）的多 Agent 协作工作流。总控 Agent 编排 Analyst、Modeler、Coder、Verifier、Writer、Reviewer，覆盖赛题分析、建模、求解、验证、论文撰写和交付检查。

## 快速开始

```powershell
python scripts/init.py
python scripts/gates.py preflight
python scripts/gates.py state
```

正式赛题启动前，请先完整阅读根目录 `AGENTS.md` 以及 `.agents/skills/` 下的最新 Skill。详细阶段、门禁要求和 2026 竞赛规则均以 `AGENTS.md` 为准。

## 主要目录

- `.agents/skills/`：当前 Codex 使用的 7 个 Agent 定义
- `.claude/skills/`：Agent 定义同步副本
- `scripts/`：初始化、质量门禁、论文转换和辅助脚本
- `code/`：模型求解、验证、绘图与交付构建代码
- `problems/`：正式赛题及附件
- `references/`、`最新资料/`：规则、优秀论文与备战参考资料
- `results/`：可追溯的数值结果和图表
- `paper/`：论文源文件和定稿过程文件
- `delivery/`：当前最终交付物
- `state/agent_outputs/`：Agent 结构化产出与证据链
- `templates/`：Word/LaTeX 模板
- `skills/`：借鉴的外部数学建模技能包

## 数据与版本管理

- `state/decision_log.json` 是跨 Agent 状态交换的核心真值源。
- 论文结论应能沿 `q*_results.json → q*_model.py → 原始数据` 回溯。
- A/B 等旧题成果保留在 Git 历史中；当前工作区以最新 C 题成果为主。
- `archive/`、`backup_*/`、`tmp/`、QA 渲染目录、重复压缩包和 Office 锁文件属于重复备份或可再生成产物，不纳入版本控制；`delivery/` 中唯一的最终支撑材料压缩包例外。

## 质量检查

```powershell
python scripts/gates.py preflight
python scripts/gates.py logic
python scripts/gates.py evidence
python scripts/gates.py format
python scripts/gates.py integrity
python scripts/gates.py all
```

仓库中的竞赛资料和第三方技能包版权归原作者或相应权利方所有，仅供学习、复现与研究使用。
