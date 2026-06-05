"""
审计日志模块

记录所有工具调用和系统操作，支持：
- 完整的操作追踪
- 风险操作告警
- 日志查询和导出
- 合规性报告
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger


class AuditEventType(str, Enum):
    """审计事件类型"""
    TOOL_CALL = "tool_call"
    PERMISSION_CHECK = "permission_check"
    PERMISSION_DENIED = "permission_denied"
    UNDO_OPERATION = "undo_operation"
    REDO_OPERATION = "redo_operation"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ERROR = "error"
    WARNING = "warning"
    SECURITY_ALERT = "security_alert"


class AuditSeverity(str, Enum):
    """审计严重级别"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件"""
    id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    tool_name: Optional[str]
    arguments: Optional[Dict]
    result: Optional[str]
    success: bool
    risk_level: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]
    agent_name: Optional[str]
    duration_ms: Optional[int]
    error_message: Optional[str]
    metadata: Dict

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "tool_name": self.tool_name,
            "arguments": json.dumps(self.arguments) if self.arguments else None,
            "result": self.result[:500] if self.result else None,
            "success": self.success,
            "risk_level": self.risk_level,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "metadata": json.dumps(self.metadata),
        }


class AuditLogger:
    """
    审计日志记录器

    记录所有工具调用和系统操作，支持查询和导出。

    Features:
        - SQLite 持久化
        - 多种事件类型
        - 风险等级分类
        - 日志查询
        - 合规性报告
    """

    def __init__(
        self,
        db_path: str = "helix_audit.db",
        log_to_file: bool = True,
        log_file: str = "audit.log",
        alert_on_high_risk: bool = True,
    ):
        """
        初始化审计日志记录器

        Args:
            db_path: 数据库路径
            log_to_file: 是否记录到文件
            log_file: 日志文件路径
            alert_on_high_risk: 高风险操作是否告警
        """
        self.db_path = db_path
        self.log_to_file = log_to_file
        self.log_file = log_file
        self.alert_on_high_risk = alert_on_high_risk
        self._logger = logger.bind(module="AuditLogger")

        # 初始化数据库
        self._init_db()

        # 当前会话 ID
        self._session_id = None
        self._user_id = None

    def _init_db(self):
        """初始化数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    tool_name TEXT,
                    arguments TEXT,
                    result TEXT,
                    success INTEGER NOT NULL,
                    risk_level TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    agent_name TEXT,
                    duration_ms INTEGER,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')

            # 创建索引
            self.conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)')
            self.conn.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)')
            self.conn.execute('CREATE INDEX IF NOT EXISTS idx_tool_name ON audit_events(tool_name)')
            self.conn.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON audit_events(session_id)')
            self.conn.execute('CREATE INDEX IF NOT EXISTS idx_severity ON audit_events(severity)')

    def start_session(self, user_id: Optional[str] = None) -> str:
        """
        开始新的审计会话

        Args:
            user_id: 用户 ID

        Returns:
            str: 会话 ID
        """
        import uuid
        self._session_id = str(uuid.uuid4())
        self._user_id = user_id

        self.log_event(
            event_type=AuditEventType.SESSION_START,
            severity=AuditSeverity.INFO,
            metadata={"user_id": user_id},
        )

        return self._session_id

    def end_session(self) -> None:
        """结束审计会话"""
        if self._session_id:
            self.log_event(
                event_type=AuditEventType.SESSION_END,
                severity=AuditSeverity.INFO,
                metadata={"session_duration": "N/A"},
            )
            self._session_id = None

    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Optional[str] = None,
        success: bool = True,
        risk_level: Optional[str] = None,
        agent_name: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> str:
        """
        记录工具调用

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            result: 调用结果
            success: 是否成功
            risk_level: 风险等级
            agent_name: 代理名称
            duration_ms: 执行时长（毫秒）
            error_message: 错误信息

        Returns:
            str: 事件 ID
        """
        severity = AuditSeverity.INFO
        if not success:
            severity = AuditSeverity.MEDIUM
        if risk_level in ("high", "critical"):
            severity = AuditSeverity.HIGH
        if error_message:
            severity = AuditSeverity.HIGH

        event_id = self.log_event(
            event_type=AuditEventType.TOOL_CALL,
            severity=severity,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=success,
            risk_level=risk_level,
            agent_name=agent_name,
            duration_ms=duration_ms,
            error_message=error_message,
        )

        # 高风险告警
        if self.alert_on_high_risk and risk_level in ("high", "critical"):
            self._trigger_alert(tool_name, arguments, risk_level)

        return event_id

    def log_permission_check(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        allowed: bool,
        reason: str,
        risk_level: str,
    ) -> str:
        """记录权限检查"""
        event_type = AuditEventType.PERMISSION_CHECK if allowed else AuditEventType.PERMISSION_DENIED
        severity = AuditSeverity.INFO if allowed else AuditSeverity.MEDIUM

        return self.log_event(
            event_type=event_type,
            severity=severity,
            tool_name=tool_name,
            arguments=arguments,
            success=allowed,
            risk_level=risk_level,
            metadata={"reason": reason},
        )

    def log_security_alert(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        alert_type: str,
        description: str,
    ) -> str:
        """记录安全告警"""
        return self.log_event(
            event_type=AuditEventType.SECURITY_ALERT,
            severity=AuditSeverity.CRITICAL,
            tool_name=tool_name,
            arguments=arguments,
            success=False,
            risk_level="critical",
            metadata={"alert_type": alert_type, "description": description},
        )

    def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        tool_name: Optional[str] = None,
        arguments: Optional[Dict] = None,
        result: Optional[str] = None,
        success: bool = True,
        risk_level: Optional[str] = None,
        agent_name: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        记录审计事件

        Args:
            event_type: 事件类型
            severity: 严重级别
            tool_name: 工具名称
            arguments: 工具参数
            result: 结果
            success: 是否成功
            risk_level: 风险等级
            agent_name: 代理名称
            duration_ms: 执行时长
            error_message: 错误信息
            metadata: 元数据

        Returns:
            str: 事件 ID
        """
        import uuid

        event_id = str(uuid.uuid4())
        event = AuditEvent(
            id=event_id,
            timestamp=datetime.now(),
            event_type=event_type,
            severity=severity,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=success,
            risk_level=risk_level,
            user_id=self._user_id,
            session_id=self._session_id,
            agent_name=agent_name,
            duration_ms=duration_ms,
            error_message=error_message,
            metadata=metadata or {},
        )

        # 保存到数据库
        self._save_to_db(event)

        # 记录到文件
        if self.log_to_file:
            self._save_to_file(event)

        return event_id

    def _save_to_db(self, event: AuditEvent):
        """保存到数据库"""
        try:
            with self.conn:
                self.conn.execute(
                    '''INSERT INTO audit_events
                       (id, timestamp, event_type, severity, tool_name, arguments,
                        result, success, risk_level, user_id, session_id, agent_name,
                        duration_ms, error_message, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        event.id,
                        event.timestamp.isoformat(),
                        event.event_type.value,
                        event.severity.value,
                        event.tool_name,
                        json.dumps(event.arguments) if event.arguments else None,
                        event.result[:1000] if event.result else None,
                        1 if event.success else 0,
                        event.risk_level,
                        event.user_id,
                        event.session_id,
                        event.agent_name,
                        event.duration_ms,
                        event.error_message,
                        json.dumps(event.metadata),
                    )
                )
        except Exception as e:
            self._logger.error(f"Failed to save audit event to DB: {e}")

    def _save_to_file(self, event: AuditEvent):
        """保存到文件"""
        try:
            log_entry = {
                "timestamp": event.timestamp.isoformat(),
                "type": event.event_type.value,
                "severity": event.severity.value,
                "tool": event.tool_name,
                "success": event.success,
                "risk": event.risk_level,
            }

            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            self._logger.error(f"Failed to save audit event to file: {e}")

    def _trigger_alert(self, tool_name: str, arguments: Dict, risk_level: str):
        """触发告警"""
        self._logger.warning(
            f"🚨 HIGH RISK OPERATION: {tool_name} "
            f"(risk: {risk_level}, args: {str(arguments)[:100]})"
        )

    def query_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[AuditEventType] = None,
        tool_name: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        查询审计事件

        Args:
            start_time: 开始时间
            end_time: 结束时间
            event_type: 事件类型
            tool_name: 工具名称
            severity: 严重级别
            session_id: 会话 ID
            limit: 返回数量限制

        Returns:
            List[Dict]: 事件列表
        """
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        if tool_name:
            query += " AND tool_name = ?"
            params.append(tool_name)

        if severity:
            query += " AND severity = ?"
            params.append(severity.value)

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self._logger.error(f"Failed to query audit events: {e}")
            return []

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取审计统计信息

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            Dict: 统计信息
        """
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            total_events = len(rows)
            successful = sum(1 for r in rows if r['success'])
            failed = total_events - successful

            # 按事件类型统计
            type_counts = {}
            for row in rows:
                event_type = row['event_type']
                type_counts[event_type] = type_counts.get(event_type, 0) + 1

            # 按工具统计
            tool_counts = {}
            for row in rows:
                tool_name = row['tool_name']
                if tool_name:
                    tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

            # 按风险等级统计
            risk_counts = {}
            for row in rows:
                risk_level = row['risk_level']
                if risk_level:
                    risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1

            return {
                "total_events": total_events,
                "successful": successful,
                "failed": failed,
                "success_rate": successful / total_events if total_events > 0 else 0,
                "by_event_type": type_counts,
                "by_tool": tool_counts,
                "by_risk_level": risk_counts,
            }

        except Exception as e:
            self._logger.error(f"Failed to get audit statistics: {e}")
            return {}

    def export_to_json(self, output_path: str, **kwargs) -> bool:
        """
        导出审计日志为 JSON

        Args:
            output_path: 输出文件路径
            **kwargs: 查询参数

        Returns:
            bool: 是否成功
        """
        try:
            events = self.query_events(**kwargs)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self._logger.error(f"Failed to export audit log: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


# 全局审计日志实例
audit_logger = AuditLogger()


def log_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    result: Optional[str] = None,
    success: bool = True,
    risk_level: Optional[str] = None,
    **kwargs,
) -> str:
    """
    记录工具调用的便捷函数

    Args:
        tool_name: 工具名称
        arguments: 工具参数
        result: 调用结果
        success: 是否成功
        risk_level: 风险等级

    Returns:
        str: 事件 ID
    """
    return audit_logger.log_tool_call(
        tool_name=tool_name,
        arguments=arguments,
        result=result,
        success=success,
        risk_level=risk_level,
        **kwargs,
    )
