"""
任务管理器模块

负责任务调度、任务队列和任务状态管理。
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from loguru import logger
import heapq
from collections import defaultdict

from .agent_base import AgentBase, AgentResult


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(int, Enum):
    """任务优先级枚举"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class Task(BaseModel):
    """任务模型"""
    id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    description: str = Field("", description="任务描述")
    agent_name: str = Field(..., description="执行Agent名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="任务优先级")
    status: TaskStatus = Field(TaskStatus.PENDING, description="任务状态")
    dependencies: List[str] = Field(default_factory=list, description="依赖任务ID列表")
    max_retries: int = Field(3, description="最大重试次数")
    retry_count: int = Field(0, description="当前重试次数")
    timeout: int = Field(300, description="超时时间(秒)")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    result: Optional[AgentResult] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def __lt__(self, other: 'Task') -> bool:
        """用于优先级队列比较"""
        return self.priority.value > other.priority.value


class TaskManager:
    """
    任务管理器
    
    负责任务调度、执行和状态管理。
    
    Features:
        - 任务优先级队列
        - 任务依赖管理
        - 任务重试机制
        - 并发任务执行
        - 任务状态追踪
    """
    
    def __init__(self, max_concurrent_tasks: int = 10):
        """
        初始化任务管理器
        
        Args:
            max_concurrent_tasks: 最大并发任务数
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self._tasks: Dict[str, Task] = {}
        self._task_queue: List[Task] = []  # 优先级队列
        self._running_tasks: Set[str] = set()
        self._completed_tasks: Set[str] = set()
        self._failed_tasks: Set[str] = set()
        self._agents: Dict[str, AgentBase] = {}
        self._task_counter: int = 0
        self._lock = asyncio.Lock()
        self._logger = logger.bind(module="TaskManager")
        
        # 任务回调
        self._on_task_complete: Optional[Callable[[Task], None]] = None
        self._on_task_fail: Optional[Callable[[Task], None]] = None
        self._on_task_start: Optional[Callable[[Task], None]] = None
    
    def register_agent(self, agent: AgentBase) -> None:
        """
        注册Agent
        
        Args:
            agent: Agent实例
        """
        self._agents[agent.name] = agent
        self._logger.info(f"Agent {agent.name} registered")
    
    def unregister_agent(self, agent_name: str) -> None:
        """
        注销Agent
        
        Args:
            agent_name: Agent名称
        """
        if agent_name in self._agents:
            del self._agents[agent_name]
            self._logger.info(f"Agent {agent_name} unregistered")
    
    def get_agent(self, agent_name: str) -> Optional[AgentBase]:
        """
        获取Agent
        
        Args:
            agent_name: Agent名称
            
        Returns:
            Optional[AgentBase]: Agent实例
        """
        return self._agents.get(agent_name)
    
    def create_task(
        self,
        name: str,
        agent_name: str,
        params: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout: int = 300,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        创建任务
        
        Args:
            name: 任务名称
            agent_name: 执行Agent名称
            params: 任务参数
            priority: 任务优先级
            dependencies: 依赖任务ID列表
            max_retries: 最大重试次数
            timeout: 超时时间
            description: 任务描述
            metadata: 元数据
            
        Returns:
            Task: 创建的任务
            
        Raises:
            ValueError: Agent不存在
        """
        if agent_name not in self._agents:
            raise ValueError(f"Agent {agent_name} not registered")
        
        # 生成任务ID
        self._task_counter += 1
        task_id = f"task_{self._task_counter:06d}"
        
        # 创建任务
        task = Task(
            id=task_id,
            name=name,
            description=description,
            agent_name=agent_name,
            params=params or {},
            priority=priority,
            dependencies=dependencies or [],
            max_retries=max_retries,
            timeout=timeout,
            metadata=metadata or {},
        )
        
        # 存储任务
        self._tasks[task_id] = task
        
        # 检查依赖是否满足
        if self._check_dependencies(task):
            task.status = TaskStatus.QUEUED
            heapq.heappush(self._task_queue, task)
            self._logger.info(f"Task {task_id} queued")
        else:
            self._logger.info(f"Task {task_id} waiting for dependencies")
        
        return task
    
    def _check_dependencies(self, task: Task) -> bool:
        """
        检查任务依赖是否满足
        
        Args:
            task: 任务
            
        Returns:
            bool: 依赖是否满足
        """
        for dep_id in task.dependencies:
            if dep_id not in self._tasks:
                return False
            dep_task = self._tasks[dep_id]
            if dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
    
    async def submit_task(self, task: Task) -> None:
        """
        提交任务执行
        
        Args:
            task: 任务
        """
        async with self._lock:
            if task.status != TaskStatus.QUEUED:
                raise RuntimeError(f"Task {task.id} is not in queued state")
            
            # 检查并发限制
            if len(self._running_tasks) >= self.max_concurrent_tasks:
                self._logger.warning(f"Max concurrent tasks reached, task {task.id} will wait")
                return
            
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self._running_tasks.add(task.id)
            
            # 触发回调
            if self._on_task_start:
                self._on_task_start(task)
            
            self._logger.info(f"Task {task.id} started")
            
            # 异步执行任务
            asyncio.create_task(self._execute_task(task))
    
    async def _execute_task(self, task: Task) -> None:
        """
        执行任务
        
        Args:
            task: 任务
        """
        try:
            # 获取Agent
            agent = self._agents[task.agent_name]
            
            # 执行任务
            result = await asyncio.wait_for(
                agent.execute(**task.params),
                timeout=task.timeout
            )
            
            # 更新任务状态
            task.result = result
            task.completed_at = datetime.now()
            
            if result.success:
                task.status = TaskStatus.COMPLETED
                self._completed_tasks.add(task.id)
                self._logger.info(f"Task {task.id} completed successfully")
                
                # 触发回调
                if self._on_task_complete:
                    self._on_task_complete(task)
                
                # 检查依赖此任务的其他任务
                await self._check_dependent_tasks(task.id)
            else:
                await self._handle_task_failure(task, result.error)
                
        except asyncio.TimeoutError:
            await self._handle_task_failure(task, f"Task timed out after {task.timeout} seconds")
            
        except Exception as e:
            await self._handle_task_failure(task, str(e))
            
        finally:
            # 从运行集合中移除
            self._running_tasks.discard(task.id)
            
            # 尝试执行队列中的下一个任务
            await self._process_queue()
    
    async def _handle_task_failure(self, task: Task, error: str) -> None:
        """
        处理任务失败
        
        Args:
            task: 任务
            error: 错误信息
        """
        task.error = error
        task.retry_count += 1
        
        # 检查是否需要重试
        if task.retry_count < task.max_retries:
            self._logger.warning(f"Task {task.id} failed, retrying ({task.retry_count}/{task.max_retries})")
            task.status = TaskStatus.QUEUED
            heapq.heappush(self._task_queue, task)
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            self._failed_tasks.add(task.id)
            self._logger.error(f"Task {task.id} failed after {task.max_retries} retries: {error}")
            
            # 触发回调
            if self._on_task_fail:
                self._on_task_fail(task)
    
    async def _check_dependent_tasks(self, completed_task_id: str) -> None:
        """
        检查依赖已完成任务的其他任务
        
        Args:
            completed_task_id: 已完成任务ID
        """
        for task in self._tasks.values():
            if (completed_task_id in task.dependencies and 
                task.status == TaskStatus.PENDING and
                self._check_dependencies(task)):
                task.status = TaskStatus.QUEUED
                heapq.heappush(self._task_queue, task)
                self._logger.info(f"Task {task.id} queued after dependency {completed_task_id} completed")
    
    async def _process_queue(self) -> None:
        """处理任务队列"""
        while (self._task_queue and 
               len(self._running_tasks) < self.max_concurrent_tasks):
            task = heapq.heappop(self._task_queue)
            if task.status == TaskStatus.QUEUED:
                await self.submit_task(task)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        
        # 从队列中移除
        if task in self._task_queue:
            self._task_queue.remove(task)
            heapq.heapify(self._task_queue)
        
        # 从运行集合中移除
        self._running_tasks.discard(task_id)
        
        self._logger.info(f"Task {task_id} cancelled")
        return True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Task]: 任务实例
        """
        return self._tasks.get(task_id)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        根据状态获取任务列表
        
        Args:
            status: 任务状态
            
        Returns:
            List[Task]: 任务列表
        """
        return [task for task in self._tasks.values() if task.status == status]
    
    def get_all_tasks(self) -> List[Task]:
        """
        获取所有任务
        
        Returns:
            List[Task]: 任务列表
        """
        return list(self._tasks.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取任务统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        status_counts = defaultdict(int)
        for task in self._tasks.values():
            status_counts[task.status.value] += 1
        
        return {
            "total_tasks": len(self._tasks),
            "pending_tasks": status_counts.get(TaskStatus.PENDING.value, 0),
            "queued_tasks": status_counts.get(TaskStatus.QUEUED.value, 0),
            "running_tasks": len(self._running_tasks),
            "completed_tasks": len(self._completed_tasks),
            "failed_tasks": len(self._failed_tasks),
            "cancelled_tasks": status_counts.get(TaskStatus.CANCELLED.value, 0),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "registered_agents": len(self._agents),
        }
    
    def set_callbacks(
        self,
        on_task_start: Optional[Callable[[Task], None]] = None,
        on_task_complete: Optional[Callable[[Task], None]] = None,
        on_task_fail: Optional[Callable[[Task], None]] = None,
    ) -> None:
        """
        设置回调函数
        
        Args:
            on_task_start: 任务开始回调
            on_task_complete: 任务完成回调
            on_task_fail: 任务失败回调
        """
        self._on_task_start = on_task_start
        self._on_task_complete = on_task_complete
        self._on_task_fail = on_task_fail
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Task:
        """
        等待任务完成
        
        Args:
            task_id: 任务ID
            timeout: 超时时间(秒)
            
        Returns:
            Task: 完成的任务
            
        Raises:
            asyncio.TimeoutError: 超时
            ValueError: 任务不存在
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self._tasks[task_id]
        
        async def _wait():
            while task.status in (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING):
                await asyncio.sleep(0.1)
            return task
        
        if timeout:
            return await asyncio.wait_for(_wait(), timeout=timeout)
        else:
            return await _wait()
    
    async def wait_for_all_tasks(self, timeout: Optional[float] = None) -> List[Task]:
        """
        等待所有任务完成
        
        Args:
            timeout: 超时时间(秒)
            
        Returns:
            List[Task]: 完成的任务列表
        """
        async def _wait_all():
            while any(task.status in (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING) 
                     for task in self._tasks.values()):
                await asyncio.sleep(0.1)
            return list(self._tasks.values())
        
        if timeout:
            return await asyncio.wait_for(_wait_all(), timeout=timeout)
        else:
            return await _wait_all()
    
    def clear_completed_tasks(self) -> int:
        """
        清理已完成的任务
        
        Returns:
            int: 清理的任务数量
        """
        completed_ids = [
            task_id for task_id, task in self._tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]
        
        for task_id in completed_ids:
            del self._tasks[task_id]
            self._completed_tasks.discard(task_id)
            self._failed_tasks.discard(task_id)
        
        return len(completed_ids)
    
    def reset(self) -> None:
        """重置任务管理器"""
        self._tasks.clear()
        self._task_queue.clear()
        self._running_tasks.clear()
        self._completed_tasks.clear()
        self._failed_tasks.clear()
        self._task_counter = 0
        self._logger.info("TaskManager reset")