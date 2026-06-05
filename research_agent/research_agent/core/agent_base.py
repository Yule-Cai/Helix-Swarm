"""
Agent基类模块

提供所有Agent的基础类，包含任务执行接口和状态管理接口。
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from pydantic import BaseModel, Field
from loguru import logger

from ..config.settings import settings


class AgentState(str, Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentResult(BaseModel):
    """Agent执行结果"""
    success: bool = Field(..., description="执行是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="结果数据")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    execution_time: float = Field(0.0, description="执行时间(秒)")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentConfig(BaseModel):
    """Agent配置"""
    name: str = Field(..., description="Agent名称")
    description: str = Field("", description="Agent描述")
    version: str = Field("1.0.0", description="版本号")
    max_retries: int = Field(3, description="最大重试次数")
    timeout: int = Field(300, description="超时时间(秒)")
    debug: bool = Field(False, description="调试模式")
    dependencies: List[str] = Field(default_factory=list, description="依赖的Agent列表")
    
    class Config:
        arbitrary_types_allowed = True


T = TypeVar('T', bound=AgentConfig)


class AgentBase(ABC, Generic[T]):
    """
    Agent基类
    
    所有Agent必须继承此类并实现抽象方法。
    
    Attributes:
        config: Agent配置
        state: Agent状态
        start_time: 开始时间
        end_time: 结束时间
    """
    
    def __init__(self, config: Optional[T] = None):
        """
        初始化Agent
        
        Args:
            config: Agent配置，如果为None则使用默认配置
        """
        self.config = config or self._get_default_config()
        self.state: AgentState = AgentState.IDLE
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._retry_count: int = 0
        self._results: List[AgentResult] = []
        self._logger = logger.bind(agent=self.config.name)
        
        # 初始化Agent
        self._initialize()
    
    def _get_default_config(self) -> T:
        """获取默认配置"""
        return AgentConfig(
            name=self.__class__.__name__,
            description=self.__class__.__doc__ or "",
        )
    
    def _initialize(self) -> None:
        """初始化Agent，子类可以重写此方法"""
        self._logger.info(f"Agent {self.config.name} initialized")
    
    @property
    def name(self) -> str:
        """获取Agent名称"""
        return self.config.name
    
    @property
    def is_running(self) -> bool:
        """检查Agent是否正在运行"""
        return self.state == AgentState.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """检查Agent是否已完成"""
        return self.state == AgentState.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """检查Agent是否失败"""
        return self.state == AgentState.FAILED
    
    @property
    def execution_time(self) -> float:
        """获取执行时间"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def last_result(self) -> Optional[AgentResult]:
        """获取最后一次执行结果"""
        return self._results[-1] if self._results else None
    
    @property
    def results(self) -> List[AgentResult]:
        """获取所有执行结果"""
        return self._results.copy()
    
    async def execute(self, **kwargs) -> AgentResult:
        """
        执行Agent任务
        
        Args:
            **kwargs: 任务参数
            
        Returns:
            AgentResult: 执行结果
        """
        if self.is_running:
            raise RuntimeError(f"Agent {self.name} is already running")
        
        self.state = AgentState.RUNNING
        self.start_time = datetime.now()
        self._retry_count = 0
        
        self._logger.info(f"Agent {self.name} started with params: {kwargs}")
        
        try:
            # 执行任务
            result = await self._execute(**kwargs)
            
            # 记录结果
            self._results.append(result)
            
            if result.success:
                self.state = AgentState.COMPLETED
                self._logger.info(f"Agent {self.name} completed successfully")
            else:
                self.state = AgentState.FAILED
                self._logger.error(f"Agent {self.name} failed: {result.error}")
            
            return result
            
        except Exception as e:
            self.state = AgentState.FAILED
            error_msg = f"Agent {self.name} failed with exception: {str(e)}"
            self._logger.exception(error_msg)
            
            result = AgentResult(
                success=False,
                error=error_msg,
                execution_time=(datetime.now() - self.start_time).total_seconds()
            )
            self._results.append(result)
            return result
            
        finally:
            self.end_time = datetime.now()
    
    @abstractmethod
    async def _execute(self, **kwargs) -> AgentResult:
        """
        执行具体任务（子类必须实现）
        
        Args:
            **kwargs: 任务参数
            
        Returns:
            AgentResult: 执行结果
        """
        raise NotImplementedError("Subclasses must implement _execute method")
    
    async def retry(self, **kwargs) -> AgentResult:
        """
        重试任务
        
        Args:
            **kwargs: 任务参数
            
        Returns:
            AgentResult: 执行结果
        """
        if self._retry_count >= self.config.max_retries:
            return AgentResult(
                success=False,
                error=f"Max retries ({self.config.max_retries}) exceeded",
                metadata={"retry_count": self._retry_count}
            )
        
        self._retry_count += 1
        self._logger.info(f"Retrying agent {self.name} (attempt {self._retry_count})")
        
        return await self.execute(**kwargs)
    
    async def pause(self) -> None:
        """暂停Agent"""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.PAUSED
            self._logger.info(f"Agent {self.name} paused")
            await self._on_pause()
    
    async def resume(self) -> None:
        """恢复Agent"""
        if self.state == AgentState.PAUSED:
            self.state = AgentState.RUNNING
            self._logger.info(f"Agent {self.name} resumed")
            await self._on_resume()
    
    async def cancel(self) -> None:
        """取消Agent"""
        if self.state in (AgentState.RUNNING, AgentState.PAUSED):
            self.state = AgentState.CANCELLED
            self._logger.info(f"Agent {self.name} cancelled")
            await self._on_cancel()
    
    async def _on_pause(self) -> None:
        """暂停回调，子类可以重写"""
        pass
    
    async def _on_resume(self) -> None:
        """恢复回调，子类可以重写"""
        pass
    
    async def _on_cancel(self) -> None:
        """取消回调，子类可以重写"""
        pass
    
    def reset(self) -> None:
        """重置Agent状态"""
        self.state = AgentState.IDLE
        self.start_time = None
        self.end_time = None
        self._retry_count = 0
        self._results.clear()
        self._logger.info(f"Agent {self.name} reset")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Agent状态信息
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time": self.execution_time,
            "retry_count": self._retry_count,
            "results_count": len(self._results),
            "last_result": self.last_result.dict() if self.last_result else None,
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', state='{self.state.value}')>"


class SimpleAgent(AgentBase[AgentConfig]):
    """
    简单Agent实现示例
    
    展示如何继承和实现AgentBase。
    """
    
    async def _execute(self, **kwargs) -> AgentResult:
        """
        执行简单任务
        
        Args:
            **kwargs: 任务参数
            
        Returns:
            AgentResult: 执行结果
        """
        self._logger.info(f"Executing simple task with params: {kwargs}")
        
        # 模拟任务执行
        await asyncio.sleep(1)
        
        return AgentResult(
            success=True,
            data={"message": "Task completed successfully"},
            metadata={"agent": self.name}
        )