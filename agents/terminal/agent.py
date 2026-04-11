"""
TerminalAgent — 终端命令执行器
修复：
  1. 用 LLM 从自然语言指令中提取真正的 shell 命令，不再直接执行指令原文
  2. pip install / python 命令自动替换为 sys.executable 路径（跨平台）
  3. 提取失败时用正则兜底识别常见命令模式
"""
import subprocess
import sys
import os
import re

class TerminalAgent:
    BLACKLIST = ["rm -rf /", "mkfs", "dd ", "sudo rm", "shutdown", "reboot", "format c:"]

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        # 1. 从指令中提取实际命令
        cmd = self._extract_command(instruction)
        if not cmd:
            return f"⚠️ 无法从指令中提取可执行命令：{instruction[:100]}"

        # 2. 黑名单检查
        for blk in self.BLACKLIST:
            if blk in cmd:
                return f"❌ 拒绝执行高危命令：{blk}"

        # 3. cd xxx && cmd 模式
        m = re.search(r'cd\s+(\S+)\s*&&\s*(.*)', cmd)
        if m:
            workspace_dir = os.path.join(workspace_dir, m.group(1))
            cmd = m.group(2).strip()

        # 4. 先判断是否全局命令（pip/npm等不需要 workspace_dir 作为 cwd）
        #    必须在替换 pip→python 之前判断，否则 first_word 会变成 python 路径
        _global_cmds = {"pip", "pip3", "conda", "npm", "node", "git", "brew", "apt", "cargo"}
        first_word = cmd.strip().split()[0].lower() if cmd.strip() else ""
        is_global = first_word in _global_cmds
        cwd = None if is_global else workspace_dir
        if not is_global:
            os.makedirs(workspace_dir, exist_ok=True)

        # 5. 用 sys.executable 替换 python / pip
        py  = sys.executable
        pip = f'"{py}" -m pip'
        # 用 lambda 替换，避免替换字符串被当作正则（防止 \P 之类报错）
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

        # 只取指令前500字符，避免 Windows 路径等特殊字符干扰正则
        text = instruction[:500]

        # ① 优先：代码块里的命令
        m = re.search(r'```(?:bash|shell|sh|cmd|powershell)?\s*\n?(.*?)```', text, re.DOTALL)
        if m:
            return m.group(1).strip().splitlines()[0].strip()

        # ② 正则兜底：逐行扫描，找第一个看起来像命令的行
        for line in text.splitlines():
            line = line.strip().lstrip('$').strip()
            if not line:
                continue
            first = line.split()[0].lower() if line.split() else ''
            # 直接匹配已知命令开头
            if first in {'pip', 'pip3', 'python', 'python3', 'npm', 'node',
                         'git', 'conda', 'brew', 'apt', 'cargo', 'go'}:
                return line
            # pip install 模式
            try:
                m2 = re.search(r'pip3?\s+install\s+[\w\-\[\],\s>=<.]+', line, re.IGNORECASE)
                if m2:
                    return m2.group(0).strip()
            except re.error:
                pass

        # ③ LLM 提取（最后手段）
        if self.llm:
            result = self.llm.chat(
                "你是命令提取器。从用户指令中提取需要执行的 shell 命令。\n"
                "只输出命令本身，不要解释，不要加代码块标记。\n"
                "如果是安装包，输出 pip install xxx 格式。\n"
                "如果无法识别，输出：NONE",
                instruction[:200],
                temperature=0.0,
                max_tokens=80,
            )
            result = (result or '').strip().strip("`").splitlines()[0].strip()
            if result and result.upper() != "NONE" and len(result) < 200:
                first_word = result.split()[0].lower() if result.split() else ""
                known_cmds = {"pip", "python", "python3", "npm", "node", "git",
                              "pip3", "conda", "brew", "apt", "cargo", "go"}
                if first_word in known_cmds:
                    return result

        return ""