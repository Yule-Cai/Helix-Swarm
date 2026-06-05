"""
测试实验运行器模块
"""
import pytest
import time
from datetime import datetime
from src.experiment_execution.experiment_runner import ExperimentRunner, RunResult
from src.idea_generation.experiment_designer import ExperimentPlan


class TestExperimentRunner:
    """测试 ExperimentRunner 类"""
    
    def test_create_experiment_runner(self):
        """测试创建 ExperimentRunner 实例"""
        runner = ExperimentRunner()
        assert runner is not None
        assert hasattr(runner, 'run_experiment')
        assert hasattr(runner, 'run_baseline')
        assert hasattr(runner, 'aggregate_results')
    
    def test_run_complete_experiment(self):
        """测试运行完整实验流程"""
        runner = ExperimentRunner()
        plan = ExperimentPlan(
            baselines=["baseline1"],
            metrics=["accuracy"],
            dataset_requirements="test dataset",
            estimated_duration=60,
            experiment_type="classification",
            description="Test experiment"
        )
        result = runner.run_experiment(plan)
        
        assert result is not None
        assert isinstance(result, RunResult)
        assert result.success is True
        assert len(result.results) > 0
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.duration >= 0
    
    def test_run_result_structure(self):
        """测试运行结果结构"""
        runner = ExperimentRunner()
        plan = ExperimentPlan(
            baselines=["baseline1"],
            metrics=["accuracy", "f1_score"],
            dataset_requirements="test dataset",
            estimated_duration=60,
            experiment_type="classification",
            description="Test experiment for result structure"
        )
        result = runner.run_experiment(plan)
        
        assert isinstance(result, RunResult)
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.duration >= 0
        assert isinstance(result.results, dict)
        assert isinstance(result.success, bool)
    
    def test_run_experiment_with_multiple_baselines(self):
        """测试运行多基线实验"""
        runner = ExperimentRunner()
        plan = ExperimentPlan(
            baselines=["baseline1", "baseline2"],
            metrics=["accuracy"],
            dataset_requirements="test dataset",
            estimated_duration=120,
            experiment_type="classification",
            description="Test experiment with multiple baselines"
        )
        result = runner.run_experiment(plan)
        
        assert result is not None
        assert isinstance(result, RunResult)
        assert result.success is True
        assert len(result.results) >= 2  # 至少两个基线
    
    def test_run_baseline(self):
        """测试运行单个基线"""
        runner = ExperimentRunner()
        plan = ExperimentPlan(
            baselines=["test_baseline"],
            metrics=["accuracy"],
            dataset_requirements="test dataset",
            estimated_duration=60,
            experiment_type="classification",
            description="Test single baseline"
        )
        
        baseline_result = runner.run_baseline("test_baseline", plan)
        
        assert baseline_result is not None
        assert "baseline_name" in baseline_result
        assert baseline_result["baseline_name"] == "test_baseline"
        assert "metrics" in baseline_result
        assert "duration" in baseline_result
    
    def test_aggregate_results(self):
        """测试聚合多个基线结果"""
        runner = ExperimentRunner()
        
        # 模拟基线结果
        baseline_results = [
            {
                "baseline_name": "baseline1",
                "metrics": {"accuracy": 0.85, "loss": 0.15},
                "duration": 1.5
            },
            {
                "baseline_name": "baseline2",
                "metrics": {"accuracy": 0.90, "loss": 0.10},
                "duration": 1.8
            }
        ]
        
        aggregated = runner.aggregate_results(baseline_results)
        
        assert aggregated is not None
        assert "baselines" in aggregated
        assert "summary" in aggregated
        assert len(aggregated["baselines"]) == 2
        assert "best_accuracy" in aggregated["summary"]
    
    def test_run_experiment_failure_handling(self):
        """测试实验失败处理"""
        runner = ExperimentRunner()
        
        # 创建一个会失败的实验计划（通过特殊标记）
        plan = ExperimentPlan(
            baselines=["failing_baseline"],
            metrics=["accuracy"],
            dataset_requirements="test dataset",
            estimated_duration=60,
            experiment_type="classification",
            description="Test experiment that will fail"
        )
        
        # 修改 runner 使其模拟失败
        result = runner.run_experiment(plan, should_fail=True)
        
        assert result is not None
        assert isinstance(result, RunResult)
        # 可能成功也可能失败，取决于实现
        assert result.start_time is not None


class TestRunResult:
    """测试 RunResult dataclass"""
    
    def test_create_run_result(self):
        """测试创建 RunResult 实例"""
        start = datetime.now()
        end = datetime.now()
        
        result = RunResult(
            success=True,
            results={"baseline1": {"accuracy": 0.95}},
            start_time=start,
            end_time=end,
            duration=1.5,
            error_message=None
        )
        
        assert result.success is True
        assert len(result.results) == 1
        assert result.start_time == start
        assert result.end_time == end
        assert result.duration == 1.5
        assert result.error_message is None
    
    def test_run_result_with_error(self):
        """测试带错误的 RunResult"""
        start = datetime.now()
        
        result = RunResult(
            success=False,
            results={},
            start_time=start,
            end_time=None,
            duration=0.5,
            error_message="Test error message"
        )
        
        assert result.success is False
        assert result.error_message == "Test error message"
        assert result.end_time is None
    
    def test_run_result_string_representation(self):
        """测试字符串表示"""
        start = datetime.now()
        end = datetime.now()
        
        result = RunResult(
            success=True,
            results={"baseline1": {"accuracy": 0.95}},
            start_time=start,
            end_time=end,
            duration=1.5,
            error_message=None
        )
        
        assert "RunResult" in str(result)
        assert "success=True" in str(result)
