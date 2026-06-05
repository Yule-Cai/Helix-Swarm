"""
记忆管理模块

提供记忆管理功能，包括：
- 短期记忆
- 长期记忆
- 记忆搜索
- 记忆整合
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class MemoryType(Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    memory_type: str = "short_term"
    importance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """从字典创建"""
        entry = cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data.get("content", ""),
            memory_type=data.get("memory_type", "short_term"),
            importance=data.get("importance", 0.5),
            metadata=data.get("metadata", {}),
        )
        
        if "created_at" in data:
            entry.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            entry.updated_at = datetime.fromisoformat(data["updated_at"])
        if "access_count" in data:
            entry.access_count = data["access_count"]
        if "last_accessed" in data and data["last_accessed"]:
            entry.last_accessed = datetime.fromisoformat(data["last_accessed"])
        
        return entry
    
    def calculate_relevance(self, query: str) -> float:
        """计算相关性"""
        # 简单的关键词匹配
        query_lower = query.lower()
        content_lower = self.content.lower()
        
        # 计算匹配的关键词数量
        query_words = query_lower.split()
        matches = sum(1 for word in query_words if word in content_lower)
        
        if not query_words:
            return 0.0
        
        # 基础相关性
        base_relevance = matches / len(query_words)
        
        # 考虑重要性
        importance_factor = self.importance
        
        # 考虑访问次数
        access_factor = min(1.0, self.access_count / 10.0)
        
        # 综合相关性
        relevance = base_relevance * 0.6 + importance_factor * 0.3 + access_factor * 0.1
        
        return min(1.0, relevance)
    
    def apply_decay(self, days: int = 1):
        """应用衰减"""
        # 短期记忆衰减更快
        if self.memory_type == "short_term":
            decay_rate = 0.1 * days
        else:
            decay_rate = 0.01 * days
        
        self.importance = max(0.0, self.importance - decay_rate)
        self.updated_at = datetime.now()


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self):
        """初始化记忆管理器"""
        self.memories: Dict[str, MemoryEntry] = {}
        logger.info("记忆管理器初始化完成")
    
    def add(
        self,
        content: str,
        memory_type: str = "short_term",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """添加记忆"""
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {},
        )
        
        self.memories[entry.id] = entry
        logger.debug(f"添加记忆: {entry.id}")
        
        return entry
    
    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """获取记忆"""
        entry = self.memories.get(memory_id)
        
        if entry:
            entry.access_count += 1
            entry.last_accessed = datetime.now()
        
        return entry
    
    def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[MemoryEntry]:
        """更新记忆"""
        entry = self.memories.get(memory_id)
        
        if not entry:
            return None
        
        if content is not None:
            entry.content = content
        if importance is not None:
            entry.importance = importance
        if metadata is not None:
            entry.metadata = metadata
        
        entry.updated_at = datetime.now()
        
        return entry
    
    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self.memories:
            del self.memories[memory_id]
            logger.debug(f"删除记忆: {memory_id}")
            return True
        
        return False
    
    def list(self, memory_type: Optional[str] = None) -> List[MemoryEntry]:
        """列出记忆"""
        if memory_type:
            return [m for m in self.memories.values() if m.memory_type == memory_type]
        
        return list(self.memories.values())
    
    def get_by_type(self, memory_type: str) -> List[MemoryEntry]:
        """按类型获取记忆"""
        return [m for m in self.memories.values() if m.memory_type == memory_type]
    
    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """搜索记忆"""
        results = []
        
        for entry in self.memories.values():
            relevance = entry.calculate_relevance(query)
            if relevance > 0:
                results.append((relevance, entry))
        
        # 按相关性排序
        results.sort(key=lambda x: x[0], reverse=True)
        
        return [entry for _, entry in results[:limit]]
    
    def consolidate(self, threshold: float = 0.7) -> int:
        """整合记忆"""
        consolidated = 0
        
        # 找出高重要性的短期记忆
        short_term = self.get_by_type("short_term")
        
        for entry in short_term:
            if entry.importance >= threshold:
                # 转换为长期记忆
                entry.memory_type = "long_term"
                entry.updated_at = datetime.now()
                consolidated += 1
                logger.debug(f"整合记忆: {entry.id}")
        
        return consolidated
    
    def clear(self, memory_type: Optional[str] = None) -> int:
        """清除记忆"""
        if memory_type:
            to_delete = [id for id, m in self.memories.items() if m.memory_type == memory_type]
        else:
            to_delete = list(self.memories.keys())
        
        for memory_id in to_delete:
            del self.memories[memory_id]
        
        logger.debug(f"清除 {len(to_delete)} 条记忆")
        return len(to_delete)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self.memories)
        
        by_type = {}
        for entry in self.memories.values():
            by_type[entry.memory_type] = by_type.get(entry.memory_type, 0) + 1
        
        avg_importance = 0.0
        if total > 0:
            avg_importance = sum(m.importance for m in self.memories.values()) / total
        
        return {
            "total": total,
            "by_type": by_type,
            "avg_importance": avg_importance,
        }