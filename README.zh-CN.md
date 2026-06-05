# Helix-Swarm

<div align="center">

**面向 LM Studio / OpenAI-compatible 本地模型的 CLI 优先 Agent 框架**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Local First](https://img.shields.io/badge/Local--First-Agent-22c55e?style=flat-square)](#)
[![CLI](https://img.shields.io/badge/Interface-CLI-0ea5e9?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-v0.1--alpha-f59e0b?style=flat-square)](#)

[English README](README.md) · [快速开始](#快速开始) · [使用方式](#使用方式) · [架构](#架构) · [安全机制](#安全机制) · [路线图](#路线图)

</div>

---

## Helix-Swarm 是什么？

Helix-Swarm 是一个 **本地优先的 CLI Agent 框架**，主要面向本地小模型和中等模型。它可以把自然语言任务转成受控的工具调用、本地文件读取、终端操作、Skill/SOP 使用，以及带证据的代码审查报告。

当前版本不再优先做 GUI，而是先稳定终端主链路：**本地模型运行、工具调用审查、文件读取、SkillHub/SOP 集成、双语 CLI 输出、Evidence Card 代码审查**。

> 当前状态：`v0.1-alpha`。这是一个实验性质的本地 Agent 工作台，不是完全自治的生产系统。

---

## 核心特性

- **CLI 优先**：直接在终端里运行和交互。
- **本地模型支持**：支持 LM Studio 或任何 OpenAI-compatible `/v1/chat/completions` 接口。
- **Gemma 4 thinking mode 自动识别**：检测 Gemma 4 风格模型 ID 后自动启用 `<|think|>`，其他模型自动使用普通模式。
- **工具调用审查**：读文件、搜索、列目录等低风险工具可自动执行；终端执行、安装、写入、删除、移动等操作需要确认。
- **直接终端命令审查**：用户直接输入 shell 命令时会先做风险分级。
- **Skill / SOP 系统**：自动发现 Markdown skills 和 Python tools。
- **本地文件读取**：支持文本/代码文件、通过 `PyPDF2` 读取 PDF、通过 `python-docx` 读取 Word 文档。
- **Evidence Card 审查模式**：代码审查、风险分析、安全检查必须输出文件路径、函数/规则、证据、后果和修复建议。
- **中英文界面切换**：通过 `/set lang zh` 和 `/set lang en` 切换 CLI 语言。
- **上下文压缩**：包含 smart compressor，用于长对话和工具结果较多的任务。

---

## 快速开始

### 1. 下载项目

```bash
git clone https://github.com/Yule-Cai/Helix-Swarm.git
cd Helix-Swarm
```

也可以直接解压项目 zip 后进入目录。

### 2. 创建 Python 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 启动本地模型服务

推荐本地方式：

1. 安装并打开 **LM Studio**。
2. 加载本地模型，例如 Gemma 4 E4B / Qwen / DeepSeek-Coder 等。
3. 开启 local server。
4. 默认接口保持为：

```text
http://localhost:1234/v1/chat/completions
```

### 4. 启动 Helix-Swarm

```bash
python3 cli.py
```

---

## 配置

运行配置保存在 `helix_config.json`。上传 GitHub 时不要提交真实本地配置，请使用 `helix_config.example.json` 作为安全模板。

示例：

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
  "lang": "zh",
  "total_tokens_used": 0,
  "keys_usage": {}
}
```

CLI 内可直接修改：

```text
/set lang en
/set lang zh
/set model google/gemma-4-e4b
/set url http://localhost:1234/v1/chat/completions
/local
/custom
```

---

## 使用方式

### 普通聊天

```text
你好
```

### 切换语言

```text
/set lang en
/set lang zh
```

### 搜索 SkillHub / 本地技能

```text
skillhub search calendar
```

低风险查询命令可以自动执行，安装命令仍然需要确认。

### 比较 skill，但不安装

```text
我想安装一个 Google Calendar 相关的 skill。比较 calendar-cli、google-calendar、google-calendar-api，不要安装。
```

### 读取本地 PDF

```text
读取 /Users/yourname/Desktop/cv.pdf，然后总结这份 CV。不要编造 PDF 里没有的信息。
```

### 使用 Evidence Card 审查项目

```text
审查当前 Helix-Swarm 项目，找出 3 个具体风险点。只读，不要修改代码。
```

期望输出格式：

```text
Evidence Card 1
- 文件路径 / File:
- 函数 / 类 / 规则名 / Symbol:
- 证据 / Evidence:
- 风险原因 / Why risky:
- 可能后果 / Consequence:
- 修复建议 / Suggested fix:
```

### 直接终端命令审查

```bash
rm -rf /tmp/test-folder
```

高风险命令应该先弹出确认，不会直接执行。

---

## Slash Commands

| 命令 | 说明 |
|---|---|
| `/help` | 查看可用命令 |
| `/reload` | 重新加载工具和 Markdown skills |
| `/local` | 切换到本地模型配置 |
| `/custom` | 切换到自定义/云端 API 配置 |
| `/set <key> <value>` | 更新模型、API、语言、主题等配置 |
| `/tools` | 显示已加载工具 |
| `/search <pattern>` | 搜索工具 |
| `/models` | 显示模型配置 |
| `/stats` | 显示 token 和系统统计 |
| `/permission` | 查看或修改权限模式 |
| `exit` / `quit` / `q` | 退出 CLI |

---

## 架构

```text
用户输入
   │
   ▼
CLI Router
   │
   ├── 直接 shell 命令审查
   │
   ├── Slash command 处理
   │
   └── SwarmRouter / Leo Supervisor
          │
          ├── File Agent
          ├── Computer Agent
          ├── App Agent
          ├── Browser Agent
          ├── Search Agent
          ├── Coder
          └── Reviewer
                 │
                 ▼
          Tool Registry + Permission Manager
                 │
                 ▼
          Tools / Skills / Local files / Terminal
```

### 重要模块

| 路径 | 作用 |
|---|---|
| `cli.py` | 终端入口、slash commands、直接命令审查、双语 UI |
| `core/agent.py` | Agent 主循环、thinking mode、工具调用处理、Evidence Card 注入 |
| `core/swarm.py` | Leo supervisor 和专家 Agent 路由 |
| `core/registry.py` | Python tools 和 Markdown skills 发现/注册 |
| `core/permission_manager.py` | 工具风险分级和权限决策 |
| `core/toolkit.py` | API 请求、余额显示、敏感信息脱敏、错误诊断 |
| `tools/` | 文件、代码搜索、Git、Shell 等内置工具 |
| `skills/` | Markdown/Python SOP 技能和文件读取器 |
| `docs/` | 项目文档和设置说明 |

---

## 安全机制

Helix-Swarm 的目标是降低 Agent 误操作风险，同时保持本地工作流顺手。

当前策略：

- **自动允许**：`read_file`、`list_directory`、`grep_code`、`glob_files`、`find_skills`、专家委派等低风险原生工具。
- **执行前确认**：终端执行、依赖安装、文件修改、删除、移动、patch 等潜在危险操作。
- **会话级禁止**：在工具审查时选择 `B`，可以在本会话内禁用该工具。
- **禁止假完成**：Agent 被要求不能在没有工具结果的情况下声称已经读取、安装、执行或检查完成。
- **证据化审查**：审查类任务必须给出文件路径、函数/规则、证据、后果和修复建议。

这仍然是 alpha 系统。高风险操作请人工确认。

---

## 项目结构

```text
Helix-Swarm/
├── cli.py
├── requirements.txt
├── helix_config.example.json
├── core/
│   ├── agent.py
│   ├── swarm.py
│   ├── registry.py
│   ├── permission_manager.py
│   ├── toolkit.py
│   ├── memory.py
│   └── ...
├── tools/
│   ├── file_ops.py
│   ├── code_search.py
│   ├── shell_ops.py
│   └── git_ops.py
├── skills/
│   ├── drag_reader.py
│   ├── safe_terminal.py
│   └── *.md
├── docs/
├── tests/
└── research_agent/
```

---

## 开发说明

运行测试：

```bash
pytest
```

搜索硬编码中文/英文：

```bash
grep -Rni "本地算力\|技能库\|回复\|审查" core tools skills cli.py
```

修改后运行：

```bash
python3 cli.py
```

推荐手动回归测试：

```text
1. /set lang en，然后输入 hello
2. /set lang zh，然后输入 你好
3. skillhub search calendar
4. skillhub install calendar-cli，先拒绝一次，再确认一次
5. 读取一个本地 PDF
6. 用 Evidence Card 审查当前项目
7. 输入危险命令，确认会被拦截或要求确认
```

---

## 路线图

- [ ] 增加一等 `/image` 支持，让 vision-capable 本地模型直接看图。
- [ ] 增加 PDF 页面转图片理解，用于扫描版 PDF、图表和截图型文档。
- [ ] 继续补齐完整中英文 CLI 文案覆盖。
- [ ] 加强 workspace path check 和终端命令 allowlist。
- [ ] 增加 GitHub Pages 首页。
- [ ] 为权限和语言切换添加自动化回归测试。

---

## License

MIT License. 如仓库中包含 `LICENSE`，以该文件为准。

---

<div align="center">

Built by **Yule-Cai** for local-first agent experimentation.

</div>
