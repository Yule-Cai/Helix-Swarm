"""
Research Orchestrator Module

主协调器，串联所有模块实现完全自主的 AI/ML 研究。
"""

import json
import os
from typing import Dict, Any

from src.idea_generation.idea_generator import IdeaGenerator
from src.idea_generation.experiment_designer import ExperimentDesigner
from src.experiment_execution.experiment_runner import ExperimentRunner
from src.paper_writing.paper_writer import PaperWriter
from src.paper_writing.paper_formatter import PaperFormatter


class ResearchOrchestrator:
    """研究协调器，串联所有组件实现完全自主研究"""
    
    def __init__(self):
        """初始化研究协调器，创建所有需要的组件"""
        self.idea_generator = IdeaGenerator()
        self.experiment_designer = ExperimentDesigner()
        self.experiment_runner = ExperimentRunner()
        self.paper_writer = PaperWriter()
        self.paper_formatter = PaperFormatter()
    
    def run_research(self, topic: str, output_dir: str) -> Dict[str, Any]:
        """
        运行完整的研究流程
        
        流程：
        1. 文献综述（Mock）
        2. 生成研究想法
        3. 设计实验方案
        4. 运行实验
        5. 撰写论文
        6. 格式化论文
        7. 保存结果到输出目录
        
        Args:
            topic: 研究主题
            output_dir: 输出目录路径
            
        Returns:
            包含研究结果的字典，至少包含 'status' 字段
        """
        result = {
            "status": "failed",
            "topic": topic,
            "output_dir": output_dir
        }
        
        try:
            # Step 1: 文献综述（Mock 实现）
            papers = self._conduct_literature_review(topic)
            
            # Step 2: 生成研究想法
            idea = self.idea_generator.generate_idea(papers)
            result["idea"] = {
                "title": idea.title,
                "abstract": idea.abstract,
                "hypothesis": idea.hypothesis,
                "novelty_score": idea.novelty_score,
                "feasibility_score": idea.feasibility_score
            }
            
            # Step 3: 设计实验方案
            experiment_plan = self.experiment_designer.design_experiment(idea)
            result["experiment_plan"] = {
                "type": experiment_plan.experiment_type,
                "baselines": experiment_plan.baselines,
                "metrics": experiment_plan.metrics,
                "estimated_duration": experiment_plan.estimated_duration
            }
            
            # Step 4: 运行实验
            run_result = self.experiment_runner.run_experiment(experiment_plan)
            
            if not run_result.success:
                result["error"] = run_result.error_message or "Experiment failed"
                return result
            
            result["experiment_result"] = {
                "success": run_result.success,
                "duration": run_result.duration,
                "summary": run_result.results.get("summary", {})
            }
            
            # Step 5: 撰写论文
            paper = self.paper_writer.generate_paper(run_result)
            result["paper"] = paper
            
            # Step 6: 格式化论文为 LaTeX
            latex_source = self.paper_formatter.to_latex(paper)
            paper.latex_source = latex_source
            result["latex_source"] = latex_source
            
            # Step 7: 保存结果到输出目录
            self._save_research_output(result, output_dir)
            
            result["status"] = "success"
            
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"
        
        return result
    
    def save_results(self, result: Dict[str, Any], path: str) -> None:
        """
        保存研究结果到 JSON 文件
        
        Args:
            result: 研究结果字典
            path: 保存路径（.json 文件）
            
        Raises:
            IOError: 如果保存失败
        """
        # 创建目录（如果不存在）
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # 准备可序列化的数据
        serializable_result = self._make_serializable(result)
        
        # 保存为 JSON
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(serializable_result, f, indent=2, ensure_ascii=False)
    
    def _conduct_literature_review(self, topic: str) -> list:
        """
        进行文献综述（Mock 实现）
        
        Args:
            topic: 研究主题
            
        Returns:
            论文列表（Mock 数据）
        """
        # Mock 实现：返回空列表或模拟的论文数据
        # 后续可接入真实的文献搜索 API（如 arXiv, Google Scholar）
        return []
    
    def _save_research_output(self, result: Dict[str, Any], output_dir: str) -> None:
        """
        保存研究输出到目录
        
        Args:
            result: 研究结果
            output_dir: 输出目录
        """
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 保存 LaTeX 源码
        if "latex_source" in result and result["latex_source"]:
            latex_path = os.path.join(output_dir, "paper.tex")
            self.paper_formatter.save_file(result["latex_source"], latex_path)
            result["paper_path"] = latex_path
        
        # 保存研究结果 JSON
        json_path = os.path.join(output_dir, "research_result.json")
        self.save_results(result, json_path)
    
    def _make_serializable(self, obj: Any) -> Any:
        """
        将对象转换为可 JSON 序列化的格式
        
        Args:
            obj: 任意对象
            
        Returns:
            可序列化的对象
        """
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif hasattr(obj, '__dict__'):
            # 对于自定义对象，转换为字典
            return self._make_serializable(obj.__dict__)
        else:
            # 其他类型，转换为字符串
            return str(obj)
