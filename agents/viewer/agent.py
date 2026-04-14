"""
ViewerAgent — 工作区查看器
升级：除了目录结构，现在也能读取文件内容。
当指令里提到具体文件名时，自动读取并展示内容。
"""
import os
import re
import glob

# 可读取的文件类型
_READABLE_EXTS = {'.py', '.js', '.ts', '.html', '.css', '.json',
                  '.md', '.txt', '.yaml', '.yml', '.toml', '.ini',
                  '.sh', '.bat', '.csv', '.sql'}
# 单文件最大读取字符数
_MAX_FILE_CHARS = 3000


class ViewerAgent:
    def __init__(self, llm_client=None):
        pass

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        base = workspace_dir if os.path.exists(workspace_dir) else "workspace"

        # 检查指令里是否提到具体文件名
        file_targets = self._extract_filenames(instruction)

        parts = []

        # 1. 目录树
        parts.append("📁 目录结构：\n" + self._tree(base))

        # 2. 读取指定文件内容
        for fname in file_targets:
            content = self._read_file(fname, base)
            if content:
                parts.append(content)

        # 3. 如果没有指定文件但指令里有"读取"/"查看"/"内容"等关键词，
        #    自动读取最近修改的 .py 文件
        if not file_targets and any(kw in instruction.lower() for kw in
                                    ['read', 'view', 'content', '读取', '查看', '内容', '代码']):
            py_files = sorted(
                glob.glob(os.path.join(base, '**', '*.py'), recursive=True),
                key=os.path.getmtime, reverse=True
            )[:2]  # 最近修改的2个
            for f in py_files:
                content = self._read_file(f, base, full_path=True)
                if content:
                    parts.append(content)

        return "\n\n".join(parts)

    def _extract_filenames(self, instruction: str) -> list[str]:
        """从指令里提取文件名。"""
        # 匹配 xxx.py / path/to/xxx.py 等
        matches = re.findall(r'[\w/\-]+\.(?:py|js|html|css|json|md|txt|yaml|yml)', instruction)
        return list(dict.fromkeys(matches))  # 去重保序

    def _read_file(self, fname: str, base: str, full_path: bool = False) -> str:
        """读取文件内容，返回格式化字符串。"""
        if full_path:
            path = fname
        else:
            # 搜索文件
            candidates = glob.glob(os.path.join(base, '**', fname), recursive=True)
            if not candidates:
                candidates = [os.path.join(base, fname)]
            path = candidates[0] if candidates else os.path.join(base, fname)

        if not os.path.exists(path):
            return ""

        ext = os.path.splitext(path)[1].lower()
        if ext not in _READABLE_EXTS:
            return ""

        try:
            with open(path, encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            return f"⚠️ 无法读取 {os.path.basename(path)}: {e}"

        rel = os.path.relpath(path, base) if not full_path else os.path.relpath(path, base)
        lines = content.splitlines()
        line_count = len(lines)

        # 截断过长文件
        if len(content) > _MAX_FILE_CHARS:
            content = content[:_MAX_FILE_CHARS] + f"\n... (截断，共 {line_count} 行)"

        # 加行号（方便定位语法错误）
        numbered = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines[:100]))
        if line_count > 100:
            numbered += f"\n     ... (共 {line_count} 行，只显示前100行)"

        return f"📄 {rel} ({line_count} 行):\n```\n{numbered}\n```"

    def _tree(self, path, prefix=""):
        if not os.path.exists(path):
            return "(空)"
        result = ""
        items = sorted(i for i in os.listdir(path)
                       if not i.startswith('.') and i not in ('__pycache__',))
        for i, item in enumerate(items):
            last = i == len(items) - 1
            conn = "└── " if last else "├── "
            result += f"{prefix}{conn}{item}\n"
            full = os.path.join(path, item)
            if os.path.isdir(full):
                result += self._tree(full, prefix + ("    " if last else "│   "))
        return result or "(空)"