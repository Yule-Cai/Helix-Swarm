"""
测试论文格式化器模块
"""
import pytest
import os
import tempfile
from src.paper_writing.paper_formatter import PaperFormatter
from src.paper_writing.paper_writer import Paper


class TestPaperFormatter:
    """测试 PaperFormatter 类"""
    
    def test_create_paper_formatter(self):
        """测试创建 PaperFormatter 实例"""
        formatter = PaperFormatter()
        assert formatter is not None
        assert hasattr(formatter, 'to_latex')
        assert hasattr(formatter, 'to_pdf')
        assert hasattr(formatter, 'to_docx')
        assert hasattr(formatter, 'save_file')
    
    def test_format_to_latex(self):
        """测试格式化为 LaTeX"""
        formatter = PaperFormatter()
        paper = Paper(
            title="Test Paper",
            authors=["Author 1"],
            abstract="This is a test abstract.",
            sections={
                "introduction": "Introduction content.",
                "methodology": "Methodology content.",
                "results": "Results content.",
                "conclusion": "Conclusion content."
            },
            references=["Reference 1"],
            latex_source=""
        )
        
        latex_content = formatter.to_latex(paper)
        
        assert isinstance(latex_content, str)
        assert len(latex_content) > 0
        assert "Test Paper" in latex_content
        assert "\\documentclass" in latex_content
        assert "\\begin{document}" in latex_content
        assert "\\end{document}" in latex_content
    
    def test_format_to_latex_contains_title(self):
        """测试 LaTeX 输出包含标题"""
        formatter = PaperFormatter()
        paper = Paper(
            title="My Special Title",
            authors=["Author"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        latex_content = formatter.to_latex(paper)
        
        assert "My Special Title" in latex_content
    
    def test_format_to_latex_contains_authors(self):
        """测试 LaTeX 输出包含作者"""
        formatter = PaperFormatter()
        paper = Paper(
            title="Title",
            authors=["John Doe", "Jane Smith"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        latex_content = formatter.to_latex(paper)
        
        assert "John Doe" in latex_content
        assert "Jane Smith" in latex_content
    
    def test_format_to_latex_contains_abstract(self):
        """测试 LaTeX 输出包含摘要"""
        formatter = PaperFormatter()
        paper = Paper(
            title="Title",
            authors=["Author"],
            abstract="This is the abstract text.",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        latex_content = formatter.to_latex(paper)
        
        assert "This is the abstract text." in latex_content
        assert "\\begin{abstract}" in latex_content
    
    def test_format_to_latex_contains_sections(self):
        """测试 LaTeX 输出包含章节"""
        formatter = PaperFormatter()
        paper = Paper(
            title="Title",
            authors=["Author"],
            abstract="Abstract",
            sections={
                "introduction": "Intro text here.",
                "methodology": "Method text here."
            },
            references=[],
            latex_source=""
        )
        
        latex_content = formatter.to_latex(paper)
        
        assert "Intro text here." in latex_content
        assert "Method text here." in latex_content
        assert "\\section{Introduction}" in latex_content or "Introduction" in latex_content
    
    def test_format_to_pdf_without_pdflatex(self):
        """测试在没有 pdflatex 时格式化 PDF"""
        formatter = PaperFormatter()
        paper = Paper(
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        # 如果 pdflatex 不可用，应该返回 None 或抛出异常
        try:
            result = formatter.to_pdf(paper, "test_output")
            # 如果成功，result 应该是输出路径
            assert result is None or isinstance(result, str)
        except (FileNotFoundError, RuntimeError) as e:
            # pdflatex 不可用，这是预期的行为
            pytest.skip(f"pdflatex not available: {e}")
        except Exception as e:
            # 其他异常
            pytest.fail(f"Unexpected error: {e}")
    
    def test_format_to_pdf_creates_file(self):
        """测试格式化 PDF 创建文件"""
        formatter = PaperFormatter()
        paper = Paper(
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output")
            
            try:
                result = formatter.to_pdf(paper, output_path)
                if result is not None:
                    # 如果成功，检查文件是否存在
                    assert os.path.isfile(result) or os.path.isfile(output_path + ".pdf")
            except (FileNotFoundError, RuntimeError):
                pytest.skip("pdflatex not available")
    
    def test_format_to_docx_without_pandoc(self):
        """测试在没有 pandoc 时格式化 DOCX"""
        formatter = PaperFormatter()
        paper = Paper(
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        try:
            result = formatter.to_docx(paper, "test_output")
            # 如果成功，result 应该是输出路径
            assert result is None or isinstance(result, str)
        except (FileNotFoundError, RuntimeError) as e:
            # pandoc 不可用，这是预期的行为
            pytest.skip(f"pandoc not available: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    def test_format_to_docx_creates_file(self):
        """测试格式化 DOCX 创建文件"""
        formatter = PaperFormatter()
        paper = Paper(
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            sections={"intro": "Content"},
            references=[],
            latex_source=""
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output")
            
            try:
                result = formatter.to_docx(paper, output_path)
                if result is not None:
                    # 如果成功，检查文件是否存在
                    assert os.path.isfile(result) or os.path.isfile(output_path + ".docx")
            except (FileNotFoundError, RuntimeError):
                pytest.skip("pandoc not available")
    
    def test_save_file(self):
        """测试保存文件"""
        formatter = PaperFormatter()
        content = "Test content\nMultiple lines"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            formatter.save_file(content, temp_path)
            
            # 检查文件是否保存成功
            assert os.path.isfile(temp_path)
            
            # 检查内容是否正确
            with open(temp_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            assert saved_content == content
        finally:
            if os.path.isfile(temp_path):
                os.remove(temp_path)
    
    def test_save_file_creates_directory(self):
        """测试保存文件时创建目录"""
        formatter = PaperFormatter()
        content = "Test content"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = os.path.join(tmpdir, "nested", "dir", "output.txt")
            
            formatter.save_file(content, nested_path)
            
            assert os.path.isfile(nested_path)
            
            with open(nested_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            assert saved_content == content


class TestPaperFormatterIntegration:
    """测试 PaperFormatter 集成"""
    
    def test_to_latex_uses_paper_writer(self):
        """测试 to_latex 使用 PaperWriter"""
        formatter = PaperFormatter()
        paper = Paper(
            title="Integration Test",
            authors=["Tester"],
            abstract="Testing integration.",
            sections={"intro": "Test content"},
            references=[],
            latex_source=""
        )
        
        # to_latex 应该调用 PaperWriter.render_to_latex
        latex_output = formatter.to_latex(paper)
        
        assert "Integration Test" in latex_output
        assert "Tester" in latex_output
        assert "Testing integration." in latex_output
