# tools/code_search.py
import os
import re
import subprocess
from pathlib import Path
from core.registry import registry

@registry.register(
    name="grep_code",
    description="Search for patterns in code files using regex. Returns matching lines with file paths and line numbers.",
    parameters={
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {"type": "string", "description": "Directory or file path to search in (default: current directory)"},
            "file_type": {"type": "string", "description": "Filter by file type (e.g., 'py', 'js', 'ts'). Optional."},
            "case_sensitive": {"type": "boolean", "description": "Case sensitive search (default: false)"},
            "max_results": {"type": "integer", "description": "Maximum number of results to return (default: 50)"}
        },
        "required": ["pattern"]
    },
    category="search"
)
def grep_code(pattern: str, path: str = ".", file_type: str = None, case_sensitive: bool = False, max_results: int = 50) -> str:
    """Search for patterns in code files using regex."""
    try:
        # Build grep command
        cmd = ["grep", "-r", "-n", "--include=*"]

        if not case_sensitive:
            cmd.append("-i")

        if file_type:
            cmd.extend([f"--include=*.{file_type}"])

        cmd.extend([pattern, path])

        # Execute grep
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Limit results
            if len(lines) > max_results:
                lines = lines[:max_results]
                lines.append(f"\n... and {len(result.stdout.strip().split(chr(10))) - max_results} more results")
            return '\n'.join(lines)
        elif result.returncode == 1:
            return f"No matches found for pattern: {pattern}"
        else:
            return f"Error executing grep: {result.stderr}"

    except subprocess.TimeoutExpired:
        return "Error: Search timed out after 30 seconds"
    except FileNotFoundError:
        # Fallback to Python-based search if grep not available
        return _python_grep(pattern, path, file_type, case_sensitive, max_results)
    except Exception as e:
        return f"Error during search: {str(e)}"

def _python_grep(pattern: str, path: str, file_type: str, case_sensitive: bool, max_results: int) -> str:
    """Fallback Python-based grep implementation."""
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
        results = []

        search_path = Path(path)
        if search_path.is_file():
            files = [search_path]
        else:
            files = list(search_path.rglob(f"*.{file_type}" if file_type else "*"))

        for file_path in files:
            if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append(f"{file_path}:{line_num}: {line.rstrip()}")
                                if len(results) >= max_results:
                                    break
                except (PermissionError, UnicodeDecodeError):
                    continue

            if len(results) >= max_results:
                break

        if results:
            return '\n'.join(results)
        else:
            return f"No matches found for pattern: {pattern}"

    except re.error as e:
        return f"Invalid regex pattern: {str(e)}"
    except Exception as e:
        return f"Error during search: {str(e)}"

@registry.register(
    name="glob_files",
    description="Find files matching glob patterns. Returns list of file paths.",
    parameters={
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern to match (e.g., '**/*.py', 'src/**/*.js')"},
            "path": {"type": "string", "description": "Base directory to search in (default: current directory)"},
            "max_results": {"type": "integer", "description": "Maximum number of results to return (default: 100)"}
        },
        "required": ["pattern"]
    },
    category="search"
)
def glob_files(pattern: str, path: str = ".", max_results: int = 100) -> str:
    """Find files matching glob patterns."""
    try:
        search_path = Path(path)
        if not search_path.exists():
            return f"Error: Path '{path}' does not exist"

        # Use Python's glob module
        import glob
        matches = list(search_path.glob(pattern))

        # Filter out hidden files and directories
        matches = [m for m in matches if not any(part.startswith('.') for part in m.parts)]

        # Limit results
        if len(matches) > max_results:
            matches = matches[:max_results]
            matches.append(f"\n... and {len(search_path.glob(pattern)) - max_results} more files")

        if matches:
            return '\n'.join(str(m) for m in matches)
        else:
            return f"No files found matching pattern: {pattern}"

    except Exception as e:
        return f"Error during glob search: {str(e)}"

@registry.register(
    name="search_symbols",
    description="Search for function/class definitions in Python code. Returns symbol names with file locations.",
    parameters={
        "properties": {
            "symbol_name": {"type": "string", "description": "Name of function or class to search for"},
            "path": {"type": "string", "description": "Directory to search in (default: current directory)"},
            "symbol_type": {"type": "string", "description": "Type of symbol: 'function', 'class', or 'any' (default: any)"}
        },
        "required": ["symbol_name"]
    },
    category="search"
)
def search_symbols(symbol_name: str, path: str = ".", symbol_type: str = "any") -> str:
    """Search for function/class definitions in Python code."""
    try:
        results = []
        search_path = Path(path)

        # Regex patterns for Python symbols
        if symbol_type == "function":
            pattern = rf"^def\s+{re.escape(symbol_name)}\s*\("
        elif symbol_type == "class":
            pattern = rf"^class\s+{re.escape(symbol_name)}\s*[\(:]"
        else:
            pattern = rf"^(def|class)\s+{re.escape(symbol_name)}\s*[\(:]"

        regex = re.compile(pattern, re.MULTILINE)

        for py_file in search_path.rglob("*.py"):
            if any(part.startswith('.') for part in py_file.parts):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for match in regex.finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    results.append(f"{py_file}:{line_num}: {match.group()}")
            except (PermissionError, UnicodeDecodeError):
                continue

        if results:
            return '\n'.join(results)
        else:
            return f"No {symbol_type} definitions found for: {symbol_name}"

    except Exception as e:
        return f"Error searching symbols: {str(e)}"
