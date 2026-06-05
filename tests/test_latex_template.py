"""
测试 LaTeX 模板模块
"""
import pytest
import os
from src.paper_writing.paper_writer import PaperWriter, Paper


class TestLaTeXTemplate:
    """测试 LaTeX 模板"""
    
    def test_latex_template_exists(self):
        """测试 LaTeX 模板文件存在"""
        template_path = "templates/paper_latex_template.tex"
        assert os.path.isfile(template_path), f"Template file not found: {template_path}"
    
    def test_latex_template_has_required_structure(self):
        """测试 LaTeX 模板包含必要的文档结构"""
        with open("templates/paper_latex_template.tex", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查文档类
        assert "\\documentclass" in content, "Missing \\documentclass"
        
        # 检查文档环境
        assert "\\begin{document}" in content, "Missing \\begin{document}"
        assert "\\end{document}" in content, "Missing \\end{document}"
    
    def test_latex_template_has_required_sections(self):
        """测试 LaTeX 模板包含必要的章节"""
        with open("templates/paper_latex_template.tex", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查必要的章节（使用模板变量）
        assert "{{title}}" in content, "Missing title placeholder"
        assert "{{authors}}" in content, "Missing authors placeholder"
        assert "{{abstract}}" in content, "Missing abstract placeholder"
        assert "{{sections}}" in content, "Missing sections placeholder"
        assert "{{references}}" in content, "Missing references placeholder"
    
    def test_latex_template_has_standard_sections(self):
        """测试 LaTeX 模板包含标准章节结构"""
        with open("templates/paper_latex_template.tex", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查标准章节（可以是注释或模板变量形式）
        assert "Introduction" in content, "Missing Introduction section"
        assert "Methodology" in content, "Missing Methodology section"
        assert "Results" in content, "Missing Results section"
        assert "Conclusion" in content, "Missing Conclusion section"
    
    def test_render_paper_to_latex(self):
        """测试将 Paper 对象渲染为 LaTeX"""
        writer = PaperWriter()
        
        paper = Paper(
            title="Test Paper on Machine Learning",
            authors=["Author 1", "Author 2"],
            abstract="This is a test abstract for the paper.",
            sections={
                "introduction": "Introduction content here.",
                "methodology": "Methodology content here.",
                "results": "Results content here.",
                "conclusion": "Conclusion content here."
            },
            references=["Reference 1", "Reference 2"],
            latex_source=""
        )
        
        latex_output = writer.render_to_latex(paper)
        
        # 检查渲染结果
        assert isinstance(latex_output, str), "render_to_latex should return string"
        assert len(latex_output) > 0, "LaTeX output should not be empty"
        assert "\\documentclass" in latex_output, "Missing \\documentclass in output"
        assert "\\begin{document}" in latex_output, "Missing \\begin{document} in output"
        assert "\\end{document}" in latex_output, "Missing \\end{document} in output"
    
    def test_render_latex_contains_title(self):
        """测试渲染的 LaTeX 包含标题"""
        writer = PaperWriter()
        
        paper = Paper(
            title="My Test Paper Title",
            authors=["Author"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        latex_output = writer.render_to_latex(paper)
        
        assert "My Test Paper Title" in latex_output, "Title not found in LaTeX output"
        assert "\\title" in latex_output, "Missing \\title command"
    
    def test_render_latex_contains_authors(self):
        """测试渲染的 LaTeX 包含作者"""
        writer = PaperWriter()
        
        paper = Paper(
            title="Title",
            authors=["John Doe", "Jane Smith"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        latex_output = writer.render_to_latex(paper)
        
        assert "John Doe" in latex_output, "Author 1 not found in LaTeX output"
        assert "Jane Smith" in latex_output, "Author 2 not found in LaTeX output"
        assert "\\author" in latex_output, "Missing \\author command"
    
    def test_render_latex_contains_abstract(self):
        """测试渲染的 LaTeX 包含摘要"""
        writer = PaperWriter()
        
        paper = Paper(
            title="Title",
            authors=["Author"],
            abstract="This is the abstract of the paper.",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        latex_output = writer.render_to_latex(paper)
        
        assert "This is the abstract of the paper." in latex_output, "Abstract not found in LaTeX output"
        assert "\\begin{abstract}" in latex_output, "Missing abstract environment"
    
    def test_render_latex_contains_sections(self):
        """测试渲染的 LaTeX 包含章节内容"""
        writer = PaperWriter()
        
        paper = Paper(
            title="Title",
            authors=["Author"],
            abstract="Abstract",
            sections={
                "introduction": "This is the introduction.",
                "methodology": "This is the methodology.",
                "results": "These are the results.",
                "conclusion": "This is the conclusion."
            },
            references=[],
            latex_source=""
        )
        
        latex_output = writer.render_to_latex(paper)
        
        assert "This is the introduction." in latex_output, "Introduction not found"
        assert "This is the methodology." in latex_output, "Methodology not found"
        assert "These are the results." in latex_output, "Results not found"
        assert "This is the conclusion." in latex_output, "Conclusion not found"
    
    def test_render_latex_contains_references(self):
        """测试渲染的 LaTeX 包含参考文献"""
        writer = PaperWriter()
        
        paper = Paper(
            title="Title",
            authors=["Author"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[
                "Author1, Title1, Journal1, 2024",
                "Author2, Title2, Journal2, 2025"
            ],
            latex_source=""
        )
        
        latex_output = writer.render_to_latex(paper)
        
        assert "Author1, Title1, Journal1, 2024" in latex_output, "Reference 1 not found"
        assert "Author2, Title2, Journal2, 2025" in latex_output, "Reference 2 not found"
    
    def test_render_latex_valid_structure(self):
        """测试渲染的 LaTeX 具有有效的文档结构"""
        writer = PaperWriter()
        
        paper = Paper(
            title="Title",
            authors=["Author"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        latex_output = writer.render_to_latex(paper)
        
        # 检查文档结构顺序
        doc_class_pos = latex_output.find("\\documentclass")
        begin_doc_pos = latex_output.find("\\begin{document}")
        end_doc_pos = latex_output.find("\\end{document}")
        
        assert doc_class_pos < begin_doc_pos, "\\documentclass should come before \\begin{document}"
        assert begin_doc_pos < end_doc_pos, "\\begin{document} should come before \\end{document}"


class TestPaperWriterRenderIntegration:
    """测试 PaperWriter 渲染集成"""
    
    def test_generate_and_render_paper(self):
        """测试生成论文并渲染为 LaTeX"""
        from src.experiment_execution.experiment_runner import RunResult
        from datetime import datetime
        
        writer = PaperWriter()
        
        # 生成论文
        run_result = RunResult(
            success=True,
            results={
                "baselines": {
                    "baseline1": {
                        "baseline_name": "baseline1",
                        "metrics": {"accuracy": 0.95},
                        "duration": 1.0
                    }
                },
                "summary": {
                    "best_accuracy": 0.95,
                    "best_baseline": "baseline1",
                    "num_baselines": 1
                }
            },
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1000.0,
            error_message=None
        )
        
        paper = writer.generate_paper(run_result)
        
        # 渲染为 LaTeX
        latex_output = writer.render_to_latex(paper)
        
        assert isinstance(latex_output, str)
        assert len(latex_output) > 100  # 应该有相当长度的内容
        assert paper.title in latex_output
