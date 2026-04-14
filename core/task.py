"""
TaskGraph — structured task graph
Planner outputs a JSON task graph, TaskExecutor runs tasks in dependency order
Replaces the two-layer "Planner natural language → Orchestrator per-step LLM" pattern
"""
import json
import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class TaskStatus(Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"
    SKIPPED  = "skipped"

@dataclass
class Task:
    id:       str
    agent:    str
    instruction: str
    depends:  list = field(default_factory=list)   # list of task ids this task depends on
    status:   TaskStatus = TaskStatus.PENDING
    result:   str = ""
    error:    str = ""
    retry:    int = 0
    max_retry: int = 2

@dataclass
class TaskGraph:
    goal:       str
    project:    str
    tasks:      list = field(default_factory=list)  # List[Task]
    skill_hint: str = ""

    def get_ready_tasks(self) -> list:
        """Return all tasks whose dependencies are done and that are still pending."""
        done_ids = {t.id for t in self.tasks if t.status == TaskStatus.DONE}
        return [
            t for t in self.tasks
            if t.status == TaskStatus.PENDING
            and all(dep in done_ids for dep in t.depends)
        ]

    def is_complete(self) -> bool:
        return all(t.status in (TaskStatus.DONE, TaskStatus.SKIPPED) for t in self.tasks)

    def has_failed(self) -> bool:
        return any(t.status == TaskStatus.FAILED for t in self.tasks)

    def summary(self) -> str:
        lines = []
        for t in self.tasks:
            icon = {"pending":"⏳","running":"▶️","done":"✅","failed":"❌","skipped":"⏭️"}.get(t.status.value,"?")
            lines.append(f"{icon} [{t.id}] {t.agent}: {t.instruction[:50]}")
        return "\n".join(lines)


class TaskPlanner:
    """
    Converts user requests into a structured TaskGraph (JSON).
    Fixed output format — no longer natural language plans.
    """

    # ── 动态 Agent 注册表 ──────────────────────────────────────
    # 不再硬编码！由 AgentRegistry 自动扫描 agents/ 目录生成。
    # 通过 set_registry() 注入，或在 __init__ 时传入。
    # 兼容旧代码：若未注入 registry，自动尝试初始化。
    _registry = None  # AgentRegistry 实例（类变量，共享）

    @classmethod
    def set_registry(cls, registry):
        """注入 AgentRegistry 实例（在 web_ui.py 启动时调用一次）。"""
        cls._registry = registry

    @classmethod
    def _get_agents_desc(cls) -> str:
        """
        获取当前可用 Agent 的描述字符串。
        优先用 AgentRegistry，回退到空字符串（Planner 会用自己的判断）。
        """
        if cls._registry is not None:
            return cls._registry.format_for_planner()
        # 懒加载：第一次调用时自动初始化 registry
        try:
            from core.agent_registry import AgentRegistry
            cls._registry = AgentRegistry()
            print(f"⚡ [Planner] 自动发现 {len(cls._registry.available_names())} 个 Agent："
                  f" {', '.join(cls._registry.available_names())}")
            return cls._registry.format_for_planner()
        except Exception as e:
            print(f"⚠️  [Planner] AgentRegistry 初始化失败，使用空列表: {e}")
            return ""

    SYSTEM_PROMPT = """You are a task planning expert. Break down user requests into a directed acyclic task graph.

Available Agents:
{agents}

Rules:
1. Always start with viewer to scan the workspace (id: t0), depends must be empty
2. searcher and terminal can run in parallel — both depend only on t0 (depends: ["t0"]), never make them depend on each other
3. coder must be followed by tester for verification
4. if tester fails, use debugger to analyze, then coder to fix
5. optionally add reviewer for code review and doc for documentation at the end
6. for fiction/story tasks: use writer for the main content, then statemanager to extract character state as JSON — do NOT use coder/tester
7. for architecture diagrams or flowcharts: use visualizer after doc to generate a Mermaid diagram
8. for unknown APIs or external services: use mcp to connect the appropriate MCP Server
9. to wrap third-party GitHub projects as callable capabilities: use plugin
10. if user mentions images/screenshots/UI mockups: include the image path in the instruction so coder can reference it
11. [IMPORTANT] for games and complex programs, the coder instruction MUST explicitly say "keep code concise, under 150 lines" to avoid LLM timeout
12. [CRITICAL] NEVER use terminal to install: sqlite3, SQLite, json, os, sys, re, math, pathlib, threading, queue, datetime, collections, itertools, functools, typing, abc, io, hashlib, uuid, random, time, csv, xml, html, urllib, http, email, logging, unittest — these are Python stdlib, already built-in. Flask is usually pre-installed; only add terminal if coder explicitly fails with ModuleNotFoundError. When in doubt, skip terminal and go straight to coder.
13. [IMPORTANT] for Flask/Web projects, coder MUST generate all required HTML template files (saved to templates/) alongside app.py — omitting templates causes TemplateNotFound errors at runtime

[Parallel planning example] when search + install + code are needed:
t0(viewer) → t1(searcher, depends:[t0]) and t2(terminal, depends:[t0]) in parallel → t3(coder, depends:[t1,t2])

Output JSON only, no explanations:
{{
  "project_name": "lowercase-english-name-max-20chars",
  "tasks": [
    {{
      "id": "t0",
      "agent": "viewer",
      "instruction": "Scan workspace structure",
      "depends": []
    }},
    {{
      "id": "t1",
      "agent": "searcher",
      "instruction": "Search for relevant references...",
      "depends": ["t0"]
    }},
    {{
      "id": "t2",
      "agent": "terminal",
      "instruction": "pip install xxx",
      "depends": ["t0"]
    }},
    {{
      "id": "t3",
      "agent": "coder",
      "instruction": "Based on search results and installed dependencies, write...",
      "depends": ["t1", "t2"]
    }}
  ]
}}"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def rebuild_from_skill(self, user_request: str, skill: dict) -> "TaskGraph":
        """
        Rebuild TaskGraph directly from skill graph_json, skipping LLM call.
        Replaces project name/keywords in instructions with current request keywords.
        """
        graph_json   = skill["graph_json"]
        old_project  = graph_json.get("project", "project")

        # Generate project name from request (no LLM call needed)
        import re as _re
        new_project = _re.sub(r'[^a-z0-9]', '',
                              user_request.lower().replace(' ', ''))[:20] or old_project

        tasks = []
        for i, t in enumerate(graph_json.get("tasks", [])):
            tasks.append(Task(
                id          = t.get("id", f"t{i}"),
                agent       = t.get("agent", "viewer"),
                instruction = t.get("instruction", ""),
                depends     = t.get("depends", []),
            ))

        print(f"⚡ [Planner] Skill library hit — reusing task graph directly (skipping LLM planning)"
              f" | confidence {skill.get('_confidence', '?')}")

        return TaskGraph(
            goal       = user_request,
            project    = new_project,
            tasks      = tasks,
            skill_hint = skill.get("name", ""),
        )

    def plan(self, user_request: str, skill_hint: str = "",
             memory=None) -> "TaskGraph":
        """
        memory: MemPalaceManager instance (optional), for structured memory injection.
        """
        agents_desc = self._get_agents_desc()

        # Inject structured memory context
        memory_hint = ""
        if memory:
            try:
                items = memory.search_structured(user_request, n_results=3)
                if items:
                    lines = ["[Relevant past experience (by relevance)]"]
                    for item in items:
                        lines.append(f"- {item['summary']} (score: {item['score']})")
                        lines.append(f"  detail: {item['content'][:150]}…")
                    memory_hint = "\n".join(lines)
            except Exception:
                pass

        hint_parts = []
        if skill_hint:
            hint_parts.append(f"Skill library hint (reference this successful path):\n{skill_hint}")
        if memory_hint:
            hint_parts.append(memory_hint)
        hint_text = ("\n\n" + "\n\n".join(hint_parts)) if hint_parts else ""

        result = self.llm.json_call(
            system=self.SYSTEM_PROMPT.format(agents=agents_desc),
            user=f"Request: {user_request}{hint_text}",
            temperature=0.1,
            max_tokens=4096,
        )

        if not result or "tasks" not in result:
            result = self._fallback_plan(user_request)

        project_name = re.sub(r'[^a-z0-9_]', '', result.get("project_name","project").lower()) or "project"
        tasks = []
        for i, t in enumerate(result.get("tasks", [])):
            tasks.append(Task(
                id          = t.get("id", f"t{i}"),
                agent       = t.get("agent", "viewer"),
                instruction = t.get("instruction", ""),
                depends     = t.get("depends", []),
            ))

        return TaskGraph(
            goal       = user_request,
            project    = project_name,
            tasks      = tasks,
            skill_hint = skill_hint,
        )

    def replan(self, original_goal: str, project_name: str,
               completed_context: str, failure_reason: str,
               memory=None) -> list["Task"]:
        """
        Dynamic re-planning: generate remaining tasks based on completed context and failure reason.
        For syntax errors, directly generate debugger → coder → tester without calling LLM.
        """
        # ── Syntax error fast-path: skip LLM ──────────────
        if "语法错误" in failure_reason or "SyntaxError" in failure_reason or \
           "invalid syntax" in failure_reason:
            # Extract file path from failure reason
            import re as _re
            fp = _re.search(r'([^\s]+\.py)', failure_reason)
            fpath = fp.group(1) if fp else "main.py"
            return [
                Task(id="r0", agent="debugger",
                     instruction=(f"Fix the syntax error in {fpath}.\n\n"
                                  f"Error details: {failure_reason[:600]}\n\n"
                                  f"Read the file, find the syntax error, output the complete fixed code."),
                     depends=[]),
                Task(id="r1", agent="tester",
                     instruction=f"Run {fpath} to verify the syntax error is fixed and it runs correctly.",
                     depends=["r0"]),
            ]

        agents_desc = self._get_agents_desc()

        memory_hint = ""
        if memory:
            try:
                items = memory.search_structured(failure_reason, n_results=2)
                if items:
                    memory_hint = "\n".join(
                        f"- 历史经验：{item['summary']}" for item in items
                    )
            except Exception:
                pass

        prompt = (
            f"Original goal (all new tasks MUST strictly serve this goal):\n{original_goal}\n\n"
            f"Completed steps:\n{completed_context}\n\n"
            f"Failure reason: {failure_reason}\n\n"
            f"{memory_hint}\n\n"
            f"Based on the above, plan the remaining tasks (do not repeat completed steps, must serve the original goal).\n"
            f"project_name must remain '{project_name}'.\n"
            f"New tasks should directly fix the failure — do not rewrite the entire project.\n"
            f"For code errors: use debugger to analyze then coder to fix. Do not use viewer."
        )

        result = self.llm.json_call(
            system=self.SYSTEM_PROMPT.format(agents=agents_desc),
            user=prompt,
            temperature=0.1,
            max_tokens=3000,
        )

        if not result or "tasks" not in result:
            return []   # re-planning failed, executor will follow original logic

        new_tasks = []
        for i, t in enumerate(result.get("tasks", [])):
            new_tasks.append(Task(
                id          = f"r{i}",
                agent       = t.get("agent", "coder"),
                instruction = t.get("instruction", ""),
                depends     = [],   # re-planned tasks run serially
            ))
        # make re-planned tasks run serially
        for i in range(1, len(new_tasks)):
            new_tasks[i].depends = [new_tasks[i-1].id]

        return new_tasks

    def _fallback_plan(self, req: str) -> dict:
        """Minimal fallback plan when LLM fails."""
        is_novel = any(kw in req.lower() for kw in ["novel","story","fiction","write a story","写小说","故事","文章","写作"])
        if is_novel:
            return {
                "project_name": "writing",
                "tasks": [
                    {"id":"t0","agent":"viewer","instruction":"Scan workspace","depends":[]},
                    {"id":"t1","agent":"writer","instruction":req,"depends":["t0"]},
                ]
            }
        return {
            "project_name": "project",
            "tasks": [
                {"id":"t0","agent":"viewer","instruction":"Scan workspace","depends":[]},
                {"id":"t1","agent":"coder","instruction":req,"depends":["t0"]},
                {"id":"t2","agent":"tester","instruction":"Run and test the code","depends":["t1"]},
                {"id":"t3","agent":"doc","instruction":"Generate README documentation","depends":["t2"]},
            ]
        }