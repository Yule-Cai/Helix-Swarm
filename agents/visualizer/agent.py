import os
import subprocess
import re

class VisualizerAgent:
    """架构画图师。负责将文本逻辑转换为专业的 Mermaid 流程图或架构图。"""
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def run(self, instruction):
        print(f"📊 [Visualizer Agent] 正在绘制架构图...")
        
        # 🟢 修复 1：尝试从经理的指令中提取带沙箱前缀的文件路径
        match = re.search(r'([a-zA-Z0-9_-]+/[\w.-]+\.(?:png|svg|md|mmd))', instruction)
        if not match:
            match = re.search(r'([\w.-]+\.(?:png|svg|md|mmd))', instruction)

        # 如果都没找到，默认起个名字
        filename = match.group(1) if match else "architecture_diagram.png"
        
        # 强制替换后缀为 png 以便 mmdc 渲染
        filename = re.sub(r'\.(md|txt|mmd)$', '.png', filename)
        
        output_path = os.path.join("workspace", filename)
        mmd_path = output_path.replace(".png", ".mmd")
        
        # 确保沙箱子目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 1. 让 LLM 生成 Mermaid 源码
        prompt = f"""你是一个资深的系统架构师。
请根据以下需求，编写一段 Mermaid.js 源码。
要求：
- 使用简洁的流程图 (graph TD) 或时序图 (sequenceDiagram)。
- 仅输出代码块，不要任何解释。
需求内容：{instruction}"""

        mermaid_code = self.llm_client.chat("你是一个绘图机器。", prompt, temperature=0.2)
        
        # 清理可能存在的 Markdown 标记
        mermaid_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()

        # 2. 将源码写入沙箱文件
        with open(mmd_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)

        # 3. 调用 Mermaid CLI 进行渲染
        try:
            # 🟢 修复 2：终极防崩溃环境注入，防止 Windows GBK 报错
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            subprocess.run(
                f"mmdc -i {mmd_path} -o {output_path} -b transparent", 
                shell=True, check=True, capture_output=True,
                text=True, encoding='utf-8', errors='replace', env=env
            )
            return f"✅ 架构图已绘制成功，保存至: {filename}"
        except Exception as e:
            return f"❌ 渲染失败。请确认是否全局安装了 @mermaid-js/mermaid-cli (在终端运行 npm install -g @mermaid-js/mermaid-cli)。错误信息: {str(e)}"