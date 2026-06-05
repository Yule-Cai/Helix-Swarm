# skills/safe_terminal.py
import os
import subprocess
from core.registry import tool

@tool(
    name="execute_terminal", 
    description="Execute a shell command in the current operating system terminal.",
    parameters={
        "properties": {
            "command": {"type": "string", "description": "Command to execute."},
            "timeout": {"type": "integer", "description": "Timeout in seconds. Default: 60."}
        },
        "required": ["command"]
    },
    category="system"
)
def safe_execute_terminal(command: str, timeout: int = 60) -> str:
    """Cross-platform terminal executor with stable UTF-8 output."""
    try:
        env = os.environ.copy()
        env["NO_COLOR"] = "1"
        env["CI"] = "true"
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            env=env,
        )
        
        output = result.stdout.strip()
        error_output = result.stderr.strip()
        
        final_output = ""
        if output:
            final_output += output
        if error_output:
            final_output += f"\n[STDERR Warning/Error]\n{error_output}"
            
        if not final_output:
            return f"Command finished with exit code {result.returncode} and no output."
            
        return final_output

    except subprocess.TimeoutExpired:
        return f"Terminal Execution Failed: command timed out after {timeout} seconds"
    except Exception as e:
        return f"Terminal Execution Failed: {str(e)}"
