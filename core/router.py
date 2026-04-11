"""Router — 请求分类器，三条路径：SYSTEM/CHAT/DEV"""
import re
from dataclasses import dataclass, field
from enum import Enum

class Intent(Enum):
    SYSTEM = "system"
    CHAT   = "chat"
    DEV    = "dev"

_SYSTEM_PATTERNS = [
    (r"(列出|查看|显示).*(技能|skill)",            "list_skills"),
    (r"(删除|移除).*(技能|skill)",                 "delete_skill"),
    (r"(查看|显示|列出).*(workspace|工作区|目录)",  "show_workspace"),
    (r"(查看|显示).*(历史|记录)",                  "show_history"),
    (r"(系统|system).*(状态|status|信息)",         "system_status"),
    (r"(错误|error).*(解决方案|记录)",              "error_solutions"),
    (r"(改进|优化).*(建议|分析|报告)",              "improve_report"),
    (r"学习.*(报告|进度|状态)",                    "learning_report"),
    (r"^(帮助|help|\?)$",                         "help"),
]

_CHAT_KEYWORDS = [
    "你好","你是谁","介绍","什么是","怎么样","如何理解","解释","为什么",
    "区别","比较","感谢","谢谢","hello","hi","what is","explain","why","thanks",
    # 图片/视觉相关 → 必须走 CHAT 才能传图片给 LLM
    "描述","看看","这张","这个图","这张图","这幅","图片","照片","截图","图中",
    "图里","画面","看这","分析图","识别","ocr","这是什么","图上","图片里",
    "describe","look at","this image","this photo","what's in",
]

_DEV_KEYWORDS = [
    "写","创建","开发","做","实现","生成","编写","构建","搭建","制作",
    "write","create","build","make","implement","develop","generate",
    "游戏","程序","脚本","项目","api","app","bot","小说","故事","工具",
]

@dataclass
class RouteResult:
    intent:  Intent
    action:  str = ""
    payload: str = ""

class Router:
    def __init__(self, llm_client=None):
        self.llm = llm_client

    def route(self, text: str, has_images: bool = False) -> RouteResult:
        """
        has_images: 本次请求是否附带图片。
        有图片时，除非明确是 DEV 开发任务，否则强制走 CHAT 让 LLM 直接看图。
        """
        t  = text.strip()
        tl = t.lower()

        # 1. SYSTEM 精确规则（图片不影响系统查询）
        for pattern, action in _SYSTEM_PATTERNS:
            if re.search(pattern, t, re.IGNORECASE):
                return RouteResult(Intent.SYSTEM, action=action, payload=t)

        # 2. 有图片且不是明确的开发任务 → 强制 CHAT，让 LLM 直接看图回答
        if has_images:
            is_dev = any(kw in tl for kw in _DEV_KEYWORDS)
            if not is_dev:
                return RouteResult(Intent.CHAT, payload=t)

        # 3. CHAT 关键词
        if any(kw in tl for kw in _CHAT_KEYWORDS):
            return RouteResult(Intent.CHAT, payload=t)

        # 4. DEV 关键词
        if any(kw in tl for kw in _DEV_KEYWORDS):
            return RouteResult(Intent.DEV, payload=t)

        # 5. LLM 兜底
        if self.llm:
            res = self.llm.json_call(
                "你是分类器。将输入分类：SYSTEM=查询系统状态，CHAT=问答闲聊，DEV=开发创作。只输出JSON：{\"intent\":\"SYSTEM\"|\"CHAT\"|\"DEV\"}",
                t, temperature=0.0, max_tokens=20,
            )
            s = res.get("intent","DEV").upper()
            if s == "SYSTEM": return RouteResult(Intent.SYSTEM, action="general", payload=t)
            if s == "CHAT":   return RouteResult(Intent.CHAT, payload=t)

        # 6. 默认 DEV
        return RouteResult(Intent.DEV, payload=t)