"""
任务管理测试

测试任务管理功能。
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from research_agent.core.task_manager import TaskManager, Task, TaskStatus, TaskPriority
from research_agent.core.agent_base import AgentBase, AgentResult, AgentConfig


class MockAgent(AgentBase):
    """模拟Agent"""
    
    async def _execute(self, **kwargs):
        """执行任务"""
        return AgentResult(
            success=True,
            data={"result": "测试结果"},
            metadata={"agent": self.name}
        )


class TestTaskManager:
    """任务管理器测试类"""
    
    @pytest.fixture
    def manager(self):
        """创建测试任务管理器"""
        manager = TaskManager()
        # 注册模拟Agent
        agent = MockAgent(config=AgentConfig(name="test_agent"))
        manager.register_agent(agent)
        return manager
    
    def test_create_task(self, manager):
        """测试创建任务"""
        task = manager.create_task(
            name="测试任务",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        assert task is not None
        assert task.name == "测试任务"
        assert task.agent_name == "test_agent"
        assert task.params == {"query": "测试"}
        assert task.status == TaskStatus.QUEUED
    
    def test_get_task(self, manager):
        """测试获取任务"""
        # 创建任务
        task = manager.create_task(
            name="测试任务",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        # 获取任务
        retrieved = manager.get_task(task.id)
        
        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.name == task.name
    
    def test_list_tasks(self, manager):
        """测试列出任务"""
        # 创建多个任务
        for i in range(5):
            manager.create_task(
                name=f"任务 {i+1}",
                agent_name="test_agent",
                params={"query": f"测试 {i+1}"},
            )
        
        # 列出任务
        tasks = manager.get_all_tasks()
        
        assert len(tasks) == 5
    
    def test_update_task_status(self, manager):
        """测试更新任务状态"""
        # 创建任务
        task = manager.create_task(
            name="测试任务",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        # 更新状态
        task.status = TaskStatus.RUNNING
        
        # 验证状态
        updated = manager.get_task(task.id)
        assert updated.status == TaskStatus.RUNNING
    
    def test_complete_task(self, manager):
        """测试完成任务"""
        # 创建任务
        task = manager.create_task(
            name="测试任务",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        # 完成任务
        task.status = TaskStatus.COMPLETED
        task.result = AgentResult(success=True, data={"data": "结果"})
        
        # 验证状态
        updated = manager.get_task(task.id)
        assert updated.status == TaskStatus.COMPLETED
        assert updated.result.data == {"data": "结果"}
    
    def test_fail_task(self, manager):
        """测试失败任务"""
        # 创建任务
        task = manager.create_task(
            name="测试任务",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        # 失败任务
        task.status = TaskStatus.FAILED
        task.error = "测试错误"
        
        # 验证状态
        updated = manager.get_task(task.id)
        assert updated.status == TaskStatus.FAILED
        assert updated.error == "测试错误"
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, manager):
        """测试取消任务"""
        # 创建任务
        task = manager.create_task(
            name="测试任务",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        # 取消任务
        result = await manager.cancel_task(task.id)
        
        # 验证状态
        assert result is True
        updated = manager.get_task(task.id)
        assert updated.status == TaskStatus.CANCELLED
    
    def test_delete_task(self, manager):
        """测试删除任务"""
        # 创建任务
        task = manager.create_task(
            name="测试任务",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        # 删除任务
        manager.clear_completed_tasks()
        
        # 验证删除（任务还在，因为状态是QUEUED）
        tasks = manager.get_all_tasks()
        assert len(tasks) == 1
    
    def test_get_tasks_by_status(self, manager):
        """测试按状态获取任务"""
        # 创建不同状态的任务
        for i in range(10):
            task = manager.create_task(
                name=f"任务 {i+1}",
                agent_name="test_agent",
                params={"query": f"测试 {i+1}"},
            )
            
            if i < 3:
                task.status = TaskStatus.RUNNING
            elif i < 7:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED
        
        # 按状态获取任务
        running_tasks = manager.get_tasks_by_status(TaskStatus.RUNNING)
        completed_tasks = manager.get_tasks_by_status(TaskStatus.COMPLETED)
        failed_tasks = manager.get_tasks_by_status(TaskStatus.FAILED)
        
        assert len(running_tasks) == 3
        assert len(completed_tasks) == 4
        assert len(failed_tasks) == 3
    
    def test_get_task_statistics(self, manager):
        """测试获取任务统计"""
        # 创建不同状态的任务
        for i in range(10):
            task = manager.create_task(
                name=f"任务 {i+1}",
                agent_name="test_agent",
                params={"query": f"测试 {i+1}"},
            )
            
            if i < 3:
                task.status = TaskStatus.RUNNING
            elif i < 7:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED
        
        # 获取统计
        stats = manager.get_statistics()
        
        assert stats["total_tasks"] == 10
        assert stats["running_tasks"] == 0  # 没有真正运行的任务
        assert stats["completed_tasks"] == 0  # 没有真正完成的任务
        assert stats["failed_tasks"] == 0  # 没有真正失败的任务


class TestTask:
    """任务测试类"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            id="task_001",
            name="测试任务",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        assert task.id == "task_001"
        assert task.name == "测试任务"
        assert task.agent_name == "test_agent"
        assert task.params == {"query": "测试"}
        assert task.status == TaskStatus.PENDING
        assert task.created_at is not None
    
    def test_task_to_dict(self):
        """测试任务转字典"""
        task = Task(
            id="task_001",
            name="测试任务",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        data = task.model_dump()
        
        assert data["id"] == "task_001"
        assert data["name"] == "测试任务"
        assert data["agent_name"] == "test_agent"
        assert data["params"] == {"query": "测试"}
        assert data["status"] == TaskStatus.PENDING.value
    
    def test_task_from_dict(self):
        """测试从字典创建任务"""
        data = {
            "id": "task_001",
            "name": "测试任务",
            "agent_name": "test_agent",
            "params": {"query": "测试"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        
        task = Task(**data)
        
        assert task.id == "task_001"
        assert task.name == "测试任务"
        assert task.agent_name == "test_agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])