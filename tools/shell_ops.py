# tools/shell_ops.py
import subprocess
import os
import sys
import time
from pathlib import Path
from core.registry import registry

@registry.register(
    name="execute_terminal",
    description="Execute a command in the terminal. Use this to run tests, install packages, or start services.",
    parameters={
        "properties": {
            "command": {"type": "string", "description": "The command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
            "background": {"type": "boolean", "description": "Run in background (default: false)"},
            "working_dir": {"type": "string", "description": "Working directory (optional)"}
        },
        "required": ["command"]
    },
    category="system"
)
def execute_terminal(command: str, timeout: int = 30, background: bool = False, working_dir: str = None) -> str:
    """Execute a command in the terminal."""
    try:
        # Set working directory
        cwd = working_dir or os.getcwd()

        # Handle background processes
        if background:
            if sys.platform == "win32":
                # Windows
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=cwd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Unix/Linux/Mac
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setpgrp
                )
            return f"Process started in background (PID: {process.pid})"

        # Execute with timeout
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )

        output = result.stdout
        error = result.stderr

        # Combine output
        full_output = ""
        if output:
            full_output += output
        if error:
            if full_output:
                full_output += "\n"
            full_output += f"[STDERR]\n{error}"

        # Truncate if too long
        if len(full_output) > 5000:
            full_output = full_output[:2500] + "\n...[OUTPUT TRUNCATED]...\n" + full_output[-2500:]

        if not full_output.strip():
            return f"Command executed successfully (exit code: {result.returncode})"

        return full_output

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"

@registry.register(
    name="execute_background",
    description="Start a process in the background. Returns the process ID.",
    parameters={
        "properties": {
            "command": {"type": "string", "description": "The command to execute"},
            "working_dir": {"type": "string", "description": "Working directory (optional)"},
            "log_file": {"type": "string", "description": "Log file path (optional)"}
        },
        "required": ["command"]
    },
    category="system"
)
def execute_background(command: str, working_dir: str = None, log_file: str = None) -> str:
    """Start a process in the background."""
    try:
        cwd = working_dir or os.getcwd()

        # Setup log file
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            stdout = open(log_file, 'w')
            stderr = subprocess.STDOUT

        if sys.platform == "win32":
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=stdout,
                stderr=stderr
            )
        else:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=stdout,
                stderr=stderr,
                preexec_fn=os.setpgrp
            )

        return f"Background process started (PID: {process.pid})"

    except Exception as e:
        return f"Error starting background process: {str(e)}"

@registry.register(
    name="check_process",
    description="Check if a process is running.",
    parameters={
        "properties": {
            "pid": {"type": "integer", "description": "Process ID"},
            "name": {"type": "string", "description": "Process name (alternative to PID)"}
        },
        "required": []
    },
    category="system"
)
def check_process(pid: int = None, name: str = None) -> str:
    """Check if a process is running."""
    try:
        if pid:
            # Check by PID
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True,
                    text=True
                )
                if str(pid) in result.stdout:
                    return f"Process {pid} is running"
                else:
                    return f"Process {pid} is not running"
            else:
                result = subprocess.run(
                    ["ps", "-p", str(pid)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return f"Process {pid} is running"
                else:
                    return f"Process {pid} is not running"

        elif name:
            # Check by name
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {name}"],
                    capture_output=True,
                    text=True
                )
                if name.lower() in result.stdout.lower():
                    return f"Process '{name}' is running"
                else:
                    return f"Process '{name}' is not running"
            else:
                result = subprocess.run(
                    ["pgrep", "-f", name],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return f"Process '{name}' is running (PIDs: {result.stdout.strip()})"
                else:
                    return f"Process '{name}' is not running"
        else:
            return "Error: Must provide either pid or name"

    except Exception as e:
        return f"Error checking process: {str(e)}"

@registry.register(
    name="kill_process",
    description="Kill a process by PID or name.",
    parameters={
        "properties": {
            "pid": {"type": "integer", "description": "Process ID"},
            "name": {"type": "string", "description": "Process name"},
            "force": {"type": "boolean", "description": "Force kill (SIGKILL) (default: false)"}
        },
        "required": []
    },
    category="system"
)
def kill_process(pid: int = None, name: str = None, force: bool = False) -> str:
    """Kill a process."""
    try:
        if pid:
            if sys.platform == "win32":
                cmd = ["taskkill", "/PID", str(pid)]
                if force:
                    cmd.append("/F")
                result = subprocess.run(cmd, capture_output=True, text=True)
            else:
                signal = "-9" if force else "-15"
                result = subprocess.run(["kill", signal, str(pid)], capture_output=True, text=True)

            if result.returncode == 0:
                return f"Process {pid} killed"
            else:
                return f"Error killing process {pid}: {result.stderr}"

        elif name:
            if sys.platform == "win32":
                cmd = ["taskkill", "/IM", name]
                if force:
                    cmd.append("/F")
                result = subprocess.run(cmd, capture_output=True, text=True)
            else:
                signal = "-9" if force else "-15"
                result = subprocess.run(["pkill", signal, "-f", name], capture_output=True, text=True)

            if result.returncode == 0:
                return f"Process '{name}' killed"
            else:
                return f"Error killing process '{name}': {result.stderr}"

        else:
            return "Error: Must provide either pid or name"

    except Exception as e:
        return f"Error killing process: {str(e)}"

@registry.register(
    name="get_environment",
    description="Get environment variables.",
    parameters={
        "properties": {
            "name": {"type": "string", "description": "Variable name (optional, returns all if not specified)"}
        },
        "required": []
    },
    category="system"
)
def get_environment(name: str = None) -> str:
    """Get environment variables."""
    try:
        if name:
            value = os.environ.get(name)
            if value is not None:
                return f"{name}={value}"
            else:
                return f"Environment variable '{name}' not set"
        else:
            # Return all env vars (filtered for security)
            sensitive_patterns = ["key", "secret", "password", "token", "credential"]
            env_vars = []
            for key, value in sorted(os.environ.items()):
                # Mask sensitive values
                if any(pattern in key.lower() for pattern in sensitive_patterns):
                    env_vars.append(f"{key}=***MASKED***")
                else:
                    env_vars.append(f"{key}={value}")
            return '\n'.join(env_vars)

    except Exception as e:
        return f"Error getting environment: {str(e)}"

@registry.register(
    name="set_environment",
    description="Set an environment variable.",
    parameters={
        "properties": {
            "name": {"type": "string", "description": "Variable name"},
            "value": {"type": "string", "description": "Variable value"}
        },
        "required": ["name", "value"]
    },
    category="system"
)
def set_environment(name: str, value: str) -> str:
    """Set an environment variable."""
    try:
        os.environ[name] = value
        return f"Set {name}={value}"
    except Exception as e:
        return f"Error setting environment variable: {str(e)}"

@registry.register(
    name="get_current_directory",
    description="Get the current working directory.",
    parameters={},
    category="system"
)
def get_current_directory() -> str:
    """Get the current working directory."""
    return os.getcwd()

@registry.register(
    name="change_directory",
    description="Change the current working directory.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Directory path"}
        },
        "required": ["path"]
    },
    category="system"
)
def change_directory(path: str) -> str:
    """Change the current working directory."""
    try:
        os.chdir(path)
        return f"Changed directory to: {os.getcwd()}"
    except FileNotFoundError:
        return f"Error: Directory '{path}' not found"
    except PermissionError:
        return f"Error: Permission denied accessing '{path}'"
    except Exception as e:
        return f"Error changing directory: {str(e)}"
