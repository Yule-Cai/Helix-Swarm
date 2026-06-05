"""
测试研究想法生成器模块
"""
import pytest
from src.idea_generation.idea_generator import IdeaGenerator, ResearchIdea


class TestIdeaGenerator:
    """测试 IdeaGenerator 类"""
    
    def test_create_idea_generator(self):
        """测试创建 IdeaGenerator 实例"""
        generator = IdeaGenerator()
        assert generator is not None
        assert hasattr(generator, 'generate_idea')
        assert hasattr(generator, 'evaluate_novelty')
        assert hasattr(generator, 'evaluate_feasibility')
    
    def test_generate_idea_from_papers(self):
        """测试基于论文生成研究想法"""
        generator = IdeaGenerator()
        papers = [
            {"title": "Neuro-Symbolic AI for Robotics", "abstract": "Combining neural and symbolic approaches..."},
            {"title": "HCI for Non-Expert Users", "abstract": "Improving human-computer interaction..."}
        ]
        idea = generator.generate_idea(papers)
        
        assert idea is not None
        assert isinstance(idea, ResearchIdea)
        assert idea.title != ""
        assert hasattr(idea, 'novelty_score')
        assert idea.novelty_score >= 0
    
    def test_idea_novelty_evaluation(self):
        """测试想法新颖性评估"""
        generator = IdeaGenerator()
        idea = generator.generate_idea([])
        
        assert hasattr(idea, 'novelty_score')
        assert 0 <= idea.novelty_score <= 1
        assert hasattr(idea, 'feasibility_score')
        assert 0 <= idea.feasibility_score <= 1
    
    def test_generate_idea_with_empty_papers(self):
        """测试没有论文时生成想法"""
        generator = IdeaGenerator()
        idea = generator.generate_idea([])
        
        assert idea is not None
        assert isinstance(idea, ResearchIdea)
        assert idea.title != ""
    
    def test_generate_idea_returns_complete_idea(self):
        """测试生成的想法包含完整信息"""
        generator = IdeaGenerator()
        papers = [{"title": "Test Paper", "abstract": "Test abstract"}]
        idea = generator.generate_idea(papers)
        
        assert idea.title != ""
        assert hasattr(idea, 'abstract')
        assert hasattr(idea, 'hypothesis')
        assert hasattr(idea, 'methodology')
        assert hasattr(idea, 'novelty_score')
        assert hasattr(idea, 'feasibility_score')
    
    def test_evaluate_novelty_with_papers(self):
        """测试基于论文评估新颖性"""
        generator = IdeaGenerator()
        idea = generator.generate_idea([])
        papers = [{"title": "Paper 1"}, {"title": "Paper 2"}]
        
        novelty = generator.evaluate_novelty(idea, papers)
        assert 0 <= novelty <= 1
    
    def test_evaluate_feasibility(self):
        """测试评估可行性"""
        generator = IdeaGenerator()
        idea = generator.generate_idea([])
        
        feasibility = generator.evaluate_feasibility(idea)
        assert 0 <= feasibility <= 1


class TestResearchIdea:
    """测试 ResearchIdea dataclass"""
    
    def test_create_research_idea(self):
        """测试创建 ResearchIdea 实例"""
        idea = ResearchIdea(
            title="Test Idea",
            abstract="Test abstract",
            hypothesis="Test hypothesis",
            methodology="Test methodology",
            novelty_score=0.8,
            feasibility_score=0.7
        )
        
        assert idea.title == "Test Idea"
        assert idea.abstract == "Test abstract"
        assert idea.novelty_score == 0.8
        assert idea.feasibility_score == 0.7
    
    def test_research_idea_default_scores(self):
        """测试默认分数"""
        idea = ResearchIdea(
            title="Test",
            abstract="Test",
            hypothesis="Test",
            methodology="Test"
        )
        
        assert idea.novelty_score == 0.0
        assert idea.feasibility_score == 0.0
    
    def test_research_idea_string_representation(self):
        """测试字符串表示"""
        idea = ResearchIdea(
            title="Test Idea",
            abstract="Test abstract",
            hypothesis="Test",
            methodology="Test"
        )
        
        assert "Test Idea" in str(idea)
