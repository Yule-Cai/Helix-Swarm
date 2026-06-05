"""
Paper Writer Module

基于实验结果自动生成学术论文。
支持 LLM 驱动的智能论文生成。
"""

import os
import json
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional
from loguru import logger

from src.experiment_execution.experiment_runner import RunResult


@dataclass
class Paper:
    """学术论文数据结构"""
    title: str
    authors: List[str]
    abstract: str
    sections: Dict[str, str]
    references: List[str]
    latex_source: Optional[str] = None
    
    def __str__(self) -> str:
        """返回论文的字符串表示"""
        return f"Paper(title='{self.title}', authors={len(self.authors)})"


class PaperWriter:
    """论文写作器，基于实验结果生成学术论文"""
    
    def __init__(self, authors: Optional[List[str]] = None, llm_service=None):
        """
        初始化论文写作器

        Args:
            authors: 作者列表，默认为 ["Autonomous AI Researcher"]
            llm_service: LLM 服务实例（可选）
        """
        self.authors = authors or ["Autonomous AI Researcher"]
        self.llm_service = llm_service
        self._template_path = "templates/paper_latex_template.tex"
        self._logger = logger.bind(module="PaperWriter")
    
    async def generate_paper_async(self, run_result: RunResult, research_idea=None) -> Paper:
        """
        基于实验结果生成论文（异步版本，支持 LLM）

        Args:
            run_result: 实验运行结果
            research_idea: 研究想法（可选）

        Returns:
            生成的论文对象
        """
        if not run_result.success:
            raise ValueError("Cannot generate paper from failed experiment")

        if self.llm_service:
            try:
                return await self._generate_paper_with_llm(run_result, research_idea)
            except Exception as e:
                self._logger.warning(f"LLM paper generation failed, using template: {e}")
                return self.generate_paper(run_result)
        else:
            return self.generate_paper(run_result)

    def generate_paper(self, run_result: RunResult) -> Paper:
        """
        基于实验结果生成论文（模板版本）

        Args:
            run_result: 实验运行结果

        Returns:
            生成的论文对象

        Raises:
            ValueError: 如果实验失败
        """
        if not run_result.success:
            raise ValueError("Cannot generate paper from failed experiment")

        title = self._generate_title(run_result)
        abstract = self._generate_abstract(run_result)
        sections = self._generate_sections(run_result)
        references = self._generate_references()

        return Paper(
            title=title,
            authors=self.authors,
            abstract=abstract,
            sections=sections,
            references=references,
            latex_source=None
        )

    async def _generate_paper_with_llm(self, run_result: RunResult, research_idea=None) -> Paper:
        """使用 LLM 生成论文"""
        # 准备实验结果摘要
        summary = run_result.results.get("summary", {})
        baselines = run_result.results.get("baselines", {})

        results_text = f"Best accuracy: {summary.get('best_accuracy', 0.0):.2%}\n"
        results_text += f"Best baseline: {summary.get('best_baseline', 'Unknown')}\n"
        results_text += f"Number of baselines: {summary.get('num_baselines', 0)}\n\n"

        for name, baseline in baselines.items():
            metrics = baseline.get('metrics', {})
            results_text += f"{name}: {json.dumps(metrics)}\n"

        idea_text = ""
        if research_idea:
            idea_text = f"""
Research Idea:
- Title: {research_idea.title}
- Abstract: {research_idea.abstract}
- Hypothesis: {research_idea.hypothesis}
- Methodology: {research_idea.methodology}
"""

        prompt = f"""Write an academic paper based on the following experiment results:

{idea_text}
Experiment Results:
{results_text}

Please generate a complete academic paper in JSON format:
{{
    "title": "Paper title",
    "abstract": "Paper abstract (200-300 words)",
    "sections": {{
        "introduction": "Introduction section (300-400 words)",
        "related_work": "Related work section (200-300 words)",
        "methodology": "Methodology section (300-400 words)",
        "results": "Results section (200-300 words)",
        "discussion": "Discussion section (200-300 words)",
        "conclusion": "Conclusion section (150-200 words)"
    }},
    "references": ["Reference 1", "Reference 2", ...]
}}

Write in academic English. Be precise and professional.
Respond ONLY with the JSON object."""

        system_prompt = "You are an expert academic paper writer. Write clear, well-structured research papers."

        response = await self.llm_service.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=4000,
        )

        # 解析响应
        json_str = response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]

        paper_data = json.loads(json_str.strip())

        return Paper(
            title=paper_data.get("title", "Untitled Paper"),
            authors=self.authors,
            abstract=paper_data.get("abstract", ""),
            sections=paper_data.get("sections", {}),
            references=paper_data.get("references", []),
            latex_source=None,
        )
    
    def render_to_latex(self, paper: Paper) -> str:
        """
        将 Paper 对象渲染为 LaTeX 源码
        
        Args:
            paper: 论文对象
            
        Returns:
            渲染后的 LaTeX 源码字符串
            
        Raises:
            FileNotFoundError: 如果模板文件不存在
        """
        # 读取模板
        if not os.path.isfile(self._template_path):
            raise FileNotFoundError(f"Template file not found: {self._template_path}")
        
        with open(self._template_path, "r", encoding="utf-8") as f:
            template = f.read()
        
        # 替换标题
        latex = template.replace("{{title}}", paper.title)
        
        # 替换作者（LaTeX 格式，用 \and 分隔）
        authors_latex = " \\and ".join(paper.authors)
        latex = latex.replace("{{authors}}", authors_latex)
        
        # 替换摘要
        latex = latex.replace("{{abstract}}", paper.abstract)
        
        # 替换章节（转换为 LaTeX \\section 格式）
        sections_latex = self._format_sections_for_latex(paper.sections)
        latex = latex.replace("{{sections}}", sections_latex)
        
        # 替换参考文献
        references_latex = self._format_references_for_latex(paper.references)
        latex = latex.replace("{{references}}", references_latex)
        
        return latex
    
    def _format_sections_for_latex(self, sections: Dict[str, str]) -> str:
        """
        将章节字典格式化为 LaTeX \\section 格式
        
        Args:
            sections: 章节字典
            
        Returns:
            格式化后的 LaTeX 字符串
        """
        latex_sections = []
        
        # 定义章节顺序
        section_order = ["introduction", "methodology", "results", "conclusion"]
        
        for section_key in section_order:
            if section_key in sections:
                content = sections[section_key]
                # 将 Markdown 标题转换为 LaTeX 章节
                # 移除 "## Section Name" 这样的标题行，使用 key 作为章节名
                section_name = section_key.capitalize()
                content_without_header = self._remove_markdown_header(content)
                latex_sections.append(f"\\section{{{section_name}}}\n{content_without_header}")
        
        return "\n\n".join(latex_sections)
    
    def _remove_markdown_header(self, content: str) -> str:
        """
        移除 Markdown 格式的标题
        
        Args:
            content: 包含 Markdown 标题的内容
            
        Returns:
            移除标题后的内容
        """
        lines = content.split("\n")
        # 如果第一行是 Markdown 标题（以 # 开头），则跳过
        if lines and lines[0].strip().startswith("#"):
            return "\n".join(lines[1:]).strip()
        return content
    
    def _format_references_for_latex(self, references: List[str]) -> str:
        """
        将参考文献列表格式化为 LaTeX bibliography 格式
        
        Args:
            references: 参考文献列表
            
        Returns:
            格式化后的 LaTeX 字符串
        """
        if not references:
            return ""
        
        bib_items = []
        for ref in references:
            bib_items.append(f"\\bibitem{{{self._make_bibkey(ref)}}}\n{ref}")
        
        return "\\begin{thebibliography}{" + str(len(references)) + "}\n" + "\n".join(bib_items) + "\n\\end{thebibliography}"
    
    def _make_bibkey(self, ref: str) -> str:
        """
        从参考文献生成 bibkey
        
        Args:
            ref: 参考文献字符串
            
        Returns:
            bibkey 字符串
        """
        # 简单处理：取前三个单词，用下划线连接
        words = ref.split()[:3]
        return "_".join(word.strip(".,") for word in words if word).lower()
    
    def _generate_title(self, run_result: RunResult) -> str:
        """
        生成论文标题
        
        Args:
            run_result: 实验运行结果
            
        Returns:
            论文标题
        """
        summary = run_result.results.get("summary", {})
        best_accuracy = summary.get("best_accuracy", 0.0)
        best_baseline = summary.get("best_baseline", "Unknown")
        num_baselines = summary.get("num_baselines", 0)
        
        return (
            f"A Comparative Study of Machine Learning Baselines: "
            f"Achieving {best_accuracy:.2%} Accuracy with {best_baseline} "
            f"and {num_baselines} Baseline(s)"
        )
    
    def _generate_abstract(self, run_result: RunResult) -> str:
        """
        生成论文摘要
        
        Args:
            run_result: 实验运行结果
            
        Returns:
            论文摘要
        """
        summary = run_result.results.get("summary", {})
        best_accuracy = summary.get("best_accuracy", 0.0)
        best_baseline = summary.get("best_baseline", "Unknown")
        num_baselines = summary.get("num_baselines", 0)
        duration_hours = run_result.duration / 3600.0
        
        return (
            f"This paper presents a comprehensive comparative study of {num_baselines} "
            f"machine learning baseline(s). Our experiments show that {best_baseline} "
            f"achieves the best performance with an accuracy of {best_accuracy:.2%}. "
            f"The total experimental duration was {duration_hours:.2f} hours. "
            f"These results provide valuable insights for practitioners and researchers "
            f"in the field of machine learning."
        )
    
    def _generate_sections(self, run_result: RunResult) -> Dict[str, str]:
        """
        生成论文章节
        
        Args:
            run_result: 实验运行结果
            
        Returns:
            章节字典，key为章节名，value为内容
        """
        baselines = run_result.results.get("baselines", {})
        summary = run_result.results.get("summary", {})
        
        sections = {}
        
        # Introduction
        sections["introduction"] = (
            "## Introduction\n\n"
            "In recent years, machine learning has seen rapid advancements. "
            "This paper provides a systematic comparison of various baseline methods "
            "to establish benchmarks for future research."
        )
        
        # Methodology
        methodology_content = "## Methodology\n\n"
        methodology_content += "We evaluated the following baseline(s):\n"
        for name, baseline in baselines.items():
            metrics = baseline.get('metrics', {})
            methodology_content += f"- {name}: Achieved metrics {metrics}\n"
        sections["methodology"] = methodology_content
        
        # Results
        results_content = "## Results\n\n"
        results_content += f"Best performing baseline: {summary.get('best_baseline', 'Unknown')}\n"
        results_content += f"Best accuracy: {summary.get('best_accuracy', 0.0):.2%}\n"
        results_content += f"Number of baselines tested: {summary.get('num_baselines', 0)}\n"
        sections["results"] = results_content
        
        # Conclusion
        sections["conclusion"] = (
            "## Conclusion\n\n"
            "This study provides a comprehensive comparison of machine learning baselines. "
            "The results demonstrate the importance of systematic evaluation in machine learning "
            "research. Future work will explore more advanced methods and larger datasets."
        )
        
        return sections
    
    def _generate_references(self) -> List[str]:
        """
        生成参考文献列表
        
        Returns:
            参考文献列表
        """
        return [
            "Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press.",
            "Hastie, T., Tibshirani, R., & Friedman, J. (2009). The Elements of Statistical Learning. Springer.",
            "Murphy, K. P. (2012). Machine Learning: A Probabilistic Perspective. MIT Press.",
            "Bishop, C. M. (2006). Pattern Recognition and Machine Learning. Springer.",
        ]
