"""
测试脚本执行器模块
"""
import pytest
import tempfile
import os
from src.experiment_execution.script_executor import ScriptExecutor


class TestScriptExecutor:
    """测试 ScriptExecutor 类"""
    
    def test_create_script_executor(self):
        """测试创建 ScriptExecutor 实例"""
        executor = ScriptExecutor()
        assert executor is not None
        assert hasattr(executor, 'execute')
        assert hasattr(executor, 'set_timeout')
        assert hasattr(executor, 'set_memory_limit')
    
    def test_execute_simple_script(self):
        """测试执行简单脚本"""
        executor = ScriptExecutor()
        script = "print('Hello, World!')"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            result = executor.execute(script_path)
            assert result['success'] is True
            assert 'Hello, World!' in result['stdout']
        finally:
            os.unlink(script_path)
    
    def test_execute_with_timeout(self):
        """测试脚本超时"""
        executor = ScriptExecutor()
        executor.set_timeout(1)  # 1秒超时
        
        script = "import time; time.sleep(10)"  # 睡眠10秒
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            result = executor.execute(script_path)
            assert result['success'] is False
            assert 'timeout' in result.get('error', '').lower() or 'timeout' in result.get('stderr', '').lower()
        finally:
            os.unlink(script_path)
    
    def test_execute_failing_script(self):
        """测试执行失败脚本"""
        executor = ScriptExecutor()
        script = "raise Exception('Test error')"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            result = executor.execute(script_path)
            assert result['success'] is False
            assert 'Test error' in result.get('stderr', '') or 'Test error' in result.get('error', '')
        finally:
            os.unlink(script_path)
    
    def test_set_timeout(self):
        """测试设置超时"""
        executor = ScriptExecutor()
        executor.set_timeout(30)
        assert executor.timeout == 30
        
        executor.set_timeout(60)
        assert executor.timeout == 60
    
    def test_set_memory_limit(self):
        """测试设置内存限制"""
        executor = ScriptExecutor()
        executor.set_memory_limit(512)  # 512 MB
        assert executor.memory_limit == 512
    
    def test_execute_with_output(self):
        """测试执行并捕获输出"""
        executor = ScriptExecutor()
        script = """
print("Line 1")
print("Line 2")
print("Accuracy: 0.95")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            result = executor.execute(script_path)
            assert result['success'] is True
            assert 'Line 1' in result['stdout']
            assert 'Line 2' in result['stdout']
            assert 'Accuracy: 0.95' in result['stdout']
        finally:
            os.unlink(script_path)
