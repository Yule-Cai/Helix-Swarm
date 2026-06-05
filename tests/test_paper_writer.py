"""
测试论文写作器模块
"""
import pytest
from datetime import datetime
from src.paper_writing.paper_writer import PaperWriter, Paper
from src.experiment_execution.experiment_runner import RunResult


class TestPaperWriter:
    """测试 PaperWriter 类"""
    
    def test_create_paper_writer(self):
        """测试创建 PaperWriter 实例"""
        writer = PaperWriter()
        assert writer is not None
        assert hasattr(writer, 'generate_paper')
        assert hasattr(writer, '_generate_title')
        assert hasattr(writer, '_generate_abstract')
        assert hasattr(writer, '_generate_sections')
        assert hasattr(writer, '_generate_references')
    
    def test_generate_paper_from_results(self):
        """测试基于实验结果生成论文"""
        writer = PaperWriter()
        
        # 创建模拟的 RunResult
        run_result = RunResult(
            success=True,
            results={
                "baselines": {
                    "baseline1": {
                        "baseline_name": "baseline1",
                        "metrics": {"accuracy": 0.95, "loss": 0.05},
                        "duration": 1.5
                    }
                },
                "summary": {
                    "best_accuracy": 0.95,
                    "best_baseline": "baseline1",
                    "num_baselines": 1
                }
            },
            start_time=datetime(2025, 1, 17, 12, 0, 0),
            end_time=datetime(2025, 1, 17, 13, 0, 0),
            duration=3600.0,
            error_message=None
        )
        
        paper = writer.generate_paper(run_result)
        
        assert paper is not None
        assert isinstance(paper, Paper)
        assert paper.title != ""
        assert paper.abstract != ""
        assert len(paper.sections) > 0
        assert len(paper.authors) > 0
    
    def test_paper_sections(self):
        """测试论文章节结构"""
        writer = PaperWriter()
        
        run_result = RunResult(
            success=True,
            results={
                "baselines": {
                    "baseline1": {
                        "baseline_name": "baseline1",
                        "metrics": {"accuracy": 0.90, "loss": 0.10},
                        "duration": 1.0
                    }
                },
                "summary": {
                    "best_accuracy": 0.90,
                    "best_baseline": "baseline1",
                    "num_baselines": 1
                }
            },
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1800.0,
            error_message=None
        )
        
        paper = writer.generate_paper(run_result)
        
        # 检查必要的章节
        assert "introduction" in paper.sections
        assert "methodology" in paper.sections
        assert "results" in paper.sections
        assert "conclusion" in paper.sections
    
    def test_paper_structure(self):
        """测试论文结构完整性"""
        writer = PaperWriter()
        
        run_result = RunResult(
            success=True,
            results={
                "baselines": {
                    "baseline1": {
                        "baseline_name": "baseline1",
                        "metrics": {"accuracy": 0.88, "f1_score": 0.85},
                        "duration": 2.0
                    }
                },
                "summary": {
                    "best_accuracy": 0.88,
                    "best_baseline": "baseline1",
                    "num_baselines": 1
                }
            },
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1200.0,
            error_message=None
        )
        
        paper = writer.generate_paper(run_result)
        
        # 检查论文基本字段
        assert isinstance(paper.title, str)
        assert isinstance(paper.abstract, str)
        assert isinstance(paper.sections, dict)
        assert isinstance(paper.references, list)
        assert isinstance(paper.authors, list)
        
        # 检查章节内容不为空
        for section_name, section_content in paper.sections.items():
            assert section_content != "", f"Section '{section_name}' is empty"
    
    def test_generate_title(self):
        """测试生成论文标题"""
        writer = PaperWriter()
        
        run_result = RunResult(
            success=True,
            results={
                "summary": {
                    "best_accuracy": 0.92,
                    "best_baseline": "proposed_method"
                }
            },
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1000.0,
            error_message=None
        )
        
        title = writer._generate_title(run_result)
        
        assert isinstance(title, str)
        assert len(title) > 0
        assert "Accuracy" in title or "0.92" in title or "Study" in title
    
    def test_generate_abstract(self):
        """测试生成论文摘要"""
        writer = PaperWriter()
        
        run_result = RunResult(
            success=True,
            results={
                "summary": {
                    "best_accuracy": 0.95,
                    "best_baseline": "proposed_method",
                    "num_baselines": 2
                }
            },
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=2000.0,
            error_message=None
        )
        
        abstract = writer._generate_abstract(run_result)
        
        assert isinstance(abstract, str)
        assert len(abstract) > 50  # 摘要应该有一定长度
        assert "accuracy" in abstract.lower() or "0.95" in abstract
    
    def test_generate_references(self):
        """测试生成参考文献"""
        writer = PaperWriter()
        references = writer._generate_references()
        
        assert isinstance(references, list)
        assert len(references) > 0
        
        # 检查参考文献格式
        for ref in references:
            assert isinstance(ref, str)
            assert len(ref) > 0


class TestPaper:
    """测试 Paper dataclass"""
    
    def test_create_paper(self):
        """测试创建 Paper 实例"""
        paper = Paper(
            title="Test Paper Title",
            authors=["Author 1", "Author 2"],
            abstract="This is a test abstract.",
            sections={
                "introduction": "Intro content",
                "methodology": "Method content"
            },
            references=["Ref 1", "Ref 2"],
            latex_source=None
        )
        
        assert paper.title == "Test Paper Title"
        assert len(paper.authors) == 2
        assert paper.abstract == "This is a test abstract."
        assert len(paper.sections) == 2
        assert len(paper.references) == 2
        assert paper.latex_source is None
    
    def test_paper_with_latex_source(self):
        """测试带 LaTeX 源码的论文"""
        latex = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"
        paper = Paper(
            title="LaTeX Paper",
            authors=["Author"],
            abstract="Abstract",
            sections={"content": "Content"},
            references=[],
            latex_source=latex
        )
        
        assert paper.latex_source == latex
        assert "documentclass" in paper.latex_source
    
    def test_paper_string_representation(self):
        """测试字符串表示"""
        paper = Paper(
            title="Test Paper",
            authors=["Author"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[],
            latex_source=None
        )
        
        assert "Paper" in str(paper)
        assert "Test Paper" in str(paper)
