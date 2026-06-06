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

### A double-helix control architecture for safer agent swarms.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Double Helix](https://img.shields.io/badge/Double--Helix-Control-111111?style=flat-square)](#)
[![Permission First](https://img.shields.io/badge/Permission--First-Agent-2f6f4e?style=flat-square)](#)
[![Evidence Cards](https://img.shields.io/badge/Evidence--Cards-Review-d98435?style=flat-square)](#)
[![Skill Aware](https://img.shields.io/badge/Skill--Aware-Workflows-6d91b8?style=flat-square)](#)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

[Meaning](#-why-helix-swarm) · [Features](#-core-features) · [Architecture](#-architecture) · [Install](#-installation) · [Usage](#-usage) · [Roadmap](#-roadmap)

</div>

---

## 🧬 Why Helix-Swarm?

**Helix-Swarm** means a swarm of agents controlled by a double-helix structure.

The project started from a simple idea:

> An agent should not only plan and act.  
> It should also be checked, approved, and traced.

So Helix-Swarm is built around two intertwined strands:

```text
Strand A — Agency
User intent → task routing → specialist agents → tool proposals → execution

Strand B — Control
permission review → evidence checks → audit logs → user approval → traceable result
```

These two strands form the **Helix**.

The **Swarm** is the group of specialist agents, tools, and skills that work around the supervisor agent.

```text
Leo Supervisor
    ├── File Agent
    ├── Search Agent
    ├── Reviewer
    ├── Computer Agent
    ├── Tool Registry
    └── SkillHub / SOP Skills
```

Helix-Swarm is not trying to be the most autonomous agent framework.

It is trying to be a more **controlled**, **auditable**, and **permission-aware** one.

---

## ✨ What is Helix-Swarm?

**Helix-Swarm** is a permission-first CLI agent framework for safe tool use, evidence-based project review, and skill-aware workflows.

It is designed for developers who want agents that can:

- inspect files;
- compare tools and skills;
- call specialist agents;
- propose terminal actions;
- read project context;
- review code with evidence;
- ask before risky execution.

The central philosophy is:

```text
Agent proposes.
System explains.
User approves.
Tool executes.
Result is traceable.
```

---

## 🔥 Core Features

### 1. Double-Helix Agent Control

Most agent systems focus on the action path:

```text
prompt → plan → tool → result
```

Helix-Swarm adds a second control path:

```text
proposal → permission check → evidence check → approval → audit
```

That is the double-helix architecture:

```text
Agency strand:  intent → agents → tools → execution
Control strand: policy → evidence → approval → trace
```

The goal is not to stop agents from acting.  
The goal is to make their actions visible before they happen.

---

### 2. Permission-First Tool Execution

Low-risk tools can be automatically allowed:

```text
read_file
glob_files
grep_code
find_skills
list_directory
delegate_to_expert
```

High-risk tools require approval:

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

This makes tool use visible, interruptible, and controllable.

---

### 3. Human-in-the-Loop Approval

Helix-Swarm does not assume that an agent should always be allowed to act.

When an operation can modify the system, install packages, execute shell commands, or touch files, the user remains in the loop.

```text
Agent: I want to run this command.
System: Here is the tool, risk level, and arguments.
User: Approve / deny / block.
```

The user keeps final authority over sensitive steps.

---

### 4. Evidence Card Review

For review, audit, security, permission, and bug-finding tasks, Helix-Swarm requires structured evidence.

```text
Evidence Card 1
- File:
- Symbol:
- Evidence:
- Why risky:
- Consequence:
- Suggested fix:
```

This turns the reviewer from a generic advice generator into a traceable project auditor.

A finding is not accepted unless it is tied to concrete code evidence.

---

### 5. Skill-Aware Workflows

Helix-Swarm can search and compare SkillHub-style skills before using or installing them.

Instead of blindly adding capabilities, the workflow becomes:

```text
Search → Compare → Explain → Ask → Install
```

Example:

```bash
skillhub search calendar
```

Then:

```text
Compare calendar-cli, google-calendar, and google-calendar-api.
Do not install anything.
```

The agent should explain the tradeoff before taking action.

---

### 6. Terminal Control Layer

The terminal is the control surface.

Helix-Swarm is built around a CLI loop where users can:

```text
chat
inspect tool calls
switch language
review permissions
compare skills
read files
run commands with approval
```

Common commands:

```bash
/set lang en
/set lang zh
/permission
/models
/stats
/reload
```

---

### 7. Traceable Agent Actions

Tool calls, permission checks, review results, and execution outputs are visible.

Helix-Swarm avoids the “black box agent” feeling by exposing:

```text
which tool is called
why it is risky
what arguments are passed
what the tool returned
whether the action was approved
```

This makes the agent easier to debug and safer to maintain.

---

## 🏗 Architecture

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

### The Double-Helix Control Pattern

```text
                    ┌──────────────────────────────┐
                    │        User Intent            │
                    └──────────────┬───────────────┘
                                   │
             ┌─────────────────────┴─────────────────────┐
             │                                           │
             ▼                                           ▼
     Agency Strand                                Control Strand
     ─────────────                                ──────────────
     Route task                                   Check scope
     Select agent                                 Estimate risk
     Propose tool                                 Ask permission
     Execute action                               Record evidence
     Return result                                Audit outcome
             │                                           │
             └─────────────────────┬─────────────────────┘
                                   ▼
                         Traceable Agent Output
```

---

## 📦 Project Structure

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

## ⚡ Installation

### 1. Clone the repository

```bash
git clone https://github.com/Yule-Cai/Helix-Swarm.git
cd Helix-Swarm
```

### 2. Create a Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your model endpoint

```bash
cp helix_config.example.json helix_config.json
```

Example:

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

### 5. Start Helix-Swarm

```bash
python3 cli.py
```

---

## 📖 Usage

### Basic chat

```text
hello
```

### Switch language

```bash
/set lang en
/set lang zh
```

### Compare skills before installation

```text
I want to install a Google Calendar related skill.
Compare calendar-cli, google-calendar, and google-calendar-api.
Do not install anything.
```

### Review a project with Evidence Cards

```text
Review the current Helix-Swarm project and identify 3 concrete risks.
Read-only. Do not modify code.
```

Expected format:

```text
Evidence Card 1
- File:
- Symbol:
- Evidence:
- Why risky:
- Consequence:
- Suggested fix:
```

### Run a command with approval

```bash
pip install PyPDF2
```

Helix-Swarm will ask before running higher-risk commands.

---

## 🛡 Safety Model

| Operation Type | Behavior |
|---|---|
| Read/search/list tools | Usually auto-approved |
| Skill search | Auto-approved |
| Agent delegation | Auto-approved |
| Terminal command | Reviewed |
| Install command | Reviewed |
| File write/edit/delete | Reviewed |
| Dangerous shell patterns | High-risk review |

Helix-Swarm is not a full operating-system sandbox.

It is a permission-first agent control layer.  
Do not approve commands you do not understand.

---

## 🧪 Manual Regression Tests

Before publishing a new version, test:

```text
1. hello
2. /set lang en
3. /set lang zh
4. skillhub search calendar
5. skillhub install calendar-cli
6. Read a local PDF
7. Review current project with Evidence Cards
8. Try a dangerous command and verify approval is required
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

---

## 🗺 Roadmap

- [x] CLI-first agent control layer
- [x] Permission-gated terminal execution
- [x] Human-in-the-loop approval
- [x] Evidence Card review mode
- [x] Skill-aware workflow
- [x] Chinese / English CLI switching
- [x] Local file reading
- [ ] Stronger reviewer verifier
- [ ] Unified `/file` pipeline for PDF / DOCX / XLSX / images / ZIP
- [ ] `/image` command for vision-capable models
- [ ] More skill adapters
- [ ] Optional lightweight Web UI
- [ ] Closer implementation of the original double-helix planner/executor architecture

---

## 🤝 Contributing

Issues and pull requests are welcome.

Good first contribution areas:

```text
Permission rules
File extractors
SkillHub adapters
Reviewer verification
Documentation
Language support
Agent orchestration
```

---

## ⚠️ Disclaimer

Helix-Swarm can execute local tools and terminal commands after approval.

Use it carefully.

Avoid committing:

```text
helix_config.json
.env
API keys
audit logs
local memory
private documents
```

---

## 📄 License

MIT License.

<div align="center">

Built with ❤️ by [Yule-Cai](https://github.com/Yule-Cai)

</div>
