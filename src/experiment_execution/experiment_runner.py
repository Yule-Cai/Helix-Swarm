"""
实验运行器模块

整合所有组件，端到端运行实验。
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import time

from src.idea_generation.experiment_designer import ExperimentPlan
from src.code_generation.code_generator import CodeGenerator
from src.experiment_execution.results_collector import ResultsCollector


@dataclass
class RunResult:
    """实验结果数据类
    
    Attributes:
        success: 实验是否成功
        results: 所有基线的结果字典
        start_time: 实验开始时间
        end_time: 实验结束时间（如果失败可能为None）
        duration: 实验总时长（秒）
        error_message: 错误信息（如果失败）
    """
    success: bool
    results: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime]
    duration: float
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        """返回可读的字符串表示"""
        return f"RunResult(success={self.success}, duration={self.duration:.2f}s)"


class ExperimentRunner:
    """实验运行器类
    
    整合代码生成、执行、结果收集，端到端运行实验。
    """
    
    def __init__(self):
        """初始化实验运行器"""
        self.code_generator = CodeGenerator()
        self.results_collector = ResultsCollector()
    
    def run_experiment(self, plan: ExperimentPlan, should_fail: bool = False) -> RunResult:
        """
        运行完整实验流程
        
        Args:
            plan: 实验计划
            should_fail: 是否模拟失败（用于测试）
            
        Returns:
            RunResult 实例
        """
        start_time = datetime.now()
        
        try:
            if should_fail:
                raise Exception("Simulated failure for testing")
            
            # 运行所有基线
            baseline_results = [
                self.run_baseline(baseline, plan)
                for baseline in plan.baselines
            ]
            
            # 聚合结果
            aggregated = self.aggregate_results(baseline_results)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return RunResult(
                success=True,
                results=aggregated,
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return RunResult(
                success=False,
                results={},
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_message=str(e)
            )
    
    def run_baseline(self, baseline_name: str, plan: ExperimentPlan) -> Dict[str, Any]:
        """
        运行单个基线实验
        
        Args:
            baseline_name: 基线名称
            plan: 实验计划
            
        Returns:
            基线结果字典，包含指标和时长
        """
        start_time = time.time()
        
        # 生成训练脚本
        script_content = self.code_generator.generate_training_script(
            baseline_name,
            plan.dataset_requirements
        )
        
        # TODO: 在实际实现中，这里应该：
        # 1. 保存脚本到临时文件
        # 2. 使用 ResultsCollector 执行脚本
        # 3. 解析结果中的指标
        
        duration = time.time() - start_time
        
        # 模拟返回结果
        return {
            "baseline_name": baseline_name,
            "metrics": {
                "accuracy": 0.85 + abs(hash(baseline_name)) % 10 / 100,
                "loss": 0.15 - abs(hash(baseline_name)) % 10 / 100
            },
            "duration": duration,
            "script_generated": True
        }
    
    def aggregate_results(self, baseline_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        聚合多个基线的结果
        
        Args:
            baseline_results: 基线结果列表
            
        Returns:
            聚合结果字典，包含各基线详细信息和汇总统计
        """
        aggregated = {
            "baselines": {},
            "summary": {}
        }
        
        best_accuracy = 0.0
        best_baseline = None
        
        for result in baseline_results:
            baseline_name = result["baseline_name"]
            aggregated["baselines"][baseline_name] = result
            
            # 追踪最佳准确率
            accuracy = result.get("metrics", {}).get("accuracy", 0)
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_baseline = baseline_name
        
        aggregated["summary"] = {
            "best_accuracy": best_accuracy,
            "best_baseline": best_baseline,
            "num_baselines": len(baseline_results)
        }
        
        return aggregated
