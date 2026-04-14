import os

_TOKEN_LADDER = [2048, 1024, 512]

class WriterAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        content = ""
        for max_tok in _TOKEN_LADDER:
            content = self.llm.chat(
                "You are a professional writer. Create high-quality story/fiction content as requested — engaging prose, compelling plot."
                "字数控制在800字以内，确保故事完整有结尾。",
                instruction,
                temperature=0.8,
                max_tokens=max_tok,
            )
            if content and content.strip():
                break
            print(f"⚠️  [Writer] max_tokens={max_tok} 无响应，降级重试…")

        if content:
            os.makedirs(workspace_dir, exist_ok=True)
            path = os.path.join(workspace_dir, "story.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"✅ 创作完成，已保存到 story.md\n\n{content[:300]}…"
        return "❌ 创作失败（LLM 无响应）"