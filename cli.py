# cli.py
import os
import sys
import json
import re
import shutil
import unicodedata
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText
from rich.console import Console
from rich.panel import Panel

from core.registry import discover_tools, registry
from core.swarm import SwarmRouter
from core.memory import memory
from core.config import config
from core.toolkit import HermesToolkit

from core.hook_manager import hook_manager, HookEvent
from core.model_router import model_router
from core.permission_manager import permission_manager, PermissionMode

console = Console()

GLOBAL_STATE = {
    "balance": "Fetching..."
}

I18N = {
    "zh": {
        "tokens": "消耗 (Tokens)",
        "balance": "余额",
        "mode": "模式",
        "thinking": "AI 正在思考中...",
        "loaded_tools": "📦 已加载的工具:",
        "loaded_skills": "📚 已加载 {n} 个高级技能 (SOP)",
        "reload_done": "🔄 工具和技能已重新加载",
        "local_done": "🏠 引擎已切回本地 (Local)。",
        "custom_done": "🌐 引擎已切回云端 (Custom API)。",
        "ui_config_updated": "🎨 界面配置已更新: {key} = {val}",
        "config_updated": "✅ 配置更新: {target}.{key} = {val}",
        "format_error": "❌ 格式错误。用法: /set <key> <val>",
        "available_keys": "可用: url, model, api_key, theme, lang",
        "found_tools": "🔍 找到 {n} 个匹配的工具:",
        "not_found": "未找到匹配 '{pattern}' 的工具",
        "usage_search": "用法: /search <pattern>",
        "models": "🤖 可用模型:",
        "stats": "📊 系统统计:",
        "tools_count": "已加载工具",
        "skills_count": "已加载技能",
        "models_count": "可用模型",
        "token_used": "Token 消耗",
        "permission_status": "权限状态",
        "current_permission_mode": "当前权限模式",
        "blocked_tools": "本会话禁止工具",
        "none": "无",
        "permission_changed": "✅ 权限模式已切换为: {mode}",
        "blocked_tool": "🚫 已禁止本会话调用工具: {tool}",
        "unblocked_tool": "✅ 已解除禁止工具: {tool}",
        "usage_permission": "用法: /permission | /permission ask-first | /permission block <tool> | /permission unblock <tool>",
        "unknown_command": "⚠️ 未知命令: {cmd}",
        "help_hint": "输入 /help 查看可用命令",
        "help_title": "帮助",
        "help_body": (
            "[bold cyan]可用命令:[/]\n\n"
            "  [bold green]/reload[/] - 重新加载工具和技能\n"
            "  [bold green]/local[/] - 切换到本地模型\n"
            "  [bold green]/custom[/] - 切换到云端 API\n"
            "  [bold green]/set <key> <val>[/] - 设置配置\n"
            "  [bold green]/tools[/] - 显示已加载的工具\n"
            "  [bold green]/search <pattern>[/] - 搜索工具\n"
            "  [bold green]/models[/] - 显示可用模型\n"
            "  [bold green]/stats[/] - 显示系统统计\n"
            "  [bold green]/permission[/] - 权限控制\n"
            "  [bold green]exit/quit/q[/] - 退出系统\n\n"
            "[dim]提示: 查询类低风险终端命令会自动执行；安装、删除、写入、脚本执行仍会确认。[/]"
        ),
        "direct_command_title": "🛡️ 直接终端命令审查",
        "direct_command_detected": "检测到你直接输入了终端命令：",
        "risk_level": "风险等级",
        "workspace": "工作目录",
        "approve": "Y = 确认执行",
        "deny": "N = 拒绝本次",
        "block_execute": "B = 禁止本会话继续调用 execute_terminal",
        "choose": "请选择 [Y/N/B]，直接回车默认拒绝: ",
        "cancelled_command": "🚫 已取消本次终端命令",
        "denied_command": "🚫 已拒绝本次终端命令",
        "blocked_execute": "🚫 已禁止本会话继续调用 execute_terminal",
        "execute_terminal_missing": "❌ execute_terminal 工具未加载，无法执行终端命令。",
        "execute_terminal_blocked": "🚫 execute_terminal 已被本会话禁止。",
        "safe_low_risk": "✅ 低风险查询命令，自动执行: {cmd}",
        "running_command": "⚙️ 正在执行终端命令...",
        "terminal_output": "📟 终端输出:",
        "arg_fallback": "⚠️ 参数兼容失败，改用 command-only 模式重试: {err}",
        "sessions_found": "📂 发现以下历史纪元 (最近 5 次):",
        "new_timeline": "✨ 开启全新的时间线 (New Session)",
        "choose_session": "> 请输入纪元编号进行穿越 (0-5): ",
        "new_timeline_started": "✨ 已开启全新的时间线。",
        "invalid_session": "❌ 无效的编号，请重新输入。",
        "forced_new_timeline": "✨ 已强制开启全新的时间线。",
        "initial_timeline": "✨ 欢迎来到初始纪元。",
        "init_agents": "🤖 正在初始化 AI 代理...",
        "loading_tools": "🔄 正在加载工具和技能...",
        "system_ready": "SYSTEM READY",
        "ready_hint": "输入 /help 查看可用命令 | 输入 exit 退出",
        "task_type": "📋 任务类型",
        "fatal_error": "❌ 终端致命错误",
        "keyboard_interrupt": "⚠️ 收到中断信号，输入 exit 退出系统...",
        "bye": "👋 蜂群休眠模式启动，再见！",
    },
    "en": {
        "tokens": "Tokens",
        "balance": "Balance",
        "mode": "Mode",
        "thinking": "AI is thinking...",
        "loaded_tools": "📦 Loaded tools:",
        "loaded_skills": "📚 Loaded {n} advanced skills (SOP)",
        "reload_done": "🔄 Tools and skills reloaded",
        "local_done": "🏠 Engine switched to Local.",
        "custom_done": "🌐 Engine switched to Custom API.",
        "ui_config_updated": "🎨 UI config updated: {key} = {val}",
        "config_updated": "✅ Config updated: {target}.{key} = {val}",
        "format_error": "❌ Format error. Usage: /set <key> <val>",
        "available_keys": "Available: url, model, api_key, theme, lang",
        "found_tools": "🔍 Found {n} matching tools:",
        "not_found": "No tools matched '{pattern}'",
        "usage_search": "Usage: /search <pattern>",
        "models": "🤖 Available models:",
        "stats": "📊 System stats:",
        "tools_count": "Loaded tools",
        "skills_count": "Loaded skills",
        "models_count": "Available models",
        "token_used": "Token usage",
        "permission_status": "Permission status",
        "current_permission_mode": "Current permission mode",
        "blocked_tools": "Blocked tools in this session",
        "none": "None",
        "permission_changed": "✅ Permission mode switched to: {mode}",
        "blocked_tool": "🚫 Tool blocked for this session: {tool}",
        "unblocked_tool": "✅ Tool unblocked: {tool}",
        "usage_permission": "Usage: /permission | /permission ask-first | /permission block <tool> | /permission unblock <tool>",
        "unknown_command": "⚠️ Unknown command: {cmd}",
        "help_hint": "Type /help to see available commands",
        "help_title": "Help",
        "help_body": (
            "[bold cyan]Available commands:[/]\n\n"
            "  [bold green]/reload[/] - Reload tools and skills\n"
            "  [bold green]/local[/] - Switch to local model\n"
            "  [bold green]/custom[/] - Switch to custom API\n"
            "  [bold green]/set <key> <val>[/] - Update config\n"
            "  [bold green]/tools[/] - Show loaded tools\n"
            "  [bold green]/search <pattern>[/] - Search tools\n"
            "  [bold green]/models[/] - Show available models\n"
            "  [bold green]/stats[/] - Show system stats\n"
            "  [bold green]/permission[/] - Permission control\n"
            "  [bold green]exit/quit/q[/] - Exit\n\n"
            "[dim]Tip: low-risk query commands run automatically; install/delete/write/script execution still require approval.[/]"
        ),
        "direct_command_title": "🛡️ Direct Terminal Command Review",
        "direct_command_detected": "Detected a direct terminal command:",
        "risk_level": "Risk level",
        "workspace": "Working directory",
        "approve": "Y = Approve",
        "deny": "N = Deny this command",
        "block_execute": "B = Block execute_terminal for this session",
        "choose": "Choose [Y/N/B], press Enter to deny by default: ",
        "cancelled_command": "🚫 Terminal command cancelled",
        "denied_command": "🚫 Terminal command denied",
        "blocked_execute": "🚫 execute_terminal blocked for this session",
        "execute_terminal_missing": "❌ execute_terminal is not loaded, cannot run terminal commands.",
        "execute_terminal_blocked": "🚫 execute_terminal is blocked in this session.",
        "safe_low_risk": "✅ Low-risk query command, auto-running: {cmd}",
        "running_command": "⚙️ Running terminal command...",
        "terminal_output": "📟 Terminal output:",
        "arg_fallback": "⚠️ Argument compatibility failed; retrying command-only mode: {err}",
        "sessions_found": "📂 Found previous sessions (latest 5):",
        "new_timeline": "✨ Start a new timeline (New Session)",
        "choose_session": "> Choose a session number (0-5): ",
        "new_timeline_started": "✨ New timeline started.",
        "invalid_session": "❌ Invalid number, please try again.",
        "forced_new_timeline": "✨ Forced a new timeline.",
        "initial_timeline": "✨ Welcome to the initial timeline.",
        "init_agents": "🤖 Initializing AI agents...",
        "loading_tools": "🔄 Loading tools and skills...",
        "system_ready": "SYSTEM READY",
        "ready_hint": "Type /help for commands | Type exit to quit",
        "task_type": "📋 Task type",
        "fatal_error": "❌ Fatal terminal error",
        "keyboard_interrupt": "⚠️ Interrupt received. Type exit to quit...",
        "bye": "👋 Swarm entering sleep mode. Goodbye!",
    },
}


def lang():
    current = str(config.data.get("lang", "zh")).lower().strip()
    return "en" if current.startswith("en") else "zh"


def t(msg_key, **kwargs):
    value = I18N.get(lang(), I18N["zh"]).get(msg_key, msg_key)
    try:
        return value.format(**kwargs)
    except Exception:
        return value


def get_current_style():
    theme = config.data.get("theme", "dark")
    if theme == "light":
        return Style.from_dict({
            "prompt.icon": "#0055ff bold",
            "prompt.text": "#000000",
            "toolbar": "bg:#e0e0e0 #333333",
            "toolbar.model": "bg:#e0e0e0 #0055ff bold",
        })

    return Style.from_dict({
        "prompt.icon": "#00ffcc bold",
        "prompt.text": "#ffffff",
        "toolbar": "bg:#282a36 #f8f8f2",
        "toolbar.model": "bg:#282a36 #8be9fd bold",
    })


LOGO = r"""
██╗  ██╗███████╗██╗     ██╗██╗  ██╗    ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗
██║  ██║██╔════╝██║     ██║╚██╗██╔╝    ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║
███████║█████╗  ██║     ██║ ╚███╔╝     ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║
██╔══██║██╔══╝  ██║     ██║ ██╔██╗     ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║
██║  ██║███████╗███████╗██║██╔╝ ██╗    ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝    ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
             A U T O N O M O U S   M U L T I - A G E N T   S W A R M
"""


def get_display_width(text):
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ("F", "W", "A"):
            width += 2
        else:
            width += 1
    return width


def get_bottom_toolbar():
    used_tokens = config.data.get("total_tokens_used", 0)
    real_balance = GLOBAL_STATE.get("balance", "...")
    active_cfg = config.get_active()

    raw_model = active_cfg.get("model", "unknown")
    model_name = raw_model[:25] + "..." if len(raw_model) > 28 else raw_model
    mode_tag = "LOCAL" if config.data.get("active") == "local" else "CLOUD"

    left_text = f" ❖ Helix Swarm | ⚡ {t('tokens')}: {used_tokens:,} | 💰 {t('balance')}: {real_balance} "
    right_text = f" {mode_tag}: {model_name} 🧠 "

    term_width = shutil.get_terminal_size().columns
    padding_len = term_width - get_display_width(left_text) - get_display_width(right_text) - 1
    if padding_len < 0:
        padding_len = 0

    return FormattedText([
        ("class:toolbar", left_text),
        ("class:toolbar", " " * padding_len),
        ("class:toolbar.model", right_text),
    ])


def get_prompt():
    return FormattedText([
        ("class:prompt.icon", "\n❯ "),
        ("class:prompt.text", ""),
    ])


def get_thinking_status():
    used_tokens = config.data.get("total_tokens_used", 0)
    real_balance = GLOBAL_STATE.get("balance", "...")
    return f"⏳ {t('thinking')} | ⚡ {t('tokens')}: {used_tokens:,} | 💰 {t('balance')}: {real_balance}"


def setup_workspace():
    current_dir = Path(os.getcwd()).absolute()
    os.environ["TERMINAL_CWD"] = str(current_dir)
    return current_dir


def load_env_keys():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ[k.strip()] = v.strip()


def display_tools_summary():
    categories = {}
    for name, schema in registry.schemas.items():
        category = schema.get("category", "general")
        categories.setdefault(category, []).append(name)

    console.print(f"\n[bold cyan]{t('loaded_tools')}[/]")
    for category, tools in sorted(categories.items()):
        suffix = f" (+{len(tools) - 5} more)" if len(tools) > 5 else ""
        console.print(f"  [bold green]{category}[/]: {', '.join(tools[:5])}{suffix}")

    if registry.md_skills:
        console.print(f"[bold cyan]{t('loaded_skills', n=len(registry.md_skills))}[/]")


def looks_like_direct_shell_command(text: str) -> bool:
    if not text:
        return False

    stripped = text.strip()

    if "\n" in stripped:
        return False

    command_prefixes = (
        "curl ",
        "wget ",
        "git ",
        "python ",
        "python3 ",
        "pip ",
        "pip3 ",
        "npm ",
        "pnpm ",
        "yarn ",
        "brew ",
        "conda ",
        "chmod ",
        "bash ",
        "sh ",
        "zsh ",
        "skillhub ",
        "ls",
        "ls ",
        "pwd",
        "cd ",
        "cat ",
        "grep ",
        "find ",
        "mkdir ",
        "rm ",
        "mv ",
        "cp ",
        "open ",
        "./",
        "source ",
    )

    if stripped.startswith(command_prefixes):
        return True

    if re.search(r"\s(\|\||&&|\|)\s", stripped):
        first_word = stripped.split(maxsplit=1)[0]
        return first_word in {
            "curl",
            "wget",
            "python",
            "python3",
            "pip",
            "pip3",
            "npm",
            "pnpm",
            "yarn",
            "bash",
            "sh",
            "zsh",
            "git",
            "cat",
            "grep",
            "find",
            "echo",
            "skillhub",
        }

    return False


def command_risk_level(command: str) -> str:
    cmd = command.strip().lower()

    high_patterns = [
        r"curl\s+.*\|\s*(bash|sh|zsh)",
        r"wget\s+.*\|\s*(bash|sh|zsh)",
        r"rm\s+-rf",
        r"sudo\s+",
        r"chmod\s+777",
        r"mkfs",
        r"dd\s+if=",
        r">\s*/dev/",
        r"npm\s+install\s+-g",
        r"pip\s+install",
        r"pip3\s+install",
        r"brew\s+install",
        r"conda\s+install",
        r"skillhub\s+install",
    ]

    for pattern in high_patterns:
        if re.search(pattern, cmd):
            return "high"

    medium_patterns = [
        r"git\s+clone",
        r"python3?\s+",
        r"npm\s+install",
        r"pnpm\s+install",
        r"yarn\s+install",
        r"bash\s+",
        r"sh\s+",
        r"zsh\s+",
        r"mv\s+",
        r"cp\s+",
        r"mkdir\s+",
    ]

    for pattern in medium_patterns:
        if re.search(pattern, cmd):
            return "medium"

    return "low"


def is_safe_low_risk_command(command: str) -> bool:
    stripped = command.strip()
    cmd = stripped.lower()

    deny_patterns = [
        r"\|\s*(bash|sh|zsh)",
        r"\brm\b",
        r"\bmv\b",
        r"\bcp\b",
        r"\bchmod\b",
        r"\bsudo\b",
        r"\binstall\b",
        r"\bupgrade\b",
        r"\bupdate\b",
        r"\buninstall\b",
        r"\bdelete\b",
        r"\bremove\b",
        r">\s*",
        r">>\s*",
        r"\btee\b",
        r"\bdd\b",
        r"\bmkfs\b",
        r"\bkill\b",
        r"\bkillall\b",
    ]

    for pattern in deny_patterns:
        if re.search(pattern, cmd):
            return False

    allow_prefixes = (
        "skillhub search ",
        "skillhub list",
        "skillhub --version",
        "skillhub version",
        "which ",
        "where ",
        "pwd",
        "ls",
        "git status",
        "git branch",
        "git log",
        "git diff",
        "cat ",
        "head ",
        "tail ",
        "grep ",
        "find ",
        "python --version",
        "python3 --version",
        "pip --version",
        "pip3 --version",
        "node --version",
        "npm --version",
        "pnpm --version",
        "yarn --version",
        "brew --version",
        "conda --version",
    )

    return stripped.startswith(allow_prefixes)


def timeout_for_command(command: str) -> int:
    cmd = command.strip().lower()

    if "curl" in cmd and "|" in cmd:
        return 180
    if "skillhub install" in cmd:
        return 300
    if "pip install" in cmd or "pip3 install" in cmd:
        return 300
    if "npm install" in cmd or "pnpm install" in cmd or "yarn install" in cmd:
        return 300
    if "brew install" in cmd or "conda install" in cmd:
        return 600
    if "git clone" in cmd:
        return 300

    return 120


def execute_terminal_command(command: str):
    args = {
        "command": command,
        "timeout": timeout_for_command(command),
    }

    try:
        return registry.execute("execute_terminal", json.dumps(args, ensure_ascii=False))
    except TypeError as e:
        console.print(f"[yellow]{t('arg_fallback', err=e)}[/]")
        fallback_args = {
            "command": command,
        }
        return registry.execute("execute_terminal", json.dumps(fallback_args, ensure_ascii=False))


def run_direct_shell_command(command: str) -> bool:
    if "execute_terminal" not in registry.functions:
        console.print(f"[bold red]{t('execute_terminal_missing')}[/]")
        return True

    if "execute_terminal" in permission_manager.get_blocked_tools():
        console.print(f"[bold red]{t('execute_terminal_blocked')}[/]")
        return True

    risk = command_risk_level(command)

    if risk == "low" and is_safe_low_risk_command(command):
        console.print(f"[dim green]{t('safe_low_risk', cmd=command)}[/]")
        result = execute_terminal_command(command)
        console.print(f"\n[bold green]{t('terminal_output')}[/]")
        console.print(result)
        return True

    console.print(Panel(
        f"{t('direct_command_detected')}\n\n"
        f"[bold yellow]{command}[/]\n\n"
        f"{t('risk_level')}: [bold red]{risk}[/]\n"
        f"{t('workspace')}: [bold cyan]{os.getcwd()}[/]\n\n"
        f"[bold green]{t('approve')}[/]\n"
        f"[bold red]{t('deny')}[/]\n"
        f"[bold magenta]{t('block_execute')}[/]",
        title=t("direct_command_title"),
        border_style="yellow",
    ))

    try:
        choice = input(t("choose")).strip().lower()
    except KeyboardInterrupt:
        console.print(f"\n[bold red]{t('cancelled_command')}[/]")
        return True
    except EOFError:
        console.print(f"\n[bold red]{t('denied_command')}[/]")
        return True

    if choice in ("b", "block"):
        permission_manager.block_tool("execute_terminal")
        console.print(f"[bold magenta]{t('blocked_execute')}[/]")
        return True

    if choice not in ("y", "yes"):
        console.print(f"[bold red]{t('denied_command')}[/]")
        return True

    console.print(f"[bold cyan]{t('running_command')}[/]")
    result = execute_terminal_command(command)

    console.print(f"\n[bold green]{t('terminal_output')}[/]")
    console.print(result)

    return True


def handle_slash_command(user_input: str) -> bool:
    if user_input.lower() == "/reload":
        registry.reload_tools(["tools", "skills"])
        console.print(f"[bold green]{t('reload_done')}[/]")
        display_tools_summary()
        return True

    if user_input.lower() == "/local":
        config.switch_to_local()
        console.print(f"[bold green]{t('local_done')}[/]")
        GLOBAL_STATE["balance"] = HermesToolkit.get_api_balance()
        return True

    if user_input.lower() == "/custom":
        config.switch_to_custom()
        console.print(f"[bold cyan]{t('custom_done')}[/]")
        GLOBAL_STATE["balance"] = HermesToolkit.get_api_balance()
        return True

    if user_input.startswith("/set"):
        parts = user_input.split(maxsplit=2)
        if len(parts) == 3:
            key, val = parts[1], parts[2]

            if key in ["theme", "lang"]:
                config.data[key] = val
                config.save()
                console.print(f"[bold green]{t('ui_config_updated', key=key, val=val)}[/]")
                return True

            target = config.data.get("active", "local")

            if key.startswith("local."):
                target = "local"
                key = key.split(".", 1)[1]
                config.update_local(key, val)
            elif key.startswith("custom."):
                target = "custom"
                key = key.split(".", 1)[1]
                config.update_custom(key, val)
            else:
                config.update_active(key, val)

            console.print(f"[bold green]{t('config_updated', target=target, key=key, val=val)}[/]")
            GLOBAL_STATE["balance"] = HermesToolkit.get_api_balance()
        else:
            console.print(f"[red]{t('format_error')}[/]")
            console.print(f"[dim]{t('available_keys')}[/dim]")
        return True

    if user_input.lower() == "/tools":
        display_tools_summary()
        return True

    if user_input.lower().startswith("/search"):
        parts = user_input.split(maxsplit=1)
        pattern = parts[1] if len(parts) > 1 else ""
        if pattern:
            matches = []
            for name, schema in registry.schemas.items():
                desc = schema.get("function", {}).get("description", "")
                if pattern.lower() in name.lower() or pattern.lower() in desc.lower():
                    matches.append(name)

            if matches:
                console.print(f"\n[bold cyan]{t('found_tools', n=len(matches))}[/]")
                for match in matches:
                    console.print(f"  • {match}")
            else:
                console.print(f"[yellow]{t('not_found', pattern=pattern)}[/]")
        else:
            console.print(f"[red]{t('usage_search')}[/]")
        return True

    if user_input.lower() == "/models":
        console.print(f"\n[bold cyan]{t('models')}[/]")
        for model_info in model_router.get_all_models():
            console.print(
                f"  • {model_info['name']} ({model_info['provider']}) - "
                f"Speed: {model_info['speed_rating']}/10, "
                f"Quality: {model_info['quality_rating']}/10"
            )
        return True

    if user_input.lower() == "/stats":
        console.print(f"\n[bold cyan]{t('stats')}[/]")
        console.print(f"  • {t('tools_count')}: {len(registry.functions)}")
        console.print(f"  • {t('skills_count')}: {len(registry.md_skills)}")
        console.print(f"  • {t('models_count')}: {len(model_router.models)}")
        console.print(f"  • {t('token_used')}: {config.data.get('total_tokens_used', 0):,}")
        console.print(f"  • {t('balance')}: {GLOBAL_STATE.get('balance', '...')}")
        return True

    if user_input.lower().startswith("/permission"):
        parts = user_input.split()
        mode_aliases = {
            "default": PermissionMode.DEFAULT,
            "auto": PermissionMode.AUTO_APPROVE,
            "auto-approve": PermissionMode.AUTO_APPROVE,
            "plan": PermissionMode.PLAN_ONLY,
            "plan-only": PermissionMode.PLAN_ONLY,
            "ask": PermissionMode.ASK_FIRST,
            "ask-first": PermissionMode.ASK_FIRST,
            "never": PermissionMode.NEVER,
            "workspace": PermissionMode.WORKSPACE_ONLY,
            "workspace-only": PermissionMode.WORKSPACE_ONLY,
        }

        if len(parts) == 1:
            blocked = sorted(permission_manager.get_blocked_tools())
            blocked_text = ", ".join(blocked) if blocked else t("none")
            console.print(Panel(
                f"{t('current_permission_mode')}: [bold cyan]{permission_manager.mode.value}[/]\n"
                f"{t('blocked_tools')}: [bold yellow]{blocked_text}[/]\n\n"
                f"Commands:\n"
                f"  /permission ask-first\n"
                f"  /permission plan-only\n"
                f"  /permission workspace-only\n"
                f"  /permission block execute_terminal\n"
                f"  /permission unblock execute_terminal",
                title=t("permission_status"),
                border_style="yellow",
            ))
            return True

        if len(parts) == 2 and parts[1].lower() in mode_aliases:
            mode = mode_aliases[parts[1].lower()]
            permission_manager.set_mode(mode)
            console.print(f"[bold green]{t('permission_changed', mode=mode.value)}[/]")
            return True

        if len(parts) == 3 and parts[1].lower() == "block":
            permission_manager.block_tool(parts[2])
            console.print(f"[bold yellow]{t('blocked_tool', tool=parts[2])}[/]")
            return True

        if len(parts) == 3 and parts[1].lower() == "unblock":
            permission_manager.unblock_tool(parts[2])
            console.print(f"[bold green]{t('unblocked_tool', tool=parts[2])}[/]")
            return True

        console.print(f"[red]❌ {t('format_error')}[/]")
        console.print(f"[dim]{t('usage_permission')}[/dim]")
        return True

    if user_input.lower() == "/help":
        console.print(Panel(
            t("help_body"),
            title=t("help_title"),
            border_style="cyan",
        ))
        return True

    if user_input.startswith("/"):
        console.print(f"[yellow]{t('unknown_command', cmd=user_input)}[/]")
        console.print(f"[dim]{t('help_hint')}[/]")
        return True

    return False


def main():
    os.system("cls" if os.name == "nt" else "clear")

    theme_color = "cyan" if config.data.get("theme", "dark") == "dark" else "blue"
    console.print(LOGO, style=f"bold {theme_color}")

    workspace_dir = setup_workspace()
    load_env_keys()

    if os.getenv("OPENROUTER_API_KEY") and not config.data["custom"]["api_key"]:
        config.update_custom("api_key", os.getenv("OPENROUTER_API_KEY"))

    console.print(f"\n[bold cyan]{t('loading_tools')}[/]")
    discover_tools("tools")
    discover_tools("skills")
    registry.reload_md_skills("skills")

    display_tools_summary()

    all_sessions = memory.get_all_sessions()

    if all_sessions:
        console.print(f"\n[bold cyan]{t('sessions_found')}[/]")
        recent_sessions = sorted(all_sessions, key=lambda x: x["started_at"], reverse=True)[:5]

        for idx, s in enumerate(recent_sessions):
            msg_count = len(memory.load_session_history(s["id"])) // 2
            console.print(f"  [bold green][{idx + 1}][/] - {s['started_at'][:16]} ({msg_count} turns)")

        console.print(f"  [bold green][0][/] - {t('new_timeline')}")

        while True:
            try:
                choice = input(f"\n{t('choose_session')}").strip()

                if choice == "0":
                    memory.start_new_session()
                    history = []
                    console.print(f"[dim]{t('new_timeline_started')}[/]\n")
                    break

                if choice.isdigit() and 1 <= int(choice) <= len(recent_sessions):
                    selected_session = recent_sessions[int(choice) - 1]
                    memory.set_active_session(selected_session["id"])
                    history = memory.load_session_history(selected_session["id"])
                    console.print(f"[dim green]✅ {selected_session['started_at'][:16]}[/]\n")
                    break

                console.print(f"[red]{t('invalid_session')}[/]")
            except (KeyboardInterrupt, EOFError):
                console.print(f"\n[dim]{t('forced_new_timeline')}[/]\n")
                memory.start_new_session()
                history = []
                break
    else:
        memory.start_new_session()
        history = []
        console.print(f"[dim]{t('initial_timeline')}[/]\n")

    console.print(f"[bold cyan]{t('init_agents')}[/]")
    swarm = SwarmRouter()
    if history:
        swarm.supervisor.messages.extend(history)

    console.print(Panel.fit(
        f"🌐 Global Mode Active! Controlling directory:\n"
        f"[bold yellow]{workspace_dir}[/]\n\n"
        f"[dim]{t('ready_hint')}[/]",
        border_style=theme_color,
        title=f"[bold {theme_color}]{t('system_ready')}[/]",
    ))

    session = PromptSession(bottom_toolbar=get_bottom_toolbar, style=get_current_style())

    GLOBAL_STATE["balance"] = HermesToolkit.get_api_balance()

    while True:
        try:
            user_input = session.prompt(get_prompt).strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                console.print(f"\n[bold green]{t('bye')}[/]")
                break

            if handle_slash_command(user_input):
                continue

            if looks_like_direct_shell_command(user_input):
                run_direct_shell_command(user_input)
                GLOBAL_STATE["balance"] = HermesToolkit.get_api_balance()
                continue

            hook_manager.trigger(HookEvent.ON_MESSAGE, {
                "role": "user",
                "content": user_input,
            })

            task_type = model_router.classify_task(user_input)
            console.print(f"[dim]{t('task_type')}: {task_type.value}[/]")

            # Keep the old Helix-Swarm thinking animation.
            # Rich "status" uses a non-circle spinner such as dots2 and automatically
            # stops when swarm.chat returns or when normal output needs to be printed.
            with console.status(get_thinking_status(), spinner="dots2"):
                swarm.chat(user_input)

            GLOBAL_STATE["balance"] = HermesToolkit.get_api_balance()

        except KeyboardInterrupt:
            console.print(f"\n[dim yellow]{t('keyboard_interrupt')}[/]")
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"\n[bold red]{t('fatal_error')}: {e}[/]")


if __name__ == "__main__":
    main()