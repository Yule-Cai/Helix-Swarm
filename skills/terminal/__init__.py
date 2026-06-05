import subprocess
from core.registry import registry

@registry.register(
    name="execute_terminal",
    description="Execute a bash/cmd command in the local terminal.",
    parameters={
        "properties": {
            "command": {"type": "string", "description": "The command to execute (e.g., 'pytest', 'python app.py')."},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 15). Max is 60."}
        },
        "required": ["command"]
    },
    category="system"
)
def execute_terminal(command: str, timeout: int = 15) -> str:
    # 🛡️ 物理拦截：如果发现启动服务器却没用后台运行符号，直接打回！
    if "http.server" in command or "app.run" in command:
        if "&" not in command and "start " not in command and "nohup" not in command:
            return "❌ 系统拦截: 危险操作！你试图前台启动一个阻塞型服务器。请仔细阅读你的 INSTRUCTIONS，使用 & 或 start 后台运行！"

    print(f"  [Skill] 💻 终端执行: {command}")
    timeout = min(timeout, 60)  # 强制最高 60 秒熔断

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = result.stdout + result.stderr
        if not output.strip():
            return f"Command executed successfully with exit code {result.returncode} (No output)."

        if len(output) > 10000:
            return output[:5000] + "\n...[OUTPUT TRUNCATED]...\n" + output[-5000:]

        return output.strip()

    except subprocess.TimeoutExpired:
        return f"❌ Error: Command timed out after {timeout} seconds. If running a web server, it must be run in the background."
    except Exception as e:
        return f"❌ Terminal Execution Error: {str(e)}"