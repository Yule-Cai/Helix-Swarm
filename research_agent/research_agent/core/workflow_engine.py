"""
工作流引擎模块

负责工作流定义、执行和监控。
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from loguru import logger

from .agent_base import AgentBase, AgentResult
from .task_manager import TaskManager, Task, TaskStatus, TaskPriority
from .state_manager import StateManager, StateType


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """步骤状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep(BaseModel):
    """工作流步骤"""
    id: str = Field(..., description="步骤ID")
    name: str = Field(..., description="步骤名称")
    agent_name: str = Field(..., description="执行Agent名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="步骤参数")
    dependencies: List[str] = Field(default_factory=list, description="依赖步骤ID列表")
    condition: Optional[str] = Field(None, description="执行条件表达式")
    timeout: int = Field(300, description="超时时间(秒)")
    retry_count: int = Field(0, description="重试次数")
    max_retries: int = Field(3, description="最大重试次数")
    status: StepStatus = Field(StepStatus.PENDING, description="步骤状态")
    result: Optional[AgentResult] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Workflow(BaseModel):
    """工作流模型"""
    id: str = Field(..., description="工作流ID")
    name: str = Field(..., description="工作流名称")
    description: str = Field("", description="工作流描述")
    steps: List[WorkflowStep] = Field(default_factory=list, description="工作流步骤")
    status: WorkflowStatus = Field(WorkflowStatus.PENDING, description="工作流状态")
    current_step_id: Optional[str] = Field(None, description="当前执行步骤ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    context: Dict[str, Any] = Field(default_factory=dict, description="工作流上下文")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """获取步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_step_dependencies(self, step_id: str) -> List[str]:
        """获取步骤依赖"""
        step = self.get_step(step_id)
        return step.dependencies if step else []
    
    def get_dependent_steps(self, step_id: str) -> List[str]:
        """获取依赖此步骤的步骤"""
        dependent_steps = []
        for step in self.steps:
            if step_id in step.dependencies:
                dependent_steps.append(step.id)
        return dependent_steps


class WorkflowEngine:
    """
    工作流引擎
    
    负责工作流定义、执行和监控。
    
    Features:
        - 工作流定义和验证
        - 工作流执行和监控
        - 步骤依赖管理
        - 条件执行
        - 错误处理和重试
        - 工作流上下文管理
    """
    
    def __init__(self, task_manager: TaskManager, state_manager: StateManager):
        """
        初始化工作流引擎
        
        Args:
            task_manager: 任务管理器
            state_manager: 状态管理器
        """
        self.task_manager = task_manager
        self.state_manager = state_manager
        self._workflows: Dict[str, Workflow] = {}
        self._running_workflows: Set[str] = set()
        self._lock = asyncio.Lock()
        self._logger = logger.bind(module="WorkflowEngine")
        
        # 工作流回调
        self._on_workflow_start: Optional[Callable[[Workflow], None]] = None
        self._on_workflow_complete: Optional[Callable[[Workflow], None]] = None
        self._on_workflow_fail: Optional[Callable[[Workflow], None]] = None
        self._on_step_start: Optional[Callable[[Workflow, WorkflowStep], None]] = None
        self._on_step_complete: Optional[Callable[[Workflow, WorkflowStep], None]] = None
        self._on_step_fail: Optional[Callable[[Workflow, WorkflowStep], None]] = None
    
    def create_workflow(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Workflow:
        """
        创建工作流
        
        Args:
            name: 工作流名称
            steps: 步骤定义列表
            description: 工作流描述
            metadata: 元数据
            
        Returns:
            Workflow: 工作流对象
        """
        # 生成工作流ID
        workflow_id = f"workflow_{datetime.now().timestamp()}"
        
        # 创建步骤对象
        workflow_steps = []
        for i, step_def in enumerate(steps):
            step_id = step_def.get("id", f"step_{i+1}")
            step = WorkflowStep(
                id=step_id,
                name=step_def.get("name", f"Step {i+1}"),
                agent_name=step_def["agent_name"],
                params=step_def.get("params", {}),
                dependencies=step_def.get("dependencies", []),
                condition=step_def.get("condition"),
                timeout=step_def.get("timeout", 300),
                max_retries=step_def.get("max_retries", 3),
            )
            workflow_steps.append(step)
        
        # 验证工作流
        self._validate_workflow(workflow_steps)
        
        # 创建工作流
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=workflow_steps,
            metadata=metadata or {},
        )
        
        self._workflows[workflow_id] = workflow
        self._logger.info(f"Workflow {workflow_id} created: {name}")
        
        return workflow
    
    def _validate_workflow(self, steps: List[WorkflowStep]) -> None:
        """
        验证工作流
        
        Args:
            steps: 步骤列表
            
        Raises:
            ValueError: 工作流无效
        """
        step_ids = {step.id for step in steps}
        
        for step in steps:
            # 检查依赖是否存在
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    raise ValueError(f"Step {step.id} depends on non-existent step {dep_id}")
        
        # 检查是否有循环依赖
        if self._has_circular_dependencies(steps):
            raise ValueError("Workflow has circular dependencies")
    
    def _has_circular_dependencies(self, steps: List[WorkflowStep]) -> bool:
        """
        检查是否有循环依赖
        
        Args:
            steps: 步骤列表
            
        Returns:
            bool: 是否有循环依赖
        """
        # 构建依赖图
        graph = {step.id: set(step.dependencies) for step in steps}
        
        # 使用DFS检测循环
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if dfs(node):
                    return True
        
        return False
    
    async def execute_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Workflow:
        """
        执行工作流
        
        Args:
            workflow_id: 工作流ID
            context: 初始上下文
            
        Returns:
            Workflow: 执行完成的工作流
            
        Raises:
            ValueError: 工作流不存在
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self._workflows[workflow_id]
        
        if workflow.status == WorkflowStatus.RUNNING:
            raise RuntimeError(f"Workflow {workflow_id} is already running")
        
        # 初始化工作流
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        workflow.context = context or {}
        self._running_workflows.add(workflow_id)
        
        # 触发回调
        if self._on_workflow_start:
            self._on_workflow_start(workflow)
        
        self._logger.info(f"Workflow {workflow_id} started")
        
        try:
            # 执行工作流
            await self._execute_workflow_steps(workflow)
            
            # 检查工作流状态
            if all(step.status == StepStatus.COMPLETED for step in workflow.steps):
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now()
                self._logger.info(f"Workflow {workflow_id} completed")
                
                # 触发回调
                if self._on_workflow_complete:
                    self._on_workflow_complete(workflow)
            else:
                workflow.status = WorkflowStatus.FAILED
                workflow.completed_at = datetime.now()
                self._logger.error(f"Workflow {workflow_id} failed")
                
                # 触发回调
                if self._on_workflow_fail:
                    self._on_workflow_fail(workflow)
            
            return workflow
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now()
            self._logger.exception(f"Workflow {workflow_id} failed with exception: {e}")
            
            # 触发回调
            if self._on_workflow_fail:
                self._on_workflow_fail(workflow)
            
            return workflow
            
        finally:
            self._running_workflows.discard(workflow_id)
            
            # 保存工作流状态
            await self._save_workflow_state(workflow)
    
    async def _execute_workflow_steps(self, workflow: Workflow) -> None:
        """
        执行工作流步骤
        
        Args:
            workflow: 工作流
        """
        # 获取可以执行的步骤
        executable_steps = self._get_executable_steps(workflow)
        
        while executable_steps:
            # 并行执行所有可执行的步骤
            tasks = []
            for step in executable_steps:
                task = asyncio.create_task(self._execute_step(workflow, step))
                tasks.append(task)
            
            # 等待所有步骤完成
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 检查是否有失败的步骤
            failed_steps = [step for step in workflow.steps if step.status == StepStatus.FAILED]
            if failed_steps:
                self._logger.error(f"Workflow has {len(failed_steps)} failed steps")
                break
            
            # 获取下一批可执行的步骤
            executable_steps = self._get_executable_steps(workflow)
    
    def _get_executable_steps(self, workflow: Workflow) -> List[WorkflowStep]:
        """
        获取可执行的步骤
        
        Args:
            workflow: 工作流
            
        Returns:
            List[WorkflowStep]: 可执行的步骤列表
        """
        executable_steps = []
        
        for step in workflow.steps:
            # 跳过已完成或失败的步骤
            if step.status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED):
                continue
            
            # 检查依赖是否满足
            dependencies_met = all(
                workflow.get_step(dep_id).status == StepStatus.COMPLETED
                for dep_id in step.dependencies
            )
            
            if dependencies_met:
                # 检查条件
                if step.condition:
                    try:
                        # 评估条件表达式
                        condition_result = eval(step.condition, {"context": workflow.context})
                        if not condition_result:
                            step.status = StepStatus.SKIPPED
                            continue
                    except Exception as e:
                        self._logger.error(f"Failed to evaluate condition for step {step.id}: {e}")
                        step.status = StepStatus.FAILED
                        step.error = f"Condition evaluation failed: {e}"
                        continue
                
                executable_steps.append(step)
        
        return executable_steps
    
    async def _execute_step(self, workflow: Workflow, step: WorkflowStep) -> None:
        """
        执行单个步骤
        
        Args:
            workflow: 工作流
            step: 步骤
        """
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        workflow.current_step_id = step.id
        
        # 触发回调
        if self._on_step_start:
            self._on_step_start(workflow, step)
        
        self._logger.info(f"Executing step {step.id}: {step.name}")
        
        try:
            # 准备参数
            params = {**step.params, **workflow.context}
            
            # 创建任务
            task = self.task_manager.create_task(
                name=f"Workflow {workflow.id} - Step {step.id}",
                agent_name=step.agent_name,
                params=params,
                priority=TaskPriority.HIGH,
                timeout=step.timeout,
                max_retries=step.max_retries,
            )
            
            # 提交任务
            await self.task_manager.submit_task(task)
            
            # 等待任务完成
            completed_task = await self.task_manager.wait_for_task(task.id, timeout=step.timeout)
            
            # 更新步骤状态
            step.result = completed_task.result
            step.completed_at = datetime.now()
            
            if completed_task.status == TaskStatus.COMPLETED:
                step.status = StepStatus.COMPLETED
                
                # 更新工作流上下文
                if step.result and step.result.data:
                    workflow.context.update(step.result.data)
                
                self._logger.info(f"Step {step.id} completed")
                
                # 触发回调
                if self._on_step_complete:
                    self._on_step_complete(workflow, step)
            else:
                step.status = StepStatus.FAILED
                step.error = completed_task.error
                self._logger.error(f"Step {step.id} failed: {step.error}")
                
                # 触发回调
                if self._on_step_fail:
                    self._on_step_fail(workflow, step)
                
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.now()
            self._logger.exception(f"Step {step.id} failed with exception: {e}")
            
            # 触发回调
            if self._on_step_fail:
                self._on_step_fail(workflow, step)
    
    async def _save_workflow_state(self, workflow: Workflow) -> None:
        """
        保存工作流状态
        
        Args:
            workflow: 工作流
        """
        await self.state_manager.set(
            StateType.WORKFLOW,
            workflow.id,
            workflow.dict(),
            metadata={"workflow_name": workflow.name}
        )
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """
        暂停工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功暂停
        """
        if workflow_id not in self._workflows:
            return False
        
        workflow = self._workflows[workflow_id]
        
        if workflow.status != WorkflowStatus.RUNNING:
            return False
        
        workflow.status = WorkflowStatus.PAUSED
        self._logger.info(f"Workflow {workflow_id} paused")
        
        return True
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """
        恢复工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功恢复
        """
        if workflow_id not in self._workflows:
            return False
        
        workflow = self._workflows[workflow_id]
        
        if workflow.status != WorkflowStatus.PAUSED:
            return False
        
        workflow.status = WorkflowStatus.RUNNING
        self._logger.info(f"Workflow {workflow_id} resumed")
        
        # 继续执行
        asyncio.create_task(self.execute_workflow(workflow_id, workflow.context))
        
        return True
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        取消工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功取消
        """
        if workflow_id not in self._workflows:
            return False
        
        workflow = self._workflows[workflow_id]
        
        if workflow.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED):
            return False
        
        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.now()
        self._running_workflows.discard(workflow_id)
        
        self._logger.info(f"Workflow {workflow_id} cancelled")
        
        return True
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        获取工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            Optional[Workflow]: 工作流对象
        """
        return self._workflows.get(workflow_id)
    
    def get_all_workflows(self) -> List[Workflow]:
        """
        获取所有工作流
        
        Returns:
            List[Workflow]: 工作流列表
        """
        return list(self._workflows.values())
    
    def get_running_workflows(self) -> List[Workflow]:
        """
        获取正在运行的工作流
        
        Returns:
            List[Workflow]: 工作流列表
        """
        return [
            workflow for workflow in self._workflows.values()
            if workflow.status == WorkflowStatus.RUNNING
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取工作流统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        status_counts = {}
        for workflow in self._workflows.values():
            status_name = workflow.status.value
            status_counts[status_name] = status_counts.get(status_name, 0) + 1
        
        return {
            "total_workflows": len(self._workflows),
            "running_workflows": len(self._running_workflows),
            "status_counts": status_counts,
        }
    
    def set_callbacks(
        self,
        on_workflow_start: Optional[Callable[[Workflow], None]] = None,
        on_workflow_complete: Optional[Callable[[Workflow], None]] = None,
        on_workflow_fail: Optional[Callable[[Workflow], None]] = None,
        on_step_start: Optional[Callable[[Workflow, WorkflowStep], None]] = None,
        on_step_complete: Optional[Callable[[Workflow, WorkflowStep], None]] = None,
        on_step_fail: Optional[Callable[[Workflow, WorkflowStep], None]] = None,
    ) -> None:
        """
        设置回调函数
        
        Args:
            on_workflow_start: 工作流开始回调
            on_workflow_complete: 工作流完成回调
            on_workflow_fail: 工作流失败回调
            on_step_start: 步骤开始回调
            on_step_complete: 步骤完成回调
            on_step_fail: 步骤失败回调
        """
        self._on_workflow_start = on_workflow_start
        self._on_workflow_complete = on_workflow_complete
        self._on_workflow_fail = on_workflow_fail
        self._on_step_start = on_step_start
        self._on_step_complete = on_step_complete
        self._on_step_fail = on_step_fail
    
    async def wait_for_workflow(self, workflow_id: str, timeout: Optional[float] = None) -> Workflow:
        """
        等待工作流完成
        
        Args:
            workflow_id: 工作流ID
            timeout: 超时时间(秒)
            
        Returns:
            Workflow: 完成的工作流
            
        Raises:
            asyncio.TimeoutError: 超时
            ValueError: 工作流不存在
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self._workflows[workflow_id]
        
        async def _wait():
            while workflow.status in (WorkflowStatus.PENDING, WorkflowStatus.RUNNING, WorkflowStatus.PAUSED):
                await asyncio.sleep(0.1)
            return workflow
        
        if timeout:
            return await asyncio.wait_for(_wait(), timeout=timeout)
        else:
            return await _wait()
    
    def clear_completed_workflows(self) -> int:
        """
        清理已完成的工作流
        
        Returns:
            int: 清理的工作流数量
        """
        completed_ids = [
            workflow_id for workflow_id, workflow in self._workflows.items()
            if workflow.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED)
        ]
        
        for workflow_id in completed_ids:
            del self._workflows[workflow_id]
        
        return len(completed_ids)
    
    def reset(self) -> None:
        """重置工作流引擎"""
        self._workflows.clear()
        self._running_workflows.clear()
        self._logger.info("WorkflowEngine reset")