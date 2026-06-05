"""
Paper Formatter Module

格式化论文输出为多种格式（PDF, DOCX, LaTeX）。
"""

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from src.paper_writing.paper_writer import Paper, PaperWriter


class PaperFormatter:
    """论文格式化器，支持多种输出格式"""
    
    def __init__(self):
        """初始化论文格式化器"""
        self._paper_writer = PaperWriter()
    
    def to_latex(self, paper: Paper) -> str:
        """
        将 Paper 对象格式化为 LaTeX 源码
        
        Args:
            paper: 论文对象
            
        Returns:
            渲染后的 LaTeX 源码字符串
            
        Raises:
            FileNotFoundError: 如果模板文件不存在
        """
        return self._paper_writer.render_to_latex(paper)
    
    def to_pdf(self, paper: Paper, output_path: str) -> Optional[str]:
        """
        将 Paper 对象格式化为 PDF
        
        尝试使用 pdflatex 或 pandoc 进行转换。
        如果工具不可用，返回 None。
        
        Args:
            paper: 论文对象
            output_path: 输出文件路径（不含扩展名）
            
        Returns:
            生成的 PDF 文件路径，如果失败则返回 None
            
        Raises:
            RuntimeError: 如果转换过程出错
        """
        # 首先生成 LaTeX 源码
        try:
            latex_content = self.to_latex(paper)
        except Exception as e:
            raise RuntimeError(f"Failed to generate LaTeX: {e}")
        
        pdf_path = output_path + ".pdf"
        
        # 创建临时目录存放 LaTeX 文件
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "paper.tex")
            
            # 保存 LaTeX 文件
            self.save_file(latex_content, tex_path)
            
            # 尝试使用 pdflatex
            if self._is_pdflatex_available():
                if self._run_pdflatex(tex_path, tmpdir):
                    tmp_pdf_path = os.path.join(tmpdir, "paper.pdf")
                    if os.path.isfile(tmp_pdf_path):
                        # 将 PDF 复制到目标路径
                        shutil.copy2(tmp_pdf_path, pdf_path)
                        return pdf_path
            
            # 尝试使用 pandoc
            if self._is_pandoc_available():
                if self._run_pandoc(tex_path, pdf_path, "pdf"):
                    return pdf_path
        
        # 所有方法都失败
        return None
    
    def to_docx(self, paper: Paper, output_path: str) -> Optional[str]:
        """
        将 Paper 对象格式化为 DOCX
        
        使用 pandoc 进行转换。
        如果 pandoc 不可用，返回 None。
        
        Args:
            paper: 论文对象
            output_path: 输出文件路径（不含扩展名）
            
        Returns:
            生成的 DOCX 文件路径，如果失败则返回 None
            
        Raises:
            RuntimeError: 如果转换过程出错
        """
        # 首先生成 LaTeX 源码
        try:
            latex_content = self.to_latex(paper)
        except Exception as e:
            raise RuntimeError(f"Failed to generate LaTeX: {e}")
        
        docx_path = output_path + ".docx"
        
        # 创建临时目录存放 LaTeX 文件
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "paper.tex")
            
            # 保存 LaTeX 文件
            self.save_file(latex_content, tex_path)
            
            # 尝试使用 pandoc
            if self._is_pandoc_available():
                if self._run_pandoc(tex_path, docx_path, "docx"):
                    return docx_path
        
        # 所有方法都失败
        return None
    
    def save_file(self, content: str, path: str) -> None:
        """
        保存内容到文件，自动创建目录
        
        Args:
            content: 要保存的内容
            path: 文件路径
            
        Raises:
            IOError: 如果保存失败
        """
        # 创建目录（如果不存在）
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # 保存文件
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _is_pdflatex_available(self) -> bool:
        """
        检查 pdflatex 是否可用
        
        Returns:
            True 如果 pdflatex 可用，否则 False
        """
        try:
            subprocess.run(
                ["pdflatex", "--version"],
                capture_output=True,
                timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _is_pandoc_available(self) -> bool:
        """
        检查 pandoc 是否可用
        
        Returns:
            True 如果 pandoc 可用，否则 False
        """
        try:
            subprocess.run(
                ["pandoc", "--version"],
                capture_output=True,
                timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _run_pdflatex(self, tex_path: str, working_dir: str) -> bool:
        """
        运行 pdflatex 编译 LaTeX 文件
        
        Args:
            tex_path: TeX 文件路径
            working_dir: 工作目录
            
        Returns:
            True 如果编译成功，否则 False
        """
        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_path],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _run_pandoc(self, input_path: str, output_path: str, output_format: str) -> bool:
        """
        运行 pandoc 转换文件格式
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            output_format: 输出格式（pdf, docx 等）
            
        Returns:
            True 如果转换成功，否则 False
        """
        try:
            result = subprocess.run(
                ["pandoc", input_path, "-o", output_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0 and os.path.isfile(output_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
