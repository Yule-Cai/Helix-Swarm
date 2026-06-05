"""
操作撤销管理器模块

实现文件操作的撤销/重做机制，确保用户可以安全地回滚任何操作。

支持的操作类型：
- 文件创建、修改、删除
- 目录创建、删除
- Git 操作（commit, stash 等）
"""

import os
import json
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from loguru import logger


class OperationType(str, Enum):
    """操作类型枚举"""
    FILE_CREATE = "file_create"
    FILE_MODIFY = "file_modify"
    FILE_DELETE = "file_delete"
    FILE_MOVE = "file_move"
    FILE_COPY = "file_copy"
    DIR_CREATE = "dir_create"
    DIR_DELETE = "dir_delete"
    GIT_COMMIT = "git_commit"
    GIT_STASH = "git_stash"
    TERMINAL_CMD = "terminal_cmd"


class OperationStatus(str, Enum):
    """操作状态枚举"""
    PENDING = "pending"
    COMPLETED = "completed"
    UNDONE = "undone"
    REDONE = "redone"
    FAILED = "failed"


@dataclass
class FileSnapshot:
    """文件快照"""
    path: str
    content: Optional[str] = None
    exists: bool = True
    is_dir: bool = False
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "exists": self.exists,
            "is_dir": self.is_dir,
            "content_hash": hashlib.md5(self.content.encode()).hexdigest() if self.content else None,
            "metadata": self.metadata,
        }


@dataclass
class Operation:
    """操作记录"""
    id: str
    type: OperationType
    timestamp: datetime
    description: str
    tool_name: str
    arguments: Dict[str, Any]
    status: OperationStatus = OperationStatus.COMPLETED

    # 操作前的状态
    before_snapshot: Optional[FileSnapshot] = None
    before_snapshots: List[FileSnapshot] = field(default_factory=list)

    # 操作后的状态
    after_snapshot: Optional[FileSnapshot] = None
    after_snapshots: List[FileSnapshot] = field(default_factory=list)

    # 备份文件路径
    backup_path: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "backup_path": self.backup_path,
        }


class UndoManager:
    """
    操作撤销管理器

    实现文件操作的撤销/重做机制。

    Features:
        - 自动备份文件
        - 撤销/重做操作
        - 操作历史管理
        - 批量操作支持
    """

    def __init__(
        self,
        backup_dir: str = ".helix_backup",
        max_history: int = 100,
        auto_backup: bool = True,
    ):
        """
        初始化撤销管理器

        Args:
            backup_dir: 备份目录
            max_history: 最大历史记录数
            auto_backup: 是否自动备份
        """
        self.backup_dir = Path(backup_dir)
        self.max_history = max_history
        self.auto_backup = auto_backup
        self._logger = logger.bind(module="UndoManager")

        # 操作历史
        self._history: List[Operation] = []
        self._undo_stack: List[Operation] = []
        self._redo_stack: List[Operation] = []

        # 初始化备份目录
        self._init_backup_dir()

    def _init_backup_dir(self):
        """初始化备份目录"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        # 创建子目录
        (self.backup_dir / "files").mkdir(exist_ok=True)
        (self.backup_dir / "dirs").mkdir(exist_ok=True)
        (self.backup_dir / "metadata").mkdir(exist_ok=True)

    def record_operation(
        self,
        operation_type: OperationType,
        tool_name: str,
        arguments: Dict[str, Any],
        description: str = "",
    ) -> Operation:
        """
        记录操作

        Args:
            operation_type: 操作类型
            tool_name: 工具名称
            arguments: 工具参数
            description: 操作描述

        Returns:
            Operation: 操作记录
        """
        operation_id = f"op_{datetime.now().timestamp()}_{len(self._history)}"

        operation = Operation(
            id=operation_id,
            type=operation_type,
            timestamp=datetime.now(),
            description=description or f"{tool_name}: {str(arguments)[:100]}",
            tool_name=tool_name,
            arguments=arguments,
        )

        # 创建操作前快照
        if self.auto_backup:
            self._create_before_snapshot(operation)

        self._history.append(operation)
        self._undo_stack.append(operation)

        # 清空重做栈
        self._redo_stack.clear()

        # 限制历史记录数
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        self._logger.info(f"Recorded operation: {operation.description}")
        return operation

    def complete_operation(self, operation: Operation, success: bool = True) -> None:
        """
        完成操作

        Args:
            operation: 操作记录
            success: 是否成功
        """
        if success:
            operation.status = OperationStatus.COMPLETED
            # 创建操作后快照
            if self.auto_backup:
                self._create_after_snapshot(operation)
        else:
            operation.status = OperationStatus.FAILED

        self._logger.info(f"Operation completed: {operation.description} ({operation.status.value})")

    def undo(self) -> Optional[Operation]:
        """
        撤销最后一个操作

        Returns:
            Optional[Operation]: 被撤销的操作，如果没有可撤销的操作则返回 None
        """
        if not self._undo_stack:
            self._logger.warning("Nothing to undo")
            return None

        operation = self._undo_stack.pop()

        try:
            self._perform_undo(operation)
            operation.status = OperationStatus.UNDONE
            self._redo_stack.append(operation)
            self._logger.info(f"Undone: {operation.description}")
            return operation
        except Exception as e:
            self._logger.error(f"Failed to undo: {e}")
            operation.status = OperationStatus.FAILED
            self._undo_stack.append(operation)
            return None

    def redo(self) -> Optional[Operation]:
        """
        重做最后一个被撤销的操作

        Returns:
            Optional[Operation]: 被重做的操作，如果没有可重做的操作则返回 None
        """
        if not self._redo_stack:
            self._logger.warning("Nothing to redo")
            return None

        operation = self._redo_stack.pop()

        try:
            self._perform_redo(operation)
            operation.status = OperationStatus.REDONE
            self._undo_stack.append(operation)
            self._logger.info(f"Redone: {operation.description}")
            return operation
        except Exception as e:
            self._logger.error(f"Failed to redo: {e}")
            operation.status = OperationStatus.FAILED
            self._redo_stack.append(operation)
            return None

    def _create_before_snapshot(self, operation: Operation) -> None:
        """创建操作前快照"""
        if operation.type in (OperationType.FILE_MODIFY, OperationType.FILE_DELETE):
            path = operation.arguments.get("path", "")
            if path and os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    operation.before_snapshot = FileSnapshot(
                        path=path,
                        content=content,
                        exists=True,
                    )
                    # 创建备份文件
                    backup_path = self._backup_file(path, content)
                    operation.backup_path = backup_path
                except Exception as e:
                    self._logger.warning(f"Failed to create before snapshot: {e}")

        elif operation.type == OperationType.FILE_MOVE:
            source = operation.arguments.get("source", "")
            if source and os.path.exists(source):
                try:
                    with open(source, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    operation.before_snapshot = FileSnapshot(
                        path=source,
                        content=content,
                        exists=True,
                    )
                    backup_path = self._backup_file(source, content)
                    operation.backup_path = backup_path
                except Exception as e:
                    self._logger.warning(f"Failed to create before snapshot: {e}")

    def _create_after_snapshot(self, operation: Operation) -> None:
        """创建操作后快照"""
        if operation.type in (OperationType.FILE_CREATE, OperationType.FILE_MODIFY):
            path = operation.arguments.get("path", "")
            if path and os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    operation.after_snapshot = FileSnapshot(
                        path=path,
                        content=content,
                        exists=True,
                    )
                except Exception as e:
                    self._logger.warning(f"Failed to create after snapshot: {e}")

    def _backup_file(self, path: str, content: str) -> str:
        """备份文件"""
        # 生成备份文件名
        path_hash = hashlib.md5(path.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{path_hash}_{timestamp}.bak"
        backup_path = self.backup_dir / "files" / backup_filename

        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return str(backup_path)
        except Exception as e:
            self._logger.error(f"Failed to backup file: {e}")
            return ""

    def _perform_undo(self, operation: Operation) -> None:
        """执行撤销操作"""
        if operation.type == OperationType.FILE_CREATE:
            # 撤销创建 = 删除文件
            path = operation.arguments.get("path", "")
            if path and os.path.exists(path):
                os.remove(path)

        elif operation.type == OperationType.FILE_MODIFY:
            # 撤销修改 = 恢复原内容
            if operation.before_snapshot and operation.before_snapshot.content:
                path = operation.before_snapshot.path
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(operation.before_snapshot.content)

        elif operation.type == OperationType.FILE_DELETE:
            # 撤销删除 = 恢复文件
            if operation.before_snapshot and operation.before_snapshot.content:
                path = operation.before_snapshot.path
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(operation.before_snapshot.content)

        elif operation.type == OperationType.FILE_MOVE:
            # 撤销移动 = 移回原位置
            source = operation.arguments.get("source", "")
            destination = operation.arguments.get("destination", "")
            if destination and os.path.exists(destination) and source:
                shutil.move(destination, source)

        elif operation.type == OperationType.DIR_CREATE:
            # 撤销创建目录 = 删除目录
            path = operation.arguments.get("path", "")
            if path and os.path.exists(path):
                os.rmdir(path)

    def _perform_redo(self, operation: Operation) -> None:
        """执行重做操作"""
        if operation.type == OperationType.FILE_CREATE:
            # 重做创建 = 重新创建文件
            if operation.after_snapshot and operation.after_snapshot.content:
                path = operation.after_snapshot.path
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(operation.after_snapshot.content)

        elif operation.type == OperationType.FILE_MODIFY:
            # 重做修改 = 应用新内容
            if operation.after_snapshot and operation.after_snapshot.content:
                path = operation.after_snapshot.path
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(operation.after_snapshot.content)

        elif operation.type == OperationType.FILE_DELETE:
            # 重做删除 = 删除文件
            path = operation.arguments.get("path", "")
            if path and os.path.exists(path):
                os.remove(path)

        elif operation.type == OperationType.FILE_MOVE:
            # 重做移动 = 重新移动
            source = operation.arguments.get("source", "")
            destination = operation.arguments.get("destination", "")
            if source and os.path.exists(source) and destination:
                shutil.move(source, destination)

    def get_undo_history(self) -> List[Dict]:
        """获取可撤销的操作历史"""
        return [op.to_dict() for op in reversed(self._undo_stack)]

    def get_redo_history(self) -> List[Dict]:
        """获取可重做的操作历史"""
        return [op.to_dict() for op in reversed(self._redo_stack)]

    def get_full_history(self) -> List[Dict]:
        """获取完整操作历史"""
        return [op.to_dict() for op in self._history]

    def can_undo(self) -> bool:
        """是否可以撤销"""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """是否可以重做"""
        return len(self._redo_stack) > 0

    def clear_history(self) -> None:
        """清空历史记录"""
        self._history.clear()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._logger.info("History cleared")

    def cleanup_backups(self, max_age_days: int = 7) -> int:
        """
        清理旧备份

        Args:
            max_age_days: 最大保留天数

        Returns:
            int: 清理的备份数量
        """
        import time

        count = 0
        cutoff_time = time.time() - (max_age_days * 86400)

        for backup_file in (self.backup_dir / "files").glob("*.bak"):
            if backup_file.stat().st_mtime < cutoff_time:
                backup_file.unlink()
                count += 1

        self._logger.info(f"Cleaned up {count} old backups")
        return count


# 全局撤销管理器实例
undo_manager = UndoManager()


def record_file_operation(
    tool_name: str,
    arguments: Dict[str, Any],
    operation_type: Optional[OperationType] = None,
) -> Operation:
    """
    记录文件操作的便捷函数

    Args:
        tool_name: 工具名称
        arguments: 工具参数
        operation_type: 操作类型（可选，自动推断）

    Returns:
        Operation: 操作记录
    """
    if operation_type is None:
        # 自动推断操作类型
        type_map = {
            "write_file": OperationType.FILE_CREATE,
            "edit_file": OperationType.FILE_MODIFY,
            "delete_file": OperationType.FILE_DELETE,
            "move_file": OperationType.FILE_MOVE,
            "copy_file": OperationType.FILE_COPY,
            "insert_at_line": OperationType.FILE_MODIFY,
            "delete_lines": OperationType.FILE_MODIFY,
        }
        operation_type = type_map.get(tool_name, OperationType.TERMINAL_CMD)

    return undo_manager.record_operation(
        operation_type=operation_type,
        tool_name=tool_name,
        arguments=arguments,
    )
