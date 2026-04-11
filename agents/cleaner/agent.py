import os, shutil, re

class CleanerAgent:
    def __init__(self, llm_client=None):
        pass

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        cleaned = []
        # 从指令中提取要删除的路径
        targets = re.findall(r'删除[：:]\s*([^\n，,]+)', instruction)
        for t in targets:
            t = t.strip()
            full = os.path.join(workspace_dir, t.lstrip("/\\"))
            if os.path.isdir(full):
                shutil.rmtree(full); cleaned.append(t+"/")
            elif os.path.isfile(full):
                os.remove(full); cleaned.append(t)
        if cleaned:
            return f"🗑️ 已清理：{', '.join(cleaned)}"
        return "✅ 工作区无需清理（或未指定清理目标）"
