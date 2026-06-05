"""
测试研究协调器模块
"""
import pytest
import os
import tempfile
from src.orchestrator.research_orchestrator import ResearchOrchestrator


class TestResearchOrchestrator:
    """测试 ResearchOrchestrator 类"""
    
    def test_create_orchestrator(self):
        """测试创建 ResearchOrchestrator 实例"""
        orchestrator = ResearchOrchestrator()
        assert orchestrator is not None
        assert hasattr(orchestrator, 'run_research')
        assert hasattr(orchestrator, 'save_results')
    
    def test_orchestrator_has_idea_generator(self):
        """测试 orchestrator 包含 IdeaGenerator"""
        orchestrator = ResearchOrchestrator()
        assert orchestrator.idea_generator is not None
        # 检查是否有 generate_idea 方法（不是 generate_ideas）
        assert hasattr(orchestrator.idea_generator, 'generate_idea')
    
    def test_orchestrator_has_experiment_runner(self):
        """测试 orchestrator 包含 ExperimentRunner"""
        orchestrator = ResearchOrchestrator()
        assert orchestrator.experiment_runner is not None
        # 检查是否有 run_experiment 方法
        assert hasattr(orchestrator.experiment_runner, 'run_experiment')
    
    def test_orchestrator_has_paper_writer(self):
        """测试 orchestrator 包含 PaperWriter"""
        orchestrator = ResearchOrchestrator()
        assert orchestrator.paper_writer is not None
        # 检查是否有 generate_paper 方法
        assert hasattr(orchestrator.paper_writer, 'generate_paper')
    
    def test_orchestrator_has_paper_formatter(self):
        """测试 orchestrator 包含 PaperFormatter"""
        orchestrator = ResearchOrchestrator()
        assert orchestrator.paper_formatter is not None
        # 检查是否有 to_latex 方法
        assert hasattr(orchestrator.paper_formatter, 'to_latex')
    
    def test_run_research_returns_result(self):
        """测试运行研究返回结果"""
        orchestrator = ResearchOrchestrator()
        result = orchestrator.run_research(
            topic="test topic",
            output_dir="output/test_run"
        )
        
        assert result is not None
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_run_research_success_status(self):
        """测试运行研究成功状态"""
        orchestrator = ResearchOrchestrator()
        result = orchestrator.run_research(
            topic="machine learning baselines",
            output_dir="output/test_run"
        )
        
        assert result["status"] == "success"
    
    def test_run_research_contains_paper_info(self):
        """测试运行研究结果包含论文信息"""
        orchestrator = ResearchOrchestrator()
        result = orchestrator.run_research(
            topic="test topic",
            output_dir="output/test_run"
        )
        
        # 结果应该包含论文相关信息
        assert "paper" in result or "paper_path" in result or "latex_source" in result
    
    def test_run_research_with_different_topics(self):
        """测试不同主题的研究"""
        orchestrator = ResearchOrchestrator()
        
        topics = [
            "neuro-symbolic AI for robotics",
            "federated learning privacy",
            "transformer efficiency"
        ]
        
        for topic in topics:
            result = orchestrator.run_research(
                topic=topic,
                output_dir=f"output/test_{topic.replace(' ', '_')}"
            )
            assert result is not None
            assert result["status"] == "success"
    
    def test_save_results(self):
        """测试保存研究结果"""
        orchestrator = ResearchOrchestrator()
        
        # 先运行研究
        result = orchestrator.run_research(
            topic="test topic",
            output_dir="output/test_save"
        )
        
        # 使用临时目录保存结果
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "results.json")
            orchestrator.save_results(result, save_path)
            
            # 检查文件是否保存
            assert os.path.isfile(save_path)
            
            # 检查内容
            import json
            with open(save_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            
            assert saved_data["status"] == "success"
    
    def test_save_results_creates_directory(self):
        """测试保存结果时创建目录"""
        orchestrator = ResearchOrchestrator()
        
        # 先运行研究
        result = orchestrator.run_research(
            topic="test topic",
            output_dir="output/test_save_nested"
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = os.path.join(tmpdir, "nested", "dir", "results.json")
            orchestrator.save_results(result, nested_path)
            
            assert os.path.isfile(nested_path)
    
    def test_run_research_output_directory_created(self):
        """测试运行研究创建输出目录"""
        orchestrator = ResearchOrchestrator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "research_output")
            
            result = orchestrator.run_research(
                topic="test topic",
                output_dir=output_dir
            )
            
            # 检查输出目录是否创建
            assert os.path.isdir(output_dir)
    
    def test_run_research_generates_latex(self):
        """测试运行研究生成 LaTeX"""
        orchestrator = ResearchOrchestrator()
        result = orchestrator.run_research(
            topic="test topic",
            output_dir="output/test_latex"
        )
        
        # 结果应该包含 LaTeX 源码或论文对象
        if "paper" in result:
            paper = result["paper"]
            assert paper is not None
            assert hasattr(paper, 'latex_source') or hasattr(paper, 'title')


class TestResearchOrchestratorIntegration:
    """测试 ResearchOrchestrator 集成"""
    
    def test_full_research_cycle(self):
        """测试完整的研究循环"""
        orchestrator = ResearchOrchestrator()
        result = orchestrator.run_research(
            topic="neuro-symbolic AI for robotics",
            output_dir="output/test_full_cycle"
        )
        
        assert result is not None
        assert result["status"] == "success"
        assert "paper" in result or "latex_source" in result
    
    def test_research_cycle_components_interaction(self):
        """测试研究循环中组件的交互"""
        orchestrator = ResearchOrchestrator()
        
        # 验证所有组件都已正确初始化
        assert orchestrator.idea_generator is not None
        assert orchestrator.experiment_runner is not None
        assert orchestrator.paper_writer is not None
        assert orchestrator.paper_formatter is not None
        
        # 运行完整流程
        result = orchestrator.run_research(
            topic="machine learning",
            output_dir="output/test_components"
        )
        
        assert result["status"] == "success"
