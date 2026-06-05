"""
测试实验设计器模块
"""
import pytest
from src.idea_generation.experiment_designer import ExperimentDesigner, ExperimentPlan
from src.idea_generation.idea_generator import ResearchIdea


class TestExperimentDesigner:
    """测试 ExperimentDesigner 类"""
    
    def test_create_experiment_designer(self):
        """测试创建 ExperimentDesigner 实例"""
        designer = ExperimentDesigner()
        assert designer is not None
        assert hasattr(designer, 'design_experiment')
        assert hasattr(designer, 'suggest_baselines')
        assert hasattr(designer, 'define_metrics')
    
    def test_design_experiment_from_idea(self):
        """测试基于研究想法设计实验"""
        designer = ExperimentDesigner()
        idea = ResearchIdea(
            title="Neuro-Symbolic Integration for Robust AI Systems",
            abstract="Combining neural networks with symbolic reasoning.",
            hypothesis="Integration improves robustness.",
            methodology="Hybrid architecture development.",
            novelty_score=0.8,
            feasibility_score=0.9
        )
        plan = designer.design_experiment(idea)
        
        assert plan is not None
        assert isinstance(plan, ExperimentPlan)
        assert len(plan.baselines) > 0
        assert len(plan.metrics) > 0
    
    def test_experiment_plan_structure(self):
        """测试实验计划结构"""
        designer = ExperimentDesigner()
        idea = ResearchIdea(
            title="Test Idea",
            abstract="Test abstract",
            hypothesis="Test hypothesis",
            methodology="Test method"
        )
        plan = designer.design_experiment(idea)
        
        assert plan.estimated_duration > 0
        assert plan.dataset_requirements != ""
        assert plan.experiment_type != ""
    
    def test_suggest_baselines_for_idea(self):
        """测试为想法建议基线方法"""
        designer = ExperimentDesigner()
        idea = ResearchIdea(
            title="Few-Shot Learning with Meta-Learning",
            abstract="Enhancing few-shot learning.",
            hypothesis="Meta-learning helps.",
            methodology="Meta-learning framework."
        )
        
        baselines = designer.suggest_baselines(idea)
        assert isinstance(baselines, list)
        assert len(baselines) > 0
        assert all(isinstance(b, str) for b in baselines)
    
    def test_define_metrics_for_idea(self):
        """测试为想法定义评估指标"""
        designer = ExperimentDesigner()
        idea = ResearchIdea(
            title="Explainable AI through Attention",
            abstract="Visualizing attention patterns.",
            hypothesis="Attention visualization helps.",
            methodology="Develop visualization tools."
        )
        
        metrics = designer.define_metrics(idea)
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert all(isinstance(m, str) for m in metrics)
    
    def test_design_experiment_with_empty_idea(self):
        """测试设计实验时处理空字段"""
        designer = ExperimentDesigner()
        idea = ResearchIdea(
            title="",
            abstract="",
            hypothesis="",
            methodology=""
        )
        
        plan = designer.design_experiment(idea)
        assert plan is not None
        assert isinstance(plan, ExperimentPlan)
    
    def test_experiment_plan_has_all_required_fields(self):
        """测试实验计划包含所有必需字段"""
        designer = ExperimentDesigner()
        idea = ResearchIdea(
            title="Test",
            abstract="Test",
            hypothesis="Test",
            methodology="Test"
        )
        
        plan = designer.design_experiment(idea)
        
        # 检查所有必需字段
        assert hasattr(plan, 'baselines')
        assert hasattr(plan, 'metrics')
        assert hasattr(plan, 'dataset_requirements')
        assert hasattr(plan, 'estimated_duration')
        assert hasattr(plan, 'experiment_type')
        assert hasattr(plan, 'description')


class TestExperimentPlan:
    """测试 ExperimentPlan dataclass"""
    
    def test_create_experiment_plan(self):
        """测试创建 ExperimentPlan 实例"""
        plan = ExperimentPlan(
            baselines=["Baseline1", "Baseline2"],
            metrics=["Accuracy", "F1-Score"],
            dataset_requirements="Standard dataset",
            estimated_duration=48,
            experiment_type="classification",
            description="Test experiment"
        )
        
        assert len(plan.baselines) == 2
        assert len(plan.metrics) == 2
        assert plan.estimated_duration == 48
        assert plan.experiment_type == "classification"
    
    def test_experiment_plan_default_values(self):
        """测试默认值和类型"""
        plan = ExperimentPlan(
            baselines=[],
            metrics=[],
            dataset_requirements="",
            estimated_duration=0,
            experiment_type="",
            description=""
        )
        
        assert isinstance(plan.baselines, list)
        assert isinstance(plan.metrics, list)
        assert isinstance(plan.estimated_duration, int)
        assert isinstance(plan.experiment_type, str)
    
    def test_experiment_plan_string_representation(self):
        """测试字符串表示"""
        plan = ExperimentPlan(
            baselines=["B1"],
            metrics=["M1"],
            dataset_requirements="Dataset",
            estimated_duration=24,
            experiment_type="test",
            description="Test plan"
        )
        
        assert "ExperimentPlan" in str(plan)
        assert "test" in str(plan).lower()
