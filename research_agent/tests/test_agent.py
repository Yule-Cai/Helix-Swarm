"""
Agent基础测试

测试Agent基础功能。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from research_agent.core.agent_base import AgentBase, AgentResult, AgentState, AgentConfig


class ConcreteAgent(AgentBase):
    """具体Agent实现"""
    
    async def _execute(self, **kwargs):
        """执行任务"""
        return AgentResult(
            success=True,
            data={"result": "测试结果"},
            metadata={"agent": self.name}
        )


class TestAgentBase:
    """Agent基础测试类"""
    
    @pytest.fixture
    def agent(self):
        """创建测试Agent"""
        return ConcreteAgent(config=AgentConfig(name="TestAgent"))
    
    def test_agent_initialization(self, agent):
        """测试Agent初始化"""
        assert agent.name == "TestAgent"
        assert agent.state == AgentState.IDLE
        assert agent.start_time is None
        assert agent.end_time is None
        assert agent.execution_time == 0.0
        assert agent._retry_count == 0
        assert len(agent._results) == 0
        assert agent.last_result is None
    
    def test_agent_status(self, agent):
        """测试Agent状态"""
        status = agent.get_status()
        
        assert "name" in status
        assert status["name"] == "TestAgent"
        assert "state" in status
        assert status["state"] == AgentState.IDLE.value
        assert "start_time" in status
        assert "end_time" in status
        assert "execution_time" in status
        assert "retry_count" in status
        assert "results_count" in status
        assert "last_result" in status
    
    @pytest.mark.asyncio
    async def test_agent_task_tracking(self, agent):
        """测试Agent任务跟踪"""
        # 执行任务
        result = await agent.execute(query="测试")
        
        # 验证结果
        assert result.success is True
        assert result.data == {"result": "测试结果"}
        assert len(agent._results) == 1
        assert agent.last_result is not None
    
    def test_agent_reset(self, agent):
        """测试Agent重置"""
        # 执行任务
        asyncio.run(agent.execute(query="测试"))
        
        # 验证状态
        assert len(agent._results) == 1
        
        # 重置
        agent.reset()
        
        # 验证重置
        assert len(agent._results) == 0
        assert agent.last_result is None
        assert agent.state == AgentState.IDLE


class TestAgentResult:
    """Agent结果测试类"""
    
    def test_result_creation(self):
        """测试结果创建"""
        result = AgentResult(
            success=True,
            data={"result": "测试结果"},
            metadata={"agent": "TestAgent"}
        )
        
        assert result.success is True
        assert result.data == {"result": "测试结果"}
        assert result.metadata == {"agent": "TestAgent"}
        assert result.error is None
        assert result.execution_time == 0.0
    
    def test_result_to_dict(self):
        """测试结果转字典"""
        result = AgentResult(
            success=True,
            data={"result": "测试结果"},
            metadata={"agent": "TestAgent"}
        )
        
        data = result.model_dump()
        
        assert data["success"] is True
        assert data["data"] == {"result": "测试结果"}
        assert data["metadata"] == {"agent": "TestAgent"}
        assert data["error"] is None
        assert data["execution_time"] == 0.0
    
    def test_result_from_dict(self):
        """测试从字典创建结果"""
        data = {
            "success": True,
            "data": {"result": "测试结果"},
            "metadata": {"agent": "TestAgent"},
            "error": None,
            "execution_time": 0.0,
        }
        
        result = AgentResult(**data)
        
        assert result.success is True
        assert result.data == {"result": "测试结果"}
        assert result.metadata == {"agent": "TestAgent"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])