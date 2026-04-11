"""
ProjectMemory — MEMORY.md 指针式记忆系统
灵感来自 Claude Code 的三层记忆架构：
  - MEMORY.md 作为轻量索引文件（每行 ≤150字符的指针）
  - 永久注入每个 Agent 的 system prompt 头部
  - 任务完成后自动用 LLM 提炼新知识合并进去
  - 自愈：合并时消除矛盾、移除过期条目

使用方法：
    pm = ProjectMemory("minesweeper", llm_client)
    context = pm.load()           # 获取注入 prompt 的文本
    pm.update(execution_history)  # 任务后自动更新
"""
from __future__ import annotations
import os
import re
import time

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "workspace")

# 每行最大字符数（参考 Claude Code 的 ~150 字符）
MAX_LINE_CHARS = 150
# MEMORY.md 最多保留多少条指针
MAX_ENTRIES = 40


class ProjectMemory:
    """
    管理单个项目的 MEMORY.md 文件。
    MEMORY.md 存放在 workspace/<project_name>/MEMORY.md
    """

    def __init__(self, project_name: str, llm_client=None):
        self.project   = project_name
        self.llm       = llm_client
        self.mem_path  = os.path.join(MEMORY_DIR, project_name, "MEMORY.md")
        os.makedirs(os.path.dirname(self.mem_path), exist_ok=True)

    # ── 读取 ─────────────────────────────────────────────────
    def load(self) -> str:
        """
        返回适合注入 system prompt 的记忆文本。
        格式：紧凑的指针列表，LLM 应把这些当作"提示"而非事实。
        """
        entries = self._read_entries()
        if not entries:
            return ""
        lines = ["【项目记忆（仅供参考，执行前请对照实际文件验证）】"]
        lines.extend(f"- {e}" for e in entries)
        return "\n".join(lines)

    def _read_entries(self) -> list[str]:
        if not os.path.exists(self.mem_path):
            return []
        try:
            with open(self.mem_path, "r", encoding="utf-8") as f:
                raw = f.read()
            entries = []
            for line in raw.splitlines():
                line = line.strip().lstrip("-•* ").strip()
                if line and not line.startswith("#"):
                    entries.append(line[:MAX_LINE_CHARS])
            return entries
        except Exception:
            return []

    # ── 更新（任务完成后调用）───────────────────────────────
    def update(self, execution_history: list[dict], goal: str, success: bool):
        """
        用 LLM 从本次执行历史中提炼新知识，合并进 MEMORY.md。
        同时做自愈：消除矛盾、移除明显过期的条目。
        """
        if not self.llm or not execution_history:
            return

        existing = self._read_entries()
        history_text = self._compress_history(execution_history)
        status = "成功" if success else "失败"

        prompt = (
            f"目标：{goal}\n执行状态：{status}\n\n"
            f"执行摘要：\n{history_text}\n\n"
            f"当前项目记忆（已有条目）：\n"
            + ("\n".join(f"- {e}" for e in existing) if existing else "（空）")
            + "\n\n"
            "任务：\n"
            "1. 从本次执行中提炼 1-3 条新的关键经验（每条不超过150字符）\n"
            "2. 检查已有条目，删除与新经验矛盾的或明显过期的\n"
            "3. 合并后输出完整的记忆列表（每行一条，以 - 开头）\n"
            "4. 只输出记忆列表，不要任何解释\n\n"
            "示例格式：\n"
            "- main.py 使用 pygame，需要 pip install pygame\n"
            "- 游戏循环在 Game.run() 中，事件处理在第45行\n"
            "- 测试时用二分搜索模拟输入，seed=42"
        )

        try:
            result = self.llm.chat(
                system="你是项目记忆整理专家。输出简洁、精确、可直接行动的知识条目。",
                user=prompt,
                temperature=0.2,
                max_tokens=600,
            )
            if not result or result.strip() == "{}":
                return
            self._write_from_llm_output(result)
        except Exception as e:
            print(f"⚠️ [ProjectMemory] 更新失败: {e}")

    def _compress_history(self, history: list[dict]) -> str:
        """压缩执行历史为紧凑摘要，节省 context。"""
        lines = []
        for rec in history[-8:]:   # 只看最近8步
            agent  = rec.get("agent", "?")
            task   = str(rec.get("task", ""))[:50]
            result = str(rec.get("result", ""))[:100]
            # 标记成功/失败
            status = "✅" if ("✅" in result or "成功" in result) else (
                     "❌" if ("❌" in result or "失败" in result or "Error" in result) else "•")
            lines.append(f"{status} [{agent}] {task}… → {result}…")
        return "\n".join(lines)

    def _write_from_llm_output(self, text: str):
        """解析 LLM 输出的条目列表并写入 MEMORY.md。"""
        entries = []
        for line in text.splitlines():
            line = line.strip().lstrip("-•* ").strip()
            if not line or line.startswith("#") or len(line) < 5:
                continue
            entries.append(line[:MAX_LINE_CHARS])

        # 去重 + 限制条目数
        seen = set()
        unique = []
        for e in entries:
            key = e[:50].lower()
            if key not in seen:
                seen.add(key)
                unique.append(e)

        unique = unique[:MAX_ENTRIES]

        content = (
            f"# {self.project} 项目记忆\n"
            f"# 更新时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"# 这些是执行提示，不是事实，执行前请对照实际文件验证\n\n"
            + "\n".join(f"- {e}" for e in unique)
            + "\n"
        )
        with open(self.mem_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"💾 [ProjectMemory] 已更新 {self.mem_path}，共 {len(unique)} 条")


class GlobalMemoryIndex:
    """
    全局 MEMORY.md：跨项目的通用知识（常见错误、最佳实践等）。
    存放在 workspace/GLOBAL_MEMORY.md
    """

    def __init__(self, llm_client=None):
        self.llm      = llm_client
        self.mem_path = os.path.join(BASE_DIR, "GLOBAL_MEMORY.md")

    def load(self) -> str:
        if not os.path.exists(self.mem_path):
            return ""
        try:
            with open(self.mem_path, "r", encoding="utf-8") as f:
                raw = f.read()
            entries = [
                line.strip().lstrip("-•* ").strip()
                for line in raw.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if not entries:
                return ""
            return "【全局经验库（仅供参考）】\n" + "\n".join(f"- {e[:MAX_LINE_CHARS]}" for e in entries[:20])
        except Exception:
            return ""

    def append(self, entry: str):
        """追加一条全局经验（由 autoDream 调用）。"""
        entry = entry.strip()[:MAX_LINE_CHARS]
        if not entry:
            return
        with open(self.mem_path, "a", encoding="utf-8") as f:
            f.write(f"- {entry}\n")
