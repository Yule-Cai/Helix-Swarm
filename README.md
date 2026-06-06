```text
██╗  ██╗███████╗██╗     ██╗██╗  ██╗    ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗
██║  ██║██╔════╝██║     ██║╚██╗██╔╝    ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║
███████║█████╗  ██║     ██║ ╚███╔╝     ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║
██╔══██║██╔══╝  ██║     ██║ ██╔██╗     ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║
██║  ██║███████╗███████╗██║██╔╝ ██╗    ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝    ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
             A U T O N O M O U S   M U L T I - A G E N T   S W A R M
```

<div align="center">

# Helix-Swarm

### A double-helix control architecture for safer agent swarms.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![CLI](https://img.shields.io/badge/CLI-Agent%20Control%20Layer-111111?style=flat-square)](#)
[![Double Helix](https://img.shields.io/badge/Double--Helix-Control-2f6f4e?style=flat-square)](#)
[![Permission First](https://img.shields.io/badge/Permission--First-Execution-d98435?style=flat-square)](#)
[![Evidence Cards](https://img.shields.io/badge/Evidence--Cards-Review-6d91b8?style=flat-square)](#)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

[Why Helix-Swarm](#-why-helix-swarm) ·
[Core Features](#-core-features) ·
[Built-in Agents](#-built-in-agents) ·
[Architecture](#-architecture) ·
[Installation](#-installation) ·
[Usage](#-usage) ·
[Roadmap](#-roadmap)

</div>

---

## 🧬 Why Helix-Swarm?

**Helix-Swarm** means a swarm of agents controlled by a double-helix structure.

The original idea was simple:

> One agent should plan the whole task.  
> Multiple specialist agents should work together.  
> A second control strand should keep every risky action visible, reviewable, and traceable.

That is why the project is called **Helix-Swarm**.

```text
Helix = double-helix control structure
Swarm = multiple specialist agents working together
```

The two strands are:

```text
Agency Strand
User intent → task routing → specialist agents → tool proposal → execution

Control Strand
permission review → evidence check → user approval → audit trail → traceable result
```

Most agent systems focus on making agents more autonomous.

Helix-Swarm focuses on making agent actions **visible before they happen**.

---

## ✨ What is Helix-Swarm?

**Helix-Swarm** is a permission-first CLI agent framework for safer tool use, evidence-based project review, and skill-aware workflows.

It is designed for developers who want agents that can:

- inspect files;
- search project context;
- compare tools and skills;
- delegate work to specialist agents;
- propose terminal actions;
- review code with evidence;
- ask before risky execution;
- keep tool calls and results traceable.

The core loop is:

```text
Agent proposes.
System explains.
User approves.
Tool executes.
Result is traceable.
```

Helix-Swarm is not trying to be the most autonomous agent framework.

It is trying to be a more **controlled**, **auditable**, and **permission-aware** one.

---

## 🔥 Core Features

### 1. Double-Helix Agent Control

Traditional agent flow:

```text
Prompt → Plan → Tool → Result
```

Helix-Swarm adds a second control path:

```text
Proposal → Permission check → Evidence check → Approval → Audit
```

Together:

```text
Agency strand:  intent → agents → tools → execution
Control strand: policy → evidence → approval → trace
```

The goal is not to stop agents from acting.

The goal is to make important actions visible, reviewable, and reversible.

---

### 2. Permission-First Execution

Helix-Swarm treats tool execution as something that should be supervised.

Low-risk tools can run automatically:

```text
read_file
glob_files
grep_code
search_symbols
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

Permission choices:

```text
Y = Approve
N = Deny
B = Block this tool for this session
```

This makes tool use visible, interruptible, and controllable.

---

### 3. Human-in-the-Loop Tool Use

Helix-Swarm does not assume an agent should always be allowed to act.

When a step can modify the system, install packages, execute shell commands, or affect local files, the user remains in the loop.

```text
Agent: I want to run this command.
System: Here is the tool, risk level, and arguments.
User: Approve / deny / block.
```

The user keeps final authority over sensitive operations.

---

### 4. Evidence Card Review

For review, audit, security, permission, and bug-finding tasks, Helix-Swarm encourages structured evidence instead of generic advice.

A review finding should look like this:

```text
Evidence Card
- File:
- Symbol:
- Evidence:
- Why risky:
- Consequence:
- Suggested fix:
```

This turns the reviewer from a vague security reporter into a traceable project auditor.

A serious finding should be tied to concrete code evidence.

---

### 5. Skill-Aware Workflows

Helix-Swarm is designed to work with SkillHub-style skills and local SOP-style skills.

Instead of blindly adding new capabilities, the intended workflow is:

```text
Search → Compare → Explain → Ask → Install
```

Example:

```bash
skillhub search calendar
```

Then ask:

```text
Compare calendar-cli, google-calendar, and google-calendar-api.
Do not install anything.
```

The agent should explain the tradeoff before taking action.

---

### 6. Real CLI Control Surface

Helix-Swarm is CLI-first.

The terminal is not just a temporary interface. It is the control surface for the agent system.

The CLI includes:

```text
startup logo
tool loading summary
skill loading summary
session selection
SYSTEM READY panel
bottom status bar
thinking spinner
tool-call review panel
permission controls
language switching
model switching
```

Common commands:

```bash
/help
/reload
/tools
/search <pattern>
/models
/stats
/permission
/set lang en
/set lang zh
/set model <model-name>
```

---

### 7. Traceable Agent Actions

Helix-Swarm exposes important agent behavior instead of hiding everything inside the model.

You can see:

```text
which agent is acting
which tool is called
why the action is risky
what arguments are passed
whether the action was approved
what the tool returned
what evidence supports the final answer
```

This makes the system easier to debug, audit, and maintain.

---

## 🧠 Built-in Agents

Helix-Swarm is organized as a small agent swarm coordinated by **Leo Supervisor**.

```text
Leo Supervisor
    ├── File Agent
    ├── Search Agent
    ├── Reviewer
    ├── Computer Agent
    ├── Tool Registry
    └── SkillHub / SOP Skills
```

### Leo Supervisor

The coordinator of the swarm.

```text
Input:
User intent, task type, active configuration, conversation state.

Output:
Delegation plan, specialist calls, final answer.

Boundary:
Does not silently execute risky tools.
Routes risky actions through permission review.
```

### File Agent

Reads local files and turns raw content into usable context.

```text
Input:
Local file path, file type, read request.

Output:
Extracted text, structured summary, file-read errors.

Boundary:
Reads requested or delegated files.
Reports dependency failures clearly.
```

### Search Agent

Looks up skills, tools, code references, and project evidence before conclusions.

```text
Input:
Search query, target directory, skill names, project keywords.

Output:
Candidate tools, matched files, skill summaries, evidence locations.

Boundary:
Searches and reads before concluding.
Avoids unsupported guesses.
```

### Reviewer

Produces structured Evidence Cards instead of generic audit text.

```text
Input:
Review task, project files, tool results.

Output:
Evidence Cards, risk priority, suggested fixes.

Boundary:
Should not make a serious finding without concrete evidence.
```

### Computer Agent

Handles terminal-facing actions after permission review.

```text
Input:
Approved command, working directory, execution constraints.

Output:
Terminal output, error logs, execution status.

Boundary:
High-risk commands require explicit user approval.
```

---

## 🏗 Architecture

```text
User Input
    │
    ▼
CLI Router
    │
    ├── Slash Commands
    │       ├── /help
    │       ├── /reload
    │       ├── /tools
    │       ├── /models
    │       ├── /stats
    │       ├── /permission
    │       └── /set
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
            │       ├── search_symbols
            │       └── execute_terminal
            │
            ├── Permission Manager
            ├── Hook Manager
            ├── Audit Logger
            ├── Memory
            └── Model Router
```

### Double-Helix Control Pattern

```text
                    ┌──────────────────────────────┐
                    │          User Intent          │
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

## 🚀 Usage

### Basic chat

```text
hello
```

### Switch language

```bash
/set lang en
/set lang zh
```

### Show available commands

```bash
/help
```

### Show loaded tools

```bash
/tools
```

### Search tools

```bash
/search file
/search terminal
/search skill
```

### Check available models

```bash
/models
```

### View system stats

```bash
/stats
```

### Check permission state

```bash
/permission
```

### Change permission mode

```bash
/permission ask-first
/permission plan-only
/permission workspace-only
```

### Block a tool for the current session

```bash
/permission block execute_terminal
```

### Unblock a tool

```bash
/permission unblock execute_terminal
```

---

## 🧪 Example Workflows

### 1. Compare skills before installing

```text
I want to install a Google Calendar related skill.
Compare calendar-cli, google-calendar, and google-calendar-api.
Do not install anything.
```

Expected behavior:

```text
Search Agent finds candidate skills.
Leo summarizes the differences.
No installation happens unless the user asks for it.
```

### 2. Review a project with Evidence Cards

```text
Review the current Helix-Swarm project and identify 3 concrete risks.
Read-only. Do not modify code.
```

Expected output style:

```text
Evidence Card 1
- File:
- Symbol:
- Evidence:
- Why risky:
- Consequence:
- Suggested fix:
```

### 3. Run a terminal command with approval

```bash
pip install PyPDF2
```

Expected behavior:

```text
Helix-Swarm detects a direct terminal command.
The permission panel shows risk level and working directory.
The user chooses Y / N / B.
```

### 4. Safe low-risk command

```bash
skillhub search calendar
```

Expected behavior:

```text
Low-risk query commands may run automatically.
Install, delete, write, and script execution still require approval.
```

---

## 🛡 Safety Model

| Operation Type | Default Behavior |
|---|---|
| Read/search/list tools | Usually auto-approved |
| Skill search | Usually auto-approved |
| Agent delegation | Usually auto-approved |
| Terminal command | Reviewed depending on risk |
| Install command | Requires approval |
| File write/edit/delete | Requires approval |
| Dangerous shell patterns | High-risk review |
| Blocked tool | Denied for current session |

Helix-Swarm is not a full operating-system sandbox.

It is a permission-first agent control layer.

Do not approve commands you do not understand.

---

## 🌐 Website

The repository includes a GitHub Pages landing page:

```text
index.html
```

The website presents:

```text
double-helix background
Agent Swarm interaction
CLI replay animation
permission-first explanation
Evidence Card workflow
installation guide
roadmap
```

If GitHub Pages is enabled, the site can be served directly from the repository root or the selected Pages branch.

---

## 🧪 Manual Regression Tests

Before publishing a new version, test:

```text
1. Start CLI
2. Choose a session
3. Confirm SYSTEM READY panel appears
4. Send a normal chat message
5. Confirm thinking spinner appears
6. Run /set lang en
7. Run /set lang zh
8. Run /tools
9. Run skillhub search calendar
10. Run a high-risk command and confirm permission review appears
11. Ask for Evidence Card project review
12. Confirm file/symbol/evidence are included
13. Confirm bottom toolbar shows tokens, balance, and active model
```

Expected behavior:

```text
Startup screen is visible.
Low-risk queries run smoothly.
High-risk commands require approval.
Review answers include concrete evidence.
Language switching changes CLI text.
Tool calls remain visible and traceable.
```

---

## 🗺 Roadmap

- [x] CLI-first agent control layer
- [x] Startup screen and system-ready panel
- [x] Bottom toolbar with token / balance / model status
- [x] Permission-gated terminal execution
- [x] Human-in-the-loop approval
- [x] Evidence Card review mode
- [x] Skill-aware workflow
- [x] Chinese / English CLI switching
- [x] Local file reading
- [x] GitHub Pages landing page
- [ ] Stronger reviewer verifier
- [ ] Unified `/file` pipeline for PDF / DOCX / XLSX / images / ZIP
- [ ] `/image` command for vision-capable models
- [ ] More SkillHub adapters
- [ ] Stronger double-helix planner / executor separation
- [ ] More robust audit log viewer
- [ ] Optional lightweight Web UI

---

## 🤝 Contributing

Issues and pull requests are welcome.

Good first contribution areas:

```text
Permission rules
Evidence Card verifier
File extractors
SkillHub adapters
Reviewer prompts
Documentation
Language support
Agent orchestration
Website polish
```

When contributing, please keep the project philosophy in mind:

```text
Agent autonomy is useful.
Visible control is necessary.
```

---

## ⚠️ Disclaimer

Helix-Swarm can execute local tools and terminal commands after user approval.

Use it carefully.

Avoid committing:

```text
helix_config.json
.env
API keys
audit logs
local memory
private documents
private PDFs
```

Review commands before approving them.

---

## 📄 License

MIT License.

<div align="center">

Built by [Yule-Cai](https://github.com/Yule-Cai)

**Helix-Swarm** — agent swarms should be powerful, but their actions should remain reviewable.

</div>
