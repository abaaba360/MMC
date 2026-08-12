# 数学建模竞赛求解+论文自动生成模板

> 一个 Claude Code Skill - 读题 → 求解 → 论文 → 编译，全流程自动完成。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Claude%20Code-Skill-green)](https://claude.ai/code)

---

## 简介

本项目是一个 **Claude Code 技能（Skill）** 项目模板，专为数学建模竞赛（如国赛、美赛、MathorCup 等）设计。只需将赛题和数据放入对应文件夹，说一句 **"开始求解"**，AI 即可自动完成：

- 读取赛题（PDF/DOCX）与附件数据（xlsx/docx/csv）
- 制定求解计划，逐问规划方法+输出
- 编写 Python 代码逐题求解，自动生成图表
- 撰写完整论文（LaTeX），含摘要/建模/检验/评价/参考文献
- 编译排版为 PDF，自动修复 Warning/Error

---

## 核心特性

- **一键启动** - 说"开始求解"即可，AI 全自动推进
- **完整流程** - 覆盖读取→规划→建模→求解→论文→编译的全部环节
- **高质量论文** - 内置详尽的 LaTeX 规范（摘要≤900字/1页、流程图固定模板、统一 longtable 表格样式等）
- **跨平台中文** - Python 绘图自动适配 macOS/Windows/Linux 中文字体
- **鲁棒性强** - 含异常预案、灵敏度分析、交叉验证等学术规范环节
- **模块化论文** - 每问拆分为 分析与准备 + 建模与求解 两个子文件，便于组织与修改
- **自适应排版** - 表格自动换页、自动修正编译错误、排版优化循环

---

## 适用场景

- 全国大学生数学建模竞赛（CUMCM）
- 美国大学生数学建模竞赛（MCM/ICM）
- MathorCup 高校数学建模挑战赛
- 亚太地区大学生数学建模竞赛（APMCM）
- 研究生数学建模竞赛
- 其他各类数学建模竞赛

覆盖问题类型：优化/预测/分类/评价/机理分析/数据分析/建议总结等。

---

## 快速开始

### 第一步：安装配置

#### 1.1 安装 Claude Code

1. 访问 [claude.ai/code](https://claude.ai/code) 下载 Claude Code 客户端
2. 按照提示完成安装并登录账号

#### 1.2 安装 Python 环境

**macOS/Linux：**
```bash
# 使用 conda（推荐）
conda create -n math建模 python=3.10
conda activate math建模

# 安装依赖
pip install pandas numpy matplotlib scipy scikit-learn chardet openpyxl xlrd
```

**Windows：**
```bash
# 使用 pip
pip install pandas numpy matplotlib scipy scikit-learn chardet openpyxl xlrd
```

#### 1.3 安装 LaTeX 环境

**macOS：**
```bash
# 安装 MacTeX（约 5GB）
brew install --cask mactex
```

**Windows：**
```bash
# 安装 MiKTeX
# 下载地址：https://miktex.org/download
# 安装完成后，在命令提示符中验证：
xelatex --version
```

**Ubuntu/Debian：**
```bash
sudo apt install texlive-xetex
```

### 第二步：获取模板

#### 方式一：克隆仓库
```bash
git clone https://github.com/Rzna-5559/Mrite-Skills.git
cd Mrite-Skills
```

#### 方式二：下载 ZIP
直接在 GitHub 页面点击 Code → Download ZIP，然后解压。

### 第三步：放入赛题和数据

1. 将赛题文件（PDF 或 DOCX 格式）放入 `题目/` 文件夹
2. 将附件数据文件（xlsx/docx/csv 格式）放入 `数据/` 文件夹

示例：
```
题目/
├── 题目B：零售销售额的预测与数据分析.pdf
数据/
├── data.csv
```

### 第四步：启动 Claude Code 并开始求解

1. 在终端中进入项目目录：
```bash
cd Mrite-Skills
```

2. 启动 Claude Code：
```bash
claude
```

3. 在 Claude Code 中输入：
```
开始求解
```

4. AI 将自动依次执行：
   - 读取赛题和数据
   - 制定求解计划
   - 逐题编写 Python 代码求解
   - 生成图表
   - 撰写完整 LaTeX 论文
   - 编译生成 PDF

---

## 项目结构

```
Mrite-Skills/
├── CLAUDE.md                    # Skill 定义文件（AI 行为规范）
├── README.md                    # 使用说明文档
├── LICENSE                      # MIT 许可证
├── 题目/                        # 放入赛题文件
│   └── 题目B：xxx.pdf
├── 数据/                        # 放入附件数据
│   └── data.csv
├── 求解/                        # AI 自动生成
│   ├── 求解计划.md
│   ├── 预处理数据.csv
│   ├── 问题一/
│   │   ├── 问题一_<描述>.py
│   │   └── figures/
│   ├── 问题二/
│   └── 问题N/
└── 论文/                        # AI 自动生成
    ├── 论文.tex                 # 主文件
    ├── 论文.pdf                 # 最终输出
    ├── format.cls               # 模板样式
    ├── fonts/                   # 思源宋体字体
    ├── 0.摘要.tex
    ├── 1.引言.tex
    ├── 2.总体分析.tex
    ├── 3.模型假设.tex
    ├── 4.符号说明.tex
    ├── 5.模型的建立与求解.tex
    ├── 5.1.问题1的建立求解.tex
    ├── 5.1.1.分析与准备.tex
    ├── 5.1.2.建模与求解.tex
    ├── 6.模型检验.tex
    ├── 7.模型评价.tex
    ├── 8.模型改进推广.tex
    ├── 9.参考文献.tex
    └── 10.附录.tex
```

---

## 执行流程详解

### Step 0：读取输入
- 解析 `题目/` 下的 PDF/DOCX 文件
- 全量读取 `数据/` 下所有 xlsx/docx/csv
- 打印数据总览，自动识别问题数量 N

### Step 1：求解计划
生成 `求解/求解计划.md`，包含：
1. 题目总体方向
2. 各题求解思路（含方法匹配表）
3. 各题输出标准（图表/表格/数值）
4. 操作步骤（含依赖顺序）
5. 文件清单
6. 异常预案

### Step 2：逐题求解
- 每题一个独立 Python 脚本
- 先算后画：先完成计算→打印统计量→再绘图
- 每题至少 4-6 张图（柱状图/折线图/热力图/散点图等）

### Step 3：撰写论文
- 按规范逐章生成 LaTeX 文件
- 摘要 ≤900字、严格 1 页
- 每问含流程图 + 算法对比表 + 完整建模推导

### Step 4：编译 PDF
```bash
cd 论文
xelatex -interaction=nonstopmode 论文.tex
xelatex -interaction=nonstopmode 论文.tex
```

### Step 5（可选）：排版优化
反复循环检查修复直到日志无错误。

---

## 论文规范一览

| 章节 | 核心要求 |
|------|---------|
| 摘要 | ≤900字，必须=1页 |
| 引言 | 2-3段背景 + 问题重述 |
| 总体分析 | 三段式，逐问串联 |
| 模型假设 | itemize 格式，每条带编号 |
| 符号说明 | 统一 longtable 模板 |
| 模型建立与求解 | 每问拆 2 子文件 |
| 模型检验 | 误差分析 + 灵敏度分析 |
| 模型评价 | 优点4条 + 缺点2条 |
| 参考文献 | GB/T 7714-2015，8-15条 |

### 核心规范
- 正文禁止分点符号（1. 2. 3.）
- 禁止正文加粗（摘要和问题重述除外）
- 图宽 0.8\textwidth，表宽 \textwidth
- 所有表格统一使用 longtable 样式

---

## Python 代码规范

- 仅允许使用 matplotlib
- 先算后画：计算全部完成后再绘图
- 跨平台中文字体自动适配

```python
# 中文字体配置
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'STHeiti', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
```

---

## 自定义配置

### 调整论文模板
编辑 `论文/format.cls` 可自定义论文样式。

### 调整 AI 行为
编辑 `CLAUDE.md` 可自定义 AI 的求解策略、论文规范等。

---

## 版本历史

| 版本 | 更新内容 |
|------|---------|
| V2.7 | 修改模板小 bug |
| V2.5 | 表格自动换页、排版优化循环 |
| V2.0 | 论文模块化拆分、完整规范体系 |
| V1.0 | 初始版本 |

---

## 交流与支持

### 联系方式

- **抖音**：[Rzna](https://www.douyin.com/user/Rzna)
- **微信**：RZN11111
- **QQ**：1834477681
- **交流群**：604148807

### 获取帮助

如果你在使用过程中遇到问题，可以通过以下方式联系：
1. 加入交流群 604148807 获取即时支持
2. 在 GitHub 提交 Issue

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

---

## Star 如果这个项目对你有帮助，请给一个 Star！
