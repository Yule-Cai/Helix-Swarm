"""
结果收集器模块

负责执行实验脚本并收集结果。
"""
import subprocess
import json
import re
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ExperimentResult:
    """实验结果数据类
    
    Attributes:
        exit_code: 脚本退出码，0表示成功
        stdout: 标准输出
        stderr: 标准错误
        metrics: 解析出的指标字典
        duration: 执行时长（秒）
        output_file: 输出文件路径（可选）
    """
    exit_code: int
    stdout: str
    stderr: str
    metrics: Dict[str, float]
    duration: float
    output_file: Optional[str] = None
    
    def __str__(self) -> str:
        """返回可读的字符串表示"""
        return f"ExperimentResult(exit_code={self.exit_code}, metrics={self.metrics})"


class ResultsCollector:
    """结果收集器类
    
    负责执行实验脚本、解析输出中的指标、保存结果。
    """
    
    def execute_script(self, script_path: str, timeout: int = 300) -> ExperimentResult:
        """
        执行训练脚本并返回结果
        
        Args:
            script_path: 脚本路径
            timeout: 超时时间（秒），默认300秒
            
        Returns:
            ExperimentResult 实例
        """
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            return ExperimentResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                metrics={},
                duration=duration
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return ExperimentResult(
                exit_code=-1,
                stdout="",
                stderr="Script execution timeout",
                metrics={},
                duration=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            return ExperimentResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                metrics={},
                duration=duration
            )
    
    def parse_metrics(self, output: str) -> Dict[str, float]:
        """
        从输出文本中解析数值指标
        
        支持格式：
        - "MetricName: 0.95"
        - "MetricName= 0.95"
        - "MetricName = 0.95"
        
        Args:
            output: 脚本输出文本
            
        Returns:
            解析出的指标字典，键为指标名，值为浮点数
        """
        metrics = {}
        
        # 匹配模式: "MetricName: value" 或 "MetricName= value"
        pattern = r'(\w+(?:\s+\w+)*)\s*[:=]\s*([0-9.]+)'
        matches = re.findall(pattern, output)
        
        for name, value in matches:
            try:
                metrics[name.strip()] = float(value)
            except ValueError:
                # 忽略无法转换为浮点数的值
                pass
        
        return metrics
    
    def save_results(self, result: ExperimentResult, output_path: str) -> None:
        """
        保存结果到 JSON 文件
        
        Args:
            result: 实验结果
            output_path: 输出文件路径
        """
        data = {
            'exit_code': result.exit_code,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'metrics': result.metrics,
            'duration': result.duration,
            'output_file': result.output_file
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
