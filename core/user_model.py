"""
UserModel — Honcho 式用户建模
记录用户的偏好、习惯、技术栈，并注入到 Agent 的 system prompt 头部。

设计原则（参考 Honcho dialectic 模型）：
  - 从对话中自动提炼用户画像，不需要用户主动填写
  - 每次任务后 LLM 更新画像（辩证式：新信息可修正旧判断）
  - 注入 prompt 时只用一小段紧凑文字，不浪费 token
  - 本地 JSON 存储，无需数据库

数据结构：
  user_model.json
  {
    "language": "zh",              # 偏好语言
    "tech_stack": ["python","flask"],  # 常用技术
    "style": "简洁直接",           # 沟通风格
    "preferences": ["不喜欢注释过多", "喜欢先看示例"],
    "expertise": "中级",           # 技术水平：初级/中级/高级
    "patterns": ["常做游戏项目", "偏好 CLI 工具"],
    "updated_at": "..."
  }
"""
from __future__ import annotations
import os, json, time

BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_MODEL_FILE = os.path.join(BASE_DIR, "user_model.json")

# 每次注入 prompt 的最大字符数（控制 token 消耗）
MAX_INJECT_CHARS = 300


class UserModel:
    """
    用户偏好建模器。
    用法：
        um = UserModel(llm_client)
        context = um.inject()                     # 注入 agent prompt
        um.update(user_message, agent_response)   # 每轮对话后更新
    """

    def __init__(self, llm_client=None):
        self.llm   = llm_client
        self._data = self._load()

    # ── 持久化 ────────────────────────────────────────────────

    def _load(self) -> dict:
        if not os.path.exists(USER_MODEL_FILE):
            return self._default()
        try:
            with open(USER_MODEL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return self._default()

    def _save(self):
        self._data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(USER_MODEL_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _default(self) -> dict:
        return {
            "language":    "zh",
            "tech_stack":  [],
            "style":       "未知",
            "preferences": [],
            "expertise":   "未知",
            "patterns":    [],
            "updated_at":  "",
        }

    # ── 注入 Prompt ──────────────────────────────────────────

    def inject(self) -> str:
        """
        返回适合插入 Agent system prompt 头部的用户画像文本。
        格式紧凑，尽量控制在 300 字符以内。
        """
        d = self._data
        parts = []

        if d.get("expertise") and d["expertise"] != "未知":
            parts.append(f"技术水平：{d['expertise']}")

        if d.get("tech_stack"):
            parts.append("常用技术：" + "、".join(d["tech_stack"][:5]))

        if d.get("style") and d["style"] != "未知":
            parts.append(f"沟通风格：{d['style']}")

        if d.get("preferences"):
            parts.append("偏好：" + "；".join(d["preferences"][:3]))

        if d.get("patterns"):
            parts.append("习惯：" + "；".join(d["patterns"][:2]))

        if not parts:
            return ""

        text = "【用户画像】\n" + "\n".join(f"- {p}" for p in parts)
        return text[:MAX_INJECT_CHARS]

    # ── 更新（每轮对话或任务完成后调用）────────────────────────

    def update_from_conversation(self, user_msg: str, agent_response: str = ""):
        """
        从单轮对话轻量提炼用户偏好（规则优先，降低 LLM 调用频率）。
        """
        # 规则提炼：技术栈关键词
        tech_keywords = {
            "python", "flask", "django", "fastapi", "pytorch", "tensorflow",
            "react", "vue", "javascript", "typescript", "nodejs", "rust",
            "golang", "java", "docker", "kubernetes", "postgresql", "mongodb",
            "sqlite", "redis", "pygame", "openai", "langchain",
        }
        msg_lower = user_msg.lower()
        for kw in tech_keywords:
            if kw in msg_lower and kw not in self._data["tech_stack"]:
                self._data["tech_stack"].append(kw)
                # 最多保留 10 个
                self._data["tech_stack"] = self._data["tech_stack"][-10:]

        # 语言偏好
        chinese_chars = sum(1 for c in user_msg if '\u4e00' <= c <= '\u9fff')
        if chinese_chars > len(user_msg) * 0.3:
            self._data["language"] = "zh"
        elif len(user_msg) > 20 and chinese_chars == 0:
            self._data["language"] = "en"

        self._save()

    def update_from_task(self, goal: str, task_types: list[str], success: bool):
        """
        从任务执行结果提炼习惯模式（LLM 辅助，每次任务后调用）。
        task_types: 本次任务用到的 agent 列表，如 ['coder','tester','pygame']
        """
        if not self.llm:
            return

        existing_patterns = self._data.get("patterns", [])
        existing_prefs    = self._data.get("preferences", [])

        prompt = (
            f"用户请求：{goal[:200]}\n"
            f"涉及技术：{', '.join(task_types)}\n"
            f"执行结果：{'成功' if success else '失败'}\n"
            f"已有习惯模式：{'; '.join(existing_patterns[:5]) or '无'}\n\n"
            "请分析这次请求，输出 JSON：\n"
            "{\n"
            "  \"new_pattern\": \"一句话描述发现的新习惯（如无新发现则为空字符串）\",\n"
            "  \"expertise\": \"初级|中级|高级（根据请求判断，无法判断则为空字符串）\",\n"
            "  \"style\": \"用户沟通风格（简洁直接|详细解释|喜欢示例|无法判断）\"\n"
            "}"
        )

        try:
            result = self.llm.json_call(
                system="你是用户行为分析专家，从任务信息中提炼用户习惯。只输出 JSON，不解释。",
                user=prompt,
                temperature=0.1,
                max_tokens=150,
            )
            if not result:
                return

            if result.get("new_pattern"):
                pattern = result["new_pattern"].strip()
                if pattern and pattern not in existing_patterns:
                    self._data["patterns"].append(pattern)
                    self._data["patterns"] = self._data["patterns"][-8:]

            if result.get("expertise") and result["expertise"] in ("初级", "中级", "高级"):
                self._data["expertise"] = result["expertise"]

            if result.get("style") and result["style"] != "无法判断":
                self._data["style"] = result["style"]

            self._save()
        except Exception as e:
            print(f"⚠️  [UserModel] update_from_task 失败: {e}")

    # ── 手动管理 ─────────────────────────────────────────────

    def add_preference(self, pref: str):
        """手动添加用户偏好（如用户明确告知）。"""
        if pref and pref not in self._data["preferences"]:
            self._data["preferences"].append(pref)
            self._data["preferences"] = self._data["preferences"][-10:]
            self._save()

    def get_summary(self) -> dict:
        """返回完整用户画像（供 Web UI 展示）。"""
        return dict(self._data)

    def reset(self):
        """重置用户画像。"""
        self._data = self._default()
        self._save()
