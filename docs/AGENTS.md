# Helix-Swarm Agents

Helix-Swarm is designed for local small models. The agent system uses strong role boundaries and tool-grounded prompts so a smaller model can work like a broader local Claude Code/Codex-style assistant.

## Main Agent

### Leo

Leo is the main router. It reads the user request, chooses the right specialist, delegates a concrete task, then summarizes the result for the user.

Leo should not do tool-heavy work directly. It should delegate first when local inspection, file operations, terminal commands, web workflows, or code changes are needed.

## Specialist Agents

### File Agent

Handles local files, folders, PDFs, docs, file summaries, file search, organization, and file edits.

### Computer Agent

Handles terminal commands, dependency checks, environment setup, git basics, processes, and local system diagnostics.

### App Agent

Coordinates local macOS apps such as Finder, VSCode, Preview, browser apps, and Office-style applications. Current implementation uses safe terminal-based app coordination where possible.

### Browser Agent

Handles browser and webpage workflows. The current implementation has a prompt and safe fallback tools; full browser automation can be connected later through Playwright or a Browser MCP/tool.

### Search Agent

Handles local/project search and synthesis. It uses project search tools first and reports whether a claim is tool-verified or inferred.

### Coder

Implements code changes, debugging, refactors, and tests. It is retained as a specialist under the broader Computer/Developer capability.

### Reviewer

Reviews diffs and code for bugs, regressions, safety risks, and missing tests.

## Prompting Principles

- One clear step at a time.
- Tool-grounded claims only.
- Search/list before read/edit.
- Ask before destructive or credential-sensitive actions.
- Prefer one specialist first; avoid multi-agent loops.
- Specialist responses must say what was checked, what changed, and what remains.
