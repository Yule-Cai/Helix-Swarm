# core/agent.py
import json
import os
import requests
import re

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from core.registry import registry
from core.prompt_builder import build_dynamic_system_prompt
from core.compressor import ContextCompressor
from core.smart_compressor import SmartCompressor
from core.hook_manager import hook_manager, HookEvent
from core.memory import memory
from core.config import config

from core.permission_manager import permission_manager, check_tool_permission, ToolCallRequest
from core.undo_manager import undo_manager, record_file_operation
from core.audit_logger import audit_logger, log_tool_call

from core.toolkit import HermesToolkit

console = Console()


class HermesAgent:
    """
    Helix-Swarm core agent.

    Features:
    - Automatically detects Gemma 4 models and enables official thinking mode.
    - Falls back to normal mode for non-thinking models.
    - Auto-approves native low-risk tools such as delegation, skill search, read/list/grep/glob.
    - Keeps write/delete/move/terminal/install operations behind approval.
    - Strips thinking output before saving to memory.
    - Uses Evidence Cards for review/security/risk tasks.
    - Follows config.data["lang"] for assistant output language.
    """

    AUTO_APPROVE_TOOLS = {
        "delegate_to_expert",
        "find_skills",
        "list_directory",
        "read_file",
        "read_dragged_file",
        "grep_search",
        "grep_code",
        "glob_files",
        "search_files",
        "search_file",
        "list_files",
        "list_skills",
        "get_skill",
        "inspect_skill",
        "read_skill",
    }

    NEVER_AUTO_APPROVE_TOOLS = {
        "execute_terminal",
        "run_command",
        "shell",
        "bash",
        "write_file",
        "edit_file",
        "delete_file",
        "move_file",
        "copy_file",
        "insert_at_line",
        "delete_lines",
        "replace_in_file",
        "apply_patch",
        "install_skill",
        "skillhub_install",
    }

    REVIEW_KEYWORDS = [
        "审查",
        "安全审查",
        "review",
        "code review",
        "security review",
        "找风险",
        "风险点",
        "找 bug",
        "找bug",
        "漏洞",
        "权限",
        "误判权限",
        "乱调用工具",
        "过度读取",
        "代码审查",
        "检查项目",
        "检查代码",
        "安全检查",
        "风险分析",
        "audit",
        "risk",
        "bug",
        "vulnerability",
        "permission",
    ]

    REVIEW_EVIDENCE_CARD_INSTRUCTION_ZH = """
[审查证据卡模式]

如果用户要求 review / 审查 / 风险分析 / 找 bug / 权限分析 / 项目安全检查，你必须遵守：

1. 最终回答不得泛泛而谈。
2. 每个发现必须基于工具结果中的具体代码证据。
3. 每个发现必须包含 Evidence Card：

Evidence Card N
- 文件路径 / File:
- 函数 / 类 / 规则名 / Symbol:
- 证据 / Evidence:
- 风险原因 / Why risky:
- 可能后果 / Consequence:
- 修复建议 / Suggested fix:

4. 如果无法定位具体文件路径和函数/类/规则名，必须说明：
   “证据不足：我还没有定位到具体文件和函数，不能给出该风险结论。”
5. 你应该继续使用搜索/读取工具获取证据，而不是根据通用安全常识猜测。
6. 对 Helix-Swarm 项目进行审查时，优先检查：
   - core/agent.py
   - core/permission_manager.py
   - core/registry.py
   - core/swarm.py
   - tools/
   - skills/
7. 如果任务要求“只读 / 不要修改 / do not modify”，不要声称已经完成修改，只能给出修复建议。
8. 最终回答必须包含优先级总结：
   - P0: 必须立即修复
   - P1: 应尽快修复
   - P2: 可优化
"""

    REVIEW_EVIDENCE_CARD_INSTRUCTION_EN = """
[REVIEW EVIDENCE CARD MODE]

If the user asks for review, code review, security review, risk analysis, bug finding, permission analysis, or project audit, you MUST follow these rules:

1. Do not give generic security advice as the final answer.
2. Every finding must be based on concrete code evidence from tool results.
3. Every finding must include an Evidence Card:

Evidence Card N
- File:
- Symbol:
- Evidence:
- Why risky:
- Consequence:
- Suggested fix:

4. If you cannot identify a concrete file path and function/class/rule name, say:
   "Insufficient evidence: I have not located a concrete file and symbol, so I cannot make this finding."
5. Continue using search/read tools to collect evidence instead of guessing from general security knowledge.
6. For Helix-Swarm reviews, prefer checking:
   - core/agent.py
   - core/permission_manager.py
   - core/registry.py
   - core/swarm.py
   - tools/
   - skills/
7. If the task says "read-only" or "do not modify", do not claim that edits have been completed. Only provide suggested fixes.
8. The final answer must include a priority summary:
   - P0: must fix immediately
   - P1: should fix soon
   - P2: improvement
"""

    def __init__(self, name="Agent", custom_prompt=None, allowed_tools=None, permission_mode=None):
        self.name = name
        self.custom_prompt = custom_prompt

        active_cfg = config.get_active()
        self.api_url = active_cfg["url"]
        self.model = active_cfg["model"]
        self.api_key = active_cfg["api_key"]

        if permission_mode:
            permission_manager.set_mode(permission_mode)

        audit_logger.start_session(user_id=name)

        self.thinking_enabled = self._model_supports_thinking(self.model)
        self.base_system_prompt = self._build_base_system_prompt(self.custom_prompt)

        self.messages = [{
            "role": "system",
            "content": self._build_final_system_prompt(),
        }]

        if allowed_tools:
            self.tools_schemas = [registry.get_schema(t) for t in allowed_tools if registry.get_schema(t)]
        else:
            self.tools_schemas = list(registry.schemas.values())

        self.compressor = ContextCompressor(self.api_url, self.model, max_tokens=32000)
        self.smart_compressor = SmartCompressor(max_tokens=32000)

    # -------------------------------------------------------------------------
    # Language / i18n
    # -------------------------------------------------------------------------
    def _current_lang(self) -> str:
        lang = str(config.data.get("lang", "zh")).lower().strip()
        if lang.startswith("en"):
            return "en"
        return "zh"

    def _is_en(self) -> bool:
        return self._current_lang() == "en"

    def _reply_label(self) -> str:
        return "Reply" if self._is_en() else "回复"

    def _language_instruction(self) -> str:
        if self._is_en():
            return (
                "CURRENT INTERFACE LANGUAGE: English.\n"
                "You MUST reply in English by default.\n"
                "Do not switch to Chinese unless the user explicitly asks for Chinese.\n"
                "All headings, summaries, tool explanations, option lists, review reports, and final answers should be in English.\n"
                "If the user sends Chinese while the interface language is English, understand the Chinese request but still answer in English unless they explicitly ask you to answer in Chinese.\n"
            )

        return (
            "当前界面语言：中文。\n"
            "默认必须使用中文回答。\n"
            "除非用户明确要求英文，否则不要切换到英文。\n"
            "所有标题、总结、工具解释、选项列表、审查报告和最终回答都应使用中文。\n"
            "如果用户发送英文但界面语言是中文，请理解英文请求，但默认仍用中文回答，除非用户明确要求英文回答。\n"
        )

    def _review_instruction(self) -> str:
        return (
            self.REVIEW_EVIDENCE_CARD_INSTRUCTION_EN
            if self._is_en()
            else self.REVIEW_EVIDENCE_CARD_INSTRUCTION_ZH
        )

    def _txt(self, key: str) -> str:
        lang = self._current_lang()
        texts = {
            "zh": {
                "permission_panel_title": "🛡️ 工具调用审查",
                "tool": "工具",
                "risk": "风险等级",
                "args": "参数",
                "approve": "Y = 确认执行",
                "deny": "N = 拒绝本次",
                "block": "B = 禁止该工具本会话继续调用",
                "choose": "请选择 [Y/N/B]，直接回车默认拒绝: ",
                "cancelled": "🚫 已取消本次工具调用",
                "permission_denied": "权限拒绝",
                "tool_blocked": "已禁止本会话继续调用工具",
                "tool_rejected": "已拒绝本次工具调用",
                "safe_tool": "安全原生工具，自动允许",
                "exec_tool": "执行工具",
                "connection_failed": "连接失败",
                "network_error": "网络异常",
                "api_error": "API 报错",
                "bad_json": "响应不是合法 JSON",
                "raw_response": "原始响应",
                "diagnosis": "💡 诊断建议",
                "missing_choices": "响应缺少 choices 字段",
                "extract_message_failed": "无法提取 message 字段",
                "dragged_file": "🔍 系统拦截：检测到本地拖拽文件，已下发读取指令...",
                "thinking_mode_on": "开启",
                "thinking_mode_off": "关闭",
            },
            "en": {
                "permission_panel_title": "🛡️ Tool Call Review",
                "tool": "Tool",
                "risk": "Risk level",
                "args": "Arguments",
                "approve": "Y = Approve",
                "deny": "N = Deny this call",
                "block": "B = Block this tool for this session",
                "choose": "Choose [Y/N/B], press Enter to deny by default: ",
                "cancelled": "🚫 Tool call cancelled",
                "permission_denied": "Permission denied",
                "tool_blocked": "Tool blocked for this session",
                "tool_rejected": "Tool call rejected",
                "safe_tool": "Safe native tool, auto-approved",
                "exec_tool": "Executing tool",
                "connection_failed": "Connection failed",
                "network_error": "Network error",
                "api_error": "API error",
                "bad_json": "Response is not valid JSON",
                "raw_response": "Raw response",
                "diagnosis": "💡 Diagnosis",
                "missing_choices": "Response is missing the choices field",
                "extract_message_failed": "Failed to extract message field",
                "dragged_file": "🔍 System intercept: local dragged file detected; read instruction injected...",
                "thinking_mode_on": "enabled",
                "thinking_mode_off": "disabled",
            },
        }
        return texts.get(lang, texts["zh"]).get(key, key)

    # -------------------------------------------------------------------------
    # Thinking mode
    # -------------------------------------------------------------------------
    def _model_supports_thinking(self, model_name: str) -> bool:
        force = os.getenv("HELIX_FORCE_THINKING", "").strip().lower()
        if force in ("1", "true", "yes", "on"):
            return True
        if force in ("0", "false", "no", "off"):
            return False

        if not model_name:
            return False

        m = model_name.lower()

        if "gemma-3" in m or "gemma3" in m:
            return False
        if "gemma-2" in m or "gemma2" in m:
            return False
        if "gemma-1" in m or "gemma1" in m:
            return False

        gemma4_markers = [
            "gemma-4",
            "gemma4",
            "google/gemma-4",
            "google/gemma4",
        ]

        return any(marker in m for marker in gemma4_markers)

    def _build_base_system_prompt(self, custom_prompt=None) -> str:
        md_skills_intro = registry.get_all_md_skills_summary()
        system_content = custom_prompt if custom_prompt else build_dynamic_system_prompt()

        return (
            f"{self._language_instruction()}\n\n"
            f"{system_content}\n\n"
            f"{md_skills_intro}\n\n"
            f"To use an Advanced Skill (SOP), read its .md file in the skills/ directory using the read_file tool, "
            f"then follow its instructions strictly to complete the task.\n\n"
            f"SUPREME DIRECTIVE FOR LOCAL SMALL MODELS: If you need to explore code, files, or skills, "
            f"use search/list tools first (`grep_code`, `glob_files`, `grep_search`, `find_skills`, or `list_directory`). "
            f"Do not blindly use `read_file` to read entire files to understand a project. "
            f"Read targeted files only after search results identify them.\n\n"
            f"IMPORTANT TRUTHFULNESS RULE: Do not pretend that a tool has fetched, read, installed, or executed anything. "
            f"If a tool result is unavailable, empty, or incomplete, say that clearly. "
            f"When comparing skills, tools, packages, or files, base the comparison on actual tool output. "
            f"If you only infer from names, explicitly say it is an inference and not verified documentation.\n\n"
            f"IMPORTANT URL RULE: If the user gives a URL such as https://example.com/file.sh, never treat URL path segments "
            f"as local files. URL paths are not local dragged files.\n\n"
            f"IMPORTANT OPTION-SELECTION RULE: When you present multiple possible choices or plans, format them as numbered "
            f"options so the user can reply with 1, 2, 3, 4, etc. Also include a final custom option such as "
            f"`Other / 自定义：你可以输入自己的想法` when appropriate. "
            f"Example: `1. Install calendar-cli`, `2. Install google-calendar`, `3. Install google-calendar-api`, "
            f"`4. Do not install yet; continue comparing`, `5. Custom: type your specific requirement`.\n\n"
            f"{self._review_instruction()}"
        )

    def _build_final_system_prompt(self) -> str:
        if self.thinking_enabled:
            return (
                "<|think|>\n"
                f"{self.base_system_prompt}\n\n"
                "You may use your private thought channel for difficult reasoning, planning, tool selection, and verification. "
                "Do not expose raw thought unless explicitly requested by the system. "
                "Return a clear final answer for the user."
            )

        return self.base_system_prompt

    def _sync_system_prompt_for_current_model(self):
        new_thinking_enabled = self._model_supports_thinking(self.model)

        if new_thinking_enabled != self.thinking_enabled:
            self.thinking_enabled = new_thinking_enabled
            mode_text = self._txt("thinking_mode_on") if self.thinking_enabled else self._txt("thinking_mode_off")
            console.print(f"[dim cyan]🧠 Thinking mode automatically {mode_text}: {self.model}[/]")

        # Rebuild base prompt every time so /set lang en or /set lang zh takes effect immediately.
        self.base_system_prompt = self._build_base_system_prompt(self.custom_prompt)
        final_prompt = self._build_final_system_prompt()

        if not self.messages:
            self.messages = [{"role": "system", "content": final_prompt}]
            return

        if self.messages[0].get("role") == "system":
            self.messages[0]["content"] = final_prompt
        else:
            self.messages.insert(0, {"role": "system", "content": final_prompt})

    def _strip_thinking_output(self, text: str) -> str:
        if not text:
            return ""

        cleaned = text

        cleaned = re.sub(
            r"<\|channel\>thought\s*.*?<channel\|>",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )

        cleaned = re.sub(
            r"<\|channel\>thought\s*.*?<\|channel\>final",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )

        cleaned = re.sub(
            r"<think>.*?</think>",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )

        cleaned = re.sub(
            r"<thought>.*?</thought>",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )

        cleaned = cleaned.replace("<|channel>final", "")
        cleaned = cleaned.replace("<channel|>", "")
        cleaned = cleaned.replace("<|final|>", "")
        cleaned = cleaned.replace("<|answer|>", "")

        return cleaned.strip()

    def _sanitize_assistant_message_for_history(self, message: dict) -> dict:
        safe_message = {
            "role": "assistant",
        }

        content = message.get("content", "")
        if content:
            safe_message["content"] = self._strip_thinking_output(content)
        else:
            safe_message["content"] = ""

        if "tool_calls" in message and message["tool_calls"]:
            safe_message["tool_calls"] = message["tool_calls"]

        return safe_message

    # -------------------------------------------------------------------------
    # Runtime config
    # -------------------------------------------------------------------------
    def _refresh_runtime_config(self):
        active_cfg = config.get_active()
        old_model = self.model

        self.api_url = active_cfg.get("url", self.api_url)
        self.model = active_cfg.get("model", self.model)
        self.api_key = active_cfg.get("api_key", self.api_key)

        if hasattr(self, "compressor"):
            self.compressor.api_url = self.api_url
            self.compressor.model = self.model

        if self.model != old_model:
            self._sync_system_prompt_for_current_model()
        else:
            self._sync_system_prompt_for_current_model()

    # -------------------------------------------------------------------------
    # Review task helpers
    # -------------------------------------------------------------------------
    def _looks_like_review_task(self, text: str) -> bool:
        if not text:
            return False

        t = text.lower()

        for keyword in self.REVIEW_KEYWORDS:
            if keyword.lower() in t:
                return True

        return False

    def _inject_review_evidence_instruction(self, user_input: str) -> str:
        if not self._looks_like_review_task(user_input):
            return user_input

        if "Evidence Card" in user_input or "证据卡" in user_input:
            return user_input

        if self._is_en():
            return (
                f"{user_input}\n\n"
                f"[System review requirement] This is a review / audit / risk analysis task. "
                f"The final answer MUST use Evidence Cards and MUST NOT be generic. "
                f"Every finding must include: file path, function/class/rule name, evidence, why risky, consequence, and suggested fix. "
                f"If you cannot locate a concrete file and symbol, do not invent a finding; state that the evidence is insufficient."
            )

        return (
            f"{user_input}\n\n"
            f"【系统审查要求】本任务属于 review / 审查 / 风险分析类任务。"
            f"最终回答必须使用 Evidence Card，不允许泛泛而谈。"
            f"每个风险点必须包含：文件路径、函数/类/规则名、证据、风险原因、可能后果、修复建议。"
            f"如果没有定位到具体文件和函数，不要编造结论，必须说明证据不足。"
        )

    # -------------------------------------------------------------------------
    # Local path detection
    # -------------------------------------------------------------------------
    def _remove_urls_before_path_detection(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"https?://[^\s\"'<>]+", "", text, flags=re.IGNORECASE)

    def _extract_local_file_path(self, text: str):
        if not text:
            return None

        clean_text = self._remove_urls_before_path_detection(text)

        patterns = [
            r"file://(?P<path>/[^\s\"'<>\|]+?\.[A-Za-z0-9]{1,10})",
            r"file:///(?P<path>[A-Za-z]:/[^\s\"'<>\|]+?\.[A-Za-z0-9]{1,10})",
            r"(?P<path>/Users/[^\s\"'<>\|]+?\.[A-Za-z0-9]{1,10})",
            r"(?P<path>/Volumes/[^\s\"'<>\|]+?\.[A-Za-z0-9]{1,10})",
            r"(?P<path>/home/[^\s\"'<>\|]+?\.[A-Za-z0-9]{1,10})",
            r"(?P<path>~/[^\s\"'<>\|]+?\.[A-Za-z0-9]{1,10})",
            r"(?P<path>[A-Za-z]:[\\/][^\s\"'<>\|]+?\.[A-Za-z0-9]{1,10})",
        ]

        for pattern in patterns:
            match = re.search(pattern, clean_text)
            if not match:
                continue

            candidate = match.group("path")

            if candidate.startswith("http://") or candidate.startswith("https://"):
                continue

            if "://" in candidate and not candidate.startswith("file://"):
                continue

            return candidate

        return None

    # -------------------------------------------------------------------------
    # Permission helpers
    # -------------------------------------------------------------------------
    def _is_native_safe_tool(self, fn_name: str, args_dict: dict) -> bool:
        if fn_name in self.NEVER_AUTO_APPROVE_TOOLS:
            return False

        if fn_name in self.AUTO_APPROVE_TOOLS:
            return True

        lowered = fn_name.lower()

        if lowered.startswith("read_"):
            return True

        if lowered.startswith("list_"):
            return True

        if lowered.startswith("search_"):
            return True

        if lowered.startswith("grep_"):
            return True

        if lowered.startswith("glob_"):
            return True

        if lowered.startswith("find_") and "install" not in lowered:
            return True

        risky_words = [
            "install",
            "delete",
            "remove",
            "write",
            "edit",
            "move",
            "copy",
            "terminal",
            "shell",
            "bash",
            "command",
            "execute",
            "patch",
        ]

        if any(word in lowered for word in risky_words):
            return False

        return False

    def _ask_user_for_tool_approval(self, fn_name: str, args_dict: dict, risk_level: str) -> str:
        if os.getenv("HELIX_NONINTERACTIVE_APPROVAL") == "deny":
            return "deny"

        console.print(Panel(
            f"{self._txt('tool')}: [bold yellow]{fn_name}[/]\n"
            f"{self._txt('risk')}: [bold red]{risk_level}[/]\n"
            f"{self._txt('args')}:\n[dim]{json.dumps(args_dict, ensure_ascii=False, indent=2)}[/]\n\n"
            f"[bold green]{self._txt('approve')}[/]\n"
            f"[bold red]{self._txt('deny')}[/]\n"
            f"[bold magenta]{self._txt('block')}[/]",
            title=self._txt("permission_panel_title"),
            border_style="yellow",
        ))

        try:
            choice = input(self._txt("choose")).strip().lower()
        except EOFError:
            return "deny"
        except KeyboardInterrupt:
            console.print(f"\n[bold red]{self._txt('cancelled')}[/]")
            return "deny"

        if choice in ("y", "yes"):
            return "approve"

        if choice in ("b", "block"):
            permission_manager.block_tool(fn_name)
            return "block"

        return "deny"

    # -------------------------------------------------------------------------
    # Main run loop
    # -------------------------------------------------------------------------
    def run(self, user_input: str, return_result: bool = False):
        self._refresh_runtime_config()

        hook_manager.trigger(HookEvent.ON_MESSAGE, {
            "role": "user",
            "content": user_input,
        })

        user_input = self._inject_review_evidence_instruction(user_input)

        extracted_path = self._extract_local_file_path(user_input)

        if extracted_path:
            original_input = user_input
            if self._is_en():
                user_input = (
                    f"[SYSTEM INSTRUCTION] A local file path was detected: {extracted_path}\n"
                    f"The file content is required before answering the user.\n"
                    f"If you have the `read_dragged_file` tool, call it immediately.\n"
                    f"If you only have `delegate_to_expert`, delegate to a relevant expert and explicitly require the expert to first call "
                    f"`read_dragged_file` with this path: {extracted_path}.\n"
                    f"If the path does not exist or cannot be read, clearly report the failure reason.\n\n"
                    f"--- Original user message ---\n"
                    f"{original_input}"
                )
            else:
                user_input = (
                    f"【系统强制指令】检测到本地文件路径：{extracted_path}\n"
                    f"该文件内容是你完成任务的绝对前提。\n"
                    f"如果你自己拥有 `read_dragged_file` 工具，请立刻亲自调用它。\n"
                    f"如果你只有 `delegate_to_expert` 工具，你必须委派给相关下属，"
                    f"并在委派描述中要求下属第一步调用 read_dragged_file 读取路径：{extracted_path}。\n"
                    f"如果该路径不存在或无法读取，请明确报告失败原因。\n\n"
                    f"---用户原话---\n"
                    f"{original_input}"
                )
            console.print(f"[dim cyan]{self._txt('dragged_file')}[/]")

        safe_input = HermesToolkit.redact(user_input)
        memory.save_message("user", safe_input)
        self.messages.append({"role": "user", "content": safe_input})

        while True:
            self.messages = self.smart_compressor.compress_if_needed(self.messages)
            self.messages = self.compressor.compress_if_needed(self.messages)

            payload = {
                "model": self.model,
                "messages": self.messages,
                "temperature": 0.2,
            }

            if self.tools_schemas:
                payload["tools"] = self.tools_schemas

            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

                raw_response = HermesToolkit.jittered_request(
                    self.api_url,
                    payload,
                    headers,
                    timeout=None,
                )

            except requests.exceptions.ConnectionError:
                err_msg = f"Cannot connect to API: {self.api_url}\nPlease check whether the local model server is running and the port is correct." if self._is_en() else f"无法连接到 API：{self.api_url}\n请检查：本地模型是否已启动？端口是否正确？"
                console.print(f"\n[bold red]❌ [{self.name}] {self._txt('connection_failed')}:[/] {self.api_url}")
                console.print(Panel(HermesToolkit.diagnose_error(err_msg), border_style="yellow"))
                return "Error"

            except Exception as e:
                console.print(f"\n[bold red]❌ [{self.name}] {self._txt('network_error')}:[/] {str(e)}")
                console.print(Panel(HermesToolkit.diagnose_error(str(e)), border_style="yellow"))
                return "Error"

            if raw_response.status_code != 200:
                error_text = raw_response.text
                console.print(f"\n[bold red]❌ [{self.name}] {self._txt('api_error')} (HTTP {raw_response.status_code}):[/]\n{error_text}")
                console.print(Panel(HermesToolkit.diagnose_error(error_text), border_style="yellow"))
                return "Error"

            try:
                response = raw_response.json()
            except Exception as e:
                raw_text = raw_response.text.strip()
                console.print(f"\n[bold red]❌ [{self.name}] {self._txt('bad_json')}:[/] {str(e)}")
                console.print(f"[dim]📄 {self._txt('raw_response')} ({len(raw_text)} chars):[/]")
                console.print(f"[dim yellow]{raw_text[:500]}{'...' if len(raw_text) > 500 else ''}[/]")

                if self._is_en():
                    diagnosis_text = (
                        "Possible causes:\n"
                        "1. Context is too long and the model returned an empty response.\n"
                        "2. The model does not support the tools field.\n"
                        "3. The local model is still loading.\n"
                        "4. The API URL or model name is incorrect."
                    )
                else:
                    diagnosis_text = (
                        "可能原因：\n"
                        "① 模型上下文超长，返回了空响应\n"
                        "② 模型不支持 tools 字段\n"
                        "③ 本地模型还在加载中\n"
                        "④ API URL 或模型名称配置错误"
                    )

                console.print(Panel(
                    diagnosis_text,
                    border_style="yellow",
                    title=self._txt("diagnosis"),
                ))
                return "Error"

            if "choices" not in response or not response["choices"]:
                console.print(f"\n[bold red]❌ [{self.name}] {self._txt('missing_choices')}:[/]")
                console.print(f"[dim yellow]{str(response)[:300]}[/]")
                console.print(Panel(HermesToolkit.diagnose_error(str(response)), border_style="yellow"))
                return "Error"

            usage = response.get("usage", {})
            if usage:
                key_id = f"...{self.api_key[-6:]}" if self.api_key else "default"

                if "keys_usage" not in config.data:
                    config.data["keys_usage"] = {}

                config.data["keys_usage"][key_id] = (
                    config.data["keys_usage"].get(key_id, 0)
                    + usage.get("total_tokens", 0)
                )

                config.data["total_tokens_used"] = config.data["keys_usage"][key_id]
                config.save()

            try:
                raw_message = response["choices"][0]["message"]
            except (KeyError, IndexError) as e:
                console.print(f"\n[bold red]❌ [{self.name}] {self._txt('extract_message_failed')}:[/] {str(e)}")
                console.print(f"[dim yellow]{str(response)[:300]}[/]")
                return "Error"

            if os.getenv("HELIX_DEBUG_THINKING", "").strip().lower() in ("1", "true", "yes", "on"):
                console.print("[bold magenta]🧠 Raw assistant message:[/]")
                console.print(json.dumps(raw_message, ensure_ascii=False, indent=2)[:4000])

            message = self._sanitize_assistant_message_for_history(raw_message)
            self.messages.append(message)

            if "tool_calls" in message and message["tool_calls"]:
                for tool_call in message["tool_calls"]:
                    fn_name = tool_call["function"]["name"]
                    fn_args = tool_call["function"]["arguments"]

                    console.print(f"  [bold yellow]⚡ [{self.name}] {self._txt('exec_tool')}:[/] {fn_name}")

                    try:
                        args_dict = json.loads(fn_args) if isinstance(fn_args, str) else fn_args
                    except Exception:
                        args_dict = {}

                    permission_decision = check_tool_permission(fn_name, args_dict)

                    audit_logger.log_permission_check(
                        tool_name=fn_name,
                        arguments=args_dict,
                        allowed=permission_decision.allowed,
                        reason=permission_decision.reason,
                        risk_level=permission_decision.risk_level.value,
                    )

                    if not permission_decision.allowed:
                        observation = f"Permission denied: {permission_decision.reason}"
                        console.print(f"  [bold red]🚫 {self._txt('permission_denied')}:[/] {permission_decision.reason}")
                        log_tool_call(
                            fn_name,
                            args_dict,
                            observation,
                            success=False,
                            risk_level=permission_decision.risk_level.value,
                        )

                    elif self._is_native_safe_tool(fn_name, args_dict):
                        console.print(f"  [dim green]✅ {self._txt('safe_tool')}:[/] {fn_name}")
                        observation = self._execute_approved_tool(
                            fn_name,
                            fn_args,
                            args_dict,
                            permission_decision,
                        )

                    elif permission_decision.requires_approval:
                        action = self._ask_user_for_tool_approval(
                            fn_name,
                            args_dict,
                            permission_decision.risk_level.value,
                        )

                        approved = action == "approve"

                        permission_manager.record_approval(
                            ToolCallRequest(tool_name=fn_name, arguments=args_dict),
                            permission_decision,
                            approved,
                        )

                        if action == "approve":
                            observation = self._execute_approved_tool(
                                fn_name,
                                fn_args,
                                args_dict,
                                permission_decision,
                            )

                        elif action == "block":
                            observation = f"Permission denied: user blocked tool {fn_name} for this session"
                            console.print(f"  [bold magenta]🚫 {self._txt('tool_blocked')}:[/] {fn_name}")
                            log_tool_call(
                                fn_name,
                                args_dict,
                                observation,
                                success=False,
                                risk_level=permission_decision.risk_level.value,
                            )

                        else:
                            observation = "Permission denied: user rejected this tool call"
                            console.print(f"  [bold red]🚫 {self._txt('tool_rejected')}[/]")
                            log_tool_call(
                                fn_name,
                                args_dict,
                                observation,
                                success=False,
                                risk_level=permission_decision.risk_level.value,
                            )

                    else:
                        observation = self._execute_approved_tool(
                            fn_name,
                            fn_args,
                            args_dict,
                            permission_decision,
                        )

                    hook_manager.trigger(HookEvent.POST_TOOL_CALL, {
                        "tool_name": fn_name,
                        "args": args_dict,
                        "result": observation,
                        "success": "Error" not in str(observation),
                    })

                    safe_observation = HermesToolkit.redact(str(observation))

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": fn_name,
                        "content": safe_observation,
                    })

                continue

            content = message.get("content", "")
            if content:
                safe_content = HermesToolkit.redact(self._strip_thinking_output(content))
                memory.save_message("assistant", safe_content)

                if not return_result:
                    console.print(f"\n[bold green]🤖 {self.name} {self._reply_label()}:[/]")
                    console.print(Markdown(safe_content))

                return safe_content

            break

    def _execute_approved_tool(self, fn_name, fn_args, args_dict, permission_decision):
        hook_context = hook_manager.trigger(HookEvent.PRE_TOOL_CALL, {
            "tool_name": fn_name,
            "args": args_dict,
        })

        if hook_context.cancelled:
            return f"Operation cancelled: {hook_context.data.get('cancel_reason', 'No reason')}"

        file_ops = [
            "write_file",
            "edit_file",
            "delete_file",
            "move_file",
            "copy_file",
            "insert_at_line",
            "delete_lines",
        ]

        op = None
        if fn_name in file_ops:
            op = record_file_operation(fn_name, args_dict)

        import time
        start_time = time.time()

        observation = registry.execute(fn_name, fn_args)

        duration_ms = int((time.time() - start_time) * 1000)

        if op is not None:
            undo_manager.complete_operation(op, success="Error" not in str(observation))

        log_tool_call(
            fn_name,
            args_dict,
            str(observation),
            success="Error" not in str(observation),
            risk_level=permission_decision.risk_level.value,
            agent_name=self.name,
            duration_ms=duration_ms,
        )

        return observation