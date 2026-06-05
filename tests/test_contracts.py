"""
测试数据契约（Data Contracts）
定义研究想法、实验结果、论文草稿的 Pydantic 模型
"""
import pytest
from src.models import ResearchIdea, ExperimentResult, PaperDraft, ResearchGap
from pydantic import ValidationError


class TestResearchIdea:
    """测试 ResearchIdea 模型"""
    
    def test_create_valid_research_idea(self):
        """测试创建有效的研究想法"""
        idea = ResearchIdea(
            title="Attention Mechanism Efficiency in Transformers",
            hypothesis="Reducing attention complexity improves training speed",
            methodology="Compare standard vs. sparse attention on BERT",
            research_domain="Natural Language Processing",
            keywords=["transformer", "attention", "efficiency"]
        )
        
        assert idea.title == "Attention Mechanism Efficiency in Transformers"
        assert idea.hypothesis == "Reducing attention complexity improves training speed"
        assert idea.status == "proposed"  # 默认值
        assert len(idea.keywords) == 3
    
    def test_research_idea_missing_required_field(self):
        """测试缺少必填字段时抛出异常"""
        with pytest.raises(ValidationError):
            ResearchIdea(
                title="Test",  # 缺少 hypothesis, methodology 等必填字段
            )
    
    def test_research_idea_validate_method(self):
        """测试 validate 方法"""
        idea = ResearchIdea(
            title="Test Idea",
            hypothesis="Test hypothesis",
            methodology="Test methodology"
        )
        
        assert idea.validate() == True
    
    def test_research_idea_to_json(self):
        """测试 to_json 方法"""
        idea = ResearchIdea(
            title="Test Idea",
            hypothesis="Test hypothesis",
            methodology="Test methodology"
        )
        
        json_output = idea.to_json()
        assert json_output is not None
        assert '"title": "Test Idea"' in json_output or "'title': 'Test Idea'" in json_output
    
    def test_research_idea_with_id(self):
        """测试自动生成 ID"""
        idea = ResearchIdea(
            title="Test Idea",
            hypothesis="Test hypothesis",
            methodology="Test methodology"
        )
        
        assert idea.id is not None
        assert len(idea.id) > 0


class TestResearchGap:
    """测试 ResearchGap 模型"""
    
    def test_create_research_gap(self):
        """测试创建研究空白"""
        gap = ResearchGap(
            topic="Transformer Efficiency",
            description="Current transformers are computationally expensive",
            keywords=["transformer", "efficiency", "computation"]
        )
        
        assert gap.topic == "Transformer Efficiency"
        assert gap.description == "Current transformers are computationally expensive"
        assert len(gap.keywords) == 3


class TestExperimentResult:
    """测试 ExperimentResult 模型"""
    
    def test_create_valid_experiment_result(self):
        """测试创建有效的实验结果"""
        result = ExperimentResult(
            experiment_id="exp_001",
            idea_id="idea_001",
            status="completed",
            metrics={
                "accuracy": 0.95,
                "loss": 0.05,
                "training_time": 120.5
            },
            artifacts={
                "model_path": "experiments/exp_001/model.pth",
                "log_path": "experiments/exp_001/training.log"
            }
        )
        
        assert result.experiment_id == "exp_001"
        assert result.status == "completed"
        assert result.metrics["accuracy"] == 0.95
        assert result.metrics["training_time"] == 120.5
    
    def test_experiment_result_invalid_status(self):
        """测试无效状态抛出异常"""
        with pytest.raises(ValidationError):
            ExperimentResult(
                experiment_id="exp_001",
                idea_id="idea_001",
                status="invalid_status",  # 应该是 completed, failed, running 之一
                metrics={}
            )
    
    def test_experiment_result_default_values(self):
        """测试默认值"""
        result = ExperimentResult(
            experiment_id="exp_001",
            idea_id="idea_001",
            status="running",
            metrics={}
        )
        
        assert result.artifacts == {}
        assert result.error_message is None


class TestPaperDraft:
    """测试 PaperDraft 模型"""
    
    def test_create_valid_paper_draft(self):
        """测试创建有效的论文草稿"""
        idea = ResearchIdea(
            title="Test Idea",
            hypothesis="Test hypothesis",
            methodology="Test methodology"
        )
        
        result = ExperimentResult(
            experiment_id="exp_001",
            idea_id="idea_001",
            status="completed",
            metrics={"accuracy": 0.95}
        )
        
        paper = PaperDraft(
            title="Attention Efficiency in Transformers",
            abstract="This paper proposes...",
            research_idea=idea,
            experiment_results=[result],
            sections={
                "introduction": "Introduction content...",
                "methods": "Methods content...",
                "results": "Results content...",
                "conclusion": "Conclusion content..."
            }
        )
        
        assert paper.title == "Attention Efficiency in Transformers"
        assert paper.status == "draft"  # 默认值
        assert len(paper.experiment_results) == 1
        assert "introduction" in paper.sections
    
    def test_paper_draft_to_latex(self):
        """测试 to_latex 方法"""
        idea = ResearchIdea(
            title="Test Idea",
            hypothesis="Test hypothesis",
            methodology="Test methodology"
        )
        
        paper = PaperDraft(
            title="Test Paper",
            abstract="Test abstract",
            research_idea=idea,
            experiment_results=[],
            sections={"abstract": "Test"}
        )
        
        latex = paper.to_latex()
        assert latex is not None
        assert "Test Paper" in latex or "documentclass" in latex
    
    def test_paper_draft_validate(self):
        """测试 validate 方法"""
        idea = ResearchIdea(
            title="Test Idea",
            hypothesis="Test hypothesis",
            methodology="Test methodology"
        )
        
        paper = PaperDraft(
            title="Test Paper",
            abstract="Test abstract",
            research_idea=idea,
            experiment_results=[],
            sections={"abstract": "Test"}
        )
        
        assert paper.validate() == True
