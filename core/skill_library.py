"""
技能库 — 升级版
新增：
  1. create_skill 时存储完整 TaskGraph JSON，下次直接复用，跳过 Planner LLM 调用
  2. find_relevant_skill 返回置信度分数
  3. 相似度计算升级：关键词匹配 + 描述子串匹配
"""
from __future__ import annotations
import os, json, time, importlib, inspect

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_FILE = os.path.join(BASE_DIR, "skills.json")
AGENTS_DIR  = os.path.join(BASE_DIR, "agents")

# 置信度达到此阈值时直接复用任务图，跳过 Planner
REUSE_THRESHOLD = 0.6


class SkillLibrary:
    def __init__(self):
        self.skills: dict = self._load()

    def _load(self) -> dict:
        if not os.path.exists(SKILLS_FILE): return {}
        try:
            with open(SKILLS_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}

    def _save(self):
        with open(SKILLS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.skills, f, ensure_ascii=False, indent=2)

    def discover_agents(self, llm_client=None) -> dict:
        discovered = {}
        if not os.path.exists(AGENTS_DIR): return discovered
        for name in os.listdir(AGENTS_DIR):
            agent_file = os.path.join(AGENTS_DIR, name, "agent.py")
            if not os.path.exists(agent_file): continue
            try:
                module    = importlib.import_module(f"agents.{name}.agent")
                agent_cls = next((getattr(module, a) for a in dir(module)
                                  if a.endswith("Agent") and isinstance(getattr(module, a), type)), None)
                if not agent_cls: continue
                sig    = inspect.signature(agent_cls.__init__)
                params = list(sig.parameters.keys())
                instance = agent_cls(llm_client) if len(params) > 1 and llm_client else agent_cls()
                discovered[name] = instance
            except Exception as e:
                print(f"⚠️  [SkillLib] 跳过 {name}: {e}")
        return discovered

    # ── 创建技能（存储完整 TaskGraph JSON）────────────────────
    def create_skill(self, task_desc: str, steps: list, result: str,
                     llm_client=None, task_graph=None) -> dict:
        """
        task_graph: TaskGraph 实例（可选）。传入后序列化存储，
                    下次命中时直接复用，跳过 Planner LLM 调用。
        """
        skill_id = f"skill_{int(time.time())}"

        if llm_client:
            summary = llm_client.chat(
                "用一句话总结任务类型，格式：技能名称|触发关键词（逗号分隔，3-6个）",
                f"任务：{task_desc[:200]}\n步骤：{' → '.join(s.get('agent','') for s in steps[:6])}",
                temperature=0.2, max_tokens=80,
            )
            parts      = summary.split("|")
            skill_name = parts[0].strip() if parts else task_desc[:30]
            keywords   = [k.strip() for k in parts[1].split(",")] if len(parts) > 1 else []
        else:
            skill_name = task_desc[:30]
            keywords   = []

        # 序列化 TaskGraph（只存需要重建的字段）
        graph_json = None
        if task_graph is not None:
            try:
                graph_json = {
                    "project": task_graph.project,
                    "tasks": [
                        {
                            "id":          t.id,
                            "agent":       t.agent,
                            "instruction": t.instruction,
                            "depends":     t.depends,
                        }
                        for t in task_graph.tasks
                    ]
                }
            except Exception as e:
                print(f"⚠️  [SkillLib] TaskGraph 序列化失败: {e}")

        skill = {
            "id":            skill_id,
            "name":          skill_name,
            "description":   task_desc,
            "keywords":      keywords,
            "steps":         steps[:10],
            "graph_json":    graph_json,   # ← 新增：完整任务图
            "success_count": 1,
            "created_at":    time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_used":     time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.skills[skill_id] = skill
        self._save()
        print(f"✨ [SkillLib] 技能已封装：{skill_name}（含任务图：{graph_json is not None}）")
        return skill

    # ── 查找技能（返回置信度）────────────────────────────────
    def find_relevant_skill(self, task_desc: str) -> dict | None:
        """
        返回最相关的技能（含 _confidence 字段），未找到返回 None。
        置信度 >= REUSE_THRESHOLD 时调用方可直接复用任务图。
        """
        tl = task_desc.lower()
        best_score, best_skill = 0.0, None

        for s in self.skills.values():
            keywords = s.get("keywords", [])
            if not keywords:
                continue

            # 关键词命中率
            kw_hits = sum(1 for kw in keywords if kw.lower() in tl)
            kw_score = kw_hits / len(keywords) if keywords else 0

            # 描述子串匹配加分
            desc_words = s.get("description", "").lower().split()
            desc_hits  = sum(1 for w in desc_words[:10] if len(w) > 2 and w in tl)
            desc_score = min(desc_hits / 5, 0.4)   # 最多加 0.4

            score = min(kw_score + desc_score, 1.0)

            if score > best_score:
                best_score, best_skill = score, s

        if best_skill and best_score >= 0.3:   # 最低展示阈值
            result = dict(best_skill)
            result["_confidence"] = round(best_score, 2)
            return result
        return None

    def can_reuse_graph(self, skill: dict) -> bool:
        """判断是否可以直接复用任务图（跳过 Planner）。"""
        return (
            skill is not None
            and skill.get("_confidence", 0) >= REUSE_THRESHOLD
            and skill.get("graph_json") is not None
        )

    def update_usage(self, skill_id: str):
        """技能被使用后更新统计。"""
        if skill_id in self.skills:
            self.skills[skill_id]["success_count"] = \
                self.skills[skill_id].get("success_count", 0) + 1
            self.skills[skill_id]["last_used"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save()

    def list_skills(self) -> list:
        return sorted(self.skills.values(),
                      key=lambda s: s.get("success_count", 0), reverse=True)

    def delete_skill(self, skill_id: str) -> bool:
        if skill_id in self.skills:
            del self.skills[skill_id]; self._save(); return True
        return False