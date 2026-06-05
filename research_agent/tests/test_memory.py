"""
记忆测试

测试记忆管理功能。
"""

import pytest
from datetime import datetime

from research_agent.core.memory import MemoryManager, MemoryEntry


class TestMemoryManager:
    """记忆管理器测试类"""
    
    @pytest.fixture
    def manager(self):
        """创建测试记忆管理器"""
        return MemoryManager()
    
    def test_add_memory(self, manager):
        """测试添加记忆"""
        entry = manager.add(
            content="测试记忆内容",
            memory_type="short_term",
            metadata={"key": "value"},
        )
        
        assert entry is not None
        assert entry.content == "测试记忆内容"
        assert entry.memory_type == "short_term"
        assert entry.metadata == {"key": "value"}
    
    def test_get_memory(self, manager):
        """测试获取记忆"""
        # 添加记忆
        entry = manager.add(
            content="测试记忆内容",
            memory_type="short_term",
        )
        
        # 获取记忆
        retrieved = manager.get(entry.id)
        
        assert retrieved is not None
        assert retrieved.id == entry.id
        assert retrieved.content == entry.content
    
    def test_search_memory(self, manager):
        """测试搜索记忆"""
        # 添加多条记忆
        manager.add(content="机器学习是人工智能的一个分支", memory_type="long_term")
        manager.add(content="深度学习是机器学习的子集", memory_type="long_term")
        manager.add(content="自然语言处理是AI的应用", memory_type="long_term")
        
        # 搜索
        results = manager.search("机器学习")
        
        assert len(results) >= 2
    
    def test_update_memory(self, manager):
        """测试更新记忆"""
        # 添加记忆
        entry = manager.add(
            content="原始内容",
            memory_type="short_term",
        )
        
        # 更新记忆
        manager.update(entry.id, content="更新后的内容")
        
        # 验证更新
        updated = manager.get(entry.id)
        assert updated.content == "更新后的内容"
        assert updated.updated_at > entry.created_at
    
    def test_delete_memory(self, manager):
        """测试删除记忆"""
        # 添加记忆
        entry = manager.add(
            content="要删除的记忆",
            memory_type="short_term",
        )
        
        # 删除记忆
        manager.delete(entry.id)
        
        # 验证删除
        deleted = manager.get(entry.id)
        assert deleted is None
    
    def test_list_memories(self, manager):
        """测试列出记忆"""
        # 添加多条记忆
        for i in range(5):
            manager.add(content=f"记忆 {i+1}", memory_type="short_term")
        
        # 列出记忆
        memories = manager.list()
        
        assert len(memories) == 5
    
    def test_get_by_type(self, manager):
        """测试按类型获取记忆"""
        # 添加不同类型的记忆
        manager.add(content="短期记忆1", memory_type="short_term")
        manager.add(content="短期记忆2", memory_type="short_term")
        manager.add(content="长期记忆1", memory_type="long_term")
        
        # 按类型获取
        short_term = manager.get_by_type("short_term")
        long_term = manager.get_by_type("long_term")
        
        assert len(short_term) == 2
        assert len(long_term) == 1
    
    def test_consolidate_memories(self, manager):
        """测试整合记忆"""
        # 添加短期记忆
        for i in range(10):
            manager.add(
                content=f"短期记忆 {i+1}",
                memory_type="short_term",
                importance=0.8 if i < 5 else 0.3,
            )
        
        # 整合记忆
        consolidated = manager.consolidate()
        
        # 验证整合结果
        assert consolidated > 0
    
    def test_clear_memories(self, manager):
        """测试清除记忆"""
        # 添加记忆
        manager.add(content="记忆1", memory_type="short_term")
        manager.add(content="记忆2", memory_type="long_term")
        
        # 清除短期记忆
        manager.clear(memory_type="short_term")
        
        # 验证清除
        short_term = manager.get_by_type("short_term")
        long_term = manager.get_by_type("long_term")
        
        assert len(short_term) == 0
        assert len(long_term) == 1
    
    def test_get_statistics(self, manager):
        """测试获取统计信息"""
        # 添加不同类型的记忆
        for i in range(10):
            memory_type = "short_term" if i < 5 else "long_term"
            manager.add(content=f"记忆 {i+1}", memory_type=memory_type)
        
        # 获取统计
        stats = manager.get_statistics()
        
        assert stats["total"] == 10
        assert stats["by_type"]["short_term"] == 5
        assert stats["by_type"]["long_term"] == 5


class TestMemoryEntry:
    """记忆条目测试类"""
    
    def test_memory_entry_creation(self):
        """测试记忆条目创建"""
        entry = MemoryEntry(
            content="测试内容",
            memory_type="short_term",
            importance=0.8,
            metadata={"key": "value"},
        )
        
        assert entry.content == "测试内容"
        assert entry.memory_type == "short_term"
        assert entry.importance == 0.8
        assert entry.metadata == {"key": "value"}
        assert entry.created_at is not None
    
    def test_memory_entry_to_dict(self):
        """测试记忆条目转字典"""
        entry = MemoryEntry(
            content="测试内容",
            memory_type="short_term",
        )
        
        data = entry.to_dict()
        
        assert "id" in data
        assert data["content"] == "测试内容"
        assert data["memory_type"] == "short_term"
    
    def test_memory_entry_from_dict(self):
        """测试从字典创建记忆条目"""
        data = {
            "id": "mem_001",
            "content": "测试内容",
            "memory_type": "short_term",
            "importance": 0.8,
            "created_at": datetime.now().isoformat(),
        }
        
        entry = MemoryEntry.from_dict(data)
        
        assert entry.id == "mem_001"
        assert entry.content == "测试内容"
        assert entry.importance == 0.8
    
    def test_memory_entry_relevance(self):
        """测试记忆条目相关性计算"""
        entry = MemoryEntry(
            content="机器学习是人工智能的一个分支",
            memory_type="long_term",
        )
        
        # 计算相关性
        relevance = entry.calculate_relevance("机器学习")
        
        assert relevance > 0
    
    def test_memory_entry_decay(self):
        """测试记忆条目衰减"""
        entry = MemoryEntry(
            content="测试内容",
            memory_type="short_term",
            importance=1.0,
        )
        
        # 模拟时间衰减
        entry.apply_decay(days=7)
        
        assert entry.importance < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])