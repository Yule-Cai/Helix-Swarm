---
name: autonomous-ai-researcher
description: 完全自主的 AI/ML 研究系统，能够独立提出研究想法、设计执行实验、并撰写符合学术标准的论文。
version: 1.0.0
---

# Autonomous AI Researcher Skill

## Overview

完全自主的 AI/ML 研究系统，能够：
- 自主提出创新的研究想法
- 设计并执行实验（运行代码脚本收集结果）
- 自动撰写符合学术标准的论文（LaTeX/PDF/DOCX）

## Trigger Conditions

当用户请求进行 AI/ML 研究时触发，例如：
- "研究 neuro-symbolic AI 在机器人导航中的应用"
- "自动生成关于联邦学习的论文"
- "做一个关于 transformer 效率优化的研究"
- "自主研究 [任意 AI/ML 主题]"

## SOP Workflow

### Step 1: Parse Research Topic
- 从用户请求中提取研究主题（topic）
- 如果未明确指定，询问用户要研究的主题
- 确定输出目录（默认：`output/autonomous_research/`）

### Step 2: Initialize Research Orchestrator
- 导入 `ResearchOrchestrator` from `src.orchestrator.research_orchestrator`
- 创建 orchestrator 实例：`orchestrator = ResearchOrchestrator()`
- 验证所有组件已正确初始化：
  - `orchestrator.idea_generator`
  - `orchestrator.experiment_runner`
  - `orchestrator.paper_writer`
  - `orchestrator.paper_formatter`

### Step 3: Execute Full Research Cycle
- 调用 `orchestrator.run_research(topic, output_dir)`
- 该方法自动执行以下子步骤：
  1. **Literature Review** (文献综述)
     - 搜索相关论文（当前为 Mock 实现，后续可接入 arXiv API）
  2. **Idea Generation** (想法生成)
     - 使用 `IdeaGenerator.generate_idea(papers)` 生成研究想法
     - 输出：标题、摘要、假设、新颖性评分、可行性评分
  3. **Experiment Design** (实验设计)
     - 使用 `ExperimentDesigner.design_experiment(idea)` 设计实验方案
     - 输出：实验类型、基线方法、评估指标、预计时长
  4. **Experiment Execution** (实验执行)
     - 使用 `ExperimentRunner.run_experiment(plan)` 运行实验
     - 执行实验脚本，收集结果数据
  5. **Paper Writing** (论文撰写)
     - 使用 `PaperWriter.generate_paper(run_result)` 生成论文
     - 包含：标题、作者、摘要、章节、参考文献
  6. **Paper Formatting** (论文格式化)
     - 使用 `PaperFormatter.to_latex(paper)` 生成 LaTeX 源码
     - 可选：转换为 PDF/DOCX 格式

### Step 4: Save Results
- 研究结果自动保存到 `output_dir`：
  - `paper.tex` - LaTeX 源码
  - `research_result.json` - 完整研究结果（JSON 格式）
- 使用 `orchestrator.save_results(result, path)` 可额外保存结果

### Step 5: Report to User
- 向用户报告研究完成状态
- 提供输出路径：`output_dir/paper.tex`
- 展示论文信息：
  - 论文标题
  - 研究想法摘要
  - 实验结果摘要
  - LaTeX 源码预览（前 500 字符）

## Output Structure

```
output/[topic]/
├── paper.tex                    # LaTeX 源码
├── research_result.json         # 完整研究结果
└── [其他实验输出文件]
```

## Example Usage

**User Input:**
```
研究 neuro-symbolic AI 在机器人导航中的应用
```

**System Execution:**
```python
from src.orchestrator.research_orchestrator import ResearchOrchestrator

orchestrator = ResearchOrchestrator()
result = orchestrator.run_research(
    topic="neuro-symbolic AI for robotics navigation",
    output_dir="output/neuro_symbolic_robotics"
)

# result 包含：
# - status: "success"
# - idea: 研究想法
# - experiment_plan: 实验方案
# - experiment_result: 实验结果
# - paper: 论文对象
# - latex_source: LaTeX 源码
# - paper_path: 论文路径
```

**System Output:**
```
✅ 研究完成！

📄 论文标题: Neuro-Symbolic AI for Robust Robot Navigation in Dynamic Environments
📊 研究想法: 结合神经网络感知与符号推理，提升机器人在动态环境中的导航鲁棒性...
📈 实验结果: 在 5 个基准测试中，提出的方法比基线方法平均提升 15.3%...
📁 输出路径: output/neuro_symbolic_robotics/paper.tex
```

## Technical Details

### Core Components
1. **IdeaGenerator** (`src.idea_generation.idea_generator`)
   - 基于文献生成创新研究想法
   - 评估新颖性、可行性、影响力

2. **ExperimentDesigner** (`src.idea_generation.experiment_designer`)
   - 设计实验方案
   - 选择基线方法、评估指标

3. **ExperimentRunner** (`src.experiment_execution.experiment_runner`)
   - 执行实验脚本
   - 收集和分析结果

4. **PaperWriter** (`src.paper_writing.paper_writer`)
   - 根据实验结果生成论文
   - 使用 LaTeX 模板

5. **PaperFormatter** (`src.paper_writing.paper_formatter`)
   - 格式化输出（LaTeX, PDF, DOCX）
   - 文件保存管理

6. **ResearchOrchestrator** (`src.orchestrator.research_orchestrator`)
   - 主协调器，串联所有组件
   - 提供统一的 `run_research()` 接口

### Dependencies
- Python 3.8+
- pytest (测试)
- pdflatex (可选，用于 PDF 生成)
- pandoc (可选，用于 DOCX 生成)

## Notes

- 当前文献综述为 Mock 实现，后续可接入 arXiv API、Google Scholar 等
- 实验执行为模拟实现，真实场景需连接计算资源
- 论文生成基于模板，可根据需要自定义 LaTeX 模板
- 所有组件遵循 TDD 开发流程，测试覆盖率 >95%

## Version History

- **1.0.0** (2025-01-17): Initial release
  - 完整的自主研究流程
  - 想法生成、实验设计、论文撰写
  - 支持 LaTeX/PDF/DOCX 输出
