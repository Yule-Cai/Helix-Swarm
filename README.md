```text
██╗  ██╗███████╗██╗     ██╗██╗  ██╗    ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗
██║  ██║██╔════╝██║     ██║╚██╗██╔╝    ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║
███████║█████╗  ██║     ██║ ╚███╔╝     ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║
██╔══██║██╔══╝  ██║     ██║ ██╔██╗     ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║
██║  ██║███████╗███████╗██║██╔╝ ██╗    ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝    ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
```

<div align="center">

# Helix-Swarm

### A local-first CLI agent swarm with safe tool approval, SkillHub integration, evidence-based review, and Gemma 4 thinking.

### 一个本地优先的 CLI Agent Swarm，支持安全工具审查、SkillHub 集成、证据卡审查和 Gemma 4 Thinking。

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Local First](https://img.shields.io/badge/Local--First-Agent-22c55e?style=flat-square)](#)
[![CLI](https://img.shields.io/badge/CLI--First-Terminal-0ea5e9?style=flat-square)](#)
[![LM Studio](https://img.shields.io/badge/LM%20Studio-Compatible-8b5cf6?style=flat-square)](https://lmstudio.ai/)
[![SkillHub](https://img.shields.io/badge/SkillHub-Integrated-f59e0b?style=flat-square)](#)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

[English](#-what-is-helix-swarm) · [中文](#-helix-swarm-是什么) · [Install](#-installation--安装) · [Usage](#-usage--使用方式) · [Architecture](#-architecture--架构) · [Roadmap](#-roadmap--路线图)

</div>

---

## ✨ What is Helix-Swarm?

**Helix-Swarm** is a CLI-first local agent framework designed for terminal workflows.

It connects local or OpenAI-compatible models with tool calling, SkillHub skills, file reading, permission-gated terminal execution, and evidence-based code review.

The goal is simple:

> Give local agents useful tool abilities without giving them silent uncontrolled system power.

Helix-Swarm is built for users who want:

- local-first AI agents;
- LM Studio / OpenAI-compatible model support;
- controlled terminal execution;
- safer tool approval;
- SkillHub skill discovery;
- PDF and file reading;
- evidence-based project review;
- Chinese / English CLI switching;
- Gemma 4 thinking mode support.

---

## ✨ Helix-Swarm 是什么？

**Helix-Swarm** 是一个 CLI 优先、本地优先的 Agent 框架，面向终端工作流。

它把本地模型或 OpenAI-compatible 模型连接到工具调用、SkillHub 技能、文件读取、终端执行审查和代码证据卡审查流程中。

核心目标很简单：

> 让本地 Agent 能真正使用工具，但不能静默地获得不受控制的系统权限。

Helix-Swarm 适合这些场景：

- 本地 AI Agent；
- LM Studio / OpenAI-compatible 模型；
- 终端命令执行审查；
- 安全工具调用；
- SkillHub 技能搜索；
- PDF 和文件读取；
- 基于证据的项目审查；
- 中英文 CLI 切换；
- Gemma 4 thinking mode。

---

## 🔥 Why Helix-Swarm?

Many local agent projects are either too chat-like, too UI-heavy, or too unsafe by default.

Helix-Swarm takes a more practical route:

```text
CLI first.
Local first.
Tool-aware.
Permission-gated.
Evidence-based.
Skill-extensible.
```

Instead of letting an agent freely run commands, Helix-Swarm adds an approval layer:

```text
Ask → Inspect → Approve → Execute → Verify
```

---

## 🔥 为什么做 Helix-Swarm？

很多本地 Agent 项目要么只是聊天工具，要么过早做复杂 UI，要么默认权限太大。

Helix-Swarm 选择更稳的路线：

```text
CLI 优先。
本地优先。
工具感知。
权限审查。
证据驱动。
技能可扩展。
```

它不是让 Agent 随便运行命令，而是加入审查流程：

```text
请求 → 检查 → 确认 → 执行 → 验证
```

---

## ✅ Key Features / 核心功能

### 🧠 Gemma 4 Thinking Mode

Helix-Swarm can detect Gemma 4-style model names and enable thinking mode automatically.

```text
google/gemma-4-e4b → thinking enabled
other models       → normal mode
```

Thinking output is filtered before being saved into memory, reducing repeated injection of internal reasoning.

### 🧠 Gemma 4 Thinking 模式

Helix-Swarm 可以根据模型名称自动识别 Gemma 4 系列，并开启 thinking mode。

```text
google/gemma-4-e4b → 自动开启 thinking
其他模型            → 普通模式
```

系统会过滤 thinking 输出，避免把内部推理内容反复写入记忆。

---

### 🛡️ Permission-Gated Tool Execution

Low-risk tools can be auto-approved:

```text
read_file
glob_files
grep_code
find_skills
list_directory
delegate_to_expert
```

High-risk tools require confirmation:

```text
execute_terminal
pip install
curl ... | bash
delete_file
write_file
edit_file
skillhub install
```

Approval UI:

```text
Y = Approve
N = Deny
B = Block this tool for this session
```

### 🛡️ 工具调用权限审查

低风险工具可以自动允许：

```text
read_file
glob_files
grep_code
find_skills
list_directory
delegate_to_expert
```

高风险工具需要用户确认：

```text
execute_terminal
pip install
curl ... | bash
delete_file
write_file
edit_file
skillhub install
```

审查选项：

```text
Y = 确认执行
N = 拒绝本次
B = 禁止该工具本会话继续调用
```

---

### 📚 SkillHub Integration

Helix-Swarm can search and compare SkillHub skills before installing them.

Example:

```bash
skillhub search calendar
```

Then ask:

```text
Compare calendar-cli, google-calendar, and google-calendar-api.
Do not install anything.
```

The agent is instructed to rely on actual tool output rather than guessing from names.

### 📚 SkillHub 集成

Helix-Swarm 可以搜索和比较 SkillHub 技能，在安装前先给出分析。

例如：

```bash
skillhub search calendar
```

然后让 Agent 比较：

```text
比较 calendar-cli、google-calendar、google-calendar-api。
不要安装。
```

系统会要求 Agent 基于真实工具输出，而不是只根据名字猜测。

---

### 🧾 Evidence Card Review

For review, audit, security, permission, and bug-finding tasks, Helix-Swarm forces structured evidence.

Example:

```text
Evidence Card 1
- File:
- Symbol:
- Evidence:
- Why risky:
- Consequence:
- Suggested fix:
```

This helps reduce generic security advice and makes each finding traceable.

### 🧾 证据卡审查

对于代码审查、安全审查、权限分析、找 bug 等任务，Helix-Swarm 会要求输出结构化证据卡。

格式：

```text
Evidence Card 1
- 文件路径 / File:
- 函数 / 类 / 规则名 / Symbol:
- 证据 / Evidence:
- 风险原因 / Why risky:
- 可能后果 / Consequence:
- 修复建议 / Suggested fix:
```

这样可以减少泛泛而谈，让每个结论都能追溯到具体文件和函数。

---

### 📄 Local File Reading

Helix-Swarm can detect local file paths and route them to file-reading tools.

Supported depending on installed dependencies:

```text
PDF
DOCX
TXT
Markdown
source code files
project files
```

Example:

```text
Read /Users/you/Desktop/resume.pdf and summarize improvements.
```

### 📄 本地文件读取

Helix-Swarm 可以识别本地文件路径，并调用文件读取工具。

根据依赖支持：

```text
PDF
DOCX
TXT
Markdown
源代码文件
项目文件
```

示例：

```text
读取 /Users/you/Desktop/resume.pdf，然后总结可以优化的地方。
```

---

### 🌐 Chinese / English CLI Switching

Switch language:

```bash
/set lang en
/set lang zh
```

This affects:

```text
CLI status text
tool review panels
agent reply labels
system language instruction
Evidence Card templates
local compute balance label
```

### 🌐 中英文 CLI 切换

切换语言：

```bash
/set lang en
/set lang zh
```

会影响：

```text
CLI 状态栏
工具审查面板
Agent 回复标签
系统语言提示词
Evidence Card 模板
本地算力余额标签
```

---

## 🏗 Architecture / 架构

```text
User Input
    │
    ▼
CLI Router
    │
    ├── Direct shell command detector
    │       └── Permission review
    │
    ├── Slash command handler
    │       ├── /set
    │       ├── /reload
    │       ├── /models
    │       ├── /permission
    │       └── /stats
    │
    └── Leo Supervisor Agent
            │
            ├── Specialist Agents
            │       ├── File Agent
            │       ├── Search Agent
            │       ├── Reviewer
            │       └── Computer Agent
            │
            ├── Tool Registry
            │       ├── read_file
            │       ├── grep_code
            │       ├── glob_files
            │       ├── find_skills
            │       └── execute_terminal
            │
            ├── Permission Manager
            ├── Audit Logger
            └── Memory / Compression
```

中文说明：

```text
用户输入
    │
    ▼
CLI 路由器
    │
    ├── 直接终端命令检测
    │       └── 权限审查
    │
    ├── Slash 命令处理
    │       ├── /set
    │       ├── /reload
    │       ├── /models
    │       ├── /permission
    │       └── /stats
    │
    └── Leo Supervisor Agent
            │
            ├── 专家 Agent
            │       ├── File Agent
            │       ├── Search Agent
            │       ├── Reviewer
            │       └── Computer Agent
            │
            ├── 工具注册表
            │       ├── read_file
            │       ├── grep_code
            │       ├── glob_files
            │       ├── find_skills
            │       └── execute_terminal
            │
            ├── 权限管理器
            ├── 审计日志
            └── 记忆 / 上下文压缩
```

---

## 📦 Project Structure / 项目结构

```text
Helix-Swarm/
├── cli.py
├── README.md
├── LICENSE
├── requirements.txt
├── helix_config.example.json
├── index.html
├── core/
│   ├── agent.py
│   ├── swarm.py
│   ├── registry.py
│   ├── config.py
│   ├── toolkit.py
│   ├── permission_manager.py
│   ├── audit_logger.py
│   ├── memory.py
│   ├── compressor.py
│   ├── smart_compressor.py
│   ├── hook_manager.py
│   └── model_router.py
├── tools/
├── skills/
└── docs/
```

---

## ⚡ Installation / 安装

### 1. Clone the repository / 克隆仓库

```bash
git clone https://github.com/Yule-Cai/Helix-Swarm.git
cd Helix-Swarm
```

### 2. Create a Python environment / 创建 Python 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies / 安装依赖

```bash
pip install -r requirements.txt
```

### 4. Start a local model server / 启动本地模型服务

Recommended / 推荐：

```text
LM Studio
Gemma 4 E4B / E2B
Qwen Coder models
Any OpenAI-compatible endpoint
```

Default endpoint example / 默认接口示例：

```text
http://localhost:1234/v1/chat/completions
```

### 5. Start Helix-Swarm / 启动 Helix-Swarm

```bash
python3 cli.py
```

---

## ⚙️ Configuration / 配置

Create local config:

```bash
cp helix_config.example.json helix_config.json
```

Example:

```json
{
  "active": "local",
  "local": {
    "url": "http://localhost:1234/v1/chat/completions",
    "model": "google/gemma-4-e4b",
    "api_key": "not-needed"
  },
  "custom": {
    "url": "",
    "model": "",
    "api_key": ""
  },
  "theme": "dark",
  "lang": "en",
  "total_tokens_used": 0,
  "keys_usage": {}
}
```

Do not commit real local config if it contains API keys, private endpoints, logs, or personal paths.

如果你的配置包含 API key、私有端点、日志或个人路径，不要提交真实的 `helix_config.json`。

---

## 📖 Usage / 使用方式

### Basic chat / 普通聊天

```text
hello
```

```text
你好
```

---

### Switch language / 切换语言

```bash
/set lang en
/set lang zh
```

---

### Switch model / 切换模型

```bash
/set model google/gemma-4-e4b
```

---

### Search SkillHub skills / 搜索 SkillHub 技能

```bash
skillhub search calendar
```

---

### Compare skills before installing / 安装前比较技能

```text
I want to install a Google Calendar related skill.
Compare calendar-cli, google-calendar, and google-calendar-api.
Do not install anything.
```

```text
我想安装一个 Google Calendar 相关的 skill。
先比较 calendar-cli、google-calendar、google-calendar-api。
不要安装。
```

---

### Read a local file / 读取本地文件

```text
Read /Users/you/Desktop/resume.pdf and summarize the key improvements.
```

```text
读取 /Users/you/Desktop/resume.pdf，然后总结可以优化的地方。
```

---

### Review the project / 审查项目

```text
Review the current Helix-Swarm project and identify 3 concrete risks.
Read-only. Do not modify code.
```

```text
审查当前 Helix-Swarm 项目，找出 3 个具体风险点。
只读，不要修改代码。
```

---

### Run a command with approval / 带审查执行命令

```bash
pip install PyPDF2
```

Helix-Swarm will ask before running higher-risk commands.

Helix-Swarm 会在执行高风险命令前请求确认。

---

## 🛡 Safety Model / 安全模型

| Operation Type | Behavior | 中文说明 |
|---|---|---|
| Read/search/list tools | Usually auto-approved | 读取、搜索、列表类工具通常自动允许 |
| Skill search | Auto-approved | Skill 搜索自动允许 |
| Agent delegation | Auto-approved | Agent 委派自动允许 |
| Terminal command | Reviewed | 终端命令需要审查 |
| Install command | Reviewed | 安装命令需要审查 |
| File write/edit/delete | Reviewed | 写入、编辑、删除文件需要审查 |
| Dangerous shell patterns | High-risk review | 危险 shell 模式会进入高风险审查 |

Helix-Swarm is not a full OS sandbox. It is a local agent framework with permission gates.

Helix-Swarm 不是完整操作系统沙箱，而是带权限审查的本地 Agent 框架。

Do not approve commands you do not understand.

不要确认你不理解的命令。

---

## 🧪 Manual Regression Tests / 手动回归测试

Before publishing a new version, test:

```text
1. hello
2. /set lang en
3. /set lang zh
4. skillhub search calendar
5. skillhub install calendar-cli
6. Read a local PDF
7. Review current project with Evidence Cards
8. rm -rf /Users/you/Desktop/test_folder
9. Ask a logic question and check Gemma 4 thinking logs
```

Expected behavior:

```text
Low-risk queries run smoothly.
High-risk commands require approval.
Review answers include file/symbol/evidence.
Language switching changes CLI and agent output.
Thinking mode starts for Gemma 4 models.
```

中文预期：

```text
低风险查询可以顺畅运行。
高风险命令必须确认。
审查回答必须包含文件、函数和证据。
语言切换会影响 CLI 和 Agent 输出。
Gemma 4 模型会触发 thinking mode。
```

---

## 🗺 Roadmap / 路线图

- [x] CLI-first local agent loop  
      CLI 优先的本地 Agent 主循环

- [x] Local / custom API configuration  
      本地 / 自定义 API 配置

- [x] SkillHub search integration  
      SkillHub 搜索集成

- [x] Permission-gated terminal execution  
      终端执行权限审查

- [x] Evidence Card review mode  
      证据卡审查模式

- [x] Gemma 4 thinking mode detection  
      Gemma 4 thinking mode 自动识别

- [x] Chinese / English CLI switching  
      中英文 CLI 切换

- [x] PDF text reading  
      PDF 文本读取

- [ ] `/image` command for vision models  
      支持视觉模型的 `/image` 命令

- [ ] PDF page-to-image visual understanding  
      PDF 页面转图片并进行视觉理解

- [ ] Unified `/file` pipeline for PDF / DOCX / XLSX / images / ZIP  
      统一 `/file` 管线，支持 PDF / DOCX / XLSX / 图片 / ZIP

- [ ] Stronger reviewer verifier  
      更强的审查验证器

- [ ] GitHub Pages documentation site  
      GitHub Pages 文档站点

- [ ] Optional lightweight Web UI  
      可选轻量 Web UI

---

## 🧠 Recommended Models / 推荐模型

| Model Type | Recommended Use | 中文说明 |
|---|---|---|
| Gemma 4 E4B / E2B | Local thinking + general agent tasks | 本地 thinking 和通用 Agent 任务 |
| Qwen Coder | Code-heavy workflows | 代码任务 |
| DeepSeek Coder | Code generation and debugging | 代码生成和调试 |
| Larger local models | Better project review and multi-file reasoning | 更好的项目审查和多文件推理 |

Gemma 4 is useful because Helix-Swarm can trigger thinking mode automatically when the model name matches Gemma 4-style identifiers.

Gemma 4 很适合 Helix-Swarm，因为系统可以根据模型名称自动触发 thinking mode。

---

## 🌍 Language / 语言

Helix-Swarm is designed for bilingual use.

Helix-Swarm 面向中英文双语使用。

```bash
/set lang en
/set lang zh
```

Single-file bilingual README:

```text
README.md
```

---

## 🤝 Contributing / 贡献

Issues and pull requests are welcome.

欢迎提交 Issue 和 Pull Request。

Good first contribution areas:

```text
Better file extractors
More robust permission rules
More SkillHub adapters
Vision input support
Better documentation
More language translations
```

适合贡献的方向：

```text
更好的文件提取器
更稳的权限规则
更多 SkillHub 适配
视觉输入支持
更好的文档
更多语言翻译
```

---

## ⚠️ Disclaimer / 免责声明

Helix-Swarm can execute local tools and terminal commands after approval.

Helix-Swarm 可以在确认后执行本地工具和终端命令。

Use it carefully.

请谨慎使用。

Do not approve commands you do not understand.

不要确认你不理解的命令。

Avoid committing:

```text
helix_config.json
.env
API keys
audit logs
local memory
private documents
```

避免提交：

```text
helix_config.json
.env
API keys
审计日志
本地记忆
私人文件
```

---

## 📄 License / 许可证

MIT License.

<div align="center">

Built with ❤️ by [Yule-Cai](https://github.com/Yule-Cai)

</div>
