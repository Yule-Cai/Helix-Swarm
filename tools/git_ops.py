# tools/git_ops.py
import subprocess
from pathlib import Path
from core.registry import registry

def _run_git(args: list, cwd: str = ".") -> tuple:
    """Run a git command and return (success, output, error)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Git command timed out"
    except FileNotFoundError:
        return False, "", "Git is not installed or not in PATH"
    except Exception as e:
        return False, "", str(e)

@registry.register(
    name="git_status",
    description="Show the working tree status. Displays modified, staged, and untracked files.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Repository path (default: current directory)"}
        },
        "required": []
    },
    category="git"
)
def git_status(path: str = ".") -> str:
    """Show git status."""
    success, output, error = _run_git(["status", "--porcelain", "-b"], cwd=path)
    if success:
        if not output.strip():
            return "Working tree clean"
        return output
    else:
        return f"Error: {error}"

@registry.register(
    name="git_diff",
    description="Show changes in the working directory. Can show staged or unstaged changes.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Repository path (default: current directory)"},
            "staged": {"type": "boolean", "description": "Show staged changes (default: false)"},
            "file_path": {"type": "string", "description": "Specific file to diff (optional)"}
        },
        "required": []
    },
    category="git"
)
def git_diff(path: str = ".", staged: bool = False, file_path: str = None) -> str:
    """Show git diff."""
    args = ["diff"]
    if staged:
        args.append("--cached")
    if file_path:
        args.extend(["--", file_path])

    success, output, error = _run_git(args, cwd=path)
    if success:
        if not output.strip():
            return "No changes" if not staged else "No staged changes"
        return output
    else:
        return f"Error: {error}"

@registry.register(
    name="git_log",
    description="Show commit history.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Repository path (default: current directory)"},
            "max_count": {"type": "integer", "description": "Maximum number of commits to show (default: 10)"},
            "oneline": {"type": "boolean", "description": "Show one line per commit (default: true)"}
        },
        "required": []
    },
    category="git"
)
def git_log(path: str = ".", max_count: int = 10, oneline: bool = True) -> str:
    """Show git log."""
    args = ["log", f"--max-count={max_count}"]
    if oneline:
        args.append("--oneline")
    else:
        args.extend(["--format=%h %an %ad %s", "--date=short"])

    success, output, error = _run_git(args, cwd=path)
    if success:
        if not output.strip():
            return "No commits yet"
        return output
    else:
        return f"Error: {error}"

@registry.register(
    name="git_add",
    description="Stage files for commit.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Repository path (default: current directory)"},
            "files": {"type": "array", "items": {"type": "string"}, "description": "Files to stage (default: all)"}
        },
        "required": []
    },
    category="git"
)
def git_add(path: str = ".", files: list = None) -> str:
    """Stage files for commit."""
    if files:
        args = ["add"] + files
    else:
        args = ["add", "-A"]

    success, output, error = _run_git(args, cwd=path)
    if success:
        return "Files staged successfully"
    else:
        return f"Error: {error}"

@registry.register(
    name="git_commit",
    description="Commit staged changes.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Repository path (default: current directory)"},
            "message": {"type": "string", "description": "Commit message"}
        },
        "required": ["message"]
    },
    category="git"
)
def git_commit(path: str = ".", message: str = "") -> str:
    """Commit staged changes."""
    if not message:
        return "Error: Commit message is required"

    args = ["commit", "-m", message]
    success, output, error = _run_git(args, cwd=path)
    if success:
        return output
    else:
        return f"Error: {error}"

@registry.register(
    name="git_branch",
    description="List, create, or switch branches.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Repository path (default: current directory)"},
            "action": {"type": "string", "description": "Action: 'list', 'create', 'switch', 'delete'"},
            "branch_name": {"type": "string", "description": "Branch name (for create/switch/delete)"}
        },
        "required": ["action"]
    },
    category="git"
)
def git_branch(path: str = ".", action: str = "list", branch_name: str = None) -> str:
    """Manage git branches."""
    if action == "list":
        args = ["branch", "-a"]
        success, output, error = _run_git(args, cwd=path)
        if success:
            return output if output.strip() else "No branches"
        else:
            return f"Error: {error}"

    elif action == "create":
        if not branch_name:
            return "Error: Branch name is required for create action"
        args = ["branch", branch_name]
        success, output, error = _run_git(args, cwd=path)
        if success:
            return f"Branch '{branch_name}' created"
        else:
            return f"Error: {error}"

    elif action == "switch":
        if not branch_name:
            return "Error: Branch name is required for switch action"
        args = ["checkout", branch_name]
        success, output, error = _run_git(args, cwd=path)
        if success:
            return output
        else:
            return f"Error: {error}"

    elif action == "delete":
        if not branch_name:
            return "Error: Branch name is required for delete action"
        args = ["branch", "-d", branch_name]
        success, output, error = _run_git(args, cwd=path)
        if success:
            return f"Branch '{branch_name}' deleted"
        else:
            return f"Error: {error}"

    else:
        return f"Error: Unknown action '{action}'. Use: list, create, switch, delete"

@registry.register(
    name="git_checkout",
    description="Switch branches or restore working tree files.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Repository path (default: current directory)"},
            "target": {"type": "string", "description": "Branch name or file path"},
            "create_new": {"type": "boolean", "description": "Create new branch (default: false)"}
        },
        "required": ["target"]
    },
    category="git"
)
def git_checkout(path: str = ".", target: str = "", create_new: bool = False) -> str:
    """Switch branches or restore files."""
    if not target:
        return "Error: Target is required"

    args = ["checkout"]
    if create_new:
        args.append("-b")
    args.append(target)

    success, output, error = _run_git(args, cwd=path)
    if success:
        return output
    else:
        return f"Error: {error}"

@registry.register(
    name="git_pull",
    description="Pull changes from remote repository.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Repository path (default: current directory)"},
            "remote": {"type": "string", "description": "Remote name (default: origin)"},
            "branch": {"type": "string", "description": "Branch name (optional)"}
        },
        "required": []
    },
    category="git"
)
def git_pull(path: str = ".", remote: str = "origin", branch: str = None) -> str:
    """Pull changes from remote."""
    args = ["pull", remote]
    if branch:
        args.append(branch)

    success, output, error = _run_git(args, cwd=path)
    if success:
        return output
    else:
        return f"Error: {error}"

@registry.register(
    name="git_push",
    description="Push changes to remote repository.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Repository path (default: current directory)"},
            "remote": {"type": "string", "description": "Remote name (default: origin)"},
            "branch": {"type": "string", "description": "Branch name (optional)"},
            "force": {"type": "boolean", "description": "Force push (default: false)"}
        },
        "required": []
    },
    category="git"
)
def git_push(path: str = ".", remote: str = "origin", branch: str = None, force: bool = False) -> str:
    """Push changes to remote."""
    args = ["push", remote]
    if branch:
        args.append(branch)
    if force:
        args.append("--force")

    success, output, error = _run_git(args, cwd=path)
    if success:
        return output
    else:
        return f"Error: {error}"

@registry.register(
    name="git_stash",
    description="Stash changes in working directory.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Repository path (default: current directory)"},
            "action": {"type": "string", "description": "Action: 'save', 'pop', 'list', 'drop'"},
            "message": {"type": "string", "description": "Stash message (for save action)"}
        },
        "required": ["action"]
    },
    category="git"
)
def git_stash(path: str = ".", action: str = "save", message: str = None) -> str:
    """Stash changes."""
    if action == "save":
        args = ["stash"]
        if message:
            args.extend(["push", "-m", message])
        success, output, error = _run_git(args, cwd=path)
        if success:
            return output if output.strip() else "No changes to stash"
        else:
            return f"Error: {error}"

    elif action == "pop":
        args = ["stash", "pop"]
        success, output, error = _run_git(args, cwd=path)
        if success:
            return output
        else:
            return f"Error: {error}"

    elif action == "list":
        args = ["stash", "list"]
        success, output, error = _run_git(args, cwd=path)
        if success:
            return output if output.strip() else "No stashes"
        else:
            return f"Error: {error}"

    elif action == "drop":
        args = ["stash", "drop"]
        success, output, error = _run_git(args, cwd=path)
        if success:
            return output
        else:
            return f"Error: {error}"

    else:
        return f"Error: Unknown action '{action}'. Use: save, pop, list, drop"

@registry.register(
    name="git_init",
    description="Initialize a new git repository.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Directory to initialize (default: current directory)"}
        },
        "required": []
    },
    category="git"
)
def git_init(path: str = ".") -> str:
    """Initialize a new git repository."""
    args = ["init"]
    success, output, error = _run_git(args, cwd=path)
    if success:
        return output
    else:
        return f"Error: {error}"

@registry.register(
    name="git_clone",
    description="Clone a repository.",
    parameters={
        "properties": {
            "url": {"type": "string", "description": "Repository URL"},
            "path": {"type": "string", "description": "Directory to clone into (optional)"}
        },
        "required": ["url"]
    },
    category="git"
)
def git_clone(url: str, path: str = None) -> str:
    """Clone a repository."""
    args = ["clone", url]
    if path:
        args.append(path)

    success, output, error = _run_git(args)
    if success:
        return output
    else:
        return f"Error: {error}"
