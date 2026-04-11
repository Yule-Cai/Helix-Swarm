import urllib.request, re

class BrowserAgent:
    def __init__(self, llm_client=None):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        url_match = re.search(r'https?://\S+', instruction)
        if not url_match:
            return "❌ 未找到 URL，请在指令中提供完整网址。"
        url = url_match.group(0)
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                html = r.read().decode("utf-8","ignore")
            # 简单提取正文文本
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()[:3000]
            if self.llm:
                summary = self.llm.chat(
                    "从网页内容中提取与任务相关的有用信息，简洁输出。",
                    f"任务：{instruction}\n网页内容：{text}", temperature=0.3, max_tokens=512
                )
                return f"🌐 网页摘要：\n{summary}"
            return f"🌐 网页内容：\n{text[:1000]}"
        except Exception as e:
            return f"❌ 抓取失败：{e}"
