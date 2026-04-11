import asyncio
import json
import re
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPUniversalAgent:
    """
    万能 MCP 特工插座。
    通过传入不同的启动命令（如 npx 启动不同 server），将任何标准的 MCP Server 包装成我们系统的特工。
    """
    def __init__(self, llm_client, server_command, server_args):
        self.llm_client = llm_client
        # 启动 MCP Server 的命令，例如: "npx", ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"]
        self.server_command = server_command
        self.server_args = server_args

    def run(self, instruction):
        """由于我们的系统是同步的，而 MCP SDK 是全异步的，这里做一层同步包装"""
        return asyncio.run(self._async_run(instruction))

    async def _async_run(self, instruction):
        print(f"🔌 [MCP Agent] 正在连接 Server: {self.server_command} {' '.join(self.server_args)}")
        
        server_params = StdioServerParameters(
            command=self.server_command,
            args=self.server_args,
            env=None # 继承当前环境变量
        )

        try:
            # 1. 通过标准输入输出连接到本地 MCP Server
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 初始化连接
                    await session.initialize()
                    
                    # 2. 获取该 Server 支持的所有工具 (Tools)
                    tools_response = await session.list_tools()
                    tools_list = tools_response.tools
                    
                    if not tools_list:
                        return "❌ 该 MCP Server 没有提供任何可用的 Tool。"

                    # 3. 将工具描述转换为给 7B 模型的 Prompt
                    tools_desc = "\n".join([
                        f"- 【工具名】: {t.name}\n  【描述】: {t.description}\n  【参数Schema】: {json.dumps(t.inputSchema)}" 
                        for t in tools_list
                    ])

                    prompt = f"""你是一个工具调用决策引擎。
你需要根据用户的需求，选择以下提供的一个工具来执行。

【可用工具列表】
{tools_desc}

【用户需求】
{instruction}

请你输出一个严格的 JSON，包含你选择的工具名和参数。不要输出任何其他解释文字。格式如下：
{{
    "tool_name": "选定的工具名",
    "arguments": {{
        "参数1": "值1",
        "参数2": "值2"
    }}
}}"""

                    # 4. 让本地 7B 模型进行决策
                    print(f"🧠 [MCP Agent] 正在让本地模型决策调用哪个 Tool...")
                    decision_text = self.llm_client.chat("你是一个严格的 JSON 输出机器。", prompt, temperature=0.1)
                    
                    # 解析大模型的 JSON 决策
                    match = re.search(r'\{.*\}', decision_text, re.DOTALL)
                    if not match:
                        return f"❌ 本地模型未能输出合法的 JSON 调用指令。原始输出：{decision_text}"
                    
                    decision = json.loads(match.group(0))
                    target_tool = decision.get("tool_name")
                    target_args = decision.get("arguments", {})

                    print(f"⚙️ [MCP Agent] 模型决定调用: {target_tool}，参数: {target_args}")

                    # 5. 执行选定的 MCP Tool
                    result = await session.call_tool(target_tool, arguments=target_args)
                    
                    # 6. 解析并返回结果
                    output = ""
                    for content in result.content:
                        if content.type == 'text':
                            output += content.text + "\n"
                    
                    # 截断防爆
                    return f"✅ MCP 工具执行成功！返回结果：\n{output[:1500]}"

        except Exception as e:
            return f"❌ MCP Server 通信或执行失败: {str(e)}"