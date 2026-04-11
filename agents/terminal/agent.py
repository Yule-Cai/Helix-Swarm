"""
TerminalAgent — 终端命令执行器
修复：
  1. 用 LLM 从自然语言指令中提取真正的 shell 命令
  2. pip install / python 命令自动替换为 sys.executable 路径（跨平台）
  3. 提取失败时跳过（返回 ✅），不触发重规划
  4. 防止 list index out of range 和 bad escape 错误
"""
import subprocess
import sys
import os
import re

def _first_line(s: str) -> str:
    """安全取第一行，空字符串返回空字符串。"""
    lines = (s or '').strip().splitlines()
    return lines[0].strip() if lines else ''

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

        # cd xxx && cmd 模式
        m = re.search(r'cd\s+(\S+)\s*&&\s*(.*)', cmd)
        if m:
            workspace_dir = os.path.join(workspace_dir, m.group(1))
            cmd = m.group(2).strip()

        # 先判断是否全局命令（必须在替换 pip→python 之前）
        _global_cmds = {"pip", "pip3", "conda", "npm", "node", "git", "brew", "apt", "cargo"}
        first_word = cmd.strip().split()[0].lower() if cmd.strip().split() else ''
        is_global = first_word in _global_cmds
        cwd = None if is_global else workspace_dir
        if not is_global:
            os.makedirs(workspace_dir, exist_ok=True)

        # 替换 python / pip 为绝对路径（用 lambda 避免替换字符串被当正则）
        py  = sys.executable
        pip = f'"{py}" -m pip'
        cmd = re.sub(r'\bpip3?\b',    lambda m: pip,       cmd)
        cmd = re.sub(r'\bpython3?\b', lambda m: f'"{py}"', cmd)

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
                return f"✅ 执行成功\n{r.stdout[:1000]}"
            return f"❌ 执行失败(退出码{r.returncode})\n{(r.stderr or r.stdout)[:500]}"
        except subprocess.TimeoutExpired:
            return "❌ 超时（120s）"
        except Exception as e:
            return f"❌ 异常：{e}"

    def _extract_command(self, instruction: str) -> str:
        """从自然语言指令中提取真正的 shell 命令。"""
        text = instruction[:500]

        # ① 代码块优先
        m = re.search(r'```(?:bash|shell|sh|cmd|powershell)?\s*\n?(.*?)```', text, re.DOTALL)
        if m:
            line = _first_line(m.group(1))
            if line:
                return line

        # ② 逐行扫描：找第一个已知命令开头的行
        known = {'pip', 'pip3', 'python', 'python3', 'npm', 'node',
                 'git', 'conda', 'brew', 'apt', 'cargo', 'go'}
        for line in text.splitlines():
            line = line.strip().lstrip('$').strip()
            if not line:
                continue
            parts = line.split()
            if not parts:
                continue
            if parts[0].lower() in known:
                return line
            # pip install 子串匹配（不用正则，避免 bad escape）
            low = line.lower()
            if 'pip install' in low or 'pip3 install' in low:
                # 提取从 pip 开始的部分
                idx = low.find('pip')
                return line[idx:].strip()

        # ③ LLM 提取
        if self.llm:
            try:
                result = self.llm.chat(
                    "你是命令提取器。从用户指令中提取需要执行的 shell 命令。\n"
                    "只输出命令本身（如 pip install xxx），不要解释，不要加代码块标记。\n"
                    "如果没有具体的包需要安装或没有明确命令，输出：NONE",
                    instruction[:200],
                    temperature=0.0,
                    max_tokens=60,
                )
                line = _first_line(result)
                line = line.strip('`').strip()
                if line and line.upper() != 'NONE' and len(line) < 200:
                    parts = line.split()
                    if parts and parts[0].lower() in known:
                        return line
            except Exception:
                pass

        return ""