import os

class ViewerAgent:
    def __init__(self, llm_client=None):
        pass

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        base = workspace_dir if os.path.exists(workspace_dir) else "workspace"
        return "📁 目录结构：\n" + self._tree(base)

    def _tree(self, path, prefix=""):
        if not os.path.exists(path): return "(空)"
        result = ""
        items  = sorted(i for i in os.listdir(path)
                       if not i.startswith('.') and i not in ('__pycache__',))
        for i, item in enumerate(items):
            last = i == len(items)-1
            conn = "└── " if last else "├── "
            result += f"{prefix}{conn}{item}\n"
            full = os.path.join(path, item)
            if os.path.isdir(full):
                result += self._tree(full, prefix+("    " if last else "│   "))
        return result or "(空)"
