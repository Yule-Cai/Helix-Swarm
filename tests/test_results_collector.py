"""
测试结果收集器模块
"""
import pytest
import tempfile
import os
import json
from src.experiment_execution.results_collector import ResultsCollector, ExperimentResult


class TestResultsCollector:
    """测试 ResultsCollector 类"""
    
    def test_create_results_collector(self):
        """测试创建 ResultsCollector 实例"""
        collector = ResultsCollector()
        assert collector is not None
        assert hasattr(collector, 'execute_script')
        assert hasattr(collector, 'parse_metrics')
        assert hasattr(collector, 'save_results')
    
    def test_execute_script_success(self):
        """测试成功执行训练脚本"""
        collector = ResultsCollector()
        
        # 创建临时脚本
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('Accuracy: 0.95')\nprint('Loss: 0.05')\n")
            script_path = f.name
        
        try:
            result = collector.execute_script(script_path)
            
            assert result is not None
            assert isinstance(result, ExperimentResult)
            assert result.exit_code == 0
            assert "Accuracy: 0.95" in result.stdout
            assert result.duration >= 0
        finally:
            os.unlink(script_path)
    
    def test_execute_script_failure(self):
        """测试执行失败脚本"""
        collector = ResultsCollector()
        
        # 创建会失败的临时脚本
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("raise Exception('Test error')\n")
            script_path = f.name
        
        try:
            result = collector.execute_script(script_path)
            
            assert result is not None
            assert isinstance(result, ExperimentResult)
            assert result.exit_code != 0
            assert "Test error" in result.stderr or "Exception" in result.stderr
        finally:
            os.unlink(script_path)
    
    def test_parse_metrics_simple(self):
        """测试解析简单指标"""
        collector = ResultsCollector()
        output = "Accuracy: 0.95\nF1 Score: 0.88\nLoss: 0.05"
        metrics = collector.parse_metrics(output)
        
        assert "Accuracy" in metrics
        assert metrics["Accuracy"] == 0.95
        assert "F1 Score" in metrics
        assert metrics["F1 Score"] == 0.88
        assert "Loss" in metrics
        assert metrics["Loss"] == 0.05
    
    def test_parse_metrics_multiple_formats(self):
        """测试解析多种格式的指标"""
        collector = ResultsCollector()
        output = """
        Test Accuracy: 0.92
        Train Loss: 0.15
        Validation F1: 0.88
        mAP: 0.75
        """
        metrics = collector.parse_metrics(output)
        
        assert len(metrics) >= 3
        assert any("Accuracy" in key for key in metrics.keys())
        assert all(isinstance(v, float) for v in metrics.values())
    
    def test_parse_metrics_no_metrics(self):
        """测试解析无指标的输"""
        collector = ResultsCollector()
        output = "This is just a log message\nNo metrics here"
        metrics = collector.parse_metrics(output)
        
        assert isinstance(metrics, dict)
        assert len(metrics) == 0
    
    def test_save_results(self):
        """测试保存结果到 JSON"""
        collector = ResultsCollector()
        
        result = ExperimentResult(
            exit_code=0,
            stdout="Accuracy: 0.95",
            stderr="",
            metrics={"Accuracy": 0.95, "Loss": 0.05},
            duration=1.5,
            output_file=None
        )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            collector.save_results(result, output_path)
            
            # 验证文件已保存
            assert os.path.exists(output_path)
            
            # 验证内容
            with open(output_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data["exit_code"] == 0
            assert saved_data["metrics"]["Accuracy"] == 0.95
            assert saved_data["duration"] == 1.5
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_execute_and_collect(self):
        """测试执行并收集完整结果"""
        collector = ResultsCollector()
        
        # 创建包含指标输出的脚本
        script_content = """
import time
time.sleep(0.1)
print("Training started...")
print("Epoch 1: Accuracy=0.85, Loss=0.25")
print("Epoch 2: Accuracy=0.90, Loss=0.15")
print("Final Accuracy: 0.90")
print("Final Loss: 0.15")
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            result = collector.execute_script(script_path)
            
            assert result.exit_code == 0
            assert result.duration > 0
            
            # 解析指标
            metrics = collector.parse_metrics(result.stdout)
            assert len(metrics) >= 2
        finally:
            os.unlink(script_path)


class TestExperimentResult:
    """测试 ExperimentResult dataclass"""
    
    def test_create_experiment_result(self):
        """测试创建 ExperimentResult 实例"""
        result = ExperimentResult(
            exit_code=0,
            stdout="test output",
            stderr="",
            metrics={"Accuracy": 0.95},
            duration=1.0,
            output_file="results.json"
        )
        
        assert result.exit_code == 0
        assert result.stdout == "test output"
        assert result.metrics["Accuracy"] == 0.95
        assert result.duration == 1.0
        assert result.output_file == "results.json"
    
    def test_experiment_result_default_values(self):
        """测试默认值"""
        result = ExperimentResult(
            exit_code=-1,
            stdout="",
            stderr="",
            metrics={},
            duration=0.0,
            output_file=None
        )
        
        assert result.exit_code == -1
        assert isinstance(result.metrics, dict)
        assert result.output_file is None
    
    def test_experiment_result_string_representation(self):
        """测试字符串表示"""
        result = ExperimentResult(
            exit_code=0,
            stdout="test",
            stderr="",
            metrics={"Accuracy": 0.95},
            duration=1.0,
            output_file=None
        )
        
        assert "ExperimentResult" in str(result)
        assert "exit_code=0" in str(result)
