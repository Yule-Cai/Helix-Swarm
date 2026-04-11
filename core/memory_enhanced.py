"""
EnhancedMemory — 增强记忆模块（v1 原版 + v2 适配）
在 MemPalaceManager 基础上增加：
  1. 任务执行记忆自动提炼（每次任务完成后自动存入）
  2. 错误-解决方案库（专门记录 Bug 和修复方案）
  3. 跨项目全局知识库
"""
import os
import json
import time
from core.memory import MemPalaceManager

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERROR_DB_FILE = os.path.join(BASE_DIR, "error_solutions.json")


class EnhancedMemory:

    def __init__(self, project_name: str, llm_client=None):
        self.project_mem = MemPalaceManager(project_name=project_name)
        self.global_mem  = MemPalaceManager(project_name="global_knowledge")
        self.llm         = llm_client
        self._error_db   = self._load_error_db()

    # ── 错误数据库 ────────────────────────────────────────────

    def _load_error_db(self) -> dict:
        if not os.path.exists(ERROR_DB_FILE):
            return {}
        try:
            with open(ERROR_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_error_db(self):
        with open(ERROR_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self._error_db, f, ensure_ascii=False, indent=2)

    def store_error_solution(self, error_msg: str, solution: str, agent: str = ""):
        key = str(hash(error_msg[:100]))
        self._error_db[key] = {
            "error":      error_msg[:500],
            "solution":   solution,
            "agent":      agent,
            "count":      self._error_db.get(key, {}).get("count", 0) + 1,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save_error_db()

    def find_error_solution(self, error_msg: str) -> str:
        err_lower = error_msg.lower()
        for entry in self._error_db.values():
            if any(word in err_lower for word in entry["error"].lower().split()[:10]):
                return entry["solution"]
        return ""

    def list_error_solutions(self) -> list:
        return sorted(self._error_db.values(), key=lambda x: x.get("count", 0), reverse=True)

    # ── 任务记忆自动提炼 ──────────────────────────────────────

    def distill_task_memory(self, task_desc: str, execution_history: list, success: bool):
        """任务完成后自动提炼经验存入记忆库"""
        if not self.llm or not execution_history:
            return
        # 提取错误-解决方案对
        for i, record in enumerate(execution_history):
            result = record.get("result", "")
            if "❌" in result or "报错" in result or "Error" in result:
                if i + 1 < len(execution_history):
                    fix = execution_history[i + 1].get("result", "")
                    if "✅" in fix:
                        self.store_error_solution(
                            result[:200], fix[:300], record.get("agent", "")
                        )
        # 提炼整体经验
        history_text = "\n".join(
            f"[{r.get('agent','?')}] {str(r.get('task',''))[:50]}… → {str(r.get('result',''))[:80]}…"
            for r in execution_history[-6:]
        )
        status = "成功" if success else "失败"
        prompt = (
            f"任务：{task_desc}\n执行状态：{status}\n"
            f"关键步骤：\n{history_text}\n\n"
            f"请用2-3句话提炼本次任务的经验教训，重点是遇到了什么问题、如何解决的。"
        )
        try:
            summary = self.llm.chat(
                system="你是经验提炼专家，擅长从任务执行历史中提取可复用的知识。",
                user=prompt,
                temperature=0.2,
                max_tokens=200,
            )
            if summary and summary != "{}":
                self.project_mem.store_memory(
                    content=f"任务：{task_desc}\n{summary}",
                    summary=f"{status}经验：{summary[:60]}",
                )
        except Exception:
            pass

    # ── 融合召回（项目 + 全局 + 错误库）──────────────────────

    def recall(self, query: str) -> str:
        project_mem = self.project_mem.recall(query)
        global_mem  = self.global_mem.recall(query)
        error_sol   = self.find_error_solution(query)
        parts = []
        if error_sol:
            parts.append(f"【已知错误解决方案】\n{error_sol}")
        if project_mem:
            parts.append(project_mem)
        if global_mem and global_mem != project_mem:
            parts.append(global_mem)
        return "\n\n".join(parts)

    # 兼容 v2 Memory.store 接口
    def store(self, content: str, summary: str = "", tags: list = None):
        self.project_mem.store_memory(content, summary)