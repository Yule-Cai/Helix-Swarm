"""技能库 — 复用上一版本的实现"""
from __future__ import annotations
import os, json, time, importlib, inspect

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_FILE = os.path.join(BASE_DIR, "skills.json")
AGENTS_DIR  = os.path.join(BASE_DIR, "agents")

class SkillLibrary:
    def __init__(self):
        self.skills: dict = self._load()

    def _load(self) -> dict:
        if not os.path.exists(SKILLS_FILE): return {}
        try:
            with open(SKILLS_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}

    def _save(self):
        with open(SKILLS_FILE,"w",encoding="utf-8") as f:
            json.dump(self.skills,f,ensure_ascii=False,indent=2)

    def discover_agents(self, llm_client=None) -> dict:
        discovered = {}
        if not os.path.exists(AGENTS_DIR): return discovered
        for name in os.listdir(AGENTS_DIR):
            agent_file = os.path.join(AGENTS_DIR, name, "agent.py")
            if not os.path.exists(agent_file): continue
            try:
                module = importlib.import_module(f"agents.{name}.agent")
                agent_cls = next((getattr(module,a) for a in dir(module)
                                  if a.endswith("Agent") and isinstance(getattr(module,a),type)), None)
                if not agent_cls: continue
                sig = inspect.signature(agent_cls.__init__)
                params = list(sig.parameters.keys())
                instance = agent_cls(llm_client) if len(params)>1 and llm_client else agent_cls()
                discovered[name] = instance
            except Exception as e:
                print(f"⚠️  [SkillLib] 跳过 {name}: {e}")
        return discovered

    def create_skill(self, task_desc:str, steps:list, result:str, llm_client=None) -> dict:
        skill_id = f"skill_{int(time.time())}"
        if llm_client:
            summary = llm_client.chat(
                "用一句话总结任务类型，格式：技能名称|触发关键词（逗号分隔）",
                f"任务：{task_desc[:200]}\n步骤数：{len(steps)}",
                temperature=0.2, max_tokens=60,
            )
            parts = summary.split("|")
            skill_name = parts[0].strip() if parts else task_desc[:30]
            keywords   = [k.strip() for k in parts[1].split(",")] if len(parts)>1 else []
        else:
            skill_name = task_desc[:30]
            keywords   = []

        skill = {
            "id": skill_id, "name": skill_name, "description": task_desc,
            "keywords": keywords, "steps": steps[:10],
            "success_count": 1,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_used":  time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.skills[skill_id] = skill
        self._save()
        return skill

    def find_relevant_skill(self, task_desc:str) -> dict | None:
        tl = task_desc.lower()
        best_score, best_skill = 0, None
        for s in self.skills.values():
            score = sum(1 for kw in s.get("keywords",[]) if kw.lower() in tl)
            if score > best_score:
                best_score, best_skill = score, s
        return best_skill if best_score >= 2 else None

    def list_skills(self) -> list:
        return sorted(self.skills.values(), key=lambda s: s.get("success_count",0), reverse=True)

    def delete_skill(self, skill_id:str) -> bool:
        if skill_id in self.skills:
            del self.skills[skill_id]; self._save(); return True
        return False