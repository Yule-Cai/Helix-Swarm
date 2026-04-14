"""
SearcherAgent — GitHub 搜索（仓库 + README 内容抓取）
修复：
  1. 不依赖 /search/code（需要 Token），改为抓取 README 内容
  2. README 内容按段落切分，每段以 📄 标记，让 LearningScheduler 正确计数
  3. 无 Token 时完全可用（只是仓库数量限制较低）
  4. [新增] _keywords() 自动剥离 executor 拼入的上下文噪音（"前序结果参考…"）
  5. [新增] _get() 保留真实错误信息，不再统一显示"限流"
  6. [新增] LLM 辅助提取搜索关键词，避免中英混杂污染查询
"""
from __future__ import annotations
import re
import json
import os
import urllib.request
import urllib.parse
import base64

DESCRIPTION    = "GitHub search for API docs, error solutions, and code references"
DESCRIPTION_ZH = "GitHub 搜索：API 文档、报错解决方案、代码参考"

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config.json",
)


def _load_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return token
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("github_token", "")
    except Exception:
        return ""


class SearcherAgent:
    BASE_HEADERS = {
        "User-Agent": "Multi-Agent-OS/2.0",
        "Accept":     "application/vnd.github+json",
    }

    def __init__(self, llm_client=None):
        self.llm = llm_client
        self._rate_limited = False
        self._last_error   = ""

    def reset_rate_limit(self):
        self._rate_limited = False

    # ── HTTP 请求 ─────────────────────────────────────────────
    def _get_headers(self) -> dict:
        h = dict(self.BASE_HEADERS)
        t = _load_token()
        if t:
            h["Authorization"] = f"Bearer {t}"
        return h

    def _get(self, url: str, timeout: int = 15) -> dict | None:
        try:
            req = urllib.request.Request(url, headers=self._get_headers())
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            err = str(e)
            self._last_error = err
            if "401" in err or "403" in err:
                self._rate_limited = True
            return None

    # ── 关键词提取 ────────────────────────────────────────────
    # executor 会把前序任务结果拼到 instruction 尾部，格式固定为：
    #   "原始指令 前序结果参考 t0 结果 ..."  或
    #   "原始指令\n\n前序结果参考..."
    # 需要先把这部分噪音剥离，只保留真正的搜索意图。
    _CONTEXT_MARKERS = [
        "前序结果参考",
        "prior task result",
        "workspace result",
        "directory structure",
        "目录结构",
        "📁",
    ]

    def _strip_executor_context(self, text: str) -> str:
        """剥离 executor 拼入的前序任务上下文，只保留原始指令部分。"""
        for marker in self._CONTEXT_MARKERS:
            idx = text.find(marker)
            if idx > 20:           # marker 之前至少要有 20 个字符才算有效指令
                text = text[:idx]
        return text.strip()

    def _keywords(self, text: str) -> str:
        # 1. 先剥离上下文噪音
        text = self._strip_executor_context(text)

        # 2. LLM 提取（最准确）
        if self.llm and len(text) > 30:
            try:
                result = self.llm.chat(
                    "Extract 3-6 English search keywords from the following instruction for a GitHub code search. "
                    "Output keywords only, space-separated, no explanation. "
                    "Focus on technology names, library names, and task type. "
                    "Example output: flask sqlite rest api python",
                    text[:300],
                    temperature=0.0,
                    max_tokens=30,
                )
                kw = (result or "").strip().lower()
                # 只保留干净的英文关键词（过滤掉中文和奇怪字符）
                tokens = re.findall(r'[a-zA-Z0-9_\-]+', kw)
                if tokens and len(tokens) >= 2:
                    return " ".join(tokens[:6])
            except Exception:
                pass

        # 3. 规则 fallback：过滤中文噪音，只取英文部分
        stops = ["search", "find", "look", "for", "please", "help",
                 "请", "帮我", "搜索", "查找", "关于", "如何", "实现",
                 "的", "和", "与", "前序", "结果", "参考", "目录", "结构"]
        for s in stops:
            text = text.replace(s, " ")

        # 优先取英文 token（不含中文），再补充中文
        en_tokens = re.findall(r'[a-zA-Z][a-zA-Z0-9_\-]*', text)
        zh_tokens = re.findall(r'[\u4e00-\u9fff]{2,}', text)

        tokens = [t for t in en_tokens if len(t) > 1]
        if len(tokens) < 3:
            tokens += zh_tokens

        return " ".join(tokens[:8])[:100]

    # ── 仓库搜索 ─────────────────────────────────────────────
    def _search_repos(self, kw: str, per_page: int = 5) -> list[dict]:
        url = (
            f"https://api.github.com/search/repositories"
            f"?q={urllib.parse.quote(kw)}&sort=stars&per_page={per_page}"
        )
        data = self._get(url)
        if data and "items" in data:
            return data["items"]
        return []

    # ── 抓取仓库 README ──────────────────────────────────────
    def _fetch_readme(self, full_name: str) -> str:
        url  = f"https://api.github.com/repos/{full_name}/readme"
        data = self._get(url, timeout=10)
        if not data or "content" not in data:
            return ""
        try:
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return content[:2000].strip()
        except Exception:
            return ""

    # ── 主入口 ────────────────────────────────────────────────
    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        self._last_error = ""
        kw = self._keywords(instruction)
        report_lines = [f"🔍 GitHub搜索：{kw}\n"]

        if not kw.strip():
            return "⚠️ 无法提取有效搜索关键词，跳过搜索。"

        # 1. 搜索仓库
        repos = self._search_repos(kw, per_page=5)
        if not repos:
            reason = ""
            if self._last_error:
                # 显示真实错误，不再统一说"限流"
                if "403" in self._last_error or "rate" in self._last_error.lower():
                    reason = "GitHub API 限流，请在 config.json 中配置 github_token"
                elif "401" in self._last_error:
                    reason = "GitHub Token 无效"
                elif "timed out" in self._last_error.lower():
                    reason = "请求超时，请检查网络"
                else:
                    reason = f"请求失败：{self._last_error[:100]}"
            else:
                reason = f"关键词 '{kw}' 未找到相关仓库"
            report_lines.append(f"⚠️ 搜索无结果：{reason}")
            return "\n".join(report_lines)

        for repo in repos:
            desc  = (repo.get("description") or "")[:80]
            stars = repo.get("stargazers_count", 0)
            name  = repo.get("full_name", "")
            report_lines.append(f"⭐{stars} {name} — {desc}")

        # 2. 抓取 README
        readme_sections = []
        for repo in repos[:3]:
            name   = repo.get("full_name", "")
            readme = self._fetch_readme(name)
            if not readme:
                continue
            paragraphs = [p.strip() for p in re.split(r'\n{2,}', readme) if p.strip()]
            for i, para in enumerate(paragraphs[:5]):
                para_clean = re.sub(r'!\[.*?\]\(.*?\)', '', para)
                para_clean = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', para_clean).strip()
                if len(para_clean) < 20:
                    continue
                readme_sections.append(f"📄 [{name} README段落{i+1}]\n{para_clean[:400]}")

        if readme_sections:
            report_lines.append(f"\n📂 README 内容摘录（共 {len(readme_sections)} 段）：")
            report_lines.extend(readme_sections)
        else:
            report_lines.append("\n💡 未获取到 README 内容")

        raw = "\n\n".join(report_lines)

        # 3. LLM 提炼摘要
        if self.llm and repos:
            try:
                summary = self.llm.chat(
                    "从GitHub仓库信息和README中提炼与需求相关的技术要点"
                    "（核心概念、关键API、代码结构、最佳实践），简洁实用，中文输出。",
                    f"需求：{instruction[:200]}\n\n搜索结果：{raw[:3000]}",
                    temperature=0.3,
                    max_tokens=512,
                )
                return raw + f"\n\n💡 技术摘要：\n{summary}"
            except Exception:
                pass

        return raw