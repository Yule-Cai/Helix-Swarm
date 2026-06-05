"""
文献综述自动化模块

提供完整的文献综述自动化功能：
- 多源文献搜索
- 论文分析与摘要
- 文献综述生成
- 引用网络构建
- 研究趋势分析
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from .literature_scraper import LiteratureScraper, PaperMetadata


@dataclass
class LiteratureReviewConfig:
    """文献综述配置"""
    max_papers: int = 50
    sources: List[str] = field(default_factory=lambda: ["arxiv", "semantic_scholar"])
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    min_citations: int = 0
    language: str = "en"


@dataclass
class PaperAnalysis:
    """论文分析结果"""
    paper_id: str
    title: str
    authors: List[str]
    year: int
    abstract: str
    key_findings: List[str]
    methodology: str
    limitations: List[str]
    relevance_score: float
    citation_count: int
    references: List[str]


@dataclass
class LiteratureReview:
    """文献综述结果"""
    topic: str
    generated_at: datetime
    total_papers: int
    papers_analyzed: List[PaperAnalysis]
    summary: str
    key_themes: List[str]
    research_gaps: List[str]
    future_directions: List[str]
    citation_network: Dict[str, List[str]]
    formatted_review: str


class LiteratureReviewGenerator:
    """
    文献综述生成器

    自动化完成文献综述的全流程：
    1. 搜索相关论文
    2. 分析每篇论文
    3. 识别关键主题
    4. 发现研究空白
    5. 生成综述文本
    """

    def __init__(
        self,
        llm_service=None,
        config: Optional[LiteratureReviewConfig] = None,
    ):
        """
        初始化文献综述生成器

        Args:
            llm_service: LLM 服务实例
            config: 文献综述配置
        """
        self.llm_service = llm_service
        self.config = config or LiteratureReviewConfig()
        self.scraper = LiteratureScraper()
        self._logger = logger.bind(module="LiteratureReviewGenerator")

    async def generate_review(self, topic: str) -> LiteratureReview:
        """
        生成文献综述

        Args:
            topic: 研究主题

        Returns:
            LiteratureReview: 文献综述结果
        """
        self._logger.info(f"Starting literature review for: {topic}")

        # Step 1: 搜索论文
        papers = await self._search_papers(topic)
        self._logger.info(f"Found {len(papers)} papers")

        # Step 2: 分析论文
        analyses = await self._analyze_papers(papers, topic)
        self._logger.info(f"Analyzed {len(analyses)} papers")

        # Step 3: 识别主题和空白
        themes = await self._identify_themes(analyses, topic)
        gaps = await self._identify_gaps(analyses, topic)
        future = await self._suggest_future_directions(analyses, topic)

        # Step 4: 构建引用网络
        citation_network = self._build_citation_network(papers)

        # Step 5: 生成综述文本
        formatted_review = await self._generate_review_text(
            topic, analyses, themes, gaps, future
        )

        # Step 6: 生成摘要
        summary = await self._generate_summary(topic, analyses, themes)

        return LiteratureReview(
            topic=topic,
            generated_at=datetime.now(),
            total_papers=len(papers),
            papers_analyzed=analyses,
            summary=summary,
            key_themes=themes,
            research_gaps=gaps,
            future_directions=future,
            citation_network=citation_network,
            formatted_review=formatted_review,
        )

    async def _search_papers(self, topic: str) -> List[Dict]:
        """搜索论文"""
        papers = self.scraper.search(
            query=topic,
            max_results=self.config.max_papers,
            sources=self.config.sources,
        )

        # 过滤年份
        if self.config.year_from or self.config.year_to:
            papers = [
                p for p in papers
                if self._check_year(p, self.config.year_from, self.config.year_to)
            ]

        # 过滤引用数
        if self.config.min_citations > 0:
            papers = [
                p for p in papers
                if p.get('citation_count', 0) >= self.config.min_citations
            ]

        return papers

    def _check_year(self, paper: Dict, year_from: Optional[int], year_to: Optional[int]) -> bool:
        """检查论文年份"""
        try:
            year = int(paper.get('published', '0')[:4])
            if year_from and year < year_from:
                return False
            if year_to and year > year_to:
                return False
            return True
        except (ValueError, IndexError):
            return True

    async def _analyze_papers(self, papers: List[Dict], topic: str) -> List[PaperAnalysis]:
        """分析论文"""
        analyses = []

        for paper in papers[:self.config.max_papers]:
            try:
                analysis = await self._analyze_single_paper(paper, topic)
                if analysis:
                    analyses.append(analysis)
            except Exception as e:
                self._logger.warning(f"Failed to analyze paper: {e}")

        # 按相关性排序
        analyses.sort(key=lambda x: x.relevance_score, reverse=True)

        return analyses

    async def _analyze_single_paper(self, paper: Dict, topic: str) -> Optional[PaperAnalysis]:
        """分析单篇论文"""
        if not self.llm_service:
            return self._create_mock_analysis(paper, topic)

        prompt = f"""Analyze this research paper in the context of the topic: {topic}

Title: {paper.get('title', 'Unknown')}
Authors: {', '.join(paper.get('authors', []))}
Year: {paper.get('published', 'Unknown')}
Abstract: {paper.get('summary', 'No abstract available')[:500]}

Please provide a JSON analysis:
{{
    "key_findings": ["finding1", "finding2", "finding3"],
    "methodology": "Brief description of the methodology used",
    "limitations": ["limitation1", "limitation2"],
    "relevance_score": 0.0-1.0
}}

Respond ONLY with the JSON object."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are an expert research paper analyst. Provide concise, accurate analysis in JSON format.",
                temperature=0.3,
                max_tokens=500,
            )

            # 解析响应
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            analysis_data = json.loads(json_str.strip())

            # 提取年份
            try:
                year = int(paper.get('published', '0')[:4])
            except (ValueError, IndexError):
                year = 0

            return PaperAnalysis(
                paper_id=paper.get('arxiv_id', paper.get('doi', '')),
                title=paper.get('title', ''),
                authors=paper.get('authors', []),
                year=year,
                abstract=paper.get('summary', ''),
                key_findings=analysis_data.get('key_findings', []),
                methodology=analysis_data.get('methodology', ''),
                limitations=analysis_data.get('limitations', []),
                relevance_score=analysis_data.get('relevance_score', 0.5),
                citation_count=paper.get('citation_count', 0),
                references=[],
            )

        except Exception as e:
            self._logger.warning(f"LLM analysis failed: {e}")
            return self._create_mock_analysis(paper, topic)

    def _create_mock_analysis(self, paper: Dict, topic: str) -> PaperAnalysis:
        """创建模拟分析（当 LLM 不可用时）"""
        try:
            year = int(paper.get('published', '0')[:4])
        except (ValueError, IndexError):
            year = 0

        # 简单的相关性评分
        title_lower = paper.get('title', '').lower()
        topic_lower = topic.lower()
        relevance = 0.5
        for word in topic_lower.split():
            if word in title_lower:
                relevance += 0.1

        return PaperAnalysis(
            paper_id=paper.get('arxiv_id', paper.get('doi', '')),
            title=paper.get('title', ''),
            authors=paper.get('authors', []),
            year=year,
            abstract=paper.get('summary', ''),
            key_findings=["See abstract for details"],
            methodology="Not analyzed",
            limitations=["Not analyzed"],
            relevance_score=min(1.0, relevance),
            citation_count=paper.get('citation_count', 0),
            references=[],
        )

    async def _identify_themes(self, analyses: List[PaperAnalysis], topic: str) -> List[str]:
        """识别关键主题"""
        if not self.llm_service or not analyses:
            return self._extract_themes_from_titles(analyses)

        # 收集所有关键发现
        all_findings = []
        for analysis in analyses[:20]:  # 最多取 20 篇
            all_findings.extend(analysis.key_findings)

        findings_text = "\n".join(f"- {f}" for f in all_findings[:50])

        prompt = f"""Based on the following key findings from research papers about "{topic}", identify the main themes.

Key Findings:
{findings_text}

Please identify 5-7 main themes as a JSON array:
["theme1", "theme2", "theme3", ...]

Respond ONLY with the JSON array."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are an expert at identifying research themes. Provide concise theme names.",
                temperature=0.3,
                max_tokens=300,
            )

            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            themes = json.loads(json_str.strip())
            return themes if isinstance(themes, list) else []

        except Exception as e:
            self._logger.warning(f"Theme identification failed: {e}")
            return self._extract_themes_from_titles(analyses)

    def _extract_themes_from_titles(self, analyses: List[PaperAnalysis]) -> List[str]:
        """从标题提取主题（简单方法）"""
        # 提取常见关键词
        word_count = {}
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}

        for analysis in analyses:
            words = analysis.title.lower().split()
            for word in words:
                word = word.strip('.,!?()[]{}')
                if word and word not in stop_words and len(word) > 3:
                    word_count[word] = word_count.get(word, 0) + 1

        # 按频率排序
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:7]]

    async def _identify_gaps(self, analyses: List[PaperAnalysis], topic: str) -> List[str]:
        """识别研究空白"""
        if not self.llm_service or not analyses:
            return ["Further research needed in this area"]

        # 收集所有限制
        all_limitations = []
        for analysis in analyses[:15]:
            all_limitations.extend(analysis.limitations)

        limitations_text = "\n".join(f"- {l}" for l in all_limitations[:30])

        prompt = f"""Based on the following limitations from research papers about "{topic}", identify research gaps.

Limitations:
{limitations_text}

Please identify 3-5 research gaps as a JSON array:
["gap1", "gap2", "gap3", ...]

Respond ONLY with the JSON array."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are an expert at identifying research gaps. Be specific and actionable.",
                temperature=0.3,
                max_tokens=300,
            )

            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            gaps = json.loads(json_str.strip())
            return gaps if isinstance(gaps, list) else []

        except Exception as e:
            self._logger.warning(f"Gap identification failed: {e}")
            return ["Further research needed in this area"]

    async def _suggest_future_directions(self, analyses: List[PaperAnalysis], topic: str) -> List[str]:
        """建议未来研究方向"""
        if not self.llm_service:
            return ["Explore new methodologies", "Investigate scalability", "Cross-domain applications"]

        themes = await self._identify_themes(analyses, topic)
        gaps = await self._identify_gaps(analyses, topic)

        prompt = f"""Based on the following themes and gaps in "{topic}" research, suggest future research directions.

Themes: {', '.join(themes)}
Gaps: {', '.join(gaps)}

Please suggest 3-5 specific future research directions as a JSON array:
["direction1", "direction2", "direction3", ...]

Respond ONLY with the JSON array."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are an expert at suggesting future research directions. Be specific and innovative.",
                temperature=0.5,
                max_tokens=300,
            )

            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            directions = json.loads(json_str.strip())
            return directions if isinstance(directions, list) else []

        except Exception as e:
            self._logger.warning(f"Future directions suggestion failed: {e}")
            return ["Explore new methodologies", "Investigate scalability"]

    def _build_citation_network(self, papers: List[Dict]) -> Dict[str, List[str]]:
        """构建引用网络"""
        network = {}

        for paper in papers:
            paper_id = paper.get('arxiv_id', paper.get('doi', ''))
            if paper_id:
                network[paper_id] = []  # 简化版本，实际需要解析引用关系

        return network

    async def _generate_review_text(
        self,
        topic: str,
        analyses: List[PaperAnalysis],
        themes: List[str],
        gaps: List[str],
        future: List[str],
    ) -> str:
        """生成综述文本"""
        if not self.llm_service:
            return self._generate_mock_review(topic, analyses, themes, gaps, future)

        # 准备论文摘要
        paper_summaries = []
        for i, analysis in enumerate(analyses[:15], 1):
            summary = f"{i}. {analysis.title} ({analysis.year})\n"
            summary += f"   Key findings: {'; '.join(analysis.key_findings[:3])}\n"
            summary += f"   Methodology: {analysis.methodology}\n"
            paper_summaries.append(summary)

        papers_text = "\n".join(paper_summaries)

        prompt = f"""Write a comprehensive literature review section on "{topic}".

Papers analyzed:
{papers_text}

Key themes: {', '.join(themes)}
Research gaps: {', '.join(gaps)}
Future directions: {', '.join(future)}

Please write a structured literature review with:
1. Introduction (overview of the field)
2. Key Themes (organized by theme)
3. Research Gaps
4. Future Directions
5. Conclusion

Write in academic style, approximately 1000 words."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are an expert academic writer. Write clear, well-structured literature reviews.",
                temperature=0.5,
                max_tokens=2000,
            )
            return response

        except Exception as e:
            self._logger.warning(f"Review text generation failed: {e}")
            return self._generate_mock_review(topic, analyses, themes, gaps, future)

    def _generate_mock_review(
        self,
        topic: str,
        analyses: List[PaperAnalysis],
        themes: List[str],
        gaps: List[str],
        future: List[str],
    ) -> str:
        """生成模拟综述文本"""
        review = f"# Literature Review: {topic}\n\n"
        review += f"## Introduction\n\n"
        review += f"This review examines {len(analyses)} papers on {topic}.\n\n"

        review += f"## Key Themes\n\n"
        for theme in themes:
            review += f"- {theme}\n"
        review += "\n"

        review += f"## Research Gaps\n\n"
        for gap in gaps:
            review += f"- {gap}\n"
        review += "\n"

        review += f"## Future Directions\n\n"
        for direction in future:
            review += f"- {direction}\n"
        review += "\n"

        review += f"## Conclusion\n\n"
        review += f"The field of {topic} shows significant potential for future research.\n"

        return review

    async def _generate_summary(
        self,
        topic: str,
        analyses: List[PaperAnalysis],
        themes: List[str],
    ) -> str:
        """生成摘要"""
        if not self.llm_service:
            return f"This literature review examines {len(analyses)} papers on {topic}, covering themes such as {', '.join(themes[:3])}."

        prompt = f"""Write a brief summary (2-3 sentences) for a literature review on "{topic}".

Number of papers analyzed: {len(analyses)}
Key themes: {', '.join(themes)}

Write in academic style."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="Write concise academic summaries.",
                temperature=0.3,
                max_tokens=200,
            )
            return response

        except Exception as e:
            return f"This literature review examines {len(analyses)} papers on {topic}, covering themes such as {', '.join(themes[:3])}."


# 便捷函数
async def generate_literature_review(
    topic: str,
    llm_service=None,
    max_papers: int = 30,
    sources: Optional[List[str]] = None,
) -> LiteratureReview:
    """
    生成文献综述的便捷函数

    Args:
        topic: 研究主题
        llm_service: LLM 服务实例
        max_papers: 最大论文数
        sources: 数据源列表

    Returns:
        LiteratureReview: 文献综述结果
    """
    config = LiteratureReviewConfig(
        max_papers=max_papers,
        sources=sources or ["arxiv", "semantic_scholar"],
    )

    generator = LiteratureReviewGenerator(llm_service=llm_service, config=config)
    return await generator.generate_review(topic)
