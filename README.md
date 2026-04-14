```
██╗  ██╗███████╗██╗     ██╗██╗  ██╗    ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗
██║  ██║██╔════╝██║     ██║╚██╗██╔╝    ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║
███████║█████╗  ██║     ██║ ╚███╔╝     ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║
██╔══██║██╔══╝  ██║     ██║ ██╔██╗     ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║
██║  ██║███████╗███████╗██║██╔╝ ██╗    ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝    ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
```
<div align="center">

🧬 **A local multi-agent swarm that turns natural language into complete software projects**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Yule-Cai/Helix-Swarm?style=flat-square&color=f59e0b)](https://github.com/Yule-Cai/Helix-Swarm/stargazers)

[Install](#-one-line-install) · [Usage](#-usage) · [Architecture](#-architecture) · [Roadmap](#-roadmap)

</div>

---

## ✨ What it does

You describe what you want. The swarm handles the rest:

```
"Write a snake game with pygame"
```

```
Planner → viewer → searcher + terminal (parallel) → coder → tester → debugger → reviewer → doc
```

The Planner generates a complete task graph upfront. The Executor follows dependency order with real parallelism where possible. The final result lands in your `workspace/` folder — tested, reviewed, and documented.

---

## ⚡ One-line Install

**Windows:**
```powershell
irm https://raw.githubusercontent.com/Yule-Cai/Helix-Swarm/main/install.ps1 | iex
```

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Yule-Cai/Helix-Swarm/main/install.sh | bash
```

Then use the `helix` command:

```bash
helix           # Start the Web UI
helix qq        # Start the QQ gateway
helix update    # Update to the latest version
helix doctor    # Diagnose the environment
```

> Requires [LM Studio](https://lmstudio.ai/) with a model loaded, or any OpenAI-compatible API endpoint.

---

## 🏗 Architecture

```
User Input
    │
    ▼
 Router ──► SYSTEM  (direct system commands)
    │
    ├──► CHAT   (plain LLM conversation)
    │
    └──► DEV    (Agent mode)
              │
              ▼
         TaskPlanner
         (generates a directed acyclic task graph in one shot)
              │
              ▼
         TaskExecutor
         (concurrent execution · dynamic re-planning · hard cancel)
              │
         ┌────┴────┐
         │  Agents  │  ← auto-discovered from agents/ directory
         └──────────┘
              │
              ▼
         ProjectMemory
         (MEMORY.md — persistent per-project knowledge)
```

### Core Modules

| Module | Description |
|--------|-------------|
| `core/router.py` | Three-way dispatch: SYSTEM / CHAT / DEV |
| `core/task.py` | TaskPlanner (one-shot planning) + TaskGraph (DAG) |
| `core/executor.py` | Concurrent execution engine with dynamic re-planning and hard cancel |
| `core/event_bus.py` | Pub/Sub event bus with distributed tracing (TraceContext) |
| `core/memory.py` | MemPalaceManager — ChromaDB vector store with JSON fallback |
| `core/memory_enhanced.py` | Error solution database + experience distillation |
| `core/project_memory.py` | MEMORY.md pointer-based memory (inspired by Claude Code) |
| `core/learning_scheduler.py` | Autonomous learning scheduler + autoDream consolidation |
| `core/skill_library.py` | Skill library with progressive disclosure (Level 0/1 loading) |
| `core/user_model.py` | User modeling — auto-extracts preferences and habits |
| `core/agent_registry.py` | Auto-discovers agents from `agents/` directory, bilingual descriptions |

### 17 Specialist Agents

| Agent | Role |
|-------|------|
| `viewer` | Scans workspace directory structure |
| `coder` | Writes code — supports `<file>` tags and markdown code blocks |
| `tester` | Runs tests — handles interactive programs via binary search stdin simulation |
| `debugger` | Reads source + error, outputs a fully fixed file directly |
| `reviewer` | Code quality review, writes improved files back to disk |
| `terminal` | Executes shell commands, intelligently extracts commands from natural language |
| `searcher` | GitHub search for API docs, error solutions, code references |
| `browser` | Fetches web page content |
| `doc` | Generates README.md documentation |
| `writer` | Writes fiction / story prose |
| `statemanager` | Extracts novel character state into JSON |
| `visualizer` | Generates Mermaid architecture diagrams |
| `cleaner` | Cleans up leftover files |
| `skill` | Queries the skill library and recommends reusable templates |
| `selfimprove` | Analyzes system weak points and outputs improvement suggestions |
| `mcp` | Connects to external tools via MCP protocol |
| `plugin` | Wraps GitHub open-source projects as callable capabilities |

---

## 🔑 Key Features

**Plan once, execute by graph**
The Planner generates a complete DAG upfront. The Executor follows dependency order — no per-step LLM calls needed for orchestration.

**True parallelism**
Tasks with no mutual dependencies run simultaneously (e.g. `searcher + terminal` at the same time) via `ThreadPoolExecutor`.

**Dynamic re-planning**
When consecutive failures exceed a threshold, the swarm calls the Planner to regenerate steps for the remaining work instead of giving up. Syntax errors take a fast path — `debugger → tester` is generated directly, skipping LLM planning entirely.

**MEMORY.md pointer memory**
Each project maintains `workspace/<project>/MEMORY.md`. After every task, the LLM distills key lessons into the file. On the next run, its contents are injected into every Agent's instruction header — inspired by Claude Code's memory architecture.

**autoDream**
When autonomous learning stops, the system consolidates learned knowledge into a global `GLOBAL_MEMORY.md`, resolves contradictions, and updates knowledge pointers.

**User modeling**
Automatically extracts your tech stack, communication style, and work patterns from conversations. Injects a compact user profile into Agent system prompts — the more you use it, the better it knows you.

**Progressive skill disclosure**
Level 0 index (~25 tokens/skill) is always in memory, letting the Planner see all historical skills when planning. Level 1 full content is loaded on-demand only when a skill is matched. Token cost stays flat no matter how many skills you accumulate.

**Auto-discovery agent registry**
Agents are discovered automatically by scanning the `agents/` directory at startup — no manual registration needed. Each agent declares its own `DESCRIPTION` and `DESCRIPTION_ZH`, and the Planner receives the correct language version based on `ui_language` in config. Adding a new agent requires only dropping a file into the directory.

**Hard cancel**
Clicking cancel immediately closes the SSE connection and sends a cancel signal directly into the LLM client — stopping inference mid-call, not just the frontend stream.

**QQ messaging gateway**
Connect via NapCatQQ / OneBot v11. Send a QQ message and Helix replies with the result. Works in private chat and group chat (mention the bot to trigger).

**Full i18n**
Complete Chinese / English switching — UI text, Agent instructions, and LLM system prompts all follow the selected language.

**Vision support**
Upload images and the LLM can analyze them (requires a vision-capable model such as Gemma 4, Qwen2-VL, or LLaVA).

---

## ⚙️ Configuration

Start LM Studio, load a model, and enable the local server (default port 1234). Or point `llm_api_url` at any OpenAI-compatible endpoint.

Edit `config.json` or use the Settings panel in the Web UI:

```json
{
  "llm_api_url": "http://localhost:1234/v1",
  "llm_model": "local-model",
  "llm_timeout": 300,
  "github_token": "",

  "qq_napcat_http": "http://127.0.0.1:3000",
  "qq_gateway_port": 6700,
  "qq_access_token": "",
  "qq_allowlist": ["your-qq-number"]
}
```

`github_token` is optional — adding one raises the GitHub search rate limit from 60 to 5,000 requests/hour.

Recommended models: **Gemma 4**, **Qwen2.5-Coder**, **DeepSeek-Coder**
(Use a vision-capable model like Gemma 4 or Qwen2-VL to enable image analysis)

---

## 📖 Usage

```bash
helix   # then open http://127.0.0.1:5000
```

### Basic prompts

```
Write a snake game using pygame
Build a Flask TODO REST API with SQLite
Write a chapter of a cyberpunk sci-fi story
Analyze this screenshot and describe what you see
```

### Agent mode vs Chat mode

The toggle in the bottom-right of the input box:
- **Agent mode (on)** — complex tasks; Planner → TaskGraph → multi-agent execution
- **Chat mode (off)** — direct LLM conversation; good for questions and simple requests

### QQ gateway

```bash
# Terminal 1 — start Helix
helix

# Terminal 2 — start QQ gateway (requires NapCatQQ running)
helix qq
```

In NapCat WebUI, add a WebSocket client pointing to `ws://127.0.0.1:6700`. Then DM the bot account from your QQ and it will reply with Helix's output.

### Autonomous learning

Click `Auto Learn` in the toolbar. Helix periodically searches GitHub for technical content, distills it into memory, and consolidates knowledge via autoDream when stopped.

### Settings

Gear icon (bottom-left sidebar):
- **General** — dark mode, language, skill library, enhanced memory toggles
- **Agents** — enable or disable individual agents

---

## 📁 Project Structure

```
Helix-Swarm/
├── install.sh              # Linux/macOS one-line installer
├── install.ps1             # Windows one-line installer
├── index.html              # Official landing page (GitHub Pages)
└── maos/
    ├── web_ui.py           # Main entry point (Flask + SSE)
    ├── config.json         # Configuration
    ├── requirements.txt
    ├── core/
    │   ├── agent_registry.py   # Auto-discovery + bilingual agent descriptions
    │   ├── task.py             # TaskGraph / TaskPlanner
    │   ├── executor.py         # Concurrent execution engine
    │   ├── router.py           # Three-way router
    │   ├── memory.py           # MemPalaceManager (ChromaDB)
    │   ├── project_memory.py   # MEMORY.md pointer memory
    │   ├── skill_library.py    # Skill library (progressive disclosure)
    │   ├── user_model.py       # User modeling
    │   ├── learning_scheduler.py  # Autonomous learning + autoDream
    │   ├── event_bus.py        # EventBus (Pub/Sub + distributed tracing)
    │   ├── memory_enhanced.py  # Error DB + experience distillation
    │   └── system_handler.py
    ├── agents/
    │   ├── coder/    tester/    debugger/    reviewer/
    │   ├── terminal/ searcher/  browser/     viewer/
    │   ├── doc/      writer/    visualizer/  cleaner/
    │   ├── statemanager/  skill/  selfimprove/
    │   └── mcp/      plugin/
    ├── gateway/
    │   ├── qq_gateway.py       # QQ messaging gateway (NapCatQQ / OneBot v11)
    │   └── wechat_gateway.py   # WeChat gateway (itchat / WeCom)
    ├── llm/
    │   └── client.py           # LLMClient (multimodal + hard cancel)
    └── templates/
        └── index.html          # Web UI (single file, full i18n)
```

---

## 🗺 Roadmap

- [ ] Markdown rendering in chat responses
- [ ] Direct file context passing between agents (not just truncated text)
- [ ] Live TaskGraph visualization during execution
- [ ] More language support (Japanese, Korean)
- [ ] Community plugin marketplace

---

## 🤝 Contributing

Issues and PRs are welcome.

**To add a new Agent** — drop a file, that's it. No registration needed:

1. Create a directory under `agents/` (e.g. `agents/translator/`)
2. Add `agent.py` with two description lines and a class:

```python
DESCRIPTION    = "Translate text between Chinese and English"
DESCRIPTION_ZH = "在中英文之间翻译文本内容"

class TranslatorAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str) -> str:
        return self.llm.chat("You are a translator.", instruction) or ""
```

3. Restart `web_ui.py`. The agent is automatically discovered, added to the Planner's available list, and ready to use.

---

## .gitignore

```gitignore
maos/workspace/
maos/memory/
maos/mem_palace_db/
maos/learning_reports/
maos/logs/
maos/history.json
maos/error_solutions.json
maos/learning_progress.json
maos/GLOBAL_MEMORY.md
maos/user_model.json
maos/gateway/__pycache__/
maos/__pycache__/
maos/**/__pycache__/
*.pyc
```

Keep `config.json` in the repo but leave `github_token` and `api_key` empty before committing.

---

<div align="center">

MIT License · Built with ❤️ by [Yule-Cai](https://github.com/Yule-Cai)

</div>
