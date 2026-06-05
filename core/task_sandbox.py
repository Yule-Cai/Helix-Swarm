"""
任务沙箱模块

为每个任务提供隔离的执行环境：
- 独立的工作目录
- 文件系统隔离
- 资源限制
- 失败回滚
"""

import os
import shutil
import tempfile
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class SandboxConfig:
    """沙箱配置"""
    task_id: str
    workspace_root: str
    max_disk_mb: int = 1024  # 最大磁盘使用 (MB)
    max_files: int = 1000    # 最大文件数
    allowed_extensions: List[str] = field(default_factory=lambda: [
        ".py", ".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".log"
    ])
    blocked_paths: List[str] = field(default_factory=lambda: [
        "/etc", "/usr", "/var", "/root", "~/.ssh", "~/.aws"
    ])


@dataclass
class SandboxSnapshot:
    """沙箱快照"""
    timestamp: datetime
    files: Dict[str, str]  # path -> content hash
    metadata: Dict[str, Any]


class TaskSandbox:
    """
    任务沙箱

    为每个任务提供隔离的执行环境。

    Features:
        - 独立的工作目录
        - 文件系统隔离
        - 快照和回滚
        - 资源限制
        - 清理机制
    """

    def __init__(
        self,
        base_dir: str = ".sandboxes",
        auto_cleanup: bool = True,
    ):
        """
        初始化任务沙箱

        Args:
            base_dir: 沙箱基础目录
            auto_cleanup: 是否自动清理
        """
        self.base_dir = Path(base_dir)
        self.auto_cleanup = auto_cleanup
        self._logger = logger.bind(module="TaskSandbox")

        # 活跃的沙箱
        self._active_sandboxes: Dict[str, Path] = {}

        # 初始化基础目录
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_sandbox(self, task_id: str, source_dir: Optional[str] = None) -> Path:
        """
        创建任务沙箱

        Args:
            task_id: 任务 ID
            source_dir: 源目录（可选，用于复制文件）

        Returns:
            Path: 沙箱工作目录
        """
        sandbox_id = self._generate_sandbox_id(task_id)
        sandbox_dir = self.base_dir / sandbox_id

        # 创建沙箱目录
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        # 如果提供了源目录，复制文件
        if source_dir and os.path.exists(source_dir):
            self._copy_workspace(source_dir, sandbox_dir)

        # 记录活跃沙箱
        self._active_sandboxes[task_id] = sandbox_dir

        self._logger.info(f"Created sandbox for task {task_id}: {sandbox_dir}")
        return sandbox_dir

    def _generate_sandbox_id(self, task_id: str) -> str:
        """生成沙箱 ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_hash = hashlib.md5(task_id.encode()).hexdigest()[:8]
        return f"sandbox_{timestamp}_{task_hash}"

    def _copy_workspace(self, source: str, destination: Path):
        """复制工作区文件"""
        source_path = Path(source)

        for item in source_path.rglob("*"):
            # 跳过隐藏文件和缓存
            if any(part.startswith('.') for part in item.parts):
                continue
            if '__pycache__' in str(item):
                continue

            relative = item.relative_to(source_path)
            dest = destination / relative

            if item.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)
            elif item.is_dir():
                dest.mkdir(parents=True, exist_ok=True)

    def get_sandbox_dir(self, task_id: str) -> Optional[Path]:
        """获取沙箱目录"""
        return self._active_sandboxes.get(task_id)

    def take_snapshot(self, task_id: str) -> Optional[SandboxSnapshot]:
        """
        创建沙箱快照

        Args:
            task_id: 任务 ID

        Returns:
            SandboxSnapshot: 快照对象
        """
        sandbox_dir = self._active_sandboxes.get(task_id)
        if not sandbox_dir:
            return None

        files = {}
        for file_path in sandbox_dir.rglob("*"):
            if file_path.is_file():
                relative = str(file_path.relative_to(sandbox_dir))
                content_hash = self._hash_file(file_path)
                files[relative] = content_hash

        return SandboxSnapshot(
            timestamp=datetime.now(),
            files=files,
            metadata={"task_id": task_id, "sandbox_dir": str(sandbox_dir)},
        )

    def _hash_file(self, file_path: Path) -> str:
        """计算文件哈希"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def rollback_to_snapshot(self, task_id: str, snapshot: SandboxSnapshot) -> bool:
        """
        回滚到快照

        Args:
            task_id: 任务 ID
            snapshot: 快照对象

        Returns:
            bool: 是否成功
        """
        sandbox_dir = self._active_sandboxes.get(task_id)
        if not sandbox_dir:
            return False

        try:
            # 获取当前文件
            current_files = set()
            for file_path in sandbox_dir.rglob("*"):
                if file_path.is_file():
                    relative = str(file_path.relative_to(sandbox_dir))
                    current_files.add(relative)

            # 删除快照中不存在的文件
            snapshot_files = set(snapshot.files.keys())
            for file_name in current_files - snapshot_files:
                file_path = sandbox_dir / file_name
                if file_path.exists():
                    file_path.unlink()

            self._logger.info(f"Rolled back sandbox for task {task_id}")
            return True

        except Exception as e:
            self._logger.error(f"Rollback failed: {e}")
            return False

    def cleanup_sandbox(self, task_id: str) -> bool:
        """
        清理沙箱

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功
        """
        sandbox_dir = self._active_sandboxes.get(task_id)
        if not sandbox_dir:
            return False

        try:
            shutil.rmtree(sandbox_dir)
            del self._active_sandboxes[task_id]
            self._logger.info(f"Cleaned up sandbox for task {task_id}")
            return True
        except Exception as e:
            self._logger.error(f"Cleanup failed: {e}")
            return False

    def cleanup_all(self) -> int:
        """
        清理所有沙箱

        Returns:
            int: 清理的沙箱数量
        """
        count = 0
        for task_id in list(self._active_sandboxes.keys()):
            if self.cleanup_sandbox(task_id):
                count += 1

        # 清理旧的沙箱目录
        if self.auto_cleanup:
            self._cleanup_old_sandboxes()

        return count

    def _cleanup_old_sandboxes(self, max_age_hours: int = 24):
        """清理旧的沙箱目录"""
        import time

        cutoff_time = time.time() - (max_age_hours * 3600)

        for sandbox_dir in self.base_dir.iterdir():
            if sandbox_dir.is_dir() and sandbox_dir.name.startswith("sandbox_"):
                if sandbox_dir.stat().st_mtime < cutoff_time:
                    try:
                        shutil.rmtree(sandbox_dir)
                        self._logger.info(f"Cleaned up old sandbox: {sandbox_dir.name}")
                    except Exception as e:
                        self._logger.warning(f"Failed to clean up {sandbox_dir.name}: {e}")

    def get_sandbox_stats(self, task_id: str) -> Dict[str, Any]:
        """
        获取沙箱统计信息

        Args:
            task_id: 任务 ID

        Returns:
            Dict: 统计信息
        """
        sandbox_dir = self._active_sandboxes.get(task_id)
        if not sandbox_dir:
            return {}

        total_size = 0
        file_count = 0

        for file_path in sandbox_dir.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1

        return {
            "task_id": task_id,
            "sandbox_dir": str(sandbox_dir),
            "file_count": file_count,
            "total_size_mb": total_size / (1024 * 1024),
        }

    def list_sandboxes(self) -> List[Dict[str, Any]]:
        """列出所有活跃的沙箱"""
        return [
            {"task_id": task_id, "sandbox_dir": str(sandbox_dir)}
            for task_id, sandbox_dir in self._active_sandboxes.items()
        ]


class SandboxedExecutor:
    """
    沙箱化执行器

    在沙箱环境中执行任务，支持：
    - 任务隔离
    - 失败回滚
    - 资源限制
    """

    def __init__(
        self,
        sandbox: TaskSandbox,
        source_dir: str,
    ):
        """
        初始化沙箱化执行器

        Args:
            sandbox: 任务沙箱实例
            source_dir: 源目录
        """
        self.sandbox = sandbox
        self.source_dir = source_dir
        self._logger = logger.bind(module="SandboxedExecutor")

    async def execute(
        self,
        task_id: str,
        task_func,
        *args,
        rollback_on_failure: bool = True,
        **kwargs,
    ) -> Any:
        """
        在沙箱中执行任务

        Args:
            task_id: 任务 ID
            task_func: 任务函数
            rollback_on_failure: 失败时是否回滚
            *args, **kwargs: 任务参数

        Returns:
            Any: 任务结果
        """
        # 创建沙箱
        sandbox_dir = self.sandbox.create_sandbox(task_id, self.source_dir)

        # 创建快照
        snapshot = self.sandbox.take_snapshot(task_id)

        try:
            # 切换到沙箱目录
            original_dir = os.getcwd()
            os.chdir(sandbox_dir)

            # 执行任务
            self._logger.info(f"Executing task {task_id} in sandbox")
            result = await task_func(*args, **kwargs)

            # 恢复目录
            os.chdir(original_dir)

            return result

        except Exception as e:
            self._logger.error(f"Task {task_id} failed: {e}")

            # 回滚
            if rollback_on_failure and snapshot:
                self.sandbox.rollback_to_snapshot(task_id, snapshot)

            # 恢复目录
            os.chdir(original_dir)

            raise

        finally:
            # 可选：清理沙箱
            # self.sandbox.cleanup_sandbox(task_id)
            pass


# 全局沙箱实例
task_sandbox = TaskSandbox()
