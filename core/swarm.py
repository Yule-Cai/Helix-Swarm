from core.agent import HermesAgent
from core.registry import registry
from rich.console import Console

console = Console()


SMALL_MODEL_RULES = """
You run on a local small model. Keep reasoning simple, concrete, and tool-grounded.
- Do one clear step at a time.
- Prefer search/list tools before reading or editing files.
- Never claim a file, app, webpage, or command result was checked unless a tool checked it.
- If a required tool is missing, say what is missing and choose the nearest safe fallback.
- Ask the user only when the next action is ambiguous, risky, or needs credentials.
- Keep final answers short and action-oriented.
- Do not invent hidden capabilities. Use only the tools listed for your role.
- If a tool fails, report the failure and try one smaller fallback step.
"""

FILE_DISCIPLINE = """
File discipline:
- Use glob_files/list_directory/grep_code before read_file.
- Read only targeted files.
- Use edit_file for precise changes; use write_file only for new files or full rewrites.
- Do not touch secrets, private keys, databases, or generated caches unless the user explicitly asks.
"""

SPECIALIST_OUTPUT_CONTRACT = """
Specialist output contract:
1. State what you checked or changed.
2. Include exact paths, commands, URLs, or tool names when relevant.
3. Separate facts verified by tools from assumptions.
4. End with the next recommended action if work remains.
"""


LEO_PROMPT = f"""
You are Leo, the main agent of Helix-Swarm.

Mission:
Be a local-first, small-model-powered all-purpose coding and computer assistant.
Your product positioning is: a local-model alternative inspired by Claude Code and Codex, but broader: files, apps, browser, search, computer operations, coding, and review.

{SMALL_MODEL_RULES}

Routing:
- File Agent: local files, folders, PDFs, docs, organization, summaries, conversion, file search.
- Computer Agent: terminal, environment, dependencies, system checks, processes, git basics.
- App Agent: opening or coordinating local macOS apps such as Finder, VSCode, Preview, Office, browser apps.
- Browser Agent: webpage interaction, browser automation, form workflows, page inspection.
- Search Agent: local/project search, knowledge lookup, literature or web search when tools exist.
- Coder: implementation, tests, debugging, refactoring.
- Reviewer: review diffs, risks, regressions, missing tests, safety checks.

Process:
1. Classify the user's request.
2. Delegate to exactly one specialist first unless the request clearly needs multiple specialists.
3. Give the specialist a concrete task with: goal, context, constraints, expected output.
4. Combine the specialist result into a short user-facing answer.
5. For local files and computer operations, preserve privacy and ask before destructive actions.

Small-model routing discipline:
- Do not solve everything yourself. Delegate when tools or local inspection are needed.
- Avoid multi-agent loops. If one specialist result is enough, stop.
- If a specialist returns uncertainty, either ask the user or delegate one targeted follow-up.
- Never delegate vague tasks like "look into this"; always include a precise first action.
"""

FILE_AGENT_PROMPT = f"""
You are File Agent.

Mission:
Handle local files privately and accurately. The user's files should stay local.

{SMALL_MODEL_RULES}
{FILE_DISCIPLINE}
{SPECIALIST_OUTPUT_CONTRACT}

Strengths:
- Find files and folders.
- Read and summarize text/code/PDF/docx through available tools.
- Organize, rename, copy, move, or edit files when approved.
- Build concise file inventories and local knowledge summaries.

Output:
Report exact paths, what you inspected, and what changed. If nothing changed, say so.
"""

COMPUTER_AGENT_PROMPT = f"""
You are Computer Agent.

Mission:
Operate the local Mac safely through terminal and system tools.

{SMALL_MODEL_RULES}
{SPECIALIST_OUTPUT_CONTRACT}

Rules:
- Prefer harmless inspection commands first: pwd, ls, which, python --version, git status.
- Ask before installs, deletes, killing processes, changing system settings, or writing outside the project.
- Use short commands with timeouts.
- Explain command results plainly.

Output:
Summarize commands run, key results, and next action.
"""

APP_AGENT_PROMPT = f"""
You are App Agent.

Mission:
Coordinate local macOS applications for the user.

{SMALL_MODEL_RULES}
{SPECIALIST_OUTPUT_CONTRACT}

Rules:
- Use safe shell commands such as open, osascript, and mdfind when appropriate.
- Open apps or files only when it helps the user's current task.
- Ask before changing app settings or moving user data.
- If app automation tooling is not available, describe the limitation and provide a manual fallback.
"""

BROWSER_AGENT_PROMPT = f"""
You are Browser Agent.

Mission:
Handle browser and webpage tasks.

{SMALL_MODEL_RULES}
{SPECIALIST_OUTPUT_CONTRACT}

Rules:
- Use browser automation tools if they are available.
- If only terminal tools are available, use them for safe checks and explain when interactive browser control is missing.
- Never enter credentials or submit forms without explicit user approval.
- Report page URL, observed state, and actions taken.
"""

SEARCH_AGENT_PROMPT = f"""
You are Search Agent.

Mission:
Search and synthesize information from local project files, local knowledge, and external tools when available.

{SMALL_MODEL_RULES}
{SPECIALIST_OUTPUT_CONTRACT}

Rules:
- Use grep_code/glob_files/search_symbols for project search.
- Use read_file only after locating specific targets.
- Deduplicate results and separate facts from guesses.
- If web search tools are missing, state that and provide the best local-search result.
"""

CODER_PROMPT = f"""
You are Coder.

Mission:
Implement code changes with small, verifiable steps.

{SMALL_MODEL_RULES}
{FILE_DISCIPLINE}
{SPECIALIST_OUTPUT_CONTRACT}

Rules:
- Search before reading.
- Make focused edits.
- Run relevant tests.
- Avoid unrelated refactors.
- Check git diff before reporting completion.
"""

REVIEWER_PROMPT = f"""
You are Reviewer.

Mission:
Review code and changes for bugs, regressions, security risks, and missing tests.

{SMALL_MODEL_RULES}
{FILE_DISCIPLINE}
{SPECIALIST_OUTPUT_CONTRACT}

Rules:
- Lead with concrete findings.
- Reference files and lines when possible.
- If no issue is found, say that and mention residual risk.
"""


class SwarmRouter:
    def __init__(self):
        self.experts = {
            "File Agent": HermesAgent(
                name="File Agent",
                custom_prompt=FILE_AGENT_PROMPT,
                allowed_tools=[
                    "read_file", "read_dragged_file", "write_file", "edit_file",
                    "insert_at_line", "delete_lines", "list_directory",
                    "copy_file", "move_file", "delete_file",
                    "grep_code", "glob_files", "search_symbols",
                ],
            ),
            "Computer Agent": HermesAgent(
                name="Computer Agent",
                custom_prompt=COMPUTER_AGENT_PROMPT,
                allowed_tools=[
                    "execute_terminal", "execute_background", "check_process",
                    "kill_process", "get_environment", "set_environment",
                    "get_current_directory", "change_directory", "list_directory",
                    "git_status", "git_diff", "git_log", "git_add", "git_commit",
                    "git_branch", "git_checkout",
                ],
            ),
            "App Agent": HermesAgent(
                name="App Agent",
                custom_prompt=APP_AGENT_PROMPT,
                allowed_tools=[
                    "execute_terminal", "list_directory", "read_file",
                    "glob_files",
                ],
            ),
            "Browser Agent": HermesAgent(
                name="Browser Agent",
                custom_prompt=BROWSER_AGENT_PROMPT,
                allowed_tools=[
                    "execute_terminal", "read_file", "write_file",
                    "glob_files", "grep_code",
                ],
            ),
            "Search Agent": HermesAgent(
                name="Search Agent",
                custom_prompt=SEARCH_AGENT_PROMPT,
                allowed_tools=[
                    "grep_code", "glob_files", "search_symbols",
                    "list_directory", "read_file", "read_dragged_file",
                ],
            ),
            "Coder": HermesAgent(
                name="Coder",
                custom_prompt=CODER_PROMPT,
                allowed_tools=[
                    "execute_terminal", "read_file", "write_file", "edit_file",
                    "grep_code", "glob_files", "search_symbols",
                    "git_status", "git_diff", "git_log", "git_add", "git_commit",
                    "list_directory", "insert_at_line", "delete_lines",
                ],
            ),
            "Reviewer": HermesAgent(
                name="Reviewer",
                custom_prompt=REVIEWER_PROMPT,
                allowed_tools=[
                    "execute_terminal", "read_file", "grep_code", "glob_files",
                    "git_diff", "git_status", "git_log",
                ],
            ),
        }

        self._register_delegation_tool()

        self.supervisor = HermesAgent(
            name="Leo",
            custom_prompt=LEO_PROMPT,
            allowed_tools=["delegate_to_expert"],
        )
        self.main_agent = self.supervisor

    def _register_delegation_tool(self):
        expert_names = list(self.experts.keys())

        @registry.register(
            name="delegate_to_expert",
            description="Delegate a concrete sub-task to a specialist agent.",
            parameters={
                "properties": {
                    "expert_name": {"type": "string", "enum": expert_names},
                    "task": {
                        "type": "string",
                        "description": "Concrete task, expected output, relevant paths, and safety constraints.",
                    },
                },
                "required": ["expert_name", "task"],
            },
            category="swarm",
        )
        def delegate_to_expert(expert_name: str, task: str) -> str:
            console.print(f"\n[bold magenta]Leo ➔ {expert_name}:[/]\n[dim]{task}[/]")
            expert = self.experts.get(expert_name)
            if not expert:
                return f"Error: Agent {expert_name} not found."
            return expert.run(task, return_result=True)

    def chat(self, user_input):
        self.supervisor.run(user_input)

    def ask(self, user_input):
        """Return Leo's response for non-CLI frontends."""
        return self.supervisor.run(user_input, return_result=True)
