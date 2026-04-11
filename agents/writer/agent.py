import os

class WriterAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        content = self.llm.chat(
            "你是专业作家。根据要求创作高质量的故事/小说内容，文笔流畅，情节引人入胜。",
            instruction, temperature=0.8, max_tokens=4096
        )
        if content:
            os.makedirs(workspace_dir, exist_ok=True)
            path = os.path.join(workspace_dir, "story.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"✅ 创作完成，已保存到 story.md\n\n{content[:300]}…"
        return "❌ 创作失败"
