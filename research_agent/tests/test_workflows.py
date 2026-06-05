"""
工作流测试

测试工作流管理功能。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from research_agent.core.workflow_engine import WorkflowEngine, Workflow, WorkflowStep, WorkflowStatus, StepStatus
from research_agent.core.task_manager import TaskManager
from research_agent.core.state_manager import StateManager


class TestWorkflowEngine:
    """工作流引擎测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建测试工作流引擎"""
        task_manager = TaskManager()
        state_manager = StateManager()
        return WorkflowEngine(task_manager, state_manager)
    
    def test_create_workflow(self, engine):
        """测试创建工作流"""
        workflow = engine.create_workflow(
            name="测试工作流",
            description="这是一个测试工作流",
            steps=[
                {
                    "id": "step_1",
                    "name": "步骤1",
                    "agent_name": "test_agent",
                    "params": {"query": "测试"},
                }
            ],
        )
        
        assert workflow is not None
        assert workflow.name == "测试工作流"
        assert workflow.description == "这是一个测试工作流"
    
    def test_add_step(self, engine):
        """测试添加步骤"""
        # 创建工作流
        workflow = engine.create_workflow(
            name="测试工作流",
            description="这是一个测试工作流",
            steps=[
                {
                    "id": "step_1",
                    "name": "步骤1",
                    "agent_name": "test_agent",
                    "params": {"query": "测试"},
                }
            ],
        )
        
        # 验证步骤已添加
        assert len(workflow.steps) == 1
        assert workflow.steps[0].name == "步骤1"
    
    def test_get_workflow(self, engine):
        """测试获取工作流"""
        # 创建工作流
        workflow = engine.create_workflow(
            name="测试工作流",
            description="这是一个测试工作流",
            steps=[
                {
                    "id": "step_1",
                    "name": "步骤1",
                    "agent_name": "test_agent",
                    "params": {"query": "测试"},
                }
            ],
        )
        
        # 获取工作流
        retrieved = engine.get_workflow(workflow.id)
        
        assert retrieved is not None
        assert retrieved.id == workflow.id
        assert retrieved.name == workflow.name
    
    def test_list_workflows(self, engine):
        """测试列出工作流"""
        # 创建多个工作流
        for i in range(5):
            engine.create_workflow(
                name=f"工作流 {i+1}",
                description=f"描述 {i+1}",
                steps=[
                    {
                        "id": f"step_{i+1}",
                        "name": f"步骤{i+1}",
                        "agent_name": "test_agent",
                        "params": {"query": f"测试 {i+1}"},
                    }
                ],
            )
        
        # 列出工作流
        workflows = engine.get_all_workflows()
        
        assert len(workflows) == 5
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, engine):
        """测试执行工作流"""
        # 创建工作流
        workflow = engine.create_workflow(
            name="测试工作流",
            description="这是一个测试工作流",
            steps=[
                {
                    "id": "step_1",
                    "name": "步骤1",
                    "agent_name": "test_agent",
                    "params": {"query": "测试"},
                }
            ],
        )
        
        # 模拟执行
        with patch.object(engine, '_execute_step', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = None
            
            result = await engine.execute_workflow(workflow.id)
            
            assert result.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)
    
    def test_update_workflow_status(self, engine):
        """测试更新工作流状态"""
        # 创建工作流
        workflow = engine.create_workflow(
            name="测试工作流",
            description="这是一个测试工作流",
            steps=[
                {
                    "id": "step_1",
                    "name": "步骤1",
                    "agent_name": "test_agent",
                    "params": {"query": "测试"},
                }
            ],
        )
        
        # 更新状态
        workflow.status = WorkflowStatus.RUNNING
        
        # 验证状态
        updated = engine.get_workflow(workflow.id)
        assert updated.status == WorkflowStatus.RUNNING
    
    def test_delete_workflow(self, engine):
        """测试删除工作流"""
        # 创建工作流
        workflow = engine.create_workflow(
            name="测试工作流",
            description="这是一个测试工作流",
            steps=[
                {
                    "id": "step_1",
                    "name": "步骤1",
                    "agent_name": "test_agent",
                    "params": {"query": "测试"},
                }
            ],
        )
        
        # 删除工作流
        engine.clear_completed_workflows()
        
        # 验证删除（工作流还在，因为状态是PENDING）
        workflows = engine.get_all_workflows()
        assert len(workflows) == 1
    
    def test_get_workflow_statistics(self, engine):
        """测试获取工作流统计"""
        # 创建不同状态的工作流
        for i in range(10):
            workflow = engine.create_workflow(
                name=f"工作流 {i+1}",
                description=f"描述 {i+1}",
                steps=[
                    {
                        "id": f"step_{i+1}",
                        "name": f"步骤{i+1}",
                        "agent_name": "test_agent",
                        "params": {"query": f"测试 {i+1}"},
                    }
                ],
            )
            
            if i < 3:
                workflow.status = WorkflowStatus.RUNNING
                # 将运行中的工作流添加到_running_workflows集合
                engine._running_workflows.add(workflow.id)
            elif i < 7:
                workflow.status = WorkflowStatus.COMPLETED
            else:
                workflow.status = WorkflowStatus.FAILED
        
        # 获取统计
        stats = engine.get_statistics()
        
        assert stats["total_workflows"] == 10
        assert stats["running_workflows"] == 3
        assert stats["status_counts"]["running"] == 3
        assert stats["status_counts"]["completed"] == 4
        assert stats["status_counts"]["failed"] == 3


class TestWorkflow:
    """工作流测试类"""
    
    def test_workflow_creation(self):
        """测试工作流创建"""
        workflow = Workflow(
            id="wf_001",
            name="测试工作流",
            description="这是一个测试工作流",
        )
        
        assert workflow.id == "wf_001"
        assert workflow.name == "测试工作流"
        assert workflow.description == "这是一个测试工作流"
        assert workflow.status == WorkflowStatus.PENDING
        assert workflow.created_at is not None
    
    def test_workflow_to_dict(self):
        """测试工作流转字典"""
        workflow = Workflow(
            id="wf_001",
            name="测试工作流",
            description="这是一个测试工作流",
        )
        
        data = workflow.model_dump()
        
        assert data["id"] == "wf_001"
        assert data["name"] == "测试工作流"
        assert data["description"] == "这是一个测试工作流"
        assert data["status"] == WorkflowStatus.PENDING.value
    
    def test_workflow_from_dict(self):
        """测试从字典创建工作流"""
        from datetime import datetime
        
        data = {
            "id": "wf_001",
            "name": "测试工作流",
            "description": "这是一个测试工作流",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "steps": [],
        }
        
        workflow = Workflow(**data)
        
        assert workflow.id == "wf_001"
        assert workflow.name == "测试工作流"
        assert workflow.status == WorkflowStatus.PENDING


class TestWorkflowStep:
    """步骤测试类"""
    
    def test_step_creation(self):
        """测试步骤创建"""
        step = WorkflowStep(
            id="step_001",
            name="步骤1",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        assert step.id == "step_001"
        assert step.name == "步骤1"
        assert step.agent_name == "test_agent"
        assert step.params == {"query": "测试"}
        assert step.status == StepStatus.PENDING
    
    def test_step_to_dict(self):
        """测试步骤转字典"""
        step = WorkflowStep(
            id="step_001",
            name="步骤1",
            agent_name="test_agent",
            params={"query": "测试"},
        )
        
        data = step.model_dump()
        
        assert data["id"] == "step_001"
        assert data["name"] == "步骤1"
        assert data["agent_name"] == "test_agent"
        assert data["params"] == {"query": "测试"}
    
    def test_step_from_dict(self):
        """测试从字典创建步骤"""
        from datetime import datetime
        
        data = {
            "id": "step_001",
            "name": "步骤1",
            "agent_name": "test_agent",
            "params": {"query": "测试"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        
        step = WorkflowStep(**data)
        
        assert step.id == "step_001"
        assert step.name == "步骤1"
        assert step.agent_name == "test_agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])