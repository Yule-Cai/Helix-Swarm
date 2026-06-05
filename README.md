# Helix-Swarm

<div align="center">

**CLI-first local agent framework for LM Studio and OpenAI-compatible models**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Local First](https://img.shields.io/badge/Local--First-Agent-22c55e?style=flat-square)](#)
[![CLI](https://img.shields.io/badge/Interface-CLI-0ea5e9?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-v0.1--alpha-f59e0b?style=flat-square)](#)

[中文 README](README.zh-CN.md) · [Quick Start](#quick-start) · [Usage](#usage) · [Architecture](#architecture) · [Safety](#safety-model) · [Roadmap](#roadmap)

</div>

---

## What is Helix-Swarm?

Helix-Swarm is a **local-first CLI agent framework** designed for small and medium local models. It turns natural language into controlled tool calls, local file inspection, terminal actions, Skill/SOP usage, and evidence-based code review.

The current version focuses on the terminal workflow instead of a GUI. The goal is to stabilize the core agent loop first: **local model execution, permission-gated tools, file reading, SkillHub/SOP integration, bilingual CLI output, and review reports grounded in code evidence**.

> Current status: `v0.1-alpha`. This is an experimental local agent workspace, not a fully autonomous production system.

---

## Key Features

- **CLI-first workflow** — run Helix directly from the terminal with slash commands.
- **Local model support** — works with LM Studio or any OpenAI-compatible `/v1/chat/completions` endpoint.
- **Gemma 4 thinking mode detection** — automatically enables `<|think|>` for Gemma 4-style model IDs and falls back to normal chat for other models.
- **Permission-gated tool calls** — low-risk read/search tools can run automatically; shell execution, installs, edits, deletes, and other risky actions require review.
- **Direct terminal command review** — commands typed into the CLI are risk-classified before execution.
- **Skill / SOP system** — Markdown skills and Python tools are discovered and exposed to the agents.
- **File reading pipeline** — supports local text/code files, PDFs through `PyPDF2`, and Word documents through `python-docx` when dependencies are installed.
- **Evidence Card review mode** — review/audit/risk tasks must produce file paths, symbols, evidence, consequences, and suggested fixes.
- **Bilingual UI** — switch CLI language with `/set lang zh` or `/set lang en`.
- **Context compression** — includes smart compression modules for long conversations and tool-heavy workflows.

---

## Quick Start

### 1. Clone or download

```bash
git clone https://github.com/Yule-Cai/Helix-Swarm.git
cd Helix-Swarm
```

Or unzip the project locally and enter the project folder.

### 2. Create a Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Start your local model server

Recommended local setup:

1. Install and open **LM Studio**.
2. Load a local model, for example Gemma 4 E4B / Qwen / DeepSeek-Coder style models.
3. Enable the local server.
4. Keep the default OpenAI-compatible endpoint:

```text
http://localhost:1234/v1/chat/completions
```

### 4. Run Helix-Swarm

```bash
python3 cli.py
```

---

## Configuration

Runtime configuration is stored in `helix_config.json`. For GitHub, do not commit your real local config. Use `helix_config.example.json` as a safe template.

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
  "lang": "zh",
  "total_tokens_used": 0,
  "keys_usage": {}
}
```

You can update config inside the CLI:

```text
/set lang en
/set lang zh
/set model google/gemma-4-e4b
/set url http://localhost:1234/v1/chat/completions
/local
/custom
```

---

## Usage

### Basic chat

```text
hello
```

### Switch language

```text
/set lang en
/set lang zh
```

### Search SkillHub / local skills

```text
skillhub search calendar
```

Low-risk query commands can be executed automatically. Installation commands still require approval.

### Compare skills without installing

```text
I want a Google Calendar related skill. Compare calendar-cli, google-calendar, and google-calendar-api. Do not install anything.
```

### Read a local PDF

```text
Read /Users/yourname/Desktop/cv.pdf and summarize the CV. Do not invent information that is not in the PDF.
```

### Review the project with evidence cards

```text
Review the current Helix-Swarm project and identify 3 concrete risks. Read-only, do not modify code.
```

Expected review format:

```text
Evidence Card 1
- File:
- Symbol:
- Evidence:
- Why risky:
- Consequence:
- Suggested fix:
```

### Direct terminal command review

```bash
rm -rf /tmp/test-folder
```

Helix-Swarm should pause and ask before executing high-risk commands.

---

## Slash Commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/reload` | Reload tools and Markdown skills |
| `/local` | Switch to local model config |
| `/custom` | Switch to custom/cloud API config |
| `/set <key> <value>` | Update active config, UI language, or model settings |
| `/tools` | Show loaded tools |
| `/search <pattern>` | Search registered tools |
| `/models` | Show configured model profiles |
| `/stats` | Show token usage and system stats |
| `/permission` | View or change permission mode |
| `exit` / `quit` / `q` | Exit the CLI |

---

## Architecture

```text
User input
   │
   ▼
CLI router
   │
   ├── Direct shell command review
   │
   ├── Slash command handler
   │
   └── SwarmRouter / Leo supervisor
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
          Tool registry + permission manager
                 │
                 ▼
          Tools / Skills / Local files / Terminal
```

### Important modules

| Path | Role |
|---|---|
| `cli.py` | Main terminal entry point, slash commands, direct command review, bilingual UI text |
| `core/agent.py` | Core agent loop, thinking mode, tool call handling, Evidence Card injection |
| `core/swarm.py` | Leo supervisor and specialist agent routing |
| `core/registry.py` | Python tool and Markdown skill discovery |
| `core/permission_manager.py` | Tool risk levels and permission decisions |
| `core/toolkit.py` | API calls, balance display, redaction, error diagnosis |
| `tools/` | Built-in Python tools for file, code search, Git, and shell operations |
| `skills/` | Markdown/Python SOP skills and file readers |
| `docs/` | Project documentation and setup notes |

---

## Safety Model

Helix-Swarm is designed to reduce accidental tool misuse while keeping local workflows convenient.

Current policy:

- **Auto-approve**: native low-risk tools such as `read_file`, `list_directory`, `grep_code`, `glob_files`, `find_skills`, and expert delegation.
- **Ask before execution**: terminal execution, installs, edits, deletes, moving files, patching, and other potentially destructive actions.
- **Block option**: during a tool review, choose `B` to block that tool for the current session.
- **No fake completion**: the agent is instructed not to claim a file, command, or tool was checked unless tool output confirms it.
- **Evidence-based review**: review tasks must include file path, symbol, evidence, consequence, and suggested fix.

This is still an alpha system. Review high-risk operations carefully.

---

## Project Structure

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

## Development Notes

Run tests:

```bash
pytest
```

Search for hardcoded Chinese/English strings:

```bash
grep -Rni "本地算力\|技能库\|回复\|审查" core tools skills cli.py
```

Run the CLI after changes:

```bash
python3 cli.py
```

Recommended manual regression checks:

```text
1. /set lang en, then say hello
2. /set lang zh, then say 你好
3. skillhub search calendar
4. skillhub install calendar-cli, deny once and approve once
5. Read a local PDF
6. Review the current project with Evidence Cards
7. Try a dangerous command and confirm it is blocked or asks for approval
```

---

## Roadmap

- [ ] Add first-class `/image` support for vision-capable local models.
- [ ] Add PDF page-to-image visual understanding for scanned PDFs and charts.
- [ ] Continue improving full bilingual CLI text coverage.
- [ ] Harden workspace path checks and terminal command allowlists.
- [ ] Add cleaner GitHub Pages landing page.
- [ ] Add automated regression tests for permission and language switching.

---

## License

MIT License. See `LICENSE` if present.

---

<div align="center">

Built by **Yule-Cai** for local-first agent experimentation.

</div>
