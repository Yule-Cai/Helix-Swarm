"""
技能库 v2 — 渐进式披露版（Progressive Disclosure）
灵感来自 Hermes Agent 的 Level 0/1 技能加载机制。

核心改进：
  Level 0（索引层）：只加载 name + description + keywords，约 3-5 token/技能
  Level 1（详情层）：按需加载完整 graph_json + steps，只在命中时读取

这样即使有 100+ 个技能，注入 Planner prompt 的 token 量也几乎不变。

兼容原版所有接口，原有代码无需修改。
"""
from __future__ import annotations
import os, json, time, importlib, inspect

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_FILE = os.path.join(BASE_DIR, "skills.json")
AGENTS_DIR  = os.path.join(BASE_DIR, "agents")

# 置信度达到此阈值时直接复用任务图，跳过 Planner
REUSE_THRESHOLD = 0.6

# Level 0 每条技能描述的最大字符数（控制 token）
L0_DESC_CHARS = 60


class SkillLibrary:
    """
    技能库（渐进式披露版）。

    内部结构：
      self._index  — Level 0 索引（轻量，常驻内存）
      self._skills — 完整数据（Level 1，按需从磁盘加载）
    """

    def __init__(self):
        self._skills: dict = self._load_all()
        self._build_index()

    # ── 持久化 ────────────────────────────────────────────────

    def _load_all(self) -> dict:
        if not os.path.exists(SKILLS_FILE):
            return {}
        try:
            with open(SKILLS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        with open(SKILLS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._skills, f, ensure_ascii=False, indent=2)

    # ── Level 0 索引构建 ─────────────────────────────────────

    def _build_index(self):
        """
        从完整数据构建 Level 0 索引。
        只保留：id / name / description(截断) / keywords / success_count
        graph_json 和 steps 不在索引中。
        """
        self._index: dict[str, dict] = {}
        for sid, s in self._skills.items():
            self._index[sid] = {
                "id":            sid,
                "name":          s.get("name", ""),
                "description":   s.get("description", "")[:L0_DESC_CHARS],
                "keywords":      s.get("keywords", []),
                "success_count": s.get("success_count", 0),
                "last_used":     s.get("last_used", ""),
            }

    # ── Level 0：列出所有技能（极低 token）────────────────────

    def list_skills_brief(self) -> list[dict]:
        """
        Level 0：返回所有技能的轻量摘要列表。
        适合注入 Planner prompt 或在 Agent 中做技能查询。
        每条约 20-30 token，100 个技能也只用约 2500 token。
        """
        return sorted(
            self._index.values(),
            key=lambda s: s.get("success_count", 0),
            reverse=True,
        )

    def format_level0_for_prompt(self) -> str:
        """
        将 Level 0 技能列表格式化为可注入 prompt 的紧凑字符串。
        示例：
          [snake_game] 使用 pygame 开发贪吃蛇游戏 (keywords: pygame,game,snake) ★3
          [flask_api]  Flask REST API + SQLite    (keywords: flask,api,sqlite)  ★1
        """
        items = self.list_skills_brief()
        if not items:
            return ""
        lines = ["【技能库（Level 0 索引）】"]
        for s in items[:30]:  # 最多展示 30 条
            kws  = ",".join(s["keywords"][:4])
            star = f"★{s['success_count']}" if s.get("success_count", 0) > 0 else ""
            lines.append(f"  [{s['name'][:20]}] {s['description'][:50]} ({kws}) {star}")
        return "\n".join(lines)

    # ── Level 1：按需加载技能详情 ────────────────────────────

    def load_skill_detail(self, skill_id: str) -> dict | None:
        """
        Level 1：加载指定技能的完整内容（含 graph_json + steps）。
        只在技能命中后调用，不预加载。
        """
        return self._skills.get(skill_id)

    # ── 查找技能（先 Level 0 筛选，再 Level 1 加载）─────────

    def find_relevant_skill(self, task_desc: str) -> dict | None:
        """
        两阶段查找：
          1. Level 0：在索引中快速计算相似度，找到最佳候选
          2. Level 1：命中后才加载完整数据（含 graph_json）
        返回含 _confidence 字段的完整技能，未找到返回 None。
        """
        tl = task_desc.lower()
        best_score, best_id = 0.0, None

        # Phase 1：Level 0 相似度计算（只用索引，不读磁盘）
        for sid, s in self._index.items():
            keywords = s.get("keywords", [])
            if not keywords:
                continue

            kw_hits  = sum(1 for kw in keywords if kw.lower() in tl)
            kw_score = kw_hits / len(keywords)

            desc_words = s.get("description", "").lower().split()
            desc_hits  = sum(1 for w in desc_words[:10] if len(w) > 2 and w in tl)
            desc_score = min(desc_hits / 5, 0.4)

            score = min(kw_score + desc_score, 1.0)
            if score > best_score:
                best_score, best_id = score, sid

        if not best_id or best_score < 0.3:
            return None

        # Phase 2：Level 1 加载完整数据
        full = self.load_skill_detail(best_id)
        if not full:
            return None

        result = dict(full)
        result["_confidence"] = round(best_score, 2)
        return result

    def can_reuse_graph(self, skill: dict) -> bool:
        return (
            skill is not None
            and skill.get("_confidence", 0) >= REUSE_THRESHOLD
            and skill.get("graph_json") is not None
        )

    # ── 创建技能 ─────────────────────────────────────────────

    def create_skill(self, task_desc: str, steps: list, result: str,
                     llm_client=None, task_graph=None) -> dict:
        skill_id = f"skill_{int(time.time())}"

        if llm_client:
            summary = llm_client.chat(
                "Summarize the task type in one line, format: skill_name|trigger_keywords (comma-separated, 3-6 keywords)",
                f"Task: {task_desc[:200]}\nSteps: {' → '.join(s.get('agent','') for s in steps[:6])}",
                temperature=0.2, max_tokens=80,
            )
            parts      = summary.split("|")
            skill_name = parts[0].strip() if parts else task_desc[:30]
            keywords   = [k.strip() for k in parts[1].split(",")] if len(parts) > 1 else []
        else:
            skill_name = task_desc[:30]
            keywords   = []

        # 序列化 TaskGraph
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
            "graph_json":    graph_json,
            "success_count": 1,
            "created_at":    time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_used":     time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._skills[skill_id] = skill
        self._save()
        # 更新 Level 0 索引（无需重建全部）
        self._index[skill_id] = {
            "id":            skill_id,
            "name":          skill_name,
            "description":   task_desc[:L0_DESC_CHARS],
            "keywords":      keywords,
            "success_count": 1,
            "last_used":     skill["last_used"],
        }
        print(f"✨ [SkillLib] 技能已封装：{skill_name}（含任务图：{graph_json is not None}）")
        return skill

    # ── 更新使用统计 ─────────────────────────────────────────

    def update_usage(self, skill_id: str):
        if skill_id in self._skills:
            self._skills[skill_id]["success_count"] = \
                self._skills[skill_id].get("success_count", 0) + 1
            self._skills[skill_id]["last_used"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save()
            # 同步更新索引
            if skill_id in self._index:
                self._index[skill_id]["success_count"] = self._skills[skill_id]["success_count"]
                self._index[skill_id]["last_used"]     = self._skills[skill_id]["last_used"]

    # ── 兼容旧接口 ────────────────────────────────────────────

    def list_skills(self) -> list:
        """兼容旧接口：返回完整技能列表（含 graph_json）。"""
        return sorted(self._skills.values(),
                      key=lambda s: s.get("success_count", 0), reverse=True)

    def delete_skill(self, skill_id: str) -> bool:
        if skill_id in self._skills:
            del self._skills[skill_id]
            self._index.pop(skill_id, None)
            self._save()
            return True
        return False

    def discover_agents(self, llm_client=None) -> dict:
        discovered = {}
        if not os.path.exists(AGENTS_DIR):
            return discovered
        for name in os.listdir(AGENTS_DIR):
            agent_file = os.path.join(AGENTS_DIR, name, "agent.py")
            if not os.path.exists(agent_file):
                continue
            try:
                module    = importlib.import_module(f"agents.{name}.agent")
                agent_cls = next((getattr(module, a) for a in dir(module)
                                  if a.endswith("Agent") and isinstance(getattr(module, a), type)), None)
                if not agent_cls:
                    continue
                sig      = inspect.signature(agent_cls.__init__)
                params   = list(sig.parameters.keys())
                instance = agent_cls(llm_client) if len(params) > 1 and llm_client else agent_cls()
                discovered[name] = instance
            except Exception as e:
                print(f"⚠️  [SkillLib] 跳过 {name}: {e}")
        return discovered