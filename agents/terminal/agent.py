"""
TerminalAgent — 终端命令执行器
修复：
  1. 用 LLM 从自然语言指令中提取真正的 shell 命令
  2. pip install 命令直接用 sys.executable -m pip 执行，绕过 Windows shell 路径问题
  3. 提取失败时跳过（返回 ✅），不触发重规划
  4. 防止 list index out of range 和 bad escape 错误
  5. [新增] 过滤 pip install 中的 Python 内置模块（sqlite3、json、os 等）
     避免因 "pip install SQLite" 这类无效命令触发无限重规划
"""
import subprocess
import sys
import os
import re

DESCRIPTION    = "Execute shell commands: pip install, compile, run scripts, system operations"
DESCRIPTION_ZH = "执行 Shell 命令：pip 安装、编译、运行脚本等系统操作"

# ── 永远不需要 pip 安装的包（Python 内置 / 标准库）────────────
# Planner 偶尔会生成 "pip install Flask SQLite" 这类命令，
# SQLite 是内置模块，安装会报错并触发无限重规划。
# 这里统一过滤，只安装真正的第三方包。
_STDLIB_PACKAGES = {
    # 数据库
    "sqlite3", "sqlite",
    # 常用内置
    "json", "os", "sys", "re", "math", "pathlib", "threading",
    "queue", "datetime", "collections", "itertools", "functools",
    "typing", "abc", "io", "hashlib", "uuid", "random", "time",
    "csv", "xml", "html", "urllib", "http", "logging", "unittest",
    "string", "copy", "pprint", "struct", "array", "enum", "dataclasses",
    "contextlib", "weakref", "gc", "inspect", "importlib", "pkgutil",
    "traceback", "warnings", "signal", "socket", "ssl", "select",
    "asyncio", "concurrent", "multiprocessing", "subprocess",
    "tempfile", "shutil", "glob", "fnmatch", "stat", "platform",
    "argparse", "getopt", "configparser", "tomllib",
    "base64", "binascii", "codecs", "unicodedata",
    "decimal", "fractions", "statistics", "cmath",
    "calendar", "locale", "gettext",
    "textwrap", "difflib", "readline",
    "pickle", "shelve", "dbm", "zlib", "gzip", "bz2", "lzma",
    "zipfile", "tarfile",
    "email", "smtplib", "poplib", "imaplib", "ftplib",
    "xmlrpc", "ipaddress",
    "tkinter", "curses",
    "ctypes", "cffi",
    "token", "tokenize", "ast", "dis", "py_compile", "compileall",
    "cProfile", "profile", "timeit", "trace", "resource",
    "atexit", "builtins",
}


def _first_line(s: str) -> str:
    """安全取第一行，空字符串返回空字符串。"""
    lines = (s or "").strip().splitlines()
    return lines[0].strip() if lines else ""


def _filter_pip_packages(packages_str: str) -> str:
    """
    从 pip install 的包列表中移除内置模块名。
    例：'Flask SQLite requests' → 'Flask requests'
    返回清理后的包列表字符串，若全是内置模块则返回空字符串。
    """
    parts   = packages_str.split()
    cleaned = []
    for p in parts:
        # 去掉版本号再判断，如 "SQLite==3.0" → "sqlite"
        name = re.split(r"[>=<!@]", p)[0].strip().lower()
        if name in _STDLIB_PACKAGES:
            print(f"⚠️  [Terminal] 跳过内置模块（无需安装）：{p}")
        else:
            cleaned.append(p)
    return " ".join(cleaned)


class TerminalAgent:
    BLACKLIST = ["rm -rf /", "mkfs", "dd ", "sudo rm", "shutdown", "reboot", "format c:"]

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        cmd = self._extract_command(instruction)
        if not cmd:
            return "✅ 无需安装额外依赖（未找到具体命令），跳过。"

        for blk in self.BLACKLIST:
            if blk in cmd:
                return f"❌ 拒绝执行高危命令：{blk}"

        # pip install 单独处理
        pip_match = re.match(r'pip3?\s+install\s+(.+)', cmd.strip(), re.IGNORECASE)
        if pip_match:
            raw_pkgs     = pip_match.group(1).strip()
            filtered_pkgs = _filter_pip_packages(raw_pkgs)

            # 过滤后为空 → 全是内置模块，直接跳过
            if not filtered_pkgs:
                return (f"✅ 跳过安装：{raw_pkgs} 均为 Python 内置模块，无需 pip 安装。")

            # 有真正的第三方包才安装
            return self._pip_install(filtered_pkgs)

        # 其他命令走 subprocess
        return self._run_shell(cmd, workspace_dir)

    def _pip_install(self, packages: str) -> str:
        """直接用 sys.executable -m pip 安装，避免 Windows 路径/编码问题。"""
        pkg_list = packages.split()
        print(f"🖥️  [Terminal] pip install {packages}")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + pkg_list,
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=120,
            )
            if result.returncode == 0:
                return f"✅ 安装成功：{packages}\n{result.stdout[-500:].strip()}"
            err = (result.stderr or result.stdout or "")[-500:]
            return f"❌ 安装失败：{packages}\n{err}"
        except subprocess.TimeoutExpired:
            return f"❌ 安装超时（120s）：{packages}"
        except Exception as e:
            return f"❌ 安装异常：{e}"

    def _run_shell(self, cmd: str, workspace_dir: str) -> str:
        """执行非 pip 的 shell 命令。"""
        _global_cmds = {"python", "python3", "npm", "node", "git", "conda", "go"}
        first = cmd.strip().split()[0].lower() if cmd.strip().split() else ""
        cwd   = None if first in _global_cmds else workspace_dir
        if cwd:
            os.makedirs(cwd, exist_ok=True)

        py  = sys.executable
        cmd = re.sub(r"\bpython3?\b", lambda m: f'"{py}"', cmd)

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        print(f"🖥️  [Terminal] 执行: {cmd}  (cwd={cwd})")
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=cwd, env=env, timeout=120,
                encoding="utf-8", errors="replace",
            )
            if r.returncode == 0:
                return f"✅ 执行成功\n{r.stdout[:800]}"
            return f"❌ 执行失败(退出码{r.returncode})\n{(r.stderr or r.stdout)[:400]}"
        except subprocess.TimeoutExpired:
            return "❌ 超时（120s）"
        except Exception as e:
            return f"❌ 异常：{e}"

    def _extract_command(self, instruction: str) -> str:
        """从自然语言指令中提取真正的 shell 命令。"""
        text = instruction[:500]

        # ① 代码块优先
        m = re.search(r"```(?:bash|shell|sh|cmd|powershell)?\s*\n?(.*?)```", text, re.DOTALL)
        if m:
            line = _first_line(m.group(1))
            if line:
                return line

        # ② 逐行扫描：找第一个已知命令开头的行
        known = {"pip", "pip3", "python", "python3", "npm", "node",
                 "git", "conda", "brew", "apt", "cargo", "go"}
        for line in text.splitlines():
            line = line.strip().lstrip("$").strip()
            if not line:
                continue
            parts = line.split()
            if not parts:
                continue
            if parts[0].lower() in known:
                return line
            low = line.lower()
            if "pip install" in low or "pip3 install" in low:
                idx = low.find("pip")
                return line[idx:].strip()

        # ③ LLM 提取
        if self.llm:
            try:
                result = self.llm.chat(
                    "You are a command extractor. Extract the shell command to run from the user instruction.\n"
                    "Output the command only (e.g. pip install flask), no explanations, no code block markers.\n"
                    "If there is no specific package to install or no clear command, output: NONE",
                    instruction[:200],
                    temperature=0.0,
                    max_tokens=60,
                )
                line = _first_line(result).strip("`").strip()
                if line and line.upper() != "NONE" and len(line) < 200:
                    parts = line.split()
                    if parts and parts[0].lower() in known:
                        return line
            except Exception:
                pass

        return ""