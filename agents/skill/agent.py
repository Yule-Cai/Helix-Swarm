import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.skill_library import SkillLibrary

class SkillAgent:
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.lib = SkillLibrary()

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        tl = instruction.lower()
        if any(k in tl for k in ["列出","所有","list"]): return self._list()
        if any(k in tl for k in ["删除","移除","delete"]): return self._delete(instruction)
        return self._search(instruction)

    def _search(self, q):
        s = self.lib.find_relevant_skill(q)
        if s:
            steps = "\n".join(f"  {i+1}. [{r['agent']}] {r['instruction'][:50]}"
                              for i,r in enumerate(s.get("steps",[])))
            return f"✅ 技能：{s['name']}\n关键词：{','.join(s.get('keywords',[]))}\n步骤：\n{steps}"
        return "📭 技能库无匹配，任务完成后将自动封装。"

    def _list(self):
        skills = self.lib.list_skills()
        if not skills: return "📭 技能库为空"
        return "📚 技能库：\n" + "\n".join(f"  ✦ {s['name']} ({s.get('success_count',1)}次)" for s in skills[:10])

    def _delete(self, inst):
        for s in self.lib.list_skills():
            if s["name"] in inst or s["id"] in inst:
                self.lib.delete_skill(s["id"]); return f"🗑️ 已删除：{s['name']}"
        return "❓ 未找到要删除的技能"
