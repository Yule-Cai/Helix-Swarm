# tools/file_ops.py
import os
import shutil
from pathlib import Path
from core.registry import registry

@registry.register(
    name="read_file",
    description="Read the contents of a file. Returns file content with line numbers.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Path to the file to read"},
            "offset": {"type": "integer", "description": "Line number to start reading from (0-based)"},
            "limit": {"type": "integer", "description": "Maximum number of lines to read"}
        },
        "required": ["path"]
    },
    category="file"
)
def read_file(path: str, offset: int = 0, limit: int = None) -> str:
    """Read the contents of a file with optional offset and limit."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return f"Error: File '{path}' does not exist"
        if not file_path.is_file():
            return f"Error: '{path}' is not a file"

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Apply offset and limit
        if offset > 0:
            lines = lines[offset:]
        if limit is not None:
            lines = lines[:limit]

        # Add line numbers
        numbered_lines = []
        for i, line in enumerate(lines, start=offset + 1):
            numbered_lines.append(f"{i:4d} | {line.rstrip()}")

        if not numbered_lines:
            return "File is empty"

        return '\n'.join(numbered_lines)

    except PermissionError:
        return f"Error: Permission denied reading '{path}'"
    except UnicodeDecodeError:
        return f"Error: Cannot read '{path}' - file may be binary"
    except Exception as e:
        return f"Error reading file: {str(e)}"

@registry.register(
    name="write_file",
    description="Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Path to the file to write"},
            "content": {"type": "string", "description": "Content to write to the file"},
            "append": {"type": "boolean", "description": "Append to file instead of overwriting (default: false)"}
        },
        "required": ["path", "content"]
    },
    category="file"
)
def write_file(path: str, content: str, append: bool = False) -> str:
    """Write content to a file."""
    try:
        file_path = Path(path)

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)

        action = "appended to" if append else "written to"
        return f"Successfully {action} '{path}' ({len(content)} characters)"

    except PermissionError:
        return f"Error: Permission denied writing to '{path}'"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@registry.register(
    name="edit_file",
    description="Edit a file by replacing exact text. This is more precise than rewriting the entire file.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Path to the file to edit"},
            "old_string": {"type": "string", "description": "Exact text to find and replace"},
            "new_string": {"type": "string", "description": "New text to replace with"},
            "replace_all": {"type": "boolean", "description": "Replace all occurrences (default: false)"}
        },
        "required": ["path", "old_string", "new_string"]
    },
    category="file"
)
def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Edit a file by replacing exact text."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return f"Error: File '{path}' does not exist"

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if old_string exists
        if old_string not in content:
            return f"Error: Text not found in '{path}'"

        # Count occurrences
        count = content.count(old_string)
        if count > 1 and not replace_all:
            return f"Error: Found {count} occurrences of the text. Use replace_all=true to replace all, or provide more context to make the match unique."

        # Perform replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacement_count = count
        else:
            new_content = content.replace(old_string, new_string, 1)
            replacement_count = 1

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return f"Successfully replaced {replacement_count} occurrence(s) in '{path}'"

    except PermissionError:
        return f"Error: Permission denied editing '{path}'"
    except Exception as e:
        return f"Error editing file: {str(e)}"

@registry.register(
    name="insert_at_line",
    description="Insert content at a specific line number in a file.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
            "line_number": {"type": "integer", "description": "Line number to insert at (1-based)"},
            "content": {"type": "string", "description": "Content to insert"}
        },
        "required": ["path", "line_number", "content"]
    },
    category="file"
)
def insert_at_line(path: str, line_number: int, content: str) -> str:
    """Insert content at a specific line number."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return f"Error: File '{path}' does not exist"

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Validate line number
        if line_number < 1 or line_number > len(lines) + 1:
            return f"Error: Line number {line_number} is out of range (1-{len(lines) + 1})"

        # Insert content
        insert_index = line_number - 1
        new_lines = content.split('\n')
        for i, line in enumerate(new_lines):
            lines.insert(insert_index + i, line + '\n')

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return f"Successfully inserted {len(new_lines)} line(s) at line {line_number} in '{path}'"

    except PermissionError:
        return f"Error: Permission denied editing '{path}'"
    except Exception as e:
        return f"Error inserting content: {str(e)}"

@registry.register(
    name="delete_lines",
    description="Delete specific lines from a file.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
            "start_line": {"type": "integer", "description": "Start line number (1-based, inclusive)"},
            "end_line": {"type": "integer", "description": "End line number (1-based, inclusive). Optional - defaults to start_line."}
        },
        "required": ["path", "start_line"]
    },
    category="file"
)
def delete_lines(path: str, start_line: int, end_line: int = None) -> str:
    """Delete specific lines from a file."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return f"Error: File '{path}' does not exist"

        if end_line is None:
            end_line = start_line

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Validate line numbers
        if start_line < 1 or start_line > len(lines):
            return f"Error: Start line {start_line} is out of range (1-{len(lines)})"
        if end_line < start_line or end_line > len(lines):
            return f"Error: End line {end_line} is out of range ({start_line}-{len(lines)})"

        # Delete lines
        deleted_count = end_line - start_line + 1
        del lines[start_line - 1:end_line]

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return f"Successfully deleted {deleted_count} line(s) from '{path}'"

    except PermissionError:
        return f"Error: Permission denied editing '{path}'"
    except Exception as e:
        return f"Error deleting lines: {str(e)}"

@registry.register(
    name="list_directory",
    description="List files and directories in a path. Returns a tree-like structure.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Directory path to list (default: current directory)"},
            "max_depth": {"type": "integer", "description": "Maximum depth to traverse (default: 2)"},
            "show_hidden": {"type": "boolean", "description": "Show hidden files (default: false)"}
        },
        "required": []
    },
    category="file"
)
def list_directory(path: str = ".", max_depth: int = 2, show_hidden: bool = False) -> str:
    """List files and directories in a tree-like structure."""
    try:
        root_path = Path(path)
        if not root_path.exists():
            return f"Error: Path '{path}' does not exist"
        if not root_path.is_dir():
            return f"Error: '{path}' is not a directory"

        result = []
        _build_tree(root_path, result, prefix="", depth=0, max_depth=max_depth, show_hidden=show_hidden)

        if not result:
            return f"Directory '{path}' is empty"

        return '\n'.join(result)

    except PermissionError:
        return f"Error: Permission denied accessing '{path}'"
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def _build_tree(path: Path, result: list, prefix: str, depth: int, max_depth: int, show_hidden: bool):
    """Recursively build directory tree."""
    if depth > max_depth:
        return

    try:
        entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    except PermissionError:
        return

    for i, entry in enumerate(entries):
        # Skip hidden files if not showing them
        if not show_hidden and entry.name.startswith('.'):
            continue

        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "

        if entry.is_dir():
            result.append(f"{prefix}{connector}{entry.name}/")
            extension = "    " if is_last else "│   "
            _build_tree(entry, result, prefix + extension, depth + 1, max_depth, show_hidden)
        else:
            # Show file size
            try:
                size = entry.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f}KB"
                else:
                    size_str = f"{size/(1024*1024):.1f}MB"
                result.append(f"{prefix}{connector}{entry.name} ({size_str})")
            except:
                result.append(f"{prefix}{connector}{entry.name}")

@registry.register(
    name="copy_file",
    description="Copy a file or directory to a new location.",
    parameters={
        "properties": {
            "source": {"type": "string", "description": "Source path"},
            "destination": {"type": "string", "description": "Destination path"}
        },
        "required": ["source", "destination"]
    },
    category="file"
)
def copy_file(source: str, destination: str) -> str:
    """Copy a file or directory."""
    try:
        src_path = Path(source)
        dst_path = Path(destination)

        if not src_path.exists():
            return f"Error: Source '{source}' does not exist"

        # Create parent directories if needed
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
            return f"Successfully copied directory '{source}' to '{destination}'"
        else:
            shutil.copy2(src_path, dst_path)
            return f"Successfully copied file '{source}' to '{destination}'"

    except PermissionError:
        return f"Error: Permission denied"
    except Exception as e:
        return f"Error copying: {str(e)}"

@registry.register(
    name="move_file",
    description="Move/rename a file or directory.",
    parameters={
        "properties": {
            "source": {"type": "string", "description": "Source path"},
            "destination": {"type": "string", "description": "Destination path"}
        },
        "required": ["source", "destination"]
    },
    category="file"
)
def move_file(source: str, destination: str) -> str:
    """Move/rename a file or directory."""
    try:
        src_path = Path(source)
        dst_path = Path(destination)

        if not src_path.exists():
            return f"Error: Source '{source}' does not exist"

        # Create parent directories if needed
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src_path), str(dst_path))
        return f"Successfully moved '{source}' to '{destination}'"

    except PermissionError:
        return f"Error: Permission denied"
    except Exception as e:
        return f"Error moving: {str(e)}"

@registry.register(
    name="delete_file",
    description="Delete a file or directory.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Path to delete"},
            "recursive": {"type": "boolean", "description": "Delete directories recursively (default: false)"}
        },
        "required": ["path"]
    },
    category="file"
)
def delete_file(path: str, recursive: bool = False) -> str:
    """Delete a file or directory."""
    try:
        target_path = Path(path)

        if not target_path.exists():
            return f"Error: '{path}' does not exist"

        if target_path.is_dir():
            if recursive:
                shutil.rmtree(target_path)
                return f"Successfully deleted directory '{path}' and all its contents"
            else:
                try:
                    target_path.rmdir()
                    return f"Successfully deleted empty directory '{path}'"
                except OSError:
                    return f"Error: Directory '{path}' is not empty. Use recursive=true to delete it with all contents."
        else:
            target_path.unlink()
            return f"Successfully deleted file '{path}'"

    except PermissionError:
        return f"Error: Permission denied deleting '{path}'"
    except Exception as e:
        return f"Error deleting: {str(e)}"
