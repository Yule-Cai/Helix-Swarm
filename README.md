# Helix Swarm 🧬

A local multi-agent swarm that takes natural language requests and autonomously plans, executes, and delivers complete software projects — running entirely on your own machine with a local LLM.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## What it does

You describe what you want. The swarm handles the rest:

```
"Write a snake game with pygame"
```

↓

```
Planner → viewer → searcher + terminal (parallel) → coder → tester → debugger → reviewer → doc
```

The Planner generates a structured task graph, agents execute in dependency order (with parallelism where possible), and the final result lands in your `workspace/` folder — tested, reviewed, and documented.

---

## Architecture

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
         (generates a directed acyclic task graph)
              │
              ▼
         TaskExecutor
         (concurrent execution, dynamic re-planning on failure)
              │
         ┌────┴────┐
         │  Agents  │  ← 17 specialist agents
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
| `core/executor.py` | Concurrent execution engine with dynamic re-planning and cancel support |
| `core/event_bus.py` | Pub/Sub event bus with distributed tracing (TraceContext) |
| `core/memory.py` | MemPalaceManager — ChromaDB vector store with JSON fallback |
| `core/memory_enhanced.py` | Error solution database + experience distillation |
| `core/project_memory.py` | MEMORY.md pointer-based memory (inspired by Claude Code) |
| `core/learning_scheduler.py` | Autonomous learning scheduler + autoDream consolidation |
| `core/skill_library.py` | Skill library — auto-packages successful tasks for reuse |

### 17 Agents

| Agent | Role |
|-------|------|
| `viewer` | Scans workspace directory structure |
| `coder` | Writes code — supports `<file>` tags and markdown code blocks |
| `tester` | Runs tests — handles interactive programs via binary search stdin simulation |
| `debugger` | Reads source + error, outputs a fixed complete file directly |
| `reviewer` | Code quality review, writes improved files back to disk |
| `terminal` | Executes shell commands, intelligently extracts commands from natural language |
| `searcher` | GitHub search for API docs, error solutions, code references |
| `browser` | Fetches web page content |
| `doc` | Generates README.md documentation |
| `writer` | Writes fiction / story prose |
| `statemanager` | Extracts novel character state into JSON |
| `visualizer` | Generates Mermaid architecture diagrams |
| `cleaner` | Cleans up leftover files |
| `skill` | Queries the skill library |
| `selfimprove` | Analyzes system weak points and outputs improvement suggestions |
| `mcp` | Connects to external tools via MCP protocol |
| `plugin` | Wraps GitHub open-source projects as callable capabilities |

---

## Key Features

**Plan once, execute by graph**  
The Planner generates a complete DAG upfront. The Executor follows dependency order — no per-step LLM calls needed.

**Concurrent execution**  
Tasks with no dependencies run in parallel (e.g. `searcher + terminal` simultaneously) using `ThreadPoolExecutor`.

**Dynamic re-planning**  
When consecutive failures exceed a threshold, the swarm automatically calls the Planner to generate new steps for the remaining work instead of giving up.

**MEMORY.md pointer memory**  
Each project maintains `workspace/<project>/MEMORY.md`. After every task, the LLM distills key lessons into the file. On the next run, its contents are injected into every Agent's instruction header — inspired by Claude Code's memory architecture.

**autoDream**  
When autonomous learning stops, the system consolidates what it learned into a global `GLOBAL_MEMORY.md`, resolves contradictions, and updates knowledge pointers — similar to Claude Code's autoDream service.

**Hard cancel**  
Clicking cancel immediately closes the SSE connection and sends a cancel signal directly into the LLM client — stopping inference mid-call, not just the frontend.

**Full i18n**  
Complete Chinese / English switching — UI text, Agent instructions, and LLM system prompts all follow the selected language.

**Vision support**  
Upload images and the LLM can analyze them (requires a vision-capable model such as Gemma 4, Qwen2-VL, or LLaVA).

**EventBus with tracing**  
Every agent action publishes structured events with `trace_id` / `span_id`. Useful for debugging complex multi-step executions.

---

## Requirements

- Python 3.11+
- [LM Studio](https://lmstudio.ai/) or any OpenAI-compatible local LLM server
- Recommended models: Gemma 4, Qwen2.5-Coder, DeepSeek-Coder  
  (Use a vision-capable model like Gemma 4 or Qwen2-VL to enable image analysis)

---

## Installation

```bash
git clone https://github.com/Yule-Cai/Helix-Swarm.git
cd Helix-Swarm/maos

pip install -r requirements.txt
```

---

## Configuration

Start LM Studio, load a model, and enable the local server (default port 1234).

Edit `config.json` or use the Settings panel in the Web UI:

```json
{
  "llm_api_url": "http://localhost:1234/v1",
  "llm_model": "local-model",
  "llm_timeout": 300,
  "github_token": ""
}
```

`github_token` is optional — adding one raises the GitHub search rate limit from 60 to 5,000 requests/hour.

---

## Usage

```bash
cd maos
python web_ui.py
```

Open your browser at http://127.0.0.1:5000

### Basic usage

Just describe what you want:

```
Write a snake game using pygame
Build a Flask TODO REST API with SQLite
Write a chapter of a cyberpunk sci-fi story
Analyze this screenshot and describe what you see
```

### Agent mode vs Chat mode

The toggle in the bottom-right of the input box switches between:
- **Agent mode (on)** — complex tasks; goes through Planner → TaskGraph → multi-agent execution
- **Chat mode (off)** — direct LLM conversation; good for questions and simple requests

### Image upload

Upload an image, then send a message. The LLM will analyze the image content (vision model required).

### Autonomous learning

Click the `Auto Learn` button in the toolbar. The system periodically searches GitHub for technical content, distills it into memory, and consolidates knowledge via autoDream when stopped.

### Settings

Click the gear icon (bottom-left sidebar) to open the Settings panel:
- **General** — dark mode, language, skill library, enhanced memory toggles
- **Agents** — enable or disable individual agents

---

## Project Structure

```
maos/
├── web_ui.py                  # Main entry point (Flask + SSE)
├── config.json                # Configuration
├── requirements.txt
├── core/
│   ├── event_bus.py           # EventBus (Pub/Sub + distributed tracing)
│   ├── task.py                # TaskGraph / TaskPlanner
│   ├── executor.py            # Concurrent execution engine
│   ├── router.py              # Three-way router
│   ├── system_handler.py      # System command handler
│   ├── memory.py              # MemPalaceManager (ChromaDB)
│   ├── memory_enhanced.py     # Error DB + experience distillation
│   ├── project_memory.py      # MEMORY.md pointer memory
│   ├── skill_library.py       # Skill library
│   └── learning_scheduler.py  # Autonomous learning + autoDream
├── agents/
│   ├── coder/    tester/    debugger/    reviewer/
│   ├── terminal/ searcher/  browser/     viewer/
│   ├── doc/      writer/    visualizer/  cleaner/
│   ├── statemanager/  skill/  selfimprove/
│   └── mcp/      plugin/
├── llm/
│   └── client.py              # LLMClient (multimodal + cancel support)
└── templates/
    └── index.html             # Web UI (single file, full i18n)
```

---

## .gitignore

Add this before pushing:

```gitignore
# Runtime data
maos/workspace/
maos/memory/
maos/mem_palace_db/
maos/learning_reports/
maos/logs/
maos/history.json
maos/error_solutions.json
maos/learning_progress.json
maos/GLOBAL_MEMORY.md
maos/__pycache__/
maos/**/__pycache__/
*.pyc
```

Keep `config.json` in the repo but leave `github_token` empty.

---

## Roadmap

- [ ] Markdown rendering in chat responses
- [ ] Direct file context passing between agents (not just truncated text)
- [ ] Live TaskGraph visualization during execution
- [ ] More language support (Japanese, Korean)
- [ ] Community plugin marketplace

---

## Contributing

Issues and PRs are welcome.

To add a new Agent: create a directory under `agents/`, implement a class with `run(instruction, workspace_dir) -> str`, and register it in `web_ui.py`'s `build_agents()`.

---

## License

MIT