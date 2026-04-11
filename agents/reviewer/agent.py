"""
ReviewerAgent — 代码审查专家
修复：
  1. 先扫描 workspace_dir 读取源码，再交给 LLM 审查，并将改进后代码写回
  2. 只审查主要业务文件（跳过测试残留文件如 output_0.py / _test_runner_.py）
  3. token 降级重试，避免本地模型超时
"""
from __future__ import annotations
import os
import re
import glob

_TOKEN_LADDER = [3000, 2048, 1024]

# 跳过这些文件名模式（测试残留、临时文件）
_SKIP_PATTERNS = {"output_0.py", "output_1.py", "_test_runner_.py", "test_"}

class ReviewerAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        code_files = self._collect_files(workspace_dir)
        if not code_files:
            return "⏭️ 工作区无源码文件，跳过审查。"

        files_block = self._format_files(code_files)
        augmented = (
            f"{instruction}\n\n"
            f"【待审查的源码文件】\n{files_block}"
        )

        review = ""
        for max_tok in _TOKEN_LADDER:
            review = self.llm.chat(
                "你是资深代码审查专家。\n"
                "任务：\n"
                "1. 审查下方提供的所有源码文件。\n"
                "2. 指出最多5条具体问题（需引用代码行）。\n"
                "3. 输出改进后的完整代码，格式：\n"
                "<file path=\"文件名\">\n改进后的完整代码\n</file>\n"
                "4. 审查摘要放在代码块之前，简洁说明改了什么。",
                augmented,
                temperature=0.3,
                max_tokens=max_tok,
            )
            if review and review.strip():
                break
            print(f"⚠️  [Reviewer] max_tokens={max_tok} 无响应，降级重试…")

        if not review:
            return "⏭️ 代码审查跳过（LLM 无响应）"

        saved = self._write_improved_files(review, workspace_dir)
        saved_msg = f"\n✅ 已更新文件：{', '.join(saved)}" if saved else ""

        return f"📋 代码审查完成\n{saved_msg}"

    def _collect_files(self, workspace_dir: str) -> dict[str, str]:
        result = {}
        exts = {".py", ".js", ".ts", ".html", ".css", ".sh"}
        skip_dirs = {"__pycache__", ".git", "node_modules", ".venv", "venv"}

        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in sorted(files):
                # 跳过测试残留文件
                if any(pat in fname for pat in _SKIP_PATTERNS):
                    continue
                if os.path.splitext(fname)[1].lower() not in exts:
                    continue
                full = os.path.join(root, fname)
                rel  = os.path.relpath(full, workspace_dir)
                try:
                    content = open(full, encoding="utf-8", errors="replace").read()
                    if len(content) > 6000:
                        content = content[:6000] + "\n...(截断)"
                    result[rel] = content
                except Exception:
                    pass
        return result

    def _format_files(self, code_files: dict[str, str]) -> str:
        parts = []
        for path, content in code_files.items():
            parts.append(f"--- {path} ---\n```\n{content}\n```")
        return "\n\n".join(parts)

    def _write_improved_files(self, text: str, workspace_dir: str) -> list[str]:
        saved = []
        for path, content in re.findall(
            r'<file\s+path="([^"]+)">\s*(.*?)\s*</file>', text, re.DOTALL
        ):
            # 同样跳过测试残留文件名
            fname = os.path.basename(path)
            if any(pat in fname for pat in _SKIP_PATTERNS):
                continue
            safe = os.path.normpath(path.lstrip("/\\"))
            if safe.startswith("..") or os.path.isabs(safe):
                continue
            # 清洗 markdown 残片
            content = re.sub(r'^\s*```[a-z]*\s*\n', '', content)
            content = re.sub(r'\n\s*```\s*$', '', content.rstrip())
            if not content.strip():
                continue
            full = os.path.join(workspace_dir, safe)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content.strip() + "\n")
            saved.append(safe)
        return saved