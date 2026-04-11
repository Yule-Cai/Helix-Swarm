"""
TaskGraph — 结构化任务图
Planner 输出JSON任务图，TaskExecutor 按依赖顺序执行
彻底替代「Planner输出自然语言→Orchestrator每轮LLM判断」的双层模式
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
    depends:  list = field(default_factory=list)   # 依赖的 task id 列表
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
        """返回所有依赖已完成、自身仍待执行的任务"""
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
    把用户需求转换为结构化 TaskGraph（JSON）。
    输出格式固定，不再是自然语言计划。
    """

    # 所有可用 Agent 的说明（供 Planner 参考）
    AGENT_REGISTRY = {
        # ── v2 核心 Agent ──
        "viewer":       "扫描查看工作区目录结构",
        "cleaner":      "清理残留文件或目录",
        "searcher":     "GitHub搜索：API文档、报错解决方案、代码参考",
        "terminal":     "执行终端命令（pip install、编译等）",
        "coder":        "编写或修改代码文件",
        "tester":       "运行代码验证功能，分析报错",
        "debugger":     "深度分析报错，输出修复方案",
        "reviewer":     "审查代码质量，添加注释",
        "doc":          "生成README.md文档",
        "writer":       "撰写小说/故事正文",
        "skill":        "查询技能库，推荐已有技能模板",
        "browser":      "抓取网页内容",
        "selfimprove":  "分析系统薄弱点，输出改进建议",
        # ── v1 新增 Agent ──
        "statemanager": "小说场记：读取章节正文，更新角色动态状态表(JSON)",
        "visualizer":   "架构画图师：将文本逻辑转换为Mermaid流程图或架构图(.png)",
        "mcp":          "MCP万能特工：通过MCP协议连接任意标准MCP Server调用工具",
        "plugin":       "插件特工：包装第三方GitHub开源项目或独立脚本为可调用能力",
    }

    SYSTEM_PROMPT = """你是任务规划专家。将用户需求分解为有向无环任务图。

可用Agent：
{agents}

规则：
1. 必须先用viewer扫描工作区（id: t0），depends为空
2. searcher搜索 和 terminal安装依赖 可以同时依赖t0并行执行（depends都只写["t0"]），不要让它们互相依赖
3. coder写代码后必须接tester验证
4. tester失败时用debugger分析，再用coder修复
5. 最后可选reviewer审查，doc生成文档
6. 小说任务用writer撰写正文，完成后必须接statemanager提取角色状态JSON，不用coder/tester
7. 需要生成系统架构图/流程图时，在doc之后用visualizer生成Mermaid图
8. 遇到陌生API或需要调用外部服务时，用mcp连接对应MCP Server
9. 需要封装第三方GitHub项目或独立脚本为能力时，用plugin处理
10. 用户提到图片/截图/UI设计稿时，在指令中说明图片路径，让coder参考图片编写代码

【并行规划示例】需要搜索+安装依赖+写代码时，正确结构：
t0(viewer) → t1(searcher,depends:[t0]) 和 t2(terminal,depends:[t0]) 并行 → t3(coder,depends:[t1,t2])

只输出JSON，不要任何解释：
{{
  "project_name": "英文小写项目名（不超过20字符）",
  "tasks": [
    {{
      "id": "t0",
      "agent": "viewer",
      "instruction": "扫描工作区结构",
      "depends": []
    }},
    {{
      "id": "t1",
      "agent": "searcher",
      "instruction": "搜索相关资料...",
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
      "instruction": "根据搜索结果和已安装依赖编写...",
      "depends": ["t1", "t2"]
    }}
  ]
}}"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def plan(self, user_request: str, skill_hint: str = "",
             memory=None) -> "TaskGraph":
        """
        memory: MemPalaceManager 实例（可选），用于结构化记忆注入。
        """
        agents_desc = "\n".join(f"- {k}: {v}" for k, v in self.AGENT_REGISTRY.items())

        # 结构化记忆注入（比直接拼字符串更清晰）
        memory_hint = ""
        if memory:
            try:
                items = memory.search_structured(user_request, n_results=3)
                if items:
                    lines = ["【历史经验参考（按相关度排序）】"]
                    for item in items:
                        lines.append(f"- {item['summary']}（相关度 {item['score']}）")
                        lines.append(f"  详情：{item['content'][:150]}…")
                    memory_hint = "\n".join(lines)
            except Exception:
                pass

        hint_parts = []
        if skill_hint:
            hint_parts.append(f"技能库提示（可参考此历史成功路径）：\n{skill_hint}")
        if memory_hint:
            hint_parts.append(memory_hint)
        hint_text = ("\n\n" + "\n\n".join(hint_parts)) if hint_parts else ""

        result = self.llm.json_call(
            system=self.SYSTEM_PROMPT.format(agents=agents_desc),
            user=f"需求：{user_request}{hint_text}",
            temperature=0.1,
            max_tokens=2048,
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
        动态重规划：根据已完成的上下文和失败原因，生成剩余任务列表。
        返回新的 Task 列表（id 以 'r0','r1'… 开头，与原任务区分）。
        """
        agents_desc = "\n".join(f"- {k}: {v}" for k, v in self.AGENT_REGISTRY.items())

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
            f"原始目标（必须严格围绕此目标规划，不得偏离）：{original_goal}\n\n"
            f"已完成的步骤和结果：\n{completed_context}\n\n"
            f"当前失败原因：{failure_reason}\n\n"
            f"{memory_hint}\n\n"
            f"请根据以上信息，重新规划后续任务（不要重复已完成的步骤，必须紧扣原始目标）。\n"
            f"project_name 必须保持 '{project_name}'，不得更改。\n"
            f"重规划的任务应直接解决失败原因，而不是重写整个项目。"
        )

        result = self.llm.json_call(
            system=self.SYSTEM_PROMPT.format(agents=agents_desc),
            user=prompt,
            temperature=0.1,
            max_tokens=1500,
        )

        if not result or "tasks" not in result:
            return []   # 重规划失败，executor 会走原有逻辑

        new_tasks = []
        for i, t in enumerate(result.get("tasks", [])):
            new_tasks.append(Task(
                id          = f"r{i}",
                agent       = t.get("agent", "coder"),
                instruction = t.get("instruction", ""),
                depends     = [],   # 重规划任务串行执行，依赖上一个
            ))
        # 让重规划任务串行
        for i in range(1, len(new_tasks)):
            new_tasks[i].depends = [new_tasks[i-1].id]

        return new_tasks

    def _fallback_plan(self, req: str) -> dict:
        """LLM失败时的最小兜底计划"""
        is_novel = any(kw in req for kw in ["小说","故事","文章","写作"])
        if is_novel:
            return {
                "project_name": "writing",
                "tasks": [
                    {"id":"t0","agent":"viewer","instruction":"扫描工作区","depends":[]},
                    {"id":"t1","agent":"writer","instruction":req,"depends":["t0"]},
                ]
            }
        return {
            "project_name": "project",
            "tasks": [
                {"id":"t0","agent":"viewer","instruction":"扫描工作区","depends":[]},
                {"id":"t1","agent":"coder","instruction":req,"depends":["t0"]},
                {"id":"t2","agent":"tester","instruction":"运行并测试代码","depends":["t1"]},
                {"id":"t3","agent":"doc","instruction":"生成README文档","depends":["t2"]},
            ]
        }