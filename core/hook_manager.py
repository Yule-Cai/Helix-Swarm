# core/hook_manager.py
import logging
from typing import Callable, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)

class HookEvent(Enum):
    """Available hook events."""
    PRE_TOOL_CALL = "pre_tool_call"
    POST_TOOL_CALL = "post_tool_call"
    PRE_COMMIT = "pre_commit"
    POST_COMMIT = "post_commit"
    PRE_PUSH = "pre_push"
    POST_PUSH = "post_push"
    ON_ERROR = "on_error"
    ON_MESSAGE = "on_message"
    ON_RESPONSE_START = "on_response_start"
    ON_RESPONSE_END = "on_response_end"
    ON_FILE_CHANGE = "on_file_change"
    ON_CONTEXT_COMPRESS = "on_context_compress"

@dataclass
class HookContext:
    """Context passed to hook handlers."""
    event: HookEvent
    data: Dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False

    def cancel(self, reason: str = ""):
        """Cancel the current operation."""
        self.cancelled = True
        self.data["cancel_reason"] = reason

class HookManager:
    """
    Manages hooks for extensible behavior.

    Hooks allow users to customize behavior at key points:
    - Before/after tool calls
    - Before/after git operations
    - Error handling
    - Message processing
    - File changes
    """

    def __init__(self):
        self.hooks: Dict[HookEvent, List[Callable]] = {}
        self._load_default_hooks()

    def _load_default_hooks(self):
        """Load default hook handlers."""
        # Security hook: prevent dangerous commands
        self.register(HookEvent.PRE_TOOL_CALL, self._security_check_hook)

        # Logging hook: log all tool calls
        self.register(HookEvent.POST_TOOL_CALL, self._logging_hook)

    def register(self, event: HookEvent, handler: Callable, priority: int = 0):
        """
        Register a hook handler.

        Args:
            event: The event to hook into
            handler: Callable that receives HookContext
            priority: Higher priority hooks run first (default: 0)
        """
        if event not in self.hooks:
            self.hooks[event] = []

        # Store with priority for sorting
        self.hooks[event].append((priority, handler))
        # Sort by priority (highest first)
        self.hooks[event].sort(key=lambda x: x[0], reverse=True)

    def unregister(self, event: HookEvent, handler: Callable):
        """Unregister a hook handler."""
        if event in self.hooks:
            self.hooks[event] = [
                (p, h) for p, h in self.hooks[event]
                if h != handler
            ]

    def trigger(self, event: HookEvent, data: Dict[str, Any] = None) -> HookContext:
        """
        Trigger a hook event.

        Args:
            event: The event to trigger
            data: Data to pass to handlers

        Returns:
            HookContext with potential modifications
        """
        context = HookContext(event=event, data=data or {})

        if event not in self.hooks:
            return context

        for priority, handler in self.hooks[event]:
            try:
                handler(context)
                if context.cancelled:
                    console.print(f"[yellow]⚠️ Hook cancelled operation: {context.data.get('cancel_reason', 'No reason provided')}[/]")
                    break
            except Exception as e:
                logger.error(f"Hook handler error for {event}: {e}")
                console.print(f"[red]❌ Hook error: {e}[/]")

        return context

    def _security_check_hook(self, context: HookContext):
        """Security hook: check for dangerous commands."""
        if context.event == HookEvent.PRE_TOOL_CALL:
            tool_name = context.data.get("tool_name", "")
            args = context.data.get("args", {})

            # Check for dangerous terminal commands
            if tool_name in ["execute_terminal", "execute_bash"]:
                command = args.get("command", "")
                dangerous_patterns = [
                    "rm -rf /",
                    "rm -rf /*",
                    ":(){:|:&};:",  # Fork bomb
                    "mkfs",
                    "dd if=",
                    "> /dev/sda",
                    "chmod 777",
                    "curl.*|.*sh",  # Pipe to shell
                    "wget.*|.*sh",
                ]

                import re
                for pattern in dangerous_patterns:
                    if re.search(pattern, command):
                        context.cancel(f"Dangerous command detected: {pattern}")
                        console.print(f"[bold red]🚫 Blocked dangerous command:[/] {command[:100]}")
                        return

            # Check for sensitive file access
            if tool_name in ["read_file", "write_file", "edit_file"]:
                path = args.get("path", "")
                sensitive_paths = [
                    "/etc/passwd",
                    "/etc/shadow",
                    "~/.ssh/",
                    "~/.aws/",
                    ".env",
                    "credentials",
                    "secret",
                ]

                for sensitive in sensitive_paths:
                    if sensitive in path:
                        console.print(f"[yellow]⚠️ Accessing sensitive file: {path}[/]")

    def _logging_hook(self, context: HookContext):
        """Logging hook: log tool calls."""
        if context.event == HookEvent.POST_TOOL_CALL:
            tool_name = context.data.get("tool_name", "unknown")
            success = context.data.get("success", True)
            result_preview = str(context.data.get("result", ""))[:100]

            status = "✅" if success else "❌"
            logger.info(f"{status} Tool call: {tool_name} - {result_preview}")

    def _file_change_hook(self, context: HookContext):
        """File change hook: track file modifications."""
        if context.event == HookEvent.ON_FILE_CHANGE:
            file_path = context.data.get("path", "")
            change_type = context.data.get("type", "modified")

            # Could integrate with git here
            logger.info(f"File {change_type}: {file_path}")

    def get_registered_hooks(self) -> Dict[str, List[str]]:
        """Get a list of all registered hooks."""
        result = {}
        for event, handlers in self.hooks.items():
            result[event.value] = [h.__name__ for _, h in handlers]
        return result


# Global hook manager instance
hook_manager = HookManager()


def hook(event: HookEvent, priority: int = 0):
    """
    Decorator to register a hook handler.

    Usage:
        @hook(HookEvent.PRE_TOOL_CALL)
        def my_hook(context):
            # Handle hook
            pass
    """
    def decorator(func):
        hook_manager.register(event, func, priority)
        return func
    return decorator
