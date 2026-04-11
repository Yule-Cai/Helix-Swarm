"""
DebuggerAgent — 深度调试专家（闭环修复版）
改进：
  1. 直接读源码 + 报错，输出修复后完整文件并写盘，形成真正闭环
  2. token 降级重试，避免本地模型超时
  3. 写盘成功后返回 ✅ 标记，让 executor 识别为成功，跳过重复 coder 步骤
"""
from __future__ import annotations
import os
import re
import glob

_TOKEN_LADDER = [3000, 2048, 1024]

class DebuggerAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        code_ctx = self._collect_relevant_files(instruction, workspace_dir)

        augmented = (
            f"{instruction}\n\n【相关源码（请基于此直接输出修复后的完整文件）】\n{code_ctx}"
        ) if code_ctx else instruction

        analysis = ""
        for max_tok in _TOKEN_LADDER:
            analysis = self.llm.chat(
                "你是资深调试专家。\n"
                "任务：\n"
                "1. 用1-2句话说明报错根因。\n"
                "2. 输出修复后的完整代码（必须），格式：\n"
                "<file path=\"文件名\">\n修复后的完整代码\n</file>\n"
                "不要省略任何代码，必须输出完整可运行的文件。",
                augmented,
                temperature=0.2,
                max_tokens=max_tok,
            )
            if analysis and analysis.strip():
                break
            print(f"⚠️  [Debugger] max_tokens={max_tok} 无响应，降级重试…")

        if not analysis:
            return "❌ 调试分析失败（LLM 无响应）"

        saved = self._write_fixed_files(analysis, workspace_dir)

        if saved:
            # 提取分析说明（<file> 标签之前的文字）
            explanation = re.sub(r'<file\s+path=.*', '', analysis, flags=re.DOTALL).strip()
            explanation = explanation[:300] if explanation else "（见修复内容）"
            return (
                f"✅ 已修复并写回：{', '.join(saved)}\n"
                f"🔍 根因：{explanation}"
            )
        else:
            # 没有提取到文件，只返回分析文字，让 executor 继续走 coder
            return f"🔍 调试分析（未自动修复，需 Coder 处理）：\n{analysis[:800]}"

    def _collect_relevant_files(self, instruction: str, workspace_dir: str) -> str:
        parts = []
        mentioned = re.findall(r'([\w/\\.\\-]+\.py)', instruction)
        found_paths = []
        for fname in mentioned:
            for base in [workspace_dir, "."]:
                full = os.path.join(base, fname.replace("\\", "/"))
                if os.path.exists(full):
                    found_paths.append(full)
                    break

        if not found_paths:
            py_files = glob.glob(os.path.join(workspace_dir, "**", "*.py"), recursive=True)
            py_files = [f for f in py_files if "__pycache__" not in f]
            py_files.sort(key=os.path.getmtime, reverse=True)
            found_paths = py_files[:2]   # 最多2个文件，节省 context

        for full in found_paths:
            rel = os.path.relpath(full, workspace_dir)
            try:
                content = open(full, encoding="utf-8", errors="replace").read()
                parts.append(f"--- {rel} ---\n```python\n{content[:2000]}\n```")
            except Exception:
                pass
        return "\n\n".join(parts)

    def _write_fixed_files(self, text: str, workspace_dir: str) -> list[str]:
        saved = []
        # 正常闭合
        for path, content in re.findall(
            r'<file\s+path="([^"]+)">\s*(.*?)\s*</file>', text, re.DOTALL
        ):
            s = self._write_one(path, content, workspace_dir)
            if s: saved.append(s)

        # 未闭合（截断）
        if not saved:
            m = re.search(r'<file\s+path="([^"]+)">\s*(.*)', text, re.DOTALL)
            if m:
                content = re.sub(r'\s*</file>.*$', '', m.group(2), flags=re.DOTALL)
                s = self._write_one(m.group(1), content, workspace_dir)
                if s: saved.append(s)
        return saved

    def _write_one(self, path: str, content: str, workspace_dir: str):
        safe = os.path.normpath(path.lstrip("/\\"))
        if safe.startswith("..") or os.path.isabs(safe):
            return None
        # 清洗 markdown 残片
        content = re.sub(r'^\s*```[a-z]*\s*\n', '', content)
        content = re.sub(r'\n\s*```\s*$', '', content.rstrip())
        if not content.strip():
            return None
        full = os.path.join(workspace_dir, safe)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        return safe