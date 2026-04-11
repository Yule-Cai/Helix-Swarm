"""
DocAgent — 技术文档生成专家
修复：
  1. 先读取 workspace_dir 里的实际源码，再生成有针对性的 README.md
  2. LLM 无响应时降低 max_tokens 重试
"""
from __future__ import annotations
import os
import re

_TOKEN_LADDER = [2048, 1024, 512]

class DocAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        code_summary = self._collect_code(workspace_dir)
        augmented = (
            f"{instruction}\n\n"
            f"【项目源码参考（请基于此生成真实可用的文档）】\n{code_summary}"
        ) if code_summary else instruction

        content = ""
        for max_tok in _TOKEN_LADDER:
            content = self.llm.chat(
                "你是技术文档专家。根据提供的项目源码，生成一份完整的 README.md。\n"
                "包含：项目简介、功能特性、安装依赖、运行方法（含示例）、注意事项。\n"
                "语言：中文。格式：标准 Markdown。直接输出文档内容，不要额外解释。",
                augmented,
                temperature=0.4,
                max_tokens=max_tok,
            )
            if content and content.strip():
                break
            print(f"⚠️  [Doc] max_tokens={max_tok} 无响应，降级重试…")

        if not content:
            return "❌ 文档生成失败（LLM 无响应）"

        content = re.sub(r'^```(?:markdown|md)?\n', '', content.strip())
        content = re.sub(r'\n```$', '', content.strip())

        readme_path = os.path.join(workspace_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"✅ README.md 已生成\n\n{content[:600]}…"

    def _collect_code(self, workspace_dir: str) -> str:
        skip_dirs = {"__pycache__", ".git", "node_modules", ".venv"}
        parts = []
        total_chars = 0
        MAX_TOTAL = 6000

        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                if ext not in {".py", ".js", ".ts", ".sh", ".yaml", ".toml"}:
                    continue
                full = os.path.join(root, fname)
                rel  = os.path.relpath(full, workspace_dir)
                try:
                    content = open(full, encoding="utf-8", errors="replace").read()
                    snippet = content[:2000]
                    block = f"--- {rel} ---\n```python\n{snippet}\n```"
                    if total_chars + len(block) > MAX_TOTAL:
                        break
                    parts.append(block)
                    total_chars += len(block)
                except Exception:
                    pass

        return "\n\n".join(parts)