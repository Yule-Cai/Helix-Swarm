# agents/pluginagent/agent.py
import subprocess
import json

class GitHubSkillAgent:
    """万能插件特工。用于包装第三方 GitHub 开源项目或独立脚本。"""
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def run(self, instruction):
        print(f"🧩 [Plugin Agent] 正在调用外部技能...")
        
        # 1. 假设我们在 workspace 下 clone 了一个火爆的开源项目 "awesome_github_tool"
        # 我们需要让大模型把自然语言指令，解析成该工具需要的 JSON 参数或命令行参数
        parse_prompt = f"请将用户需求转换为 awesome_github_tool 需要的搜索关键词。需求：{instruction}"
        parsed_args = self.llm_client.chat("参数解析器", parse_prompt, temperature=0.1).strip()
        
        try:
            # 2. 通过子进程调用该 GitHub 项目的入口脚本
            result = subprocess.run(
                f"python awesome_github_tool/main.py --query '{parsed_args}'", 
                shell=True, 
                capture_output=True, 
                text=True,
                cwd="workspace"
            )
            
            # 3. 拦截结果并返回给 Manager
            if result.returncode == 0:
                return f"✅ 外部技能执行成功！\n返回数据: {result.stdout[:1000]}"
            else:
                return f"❌ 外部技能执行报错: {result.stderr}"
                
        except Exception as e:
            return f"❌ 插件系统崩溃: {str(e)}"