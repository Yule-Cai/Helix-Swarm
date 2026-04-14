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
_TOKEN_LADDER = [2000, 1200, 600]

class CoderAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        os.makedirs(workspace_dir, exist_ok=True)

        resp = ""
        for max_tok in _TOKEN_LADDER:
            resp = self.llm.chat(
                "You are a senior software engineer.\n"
                "Output format (choose one):\n"
                "Option 1: <file path=\"filepath\">\ncode\n</file>\n"
                "Option 2: ```python\ncode\n```\n"
                "Delete file: <delete path=\"path\"/>\n"
                "Output code only, no explanations. Code must be complete and runnable.",
                instruction,
                temperature=0.5,
                max_tokens=max_tok,
            )
            if resp and resp.strip():
                break
            print(f"⚠️  [Coder] max_tokens={max_tok} no response, retrying with lower limit…")

        if not resp or not resp.strip():
            return "❌ Coder got no response (LLM timeout). Please check LM Studio is running, or try a simpler request."

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
            code_clean = self._clean_code(code)
            if not code_clean.strip():
                continue

            # Python 代码不能保存为 .html 文件（Flask 模板名被误识别的问题）
            is_python = any(kw in code_clean for kw in [
                'import ', 'def ', 'class ', 'from ', 'if __name__', 'print('
            ])

            pm = re.search(
                r'([a-zA-Z0-9_\-]+[/\\][\w.\-]+\.(?:py|js|html|css|sh|md))', text
            ) or re.search(
                r'([\w\-]+\.(?:py|js|html|css|sh|md))', text
            )
            if pm:
                candidate = pm.group(1).replace("\\", "/")
                stem = candidate.rsplit('.', 1)[0].rsplit('/', 1)[-1].lower()
                # Python 代码块不能用 .html/.css 文件名
                # 也不能用黑名单里的通用词作文件名
                if is_python and candidate.endswith(('.html', '.css')):
                    fname = self._infer_filename(instruction, i)
                elif stem in self._FILENAME_BLACKLIST:
                    fname = self._infer_filename(instruction, i)
                else:
                    fname = candidate
            else:
                fname = self._infer_filename(instruction, i)

            full = self._safe_path(fname, base)
            if not full: continue
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(code_clean)
            saved.append(fname)

        return saved

    # 不能作为文件名的通用词（会被误识别）
    _FILENAME_BLACKLIST = {
        "response", "output", "result", "data", "main",
        "index", "test", "temp", "tmp", "file", "code",
        "module", "script", "program", "example", "demo",
    }

    def _infer_filename(self, instruction: str, idx: int = 0) -> str:
        kw_map = {
            ("猜数字", "guess", "number"):              "guess_number.py",
            ("贪吃蛇", "snake"):                        "snake_game.py",
            ("扫雷", "minesweeper"):                    "minesweeper.py",
            ("计算器", "calculator"):                   "calculator.py",
            ("flask", "web app", "接口"):               "app.py",
            ("学生", "student", "管理系统", "sms"):     "app.py",
            ("爬虫", "scraper", "spider", "crawl"):     "scraper.py",
            ("trending", "github scraper", "github.*repo"): "github_scraper.py",
            ("小说", "story", "writer"):                "story.py",
            ("pygame", "tetris", "俄罗斯方块"):         "game.py",
            ("游戏", "game"):                           "game.py",
            ("数独", "sudoku"):                         "sudoku.py",
            ("todo", "task manager"):                   "app.py",
        }
        il = instruction.lower()
        for keys, name in kw_map.items():
            if any(k in il for k in keys):
                return name
        return f"output_{idx}.py"