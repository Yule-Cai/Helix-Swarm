"""
权限管理器模块

实现 Claude Code 风格的七种权限模式，确保每个工具调用都经过安全检查。

权限模式：
1. default        - 默认模式，工具调用需确认
2. auto-approve   - 自动批准低风险操作
3. plan-only      - 只规划不执行
4. ask-first      - 高风险操作先问
5. never          - 禁止特定工具
6. workspace-only - 限制在工作区
7. custom         - 自定义规则
"""

import os
import json
import re
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from loguru import logger


class PermissionMode(str, Enum):
    """权限模式枚举"""
    DEFAULT = "default"           # 默认模式，工具调用需确认
    AUTO_APPROVE = "auto-approve" # 自动批准低风险操作
    PLAN_ONLY = "plan-only"       # 只规划不执行
    ASK_FIRST = "ask-first"       # 高风险操作先问
    NEVER = "never"               # 禁止特定工具
    WORKSPACE_ONLY = "workspace-only"  # 限制在工作区
    CUSTOM = "custom"             # 自定义规则


class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "low"           # 低风险：读取文件、搜索
    MEDIUM = "medium"     # 中风险：写入文件、git 操作
    HIGH = "high"         # 高风险：删除文件、执行命令
    CRITICAL = "critical" # 关键风险：系统命令、权限修改


@dataclass
class PermissionRule:
    """权限规则"""
    tool_pattern: str          # 工具名称模式（支持通配符）
    risk_level: RiskLevel      # 风险等级
    allowed: bool              # 是否允许
    requires_approval: bool    # 是否需要确认
    conditions: Dict = field(default_factory=dict)  # 附加条件
    description: str = ""      # 规则描述


@dataclass
class ToolCallRequest:
    """工具调用请求"""
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    agent_name: Optional[str] = None


@dataclass
class PermissionDecision:
    """权限决策"""
    allowed: bool
    reason: str
    risk_level: RiskLevel
    requires_approval: bool = False
    conditions_met: bool = True
    modified_args: Optional[Dict] = None  # 可能修改后的参数


# 工具风险等级映射
TOOL_RISK_LEVELS: Dict[str, RiskLevel] = {
    # 低风险：只读操作
    "read_file": RiskLevel.LOW,
    "list_directory": RiskLevel.LOW,
    "grep_code": RiskLevel.LOW,
    "glob_files": RiskLevel.LOW,
    "search_symbols": RiskLevel.LOW,
    "git_status": RiskLevel.LOW,
    "git_diff": RiskLevel.LOW,
    "git_log": RiskLevel.LOW,
    "get_current_directory": RiskLevel.LOW,
    "get_environment": RiskLevel.LOW,
    "check_process": RiskLevel.LOW,

    # 中风险：写入操作
    "write_file": RiskLevel.MEDIUM,
    "edit_file": RiskLevel.MEDIUM,
    "insert_at_line": RiskLevel.MEDIUM,
    "copy_file": RiskLevel.MEDIUM,
    "move_file": RiskLevel.MEDIUM,
    "git_add": RiskLevel.MEDIUM,
    "git_commit": RiskLevel.MEDIUM,
    "git_branch": RiskLevel.MEDIUM,
    "git_checkout": RiskLevel.MEDIUM,
    "git_stash": RiskLevel.MEDIUM,
    "set_environment": RiskLevel.MEDIUM,
    "change_directory": RiskLevel.MEDIUM,

    # 高风险：删除和执行操作
    "delete_file": RiskLevel.HIGH,
    "delete_lines": RiskLevel.HIGH,
    "execute_terminal": RiskLevel.HIGH,
    "execute_background": RiskLevel.HIGH,
    "kill_process": RiskLevel.HIGH,
    "git_push": RiskLevel.HIGH,
    "git_pull": RiskLevel.HIGH,
    "git_clone": RiskLevel.HIGH,

    # 关键风险：系统操作
    "git_init": RiskLevel.CRITICAL,
}

# 危险命令模式
DANGEROUS_COMMAND_PATTERNS = [
    r"rm\s+-rf\s+/",           # 删除根目录
    r"rm\s+-rf\s+/\*",         # 删除根目录所有内容
    r":\(\)\{.*\|.*\&\}",      # Fork bomb
    r"mkfs",                    # 格式化
    r"dd\s+if=",                # 磁盘写入
    r">\s*/dev/sd",             # 写入磁盘设备
    r"chmod\s+777",             # 开放所有权限
    r"curl.*\|.*sh",            # 下载并执行
    r"wget.*\|.*sh",            # 下载并执行
    r"eval\s*\(",               # 动态执行
    r"exec\s*\(",               # 进程替换
]


class PermissionManager:
    """
    权限管理器

    实现七种权限模式，控制工具调用的安全性。

    Features:
        - 七种权限模式
        - 风险等级评估
        - 危险命令检测
        - 工作区限制
        - 自定义规则
        - 审批流程
    """

    def __init__(
        self,
        mode: PermissionMode = PermissionMode.DEFAULT,
        workspace_root: Optional[str] = None,
        auto_approve_low_risk: bool = True,
        custom_rules: Optional[List[PermissionRule]] = None,
        approval_callback: Optional[Callable[[ToolCallRequest, PermissionDecision], bool]] = None,
    ):
        """
        初始化权限管理器

        Args:
            mode: 权限模式
            workspace_root: 工作区根目录
            auto_approve_low_risk: 是否自动批准低风险操作
            custom_rules: 自定义规则列表
            approval_callback: 审批回调函数
        """
        self.mode = mode
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.auto_approve_low_risk = auto_approve_low_risk
        self.custom_rules = custom_rules or []
        self.approval_callback = approval_callback
        self._logger = logger.bind(module="PermissionManager")

        # 禁止的工具列表
        self._blocked_tools: Set[str] = set()

        # 审批历史
        self._approval_history: List[Dict] = []

    def check_permission(self, request: ToolCallRequest) -> PermissionDecision:
        """
        检查工具调用权限

        Args:
            request: 工具调用请求

        Returns:
            PermissionDecision: 权限决策
        """
        # 获取风险等级
        risk_level = self._get_risk_level(request.tool_name)

        # 根据权限模式检查
        if self.mode == PermissionMode.DEFAULT:
            return self._check_default(request, risk_level)
        elif self.mode == PermissionMode.AUTO_APPROVE:
            return self._check_auto_approve(request, risk_level)
        elif self.mode == PermissionMode.PLAN_ONLY:
            return self._check_plan_only(request, risk_level)
        elif self.mode == PermissionMode.ASK_FIRST:
            return self._check_ask_first(request, risk_level)
        elif self.mode == PermissionMode.NEVER:
            return self._check_never(request, risk_level)
        elif self.mode == PermissionMode.WORKSPACE_ONLY:
            return self._check_workspace_only(request, risk_level)
        elif self.mode == PermissionMode.CUSTOM:
            return self._check_custom(request, risk_level)
        else:
            return PermissionDecision(
                allowed=False,
                reason=f"Unknown permission mode: {self.mode}",
                risk_level=risk_level,
            )

    def _get_risk_level(self, tool_name: str) -> RiskLevel:
        """获取工具的风险等级"""
        return TOOL_RISK_LEVELS.get(tool_name, RiskLevel.MEDIUM)

    def _check_default(self, request: ToolCallRequest, risk_level: RiskLevel) -> PermissionDecision:
        """默认模式检查"""
        # 检查是否被阻止
        if request.tool_name in self._blocked_tools:
            return PermissionDecision(
                allowed=False,
                reason=f"Tool {request.tool_name} is blocked",
                risk_level=risk_level,
            )

        # 检查危险命令
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            danger_check = self._check_dangerous_command(request)
            if not danger_check.allowed:
                return danger_check

        # 低风险自动批准
        if risk_level == RiskLevel.LOW and self.auto_approve_low_risk:
            return PermissionDecision(
                allowed=True,
                reason="Low risk operation auto-approved",
                risk_level=risk_level,
            )

        # 其他需要确认
        return PermissionDecision(
            allowed=True,
            reason=f"Operation allowed ({risk_level.value} risk)",
            risk_level=risk_level,
            requires_approval=risk_level != RiskLevel.LOW,
        )

    def _check_auto_approve(self, request: ToolCallRequest, risk_level: RiskLevel) -> PermissionDecision:
        """自动批准模式检查"""
        # 关键风险仍需确认
        if risk_level == RiskLevel.CRITICAL:
            danger_check = self._check_dangerous_command(request)
            if not danger_check.allowed:
                return danger_check
            return PermissionDecision(
                allowed=True,
                reason="Critical operation requires confirmation",
                risk_level=risk_level,
                requires_approval=True,
            )

        return PermissionDecision(
            allowed=True,
            reason="Auto-approved",
            risk_level=risk_level,
        )

    def _check_plan_only(self, request: ToolCallRequest, risk_level: RiskLevel) -> PermissionDecision:
        """只规划模式检查"""
        # 只允许只读操作
        if risk_level == RiskLevel.LOW:
            return PermissionDecision(
                allowed=True,
                reason="Read-only operation allowed in plan mode",
                risk_level=risk_level,
            )

        return PermissionDecision(
            allowed=False,
            reason=f"Write operations not allowed in plan-only mode ({risk_level.value} risk)",
            risk_level=risk_level,
        )

    def _check_ask_first(self, request: ToolCallRequest, risk_level: RiskLevel) -> PermissionDecision:
        """先问模式检查"""
        danger_check = self._check_dangerous_command(request)
        if not danger_check.allowed:
            return danger_check

        return PermissionDecision(
            allowed=True,
            reason=f"Operation allowed with approval ({risk_level.value} risk)",
            risk_level=risk_level,
            requires_approval=risk_level != RiskLevel.LOW,
        )

    def _check_never(self, request: ToolCallRequest, risk_level: RiskLevel) -> PermissionDecision:
        """禁止模式检查"""
        if request.tool_name in self._blocked_tools:
            return PermissionDecision(
                allowed=False,
                reason=f"Tool {request.tool_name} is permanently blocked",
                risk_level=risk_level,
            )

        # 低风险操作仍然允许
        if risk_level == RiskLevel.LOW:
            return PermissionDecision(
                allowed=True,
                reason="Low risk operation allowed",
                risk_level=risk_level,
            )

        return PermissionDecision(
            allowed=False,
            reason=f"Non-low-risk operations blocked in never mode ({risk_level.value})",
            risk_level=risk_level,
        )

    def _check_workspace_only(self, request: ToolCallRequest, risk_level: RiskLevel) -> PermissionDecision:
        """工作区限制模式检查"""
        # 检查文件操作是否在工作区内
        if request.tool_name in ("read_file", "write_file", "edit_file", "delete_file",
                                  "copy_file", "move_file", "list_directory"):
            path = request.arguments.get("path", "")
            if path and not self._is_in_workspace(path):
                return PermissionDecision(
                    allowed=False,
                    reason=f"Path {path} is outside workspace",
                    risk_level=risk_level,
                )

        # 检查危险命令
        danger_check = self._check_dangerous_command(request)
        if not danger_check.allowed:
            return danger_check

        return PermissionDecision(
            allowed=True,
            reason="Operation within workspace",
            risk_level=risk_level,
            requires_approval=risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
        )

    def _check_custom(self, request: ToolCallRequest, risk_level: RiskLevel) -> PermissionDecision:
        """自定义规则检查"""
        for rule in self.custom_rules:
            if self._matches_pattern(request.tool_name, rule.tool_pattern):
                if not rule.allowed:
                    return PermissionDecision(
                        allowed=False,
                        reason=f"Blocked by custom rule: {rule.description}",
                        risk_level=risk_level,
                    )
                return PermissionDecision(
                    allowed=rule.allowed,
                    reason=f"Allowed by custom rule: {rule.description}",
                    risk_level=risk_level,
                    requires_approval=rule.requires_approval,
                )

        # 默认允许
        return PermissionDecision(
            allowed=True,
            reason="No matching custom rule, defaulting to allow",
            risk_level=risk_level,
        )

    def _check_dangerous_command(self, request: ToolCallRequest) -> PermissionDecision:
        """检查危险命令"""
        if request.tool_name not in ("execute_terminal", "execute_background"):
            return PermissionDecision(allowed=True, reason="Not a terminal command", risk_level=RiskLevel.LOW)

        command = request.arguments.get("command", "")
        if not command:
            return PermissionDecision(allowed=True, reason="Empty command", risk_level=RiskLevel.LOW)

        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                self._logger.warning(f"Dangerous command detected: {command[:100]}")
                return PermissionDecision(
                    allowed=False,
                    reason=f"Dangerous command pattern detected: {pattern}",
                    risk_level=RiskLevel.CRITICAL,
                )

        return PermissionDecision(allowed=True, reason="Command passed safety check", risk_level=RiskLevel.HIGH)

    def _is_in_workspace(self, path: str) -> bool:
        """检查路径是否在工作区内"""
        try:
            target_path = Path(path).resolve()
            workspace_path = self.workspace_root.resolve()
            return str(target_path).startswith(str(workspace_path))
        except Exception:
            return False

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """匹配工具名称模式"""
        if pattern == "*":
            return True
        if "*" in pattern:
            regex_pattern = pattern.replace("*", ".*")
            return bool(re.match(regex_pattern, name))
        return name == pattern

    def block_tool(self, tool_name: str) -> None:
        """阻止工具"""
        self._blocked_tools.add(tool_name)
        self._logger.info(f"Blocked tool: {tool_name}")

    def unblock_tool(self, tool_name: str) -> None:
        """取消阻止工具"""
        self._blocked_tools.discard(tool_name)
        self._logger.info(f"Unblocked tool: {tool_name}")

    def set_mode(self, mode: PermissionMode) -> None:
        """设置权限模式"""
        self.mode = mode
        self._logger.info(f"Permission mode set to: {mode.value}")

    def add_custom_rule(self, rule: PermissionRule) -> None:
        """添加自定义规则"""
        self.custom_rules.append(rule)
        self._logger.info(f"Added custom rule: {rule.description}")

    def get_blocked_tools(self) -> Set[str]:
        """获取被阻止的工具列表"""
        return self._blocked_tools.copy()

    def get_approval_history(self) -> List[Dict]:
        """获取审批历史"""
        return self._approval_history.copy()

    def record_approval(self, request: ToolCallRequest, decision: PermissionDecision, approved: bool) -> None:
        """记录审批结果"""
        self._approval_history.append({
            "timestamp": request.timestamp.isoformat(),
            "tool": request.tool_name,
            "args": str(request.arguments)[:200],
            "risk_level": decision.risk_level.value,
            "allowed": decision.allowed,
            "approved": approved,
            "reason": decision.reason,
        })


# 全局权限管理器实例
permission_manager = PermissionManager()


def check_tool_permission(tool_name: str, arguments: Dict[str, Any]) -> PermissionDecision:
    """
    检查工具权限的便捷函数

    Args:
        tool_name: 工具名称
        arguments: 工具参数

    Returns:
        PermissionDecision: 权限决策
    """
    request = ToolCallRequest(tool_name=tool_name, arguments=arguments)
    return permission_manager.check_permission(request)
