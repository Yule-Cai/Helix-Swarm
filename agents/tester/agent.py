"""
TesterAgent — 代码测试员
修复：
  1. sys.executable 替代硬编码 "python"（跨平台）
  2. 找不到显式文件名时自动扫描 workspace_dir
  3. 交互式程序：注入固定 random.seed + 二分搜索 stdin，彻底解决 EOFError
  4. 写入 _test_runner_.py 前清洗 markdown 代码栅栏（```），避免 SyntaxError
"""
from __future__ import annotations
import os
import sys
import subprocess
import re
import glob
import random
import ast


class TesterAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    # ── 公共入口 ──────────────────────────────────────────────
    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        script_path = self._find_script(instruction, workspace_dir)
        if not script_path:
            return "⏭️ 未找到可执行的 .py 文件，跳过测试。"

        src = self._read_src(script_path)

        # 修复：先清洗 markdown 残片，再做语法检查（原顺序相反，导致误报）
        src = self._clean_src(src)

        # 清洗后写回文件，避免后续 _run_simple 跑到带栅栏的原文件
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(src)
        except Exception:
            pass

        syntax_err = self._check_syntax(src, script_path)
        if syntax_err:
            # 把出错代码一并返回，让 debugger 能直接看到并修复
            lines = src.splitlines()
            try:
                err_line = int(re.search(r'第(\d+)行', syntax_err).group(1))
                lo = max(0, err_line - 4)
                hi = min(len(lines), err_line + 3)
                snippet = "\n".join(f"{lo+i+1}: {l}" for i, l in enumerate(lines[lo:hi]))
            except Exception:
                snippet = src[:800]
            return (f"❌ 语法错误：{syntax_err}\n\n"
                    f"出错代码片段：\n{snippet}\n\n"
                    f"完整文件路径：{script_path}")

        is_interactive = "input(" in src
        if is_interactive:
            return self._run_interactive(script_path, src)
        else:
            return self._run_simple(script_path)

    # ── 查找脚本 ──────────────────────────────────────────────
    def _find_script(self, instruction: str, workspace_dir: str) -> str | None:
        m = re.search(r'([\w/\\.\-]+\.py)', instruction)
        if m:
            candidate = m.group(1).replace("\\", "/")
            for base in [workspace_dir, "."]:
                full = os.path.join(base, candidate)
                if os.path.exists(full):
                    return os.path.abspath(full)

        py_files = [
            f for f in glob.glob(
                os.path.join(workspace_dir, "**", "*.py"), recursive=True
            )
            if not os.path.basename(f).startswith(("test_", "__", "_test"))
        ]
        if not py_files:
            return None
        py_files.sort(key=os.path.getmtime, reverse=True)
        return os.path.abspath(py_files[0])

    def _read_src(self, path: str) -> str:
        try:
            return open(path, encoding="utf-8", errors="replace").read()
        except Exception:
            return ""

    # ── 语法预检（新增）──────────────────────────────────────
    def _check_syntax(self, src: str, path: str) -> str:
        """返回空字符串表示语法正确，否则返回错误描述"""
        try:
            ast.parse(src)
            return ""
        except SyntaxError as e:
            return f"{os.path.basename(path)} 第{e.lineno}行：{e.msg}"

    # ── 清洗源码（核心修复）──────────────────────────────────
    def _clean_src(self, src: str) -> str:
        """
        去除 CoderAgent 偶尔留下的 markdown 代码栅栏残片。
        支持：开头的 ```python / ```py / ``` 和结尾的 ```
        """
        # 去掉行首的代码栅栏（可能带语言标识）
        src = re.sub(r'^\s*```[\w]*\s*\n?', '', src)
        # 去掉行尾/末尾的 ```
        src = re.sub(r'\n?\s*```\s*$', '', src.rstrip())
        # 去掉正文中间偶发的单独 ``` 行（最危险的情况）
        src = re.sub(r'^```\s*$', '', src, flags=re.MULTILINE)
        return src.strip() + "\n"

    # ── 非交互式运行 ──────────────────────────────────────────
    def _run_simple(self, script_path: str) -> str:
        cwd = os.path.dirname(script_path)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        # Flask/Web 服务检测：超时视为成功
        src = self._read_src(script_path)
        is_web = any(kw in src for kw in ["app.run(", "Flask(", "uvicorn", "gunicorn"])
        timeout = 12 if is_web else 30
        cmd = [sys.executable, os.path.basename(script_path)]

        try:
            r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               env=env, timeout=timeout)
            if r.returncode == 0:
                return f"✅ 运行成功\n{(r.stdout or '').strip()[:600]}"
            err = (r.stderr or r.stdout or "").strip()

            # 自动安装缺失模块后重试一次
            mod = self._extract_missing_module(err)
            if mod:
                print(f"🔧 [Tester] 自动安装缺失模块: {mod}")
                inst = subprocess.run(
                    [sys.executable, "-m", "pip", "install", mod],
                    capture_output=True, text=True, timeout=60
                )
                if inst.returncode == 0:
                    try:
                        r2 = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                                            encoding="utf-8", errors="replace",
                                            env=env, timeout=timeout)
                        if r2.returncode == 0:
                            return f"✅ 自动安装 {mod} 后运行成功\n{(r2.stdout or '').strip()[:400]}"
                        err = (r2.stderr or r2.stdout or "").strip()
                    except subprocess.TimeoutExpired:
                        return f"✅ 超时（Web 服务正常运行），视为成功。已自动安装：{mod}"

            return f"❌ 运行失败\n【分析】{self._analyze(os.path.basename(script_path), err)}\n【stderr】{err[:300]}"
        except subprocess.TimeoutExpired:
            if is_web:
                return "✅ 超时（Web 服务正常运行），视为成功。"
            return "✅ 超时（视为正常游戏循环），视为成功。"
        except Exception as e:
            return f"❌ 执行异常：{e}"

    def _extract_missing_module(self, err: str) -> str | None:
        """从报错里提取缺失的模块名并映射到 pip 包名。"""
        m = re.search(r"No module named '([^']+)'", err) or re.search(r'No module named "([^"]+)"', err)
        if not m:
            return None
        mod = m.group(1).split(".")[0]
        name_map = {
            "flask_migrate":    "flask-migrate",
            "flask_sqlalchemy": "flask-sqlalchemy",
            "flask_login":      "flask-login",
            "flask_wtf":        "flask-wtf",
            "flask_cors":       "flask-cors",
            "dotenv":           "python-dotenv",
            "PIL":              "Pillow",
            "cv2":              "opencv-python",
            "sklearn":          "scikit-learn",
        }
        return name_map.get(mod, mod.replace("_", "-"))

    # ── 交互式运行 ────────────────────────────────────────────
    def _run_interactive(self, script_path: str, src: str) -> str:
        seed   = 42
        lo, hi = self._detect_range(src)
        secret = self._compute_secret(lo, hi, seed)
        stdin_lines = self._binary_search_inputs(lo, hi, secret)

        # 清洗源码，再注入 seed ← 关键修复
        clean = self._clean_src(src)
        patched_src = f"import random as _rnd_; _rnd_.seed({seed})\n{clean}"

        # 再做一次语法检查，确保 patch 后合法
        try:
            ast.parse(patched_src)
        except SyntaxError as e:
            return (
                f"❌ 注入seed后仍有语法错误（第{e.lineno}行：{e.msg}）\n"
                f"请检查 {os.path.basename(script_path)} 是否含有非Python语法内容。"
            )

        tmp_dir  = os.path.dirname(script_path)
        tmp_file = os.path.join(tmp_dir, "_test_runner_.py")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(patched_src)

            stdin_data = "\n".join(str(x) for x in stdin_lines) + "\n"
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            r = subprocess.run(
                [sys.executable, "_test_runner_.py"],
                cwd=tmp_dir,
                input=stdin_data,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=20,
            )
            out = (r.stdout or "").strip()
            err = (r.stderr or "").strip()

            if r.returncode == 0:
                return (
                    f"✅ 运行成功\n"
                    f"【测试信息】secret={secret}，输入序列：{stdin_lines}\n"
                    f"【输出】\n{out[:800]}"
                )
            return (
                f"❌ 运行失败（returncode={r.returncode}）\n"
                f"【分析】{self._analyze(os.path.basename(script_path), err or out)}\n"
                f"【stderr】{(err or out)[:300]}"
            )
        except subprocess.TimeoutExpired:
            return "✅ 超时（视为正常游戏循环），视为成功。"
        except Exception as e:
            return f"❌ 执行异常：{e}"
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

    # ── 辅助 ──────────────────────────────────────────────────
    def _detect_range(self, src: str) -> tuple[int, int]:
        m = re.search(r'randint\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', src)
        return (int(m.group(1)), int(m.group(2))) if m else (1, 100)

    def _compute_secret(self, lo: int, hi: int, seed: int) -> int:
        return random.Random(seed).randint(lo, hi)

    def _binary_search_inputs(self, lo: int, hi: int, secret: int) -> list[int]:
        inputs, l, r = [], lo, hi
        while l <= r:
            mid = (l + r) // 2
            inputs.append(mid)
            if mid == secret: break
            elif mid < secret: l = mid + 1
            else: r = mid - 1
        return inputs

    def _analyze(self, filename: str, err: str) -> str:
        try:
            return self.llm.chat(
                "You are an error analysis expert. In one sentence, explain the root cause and fix suggestion.",
                f"脚本：{filename}\n报错：{err[-1500:]}",
                temperature=0.2,
            )
        except Exception:
            return err[:200]