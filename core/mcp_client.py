import subprocess
import json
import threading
from core.registry import registry
from rich.console import Console

console = Console()

class MCPBridge:
    def __init__(self, name: str, command: str, args: list):
        self.name = name
        self.msg_id = 1
        
        try:
            self.process = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            console.print(f"[dim]🔌 [{self.name}] MCP 服务已启动: {command} {' '.join(args)}[/]")
        except FileNotFoundError:
            console.print(f"[bold red]❌ 找不到命令 '{command}'。[/]")
            self.process = None

    def _send_request(self, method: str, params: dict = None):
        """发送请求，并且【死等】返回值"""
        if not self.process: return {}
        
        req = {
            "jsonrpc": "2.0",
            "id": self.msg_id,
            "method": method,
            "params": params or {}
        }
        self.msg_id += 1
        
        self.process.stdin.write(json.dumps(req) + "\n")
        self.process.stdin.flush()

        while True:
            line = self.process.stdout.readline()
            if not line:
                break
            try:
                resp = json.loads(line)
                if "id" in resp and resp["id"] == req["id"]:
                    return resp
            except json.JSONDecodeError:
                continue
        return {}

    # 🚀 新增：专门发通知，发完就走，绝不等待！
    def _send_notification(self, method: str, params: dict = None):
        if not self.process: return
        req = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        self.process.stdin.write(json.dumps(req) + "\n")
        self.process.stdin.flush()

    def discover_and_register(self):
        """核心魔法：询问服务器能力，并动态注册"""
        if not self.process: return

        # 1. 握手初始化
        init_res = self._send_request("initialize", {
            "protocolVersion": "2024-11-05", 
            "capabilities": {}, 
            "clientInfo": {"name": "Helix-Swarm", "version": "1.0"}
        })
        
        # 🚀 修复：这里改成 _send_notification，发完就走！
        self._send_notification("notifications/initialized")

        # 2. 获取技能列表
        tools_res = self._send_request("tools/list")
        mcp_tools = tools_res.get("result", {}).get("tools", [])

        if not mcp_tools:
            console.print(f"[yellow]⚠️ [{self.name}] 服务器未提供任何工具。[/]")
            return

        # 3. 动态注册进 Registry
        for tool in mcp_tools:
            tool_name = tool["name"]
            
            def make_handler(t_name, client_instance):
                def handler(**kwargs):
                    console.print(f"  [MCP外挂] ⚡ 调用服务器 [{client_instance.name}] 的技能: {t_name}")
                    res = client_instance._send_request("tools/call", {
                        "name": t_name, 
                        "arguments": kwargs
                    })
                    
                    content_list = res.get("result", {}).get("content", [])
                    if not content_list and "error" in res:
                        return f"❌ MCP Error: {res['error']}"
                        
                    return "\n".join([c.get("text", "") for c in content_list])
                return handler

            registry.register(
                name=f"{self.name}_{tool_name}", 
                description=tool.get("description", f"External MCP tool: {tool_name}"),
                parameters=tool.get("inputSchema", {}),
                category="mcp"
            )(make_handler(tool_name, self))

            console.print(f"[bold green]  ✓ 成功装载外挂技能:[/] {self.name}_{tool_name}")