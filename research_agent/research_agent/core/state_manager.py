"""
状态管理器模块

负责全局状态管理、Agent间状态共享和持久化存储。
"""

import asyncio
import json
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar
from pydantic import BaseModel, Field
from loguru import logger
import redis.asyncio as redis

from ..config.settings import settings


class StateType(str, Enum):
    """状态类型枚举"""
    GLOBAL = "global"
    AGENT = "agent"
    TASK = "task"
    WORKFLOW = "workflow"
    USER = "user"


class State(BaseModel):
    """状态模型"""
    id: str = Field(..., description="状态ID")
    type: StateType = Field(..., description="状态类型")
    key: str = Field(..., description="状态键")
    value: Any = Field(None, description="状态值")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    version: int = Field(1, description="版本号")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StateManager:
    """
    状态管理器
    
    负责全局状态管理、Agent间状态共享和持久化存储。
    
    Features:
        - 多级状态管理（全局、Agent、任务、工作流）
        - 状态版本控制
        - 状态过期机制
        - 状态变更通知
        - 持久化存储（Redis）
        - 内存缓存
    """
    
    def __init__(self, use_redis: bool = True):
        """
        初始化状态管理器
        
        Args:
            use_redis: 是否使用Redis持久化
        """
        self.use_redis = use_redis
        self._states: Dict[str, State] = {}
        self._redis_client: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()
        self._logger = logger.bind(module="StateManager")
        
        # 状态变更回调
        self._on_state_change: Optional[Callable[[State, str], None]] = None
        
        # 状态键前缀
        self._key_prefix = "research_agent:state:"
    
    async def initialize(self) -> None:
        """初始化状态管理器"""
        if self.use_redis:
            try:
                self._redis_client = redis.Redis(
                    host=settings.redis.host,
                    port=settings.redis.port,
                    password=settings.redis.password,
                    db=settings.redis.db,
                    decode_responses=True
                )
                # 测试连接
                await self._redis_client.ping()
                self._logger.info("Redis connection established")
            except Exception as e:
                self._logger.warning(f"Redis connection failed: {e}, using in-memory storage")
                self.use_redis = False
        
        self._logger.info("StateManager initialized")
    
    async def close(self) -> None:
        """关闭状态管理器"""
        if self._redis_client:
            await self._redis_client.close()
            self._logger.info("Redis connection closed")
    
    def _get_key(self, state_type: StateType, key: str) -> str:
        """
        生成状态键
        
        Args:
            state_type: 状态类型
            key: 状态键
            
        Returns:
            str: 完整的状态键
        """
        return f"{self._key_prefix}{state_type.value}:{key}"
    
    async def set(
        self,
        state_type: StateType,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        expires_in: Optional[int] = None,
    ) -> State:
        """
        设置状态
        
        Args:
            state_type: 状态类型
            key: 状态键
            value: 状态值
            metadata: 元数据
            expires_in: 过期时间(秒)
            
        Returns:
            State: 状态对象
        """
        async with self._lock:
            full_key = self._get_key(state_type, key)
            
            # 检查是否存在
            existing_state = self._states.get(full_key)
            
            if existing_state:
                # 更新现有状态
                existing_state.value = value
                existing_state.metadata = metadata or existing_state.metadata
                existing_state.updated_at = datetime.now()
                existing_state.version += 1
                
                if expires_in:
                    from datetime import timedelta
                    existing_state.expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                state = existing_state
                action = "updated"
            else:
                # 创建新状态
                state_id = f"{state_type.value}_{key}_{datetime.now().timestamp()}"
                expires_at = None
                if expires_in:
                    from datetime import timedelta
                    expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                state = State(
                    id=state_id,
                    type=state_type,
                    key=key,
                    value=value,
                    metadata=metadata or {},
                    expires_at=expires_at,
                )
                self._states[full_key] = state
                action = "created"
            
            # 持久化到Redis
            if self.use_redis and self._redis_client:
                try:
                    await self._redis_client.set(
                        full_key,
                        state.json(),
                        ex=expires_in
                    )
                except Exception as e:
                    self._logger.error(f"Failed to persist state to Redis: {e}")
            
            # 触发回调
            if self._on_state_change:
                self._on_state_change(state, action)
            
            self._logger.debug(f"State {action}: {full_key}")
            return state
    
    async def get(
        self,
        state_type: StateType,
        key: str,
        default: Any = None,
    ) -> Optional[Any]:
        """
        获取状态值
        
        Args:
            state_type: 状态类型
            key: 状态键
            default: 默认值
            
        Returns:
            Optional[Any]: 状态值
        """
        full_key = self._get_key(state_type, key)
        
        # 先从内存缓存获取
        state = self._states.get(full_key)
        
        if state:
            # 检查是否过期
            if state.expires_at and state.expires_at < datetime.now():
                await self.delete(state_type, key)
                return default
            return state.value
        
        # 从Redis获取
        if self.use_redis and self._redis_client:
            try:
                data = await self._redis_client.get(full_key)
                if data:
                    state = State.parse_raw(data)
                    # 检查是否过期
                    if state.expires_at and state.expires_at < datetime.now():
                        await self.delete(state_type, key)
                        return default
                    # 缓存到内存
                    self._states[full_key] = state
                    return state.value
            except Exception as e:
                self._logger.error(f"Failed to get state from Redis: {e}")
        
        return default
    
    async def get_state(
        self,
        state_type: StateType,
        key: str,
    ) -> Optional[State]:
        """
        获取完整状态对象
        
        Args:
            state_type: 状态类型
            key: 状态键
            
        Returns:
            Optional[State]: 状态对象
        """
        full_key = self._get_key(state_type, key)
        
        # 先从内存缓存获取
        state = self._states.get(full_key)
        
        if state:
            # 检查是否过期
            if state.expires_at and state.expires_at < datetime.now():
                await self.delete(state_type, key)
                return None
            return state
        
        # 从Redis获取
        if self.use_redis and self._redis_client:
            try:
                data = await self._redis_client.get(full_key)
                if data:
                    state = State.parse_raw(data)
                    # 检查是否过期
                    if state.expires_at and state.expires_at < datetime.now():
                        await self.delete(state_type, key)
                        return None
                    # 缓存到内存
                    self._states[full_key] = state
                    return state
            except Exception as e:
                self._logger.error(f"Failed to get state from Redis: {e}")
        
        return None
    
    async def delete(
        self,
        state_type: StateType,
        key: str,
    ) -> bool:
        """
        删除状态
        
        Args:
            state_type: 状态类型
            key: 状态键
            
        Returns:
            bool: 是否成功删除
        """
        async with self._lock:
            full_key = self._get_key(state_type, key)
            
            # 从内存删除
            if full_key in self._states:
                del self._states[full_key]
            
            # 从Redis删除
            if self.use_redis and self._redis_client:
                try:
                    await self._redis_client.delete(full_key)
                except Exception as e:
                    self._logger.error(f"Failed to delete state from Redis: {e}")
            
            self._logger.debug(f"State deleted: {full_key}")
            return True
    
    async def exists(
        self,
        state_type: StateType,
        key: str,
    ) -> bool:
        """
        检查状态是否存在
        
        Args:
            state_type: 状态类型
            key: 状态键
            
        Returns:
            bool: 状态是否存在
        """
        full_key = self._get_key(state_type, key)
        
        # 检查内存缓存
        if full_key in self._states:
            state = self._states[full_key]
            # 检查是否过期
            if state.expires_at and state.expires_at < datetime.now():
                await self.delete(state_type, key)
                return False
            return True
        
        # 检查Redis
        if self.use_redis and self._redis_client:
            try:
                return await self._redis_client.exists(full_key) > 0
            except Exception as e:
                self._logger.error(f"Failed to check state existence in Redis: {e}")
        
        return False
    
    async def get_by_type(
        self,
        state_type: StateType,
        prefix: Optional[str] = None,
    ) -> List[State]:
        """
        根据类型获取状态列表
        
        Args:
            state_type: 状态类型
            key_prefix: 键前缀
            
        Returns:
            List[State]: 状态列表
        """
        states = []
        
        # 从内存缓存获取
        for full_key, state in self._states.items():
            if full_key.startswith(f"{self._key_prefix}{state_type.value}:"):
                if prefix is None or state.key.startswith(prefix):
                    # 检查是否过期
                    if state.expires_at and state.expires_at < datetime.now():
                        continue
                    states.append(state)
        
        # 从Redis获取
        if self.use_redis and self._redis_client:
            try:
                pattern = f"{self._key_prefix}{state_type.value}:"
                if prefix:
                    pattern += f"{prefix}*"
                else:
                    pattern += "*"
                
                keys = await self._redis_client.keys(pattern)
                for key in keys:
                    if key not in self._states:
                        data = await self._redis_client.get(key)
                        if data:
                            state = State.parse_raw(data)
                            # 检查是否过期
                            if state.expires_at and state.expires_at < datetime.now():
                                await self._redis_client.delete(key)
                                continue
                            # 缓存到内存
                            self._states[key] = state
                            states.append(state)
            except Exception as e:
                self._logger.error(f"Failed to get states from Redis: {e}")
        
        return states
    
    async def clear_by_type(self, state_type: StateType) -> int:
        """
        根据类型清除状态
        
        Args:
            state_type: 状态类型
            
        Returns:
            int: 清除的状态数量
        """
        async with self._lock:
            count = 0
            
            # 从内存清除
            keys_to_delete = []
            for full_key in self._states:
                if full_key.startswith(f"{self._key_prefix}{state_type.value}:"):
                    keys_to_delete.append(full_key)
            
            for key in keys_to_delete:
                del self._states[key]
                count += 1
            
            # 从Redis清除
            if self.use_redis and self._redis_client:
                try:
                    pattern = f"{self._key_prefix}{state_type.value}:*"
                    keys = await self._redis_client.keys(pattern)
                    if keys:
                        await self._redis_client.delete(*keys)
                        count += len(keys)
                except Exception as e:
                    self._logger.error(f"Failed to clear states from Redis: {e}")
            
            self._logger.info(f"Cleared {count} states of type {state_type.value}")
            return count
    
    async def clear_all(self) -> int:
        """
        清除所有状态
        
        Returns:
            int: 清除的状态数量
        """
        async with self._lock:
            count = len(self._states)
            self._states.clear()
            
            # 从Redis清除
            if self.use_redis and self._redis_client:
                try:
                    pattern = f"{self._key_prefix}*"
                    keys = await self._redis_client.keys(pattern)
                    if keys:
                        await self._redis_client.delete(*keys)
                        count += len(keys)
                except Exception as e:
                    self._logger.error(f"Failed to clear all states from Redis: {e}")
            
            self._logger.info(f"Cleared all {count} states")
            return count
    
    def set_on_state_change(self, callback: Callable[[State, str], None]) -> None:
        """
        设置状态变更回调
        
        Args:
            callback: 回调函数
        """
        self._on_state_change = callback
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取状态统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        type_counts = {}
        for state in self._states.values():
            type_name = state.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            "total_states": len(self._states),
            "type_counts": type_counts,
            "use_redis": self.use_redis,
            "redis_connected": self._redis_client is not None,
        }
    
    async def export_states(self, state_type: Optional[StateType] = None) -> Dict[str, Any]:
        """
        导出状态
        
        Args:
            state_type: 状态类型，为None则导出所有
            
        Returns:
            Dict[str, Any]: 状态数据
        """
        states = {}
        
        for full_key, state in self._states.items():
            if state_type is None or state.type == state_type:
                # 检查是否过期
                if state.expires_at and state.expires_at < datetime.now():
                    continue
                states[full_key] = state.dict()
        
        return {
            "exported_at": datetime.now().isoformat(),
            "states": states,
        }
    
    async def import_states(self, data: Dict[str, Any]) -> int:
        """
        导入状态
        
        Args:
            data: 状态数据
            
        Returns:
            int: 导入的状态数量
        """
        count = 0
        
        for full_key, state_data in data.get("states", {}).items():
            try:
                state = State(**state_data)
                self._states[full_key] = state
                
                # 持久化到Redis
                if self.use_redis and self._redis_client:
                    expires_in = None
                    if state.expires_at:
                        expires_in = int((state.expires_at - datetime.now()).total_seconds())
                        if expires_in <= 0:
                            continue
                    await self._redis_client.set(full_key, state.json(), ex=expires_in)
                
                count += 1
            except Exception as e:
                self._logger.error(f"Failed to import state {full_key}: {e}")
        
        self._logger.info(f"Imported {count} states")
        return count