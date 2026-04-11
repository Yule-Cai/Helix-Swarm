"""
SearcherAgent — GitHub 搜索（仓库 + README 内容抓取）
修复：
  1. 不依赖 /search/code（需要 Token），改为抓取 README 内容
  2. README 内容按段落切分，每段以 📄 标记，让 LearningScheduler 正确计数
  3. 无 Token 时完全可用（只是仓库数量限制较低）
"""
from __future__ import annotations
import re
import json
import os
import urllib.request
import urllib.parse
import base64

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
            # 403 on /search/code without token is expected — don't flag rate limit
            if "401" in err:
                self._rate_limited = True
            return None

    # ── 关键词提取 ────────────────────────────────────────────
    def _keywords(self, text: str) -> str:
        stops = ["请", "帮我", "搜索", "查找", "关于", "如何", "实现", "的", "和", "与"]
        for s in stops:
            text = text.replace(s, " ")
        tokens = re.findall(r'[a-zA-Z0-9_\-\.]+|[\u4e00-\u9fff]+', text)
        return " ".join(t for t in tokens if len(t) > 1)[:100]

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

    # ── 抓取仓库 README（无需 Token）────────────────────────
    def _fetch_readme(self, full_name: str) -> str:
        """
        通过 GitHub API 获取仓库 README 内容（base64 解码）。
        无需 Token，每个仓库独立请求，失败时跳过。
        """
        url = f"https://api.github.com/repos/{full_name}/readme"
        data = self._get(url, timeout=10)
        if not data or "content" not in data:
            return ""
        try:
            # GitHub API 返回 base64 编码的内容
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            # 截取前 2000 字符，避免超大 README
            return content[:2000].strip()
        except Exception:
            return ""

    # ── 主入口 ────────────────────────────────────────────────
    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        kw = self._keywords(instruction)
        report_lines = [f"🔍 GitHub搜索：{kw}\n"]

        # 1. 搜索仓库
        repos = self._search_repos(kw, per_page=5)
        if not repos:
            report_lines.append("⚠️ 仓库搜索失败（可能是API限流）")
            return "\n".join(report_lines)

        for repo in repos:
            desc  = (repo.get("description") or "")[:80]
            stars = repo.get("stargazers_count", 0)
            name  = repo.get("full_name", "")
            report_lines.append(f"⭐{stars} {name} — {desc}")

        # 2. 抓取每个仓库的 README，切分为段落，每段标记 📄
        readme_sections = []
        for repo in repos[:3]:   # 最多抓 3 个 README，控制时间
            name = repo.get("full_name", "")
            readme = self._fetch_readme(name)
            if not readme:
                continue
            # 按段落切分（空行分隔），每段作为一个 📄 代码/文档片段
            paragraphs = [p.strip() for p in re.split(r'\n{2,}', readme) if p.strip()]
            for i, para in enumerate(paragraphs[:5]):  # 每个 README 最多取 5 段
                # 去掉 markdown 图片和徽章，保留文字
                para_clean = re.sub(r'!\[.*?\]\(.*?\)', '', para)
                para_clean = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', para_clean).strip()
                if len(para_clean) < 20:    # 跳过太短的段落（如纯图片行）
                    continue
                readme_sections.append(f"📄 [{name} README段落{i+1}]\n{para_clean[:400]}")

        if readme_sections:
            report_lines.append(f"\n📂 README 内容摘录（共 {len(readme_sections)} 段）：")
            report_lines.extend(readme_sections)
        else:
            report_lines.append("\n💡 未获取到 README 内容（仓库可能无 README）")

        raw = "\n\n".join(report_lines)

        # 3. LLM 提炼摘要
        if self.llm and repos:
            try:
                summary = self.llm.chat(
                    "从GitHub仓库信息和README中提炼与需求相关的技术要点"
                    "（核心概念、关键API、代码结构、最佳实践），简洁实用，中文输出。",
                    f"需求：{instruction}\n\n搜索结果：{raw[:3000]}",
                    temperature=0.3,
                    max_tokens=512,
                )
                return raw + f"\n\n💡 技术摘要：\n{summary}"
            except Exception:
                pass

        return raw