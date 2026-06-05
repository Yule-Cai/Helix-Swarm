"""
核心模块

提供Agent框架的核心功能，包括：
- Agent基类
- 任务管理
- 状态管理
- 工作流引擎
- 记忆管理
"""

from .agent_base import AgentBase, AgentResult
from .task_manager import TaskManager, Task, TaskStatus, TaskPriority
from .state_manager import StateManager, StateType, State
from .workflow_engine import WorkflowEngine, Workflow, WorkflowStep, WorkflowStatus, StepStatus
from .memory import MemoryManager, MemoryEntry, MemoryType

__all__ = [
    # Agent基类
    "AgentBase",
    "AgentResult",
    
    # 任务管理
    "TaskManager",
    "Task",
    "TaskStatus",
    "TaskPriority",
    
    # 状态管理
    "StateManager",
    "StateType",
    "State",
    
    # 工作流引擎
    "WorkflowEngine",
    "Workflow",
    "WorkflowStep",
    "WorkflowStatus",
    "StepStatus",
    
    # 记忆管理
    "MemoryManager",
    "MemoryEntry",
    "MemoryType",
]