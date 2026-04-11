"""
CoderAgent — 代码编写员
修复：
  1. <file path="..."> 未闭合时（LLM 截断），仍能提取内容
  2. 无文件名时从指令推断合理默认名
  3. 保存前清洗 markdown 代码栅栏（```），从源头防止后续 SyntaxError
  4. LLM 无响应时自动降低 max_tokens 重试（解决本地模型超时问题）
"""
from __future__ import annotations
import os
import re
import shutil

# 依次尝试的 token 上限，本地模型大 context 容易超时
_TOKEN_LADDER = [4096, 2048, 1024]

class CoderAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        os.makedirs(workspace_dir, exist_ok=True)

        resp = ""
        for max_tok in _TOKEN_LADDER:
            resp = self.llm.chat(
                "你是资深软件工程师。\n"
                "输出格式（二选一）：\n"
                "方式一：<file path=\"文件路径\">\n代码\n</file>\n"
                "方式二：```python\n代码\n```\n"
                "删除文件：<delete path=\"路径\"/>\n"
                "直接输出代码，不要任何解释。代码必须完整可运行。",
                instruction,
                temperature=0.5,
                max_tokens=max_tok,
            )
            if resp and resp.strip():
                break
            print(f"⚠️  [Coder] max_tokens={max_tok} 无响应，降级重试…")

        if not resp or not resp.strip():
            return "❌ Coder 无响应（LLM 连续超时）。请检查 LM Studio 是否正常运行，或尝试更简单的需求。"

        deleted = self._handle_deletes(resp, workspace_dir)
        saved   = self._handle_writes(resp, workspace_dir, instruction)
        if not saved and not deleted:
            return f"⚠️ 未提取到代码。原始输出：\n{resp[:400]}"
        parts = []
        if deleted: parts.append(f"🗑️ 已清理：{', '.join(deleted)}")
        if saved:   parts.append(f"✅ 已保存：{', '.join(saved)}")
        return "\n".join(parts)

    def _clean_code(self, code: str) -> str:
        code = re.sub(r'^\s*```[a-z]*\s*\n', '', code)
        code = re.sub(r'\n\s*```\s*$', '', code.rstrip())
        code = re.sub(r'^```\s*$', '', code, flags=re.MULTILINE)
        return code.strip() + "\n"

    def _safe_path(self, raw: str, base: str) -> str | None:
        safe = os.path.normpath(raw.lstrip("/\\"))
        if safe.startswith("..") or os.path.isabs(safe):
            return None
        return os.path.join(base, safe)

    def _handle_deletes(self, text: str, base: str) -> list:
        deleted = []
        for p in re.findall(r'<delete\s+path="([^"]+)"\s*/?>', text):
            full = self._safe_path(p, base)
            if not full:
                continue
            if os.path.isdir(full):
                shutil.rmtree(full); deleted.append(p + "/")
            elif os.path.isfile(full):
                os.remove(full); deleted.append(p)
        return deleted

    def _handle_writes(self, text: str, base: str, instruction: str = "") -> list:
        saved = []

        for p, content in re.findall(
            r'<file\s+path="([^"]+)">\s*(.*?)\s*</file>', text, re.DOTALL
        ):
            full = self._safe_path(p, base)
            if not full: continue
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(self._clean_code(content))
            saved.append(p)

        if not saved:
            m = re.search(r'<file\s+path="([^"]+)">\s*(.*)', text, re.DOTALL)
            if m:
                p       = m.group(1)
                content = re.sub(r'\s*</file>.*$', '', m.group(2), flags=re.DOTALL)
                full = self._safe_path(p, base)
                if full and content.strip():
                    os.makedirs(os.path.dirname(full), exist_ok=True)
                    with open(full, "w", encoding="utf-8") as f:
                        f.write(self._clean_code(content))
                    saved.append(p)

        if saved:
            return saved

        blocks = re.findall(r'```(?:python|py|js|html|css|bash)?\n(.*?)```', text, re.DOTALL)
        for i, code in enumerate(blocks):
            pm = re.search(
                r'([a-zA-Z0-9_\-]+[/\\][\w.\-]+\.(?:py|js|html|css|sh|md))', text
            ) or re.search(
                r'([\w\-]+\.(?:py|js|html|css|sh|md))', text
            )
            fname = pm.group(1).replace("\\", "/") if pm else self._infer_filename(instruction, i)
            full  = self._safe_path(fname, base)
            if not full: continue
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(self._clean_code(code))
            saved.append(fname)

        return saved

    def _infer_filename(self, instruction: str, idx: int = 0) -> str:
        kw_map = {
            ("猜数字", "guess", "number"):  "guess_number.py",
            ("贪吃蛇", "snake"):            "snake_game.py",
            ("扫雷", "minesweeper"):        "minesweeper.py",
            ("计算器", "calculator"):       "calculator.py",
            ("flask", "api", "接口"):       "app.py",
            ("爬虫", "scraper", "spider"):  "scraper.py",
            ("小说", "story", "writer"):    "story.py",
        }
        il = instruction.lower()
        for keys, name in kw_map.items():
            if any(k in il for k in keys):
                return name
        return f"output_{idx}.py"