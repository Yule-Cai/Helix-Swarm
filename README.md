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

### AI agents should ask before they act.

### AI Agent 在行动前，应该先让你看见。

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Permission First](https://img.shields.io/badge/Permission--First-Agent-111111?style=flat-square)](#)
[![Evidence Cards](https://img.shields.io/badge/Evidence--Cards-Review-2f6f4e?style=flat-square)](#)
[![Skill Aware](https://img.shields.io/badge/Skill--Aware-Workflows-d98435?style=flat-square)](#)
[![CLI](https://img.shields.io/badge/CLI-Control%20Layer-6d91b8?style=flat-square)](#)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

[English](#-what-is-helix-swarm) · [中文](#-helix-swarm-是什么) · [Install](#-installation--安装) · [Usage](#-usage--使用方式) · [Architecture](#-architecture--架构) · [Roadmap](#-roadmap--路线图)

</div>

---

## ✨ What is Helix-Swarm?

**Helix-Swarm** is a permission-first CLI agent framework for safe tool use, evidence-based project review, and skill-aware workflows.

It is designed for developers who want AI agents that can inspect files, compare skills, call tools, and execute terminal actions — while keeping risky steps visible, reviewable, and rejectable.

The core idea is simple:

```text
Agent proposes.
System explains.
User approves.
Tool executes.
Result is traceable.
```

Helix-Swarm is not trying to be the most autonomous agent.  
It is trying to be a more controllable one.

---

## ✨ Helix-Swarm 是什么？

**Helix-Swarm** 是一个权限优先的 CLI Agent 框架，面向安全工具调用、证据化项目审查和技能感知工作流。

它适合希望 AI Agent 能读取文件、比较技能、调用工具、执行终端动作，同时又希望高风险步骤保持可见、可审查、可拒绝的开发者。

核心逻辑很简单：

```text
Agent 提议。
系统解释。
用户确认。
工具执行。
结果可追踪。
```

Helix-Swarm 不是为了做“最自动”的 Agent。  
它更关注做一个**更可控的 Agent**。

---

## 🧭 Project Philosophy / 项目理念

### Permission-first execution

High-risk actions should not happen silently.

Terminal commands, installs, file writes, edits, deletes, and script execution are reviewed before they run.

### 权限优先执行

高风险动作不应该静默发生。

终端命令、安装、文件写入、编辑、删除和脚本执行都应该先经过审查。

---

### Human-in-the-loop tool use

The agent can suggest actions, but the user keeps final authority over risky operations.

### 人在回路中的工具调用

Agent 可以提出动作，但用户保留对高风险操作的最终决定权。

---

### Evidence-based review

Project review should not be generic advice.

Every serious finding should include:

```text
File
Symbol
Evidence
Risk
Consequence
Suggested fix
```

### 基于证据的审查

项目审查不应该只是泛泛而谈。

每个关键发现都应该包含：

```text
文件路径
函数 / 类 / 规则名
证据
风险原因
可能后果
修复建议
```

---

### Skill-aware workflows

Skills should be searchable, comparable, and inspectable before they are installed or used.

### 技能感知型工作流

Skill 不应该盲目安装或调用，而应该先搜索、比较、检查，再决定是否使用。

---

## ✅ Key Features / 核心功能

### 🛡️ Permission-first tool execution

Low-risk tools can be allowed automatically:

```text
read_file
glob_files
grep_code
find_skills
list_directory
delegate_to_expert
```

Risky tools require review:

```text
execute_terminal
pip install
curl ... | bash
delete_file
write_file
edit_file
skillhub install
```

Review choices:

```text
Y = Approve
N = Deny
B = Block this tool for this session
```

---

### 🧾 Evidence Card review

For review, audit, security, permission, and bug-finding tasks, Helix-Swarm forces structured evidence.

```text
Evidence Card 1
- File:
- Symbol:
- Evidence:
- Why risky:
- Consequence:
- Suggested fix:
```

This makes the reviewer less like a vague security report generator and more like a traceable code auditor.

---

### 🧩 Skill-aware agent workflow

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

The goal is not just “install skills”, but:

```text
Search → Compare → Explain → Ask → Install
```

---

### 🖥️ Terminal control layer

The terminal is the control surface.

Helix-Swarm is designed around a simple CLI loop where users can chat, inspect tools, switch models, change language, review permissions, and run commands with approval.

```bash
/set lang en
/set lang zh
/permission
/models
/stats
```

---

### 📄 File-aware agent context

Helix-Swarm can detect local file paths and route them into the file-reading workflow.

Supported depending on installed extractors:

```text
PDF
DOCX
TXT
Markdown
source files
project files
```

Example:

```text
Read /Users/you/Desktop/resume.pdf and summarize improvements.
```

---

### 🌐 Bilingual CLI

Switch language inside the CLI:

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
local compute labels
```

---

### 🧠 Model-flexible backend

Helix-Swarm works with local or OpenAI-compatible endpoints.

It can use local model servers such as LM Studio, or a custom API endpoint.

Some models may support additional abilities such as thinking or vision, but Helix-Swarm’s main value is the permission-first workflow around tool use.

---

## 🏗 Architecture / 架构

```text
User Input
    │
    ▼
CLI Router
    │
    ├── Slash Commands
    │       ├── /set
    │       ├── /reload
    │       ├── /models
    │       ├── /permission
    │       └── /stats
    │
    ├── Direct Command Detector
    │       └── Permission Review
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
    ├── Slash 命令
    │       ├── /set
    │       ├── /reload
    │       ├── /models
    │       ├── /permission
    │       └── /stats
    │
    ├── 直接终端命令检测
    │       └── 权限审查
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

### 1. Clone / 克隆仓库

```bash
git clone https://github.com/Yule-Cai/Helix-Swarm.git
cd Helix-Swarm
```

### 2. Create environment / 创建环境

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

### 4. Configure model endpoint / 配置模型接口

Example:

```bash
cp helix_config.example.json helix_config.json
```

Example config:

```json
{
  "active": "local",
  "local": {
    "url": "http://localhost:1234/v1/chat/completions",
    "model": "your-model-name",
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

### 5. Start / 启动

```bash
python3 cli.py
```

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

### Review a project with evidence / 基于证据审查项目

```text
Review the current Helix-Swarm project and identify 3 concrete risks.
Read-only. Do not modify code.
```

```text
审查当前 Helix-Swarm 项目，找出 3 个具体风险点。
只读，不要修改代码。
```

Expected output:

```text
Evidence Card 1
- File:
- Symbol:
- Evidence:
- Why risky:
- Consequence:
- Suggested fix:
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

Helix-Swarm is not a full operating-system sandbox. It is a local agent framework with permission gates.

Helix-Swarm 不是完整操作系统沙箱，而是一个带权限审查的本地 Agent 框架。

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
9. Compare multiple skills without installing
```

Expected behavior:

```text
Low-risk queries run smoothly.
High-risk commands require approval.
Review answers include file/symbol/evidence.
Language switching changes CLI and agent output.
Risky tool calls remain visible.
```

中文预期：

```text
低风险查询可以顺畅运行。
高风险命令必须确认。
审查回答必须包含文件、函数和证据。
语言切换会影响 CLI 和 Agent 输出。
高风险工具调用保持可见。
```

---

## 🗺 Roadmap / 路线图

- [x] CLI-first agent control layer  
      CLI 优先的 Agent 控制层

- [x] Permission-gated terminal execution  
      终端执行权限审查

- [x] Evidence Card review mode  
      证据卡审查模式

- [x] Skill-aware workflow  
      技能感知工作流

- [x] Chinese / English CLI switching  
      中英文 CLI 切换

- [x] Local file reading  
      本地文件读取

- [ ] Stronger reviewer verifier  
      更强的审查验证器

- [ ] Unified `/file` pipeline for PDF / DOCX / XLSX / images / ZIP  
      统一 `/file` 管线，支持 PDF / DOCX / XLSX / 图片 / ZIP

- [ ] `/image` command for vision-capable models  
      面向视觉模型的 `/image` 命令

- [ ] More skill adapters  
      更多 Skill 适配器

- [ ] Optional lightweight Web UI  
      可选轻量 Web UI

---

## 🤝 Contributing / 贡献

Issues and pull requests are welcome.

欢迎提交 Issue 和 Pull Request。

Good first contribution areas:

```text
Better permission rules
Better file extractors
More SkillHub adapters
Reviewer verification
Documentation
Language translations
```

适合贡献的方向：

```text
更稳的权限规则
更好的文件提取器
更多 SkillHub 适配
审查验证器
文档优化
多语言翻译
```

---

## ⚠️ Disclaimer / 免责声明

Helix-Swarm can execute local tools and terminal commands after approval.

Helix-Swarm 可以在确认后执行本地工具和终端命令。

Use it carefully.

请谨慎使用。

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
