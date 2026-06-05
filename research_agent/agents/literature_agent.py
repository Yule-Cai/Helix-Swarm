"""
文献检索Agent

负责文献检索、筛选、分析和管理。
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from loguru import logger

from ..core.agent_base import AgentBase, AgentResult
from ..services.llm_service import LLMService
from ..services.search_service import SearchService
from ..services.vector_store import VectorStore


class Paper(BaseModel):
    """论文模型"""
    id: str = Field(..., description="论文ID")
    title: str = Field(..., description="论文标题")
    authors: List[str] = Field(default_factory=list, description="作者列表")
    abstract: str = Field("", description="摘要")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    year: Optional[int] = Field(None, description="发表年份")
    journal: str = Field("", description="期刊/会议")
    doi: str = Field("", description="DOI")
    url: str = Field("", description="URL")
    citations: int = Field(0, description="引用次数")
    relevance_score: float = Field(0.0, description="相关性评分")
    quality_score: float = Field(0.0, description="质量评分")
    summary: str = Field("", description="AI生成的摘要")
    key_findings: List[str] = Field(default_factory=list, description="关键发现")
    methodology: str = Field("", description="研究方法")
    limitations: List[str] = Field(default_factory=list, description="局限性")
    future_work: List[str] = Field(default_factory=list, description="未来工作")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LiteratureSearchResult(BaseModel):
    """文献检索结果"""
    query: str = Field(..., description="检索查询")
    total_results: int = Field(0, description="总结果数")
    papers: List[Paper] = Field(default_factory=list, description="论文列表")
    search_time: float = Field(0.0, description="检索时间(秒)")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="应用的过滤器")
    summary: str = Field("", description="检索结果摘要")


class LiteratureAgent(AgentBase):
    """
    文献检索Agent
    
    负责文献检索、筛选、分析和管理。
    
    Features:
        - 多源文献检索（Google Scholar, PubMed, arXiv等）
        - 智能筛选和排序
        - 论文质量评估
        - 论文内容分析
        - 文献综述生成
        - 引用网络分析
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        search_service: SearchService,
        vector_store: VectorStore,
        name: str = "LiteratureAgent",
    ):
        """
        初始化文献检索Agent
        
        Args:
            llm_service: LLM服务
            search_service: 搜索服务
            vector_store: 向量存储
            name: Agent名称
        """
        super().__init__(name=name)
        self.llm_service = llm_service
        self.search_service = search_service
        self.vector_store = vector_store
        self._logger = logger.bind(module="LiteratureAgent")
        
        # 检索历史
        self._search_history: List[LiteratureSearchResult] = []
        
        # 收藏的论文
        self._favorite_papers: Dict[str, Paper] = {}
    
    async def execute(self, **kwargs) -> AgentResult:
        """
        执行文献检索任务
        
        Args:
            **kwargs: 任务参数
                - action: 操作类型 (search, analyze, summarize, review, cite)
                - query: 检索查询
                - filters: 过滤条件
                - paper_id: 论文ID
                - papers: 论文列表
                
        Returns:
            AgentResult: 执行结果
        """
        action = kwargs.get("action", "search")
        
        try:
            if action == "search":
                result = await self.search_literature(
                    query=kwargs["query"],
                    filters=kwargs.get("filters", {}),
                    max_results=kwargs.get("max_results", 20),
                )
            elif action == "analyze":
                result = await self.analyze_paper(kwargs["paper_id"])
            elif action == "summarize":
                result = await self.summarize_papers(kwargs["papers"])
            elif action == "review":
                result = await self.generate_literature_review(
                    topic=kwargs["topic"],
                    papers=kwargs.get("papers", []),
                )
            elif action == "cite":
                result = await self.generate_citations(
                    papers=kwargs["papers"],
                    style=kwargs.get("style", "APA"),
                )
            elif action == "favorite":
                result = await self.add_to_favorites(kwargs["paper_id"])
            elif action == "get_favorites":
                result = await self.get_favorites()
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    agent_name=self.name,
                )
            
            return AgentResult(
                success=True,
                data=result,
                agent_name=self.name,
            )
            
        except Exception as e:
            self._logger.exception(f"Error in LiteratureAgent: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                agent_name=self.name,
            )
    
    async def search_literature(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        max_results: int = 20,
    ) -> LiteratureSearchResult:
        """
        检索文献
        
        Args:
            query: 检索查询
            filters: 过滤条件
            max_results: 最大结果数
            
        Returns:
            LiteratureSearchResult: 检索结果
        """
        start_time = datetime.now()
        filters = filters or {}
        
        self._logger.info(f"Searching literature: {query}")
        
        # 执行搜索
        search_results = await self.search_service.search(
            query=query,
            max_results=max_results,
            filters=filters,
        )
        
        # 转换为论文对象
        papers = []
        for result in search_results:
            paper = Paper(
                id=result.get("id", ""),
                title=result.get("title", ""),
                authors=result.get("authors", []),
                abstract=result.get("abstract", ""),
                keywords=result.get("keywords", []),
                year=result.get("year"),
                journal=result.get("journal", ""),
                doi=result.get("doi", ""),
                url=result.get("url", ""),
                citations=result.get("citations", 0),
            )
            papers.append(paper)
        
        # 评估论文相关性和质量
        papers = await self._evaluate_papers(query, papers)
        
        # 按相关性排序
        papers.sort(key=lambda p: p.relevance_score, reverse=True)
        
        # 生成摘要
        summary = await self._generate_search_summary(query, papers)
        
        # 计算搜索时间
        search_time = (datetime.now() - start_time).total_seconds()
        
        # 创建检索结果
        result = LiteratureSearchResult(
            query=query,
            total_results=len(papers),
            papers=papers[:max_results],
            search_time=search_time,
            filters_applied=filters,
            summary=summary,
        )
        
        # 保存到历史
        self._search_history.append(result)
        
        # 保存到向量存储
        await self._save_to_vector_store(papers)
        
        self._logger.info(f"Found {len(papers)} papers in {search_time:.2f}s")
        
        return result
    
    async def _evaluate_papers(self, query: str, papers: List[Paper]) -> List[Paper]:
        """
        评估论文相关性和质量
        
        Args:
            query: 检索查询
            papers: 论文列表
            
        Returns:
            List[Paper]: 评估后的论文列表
        """
        for paper in papers:
            # 评估相关性
            relevance_prompt = f"""
            评估以下论文与查询的相关性（0-1分）：
            
            查询：{query}
            
            论文标题：{paper.title}
            论文摘要：{paper.abstract}
            关键词：{', '.join(paper.keywords)}
            
            请只返回一个0-1之间的数字，表示相关性评分。
            """
            
            try:
                relevance_response = await self.llm_service.generate(relevance_prompt)
                paper.relevance_score = float(relevance_response.strip())
            except:
                paper.relevance_score = 0.5
            
            # 评估质量
            quality_prompt = f"""
            评估以下论文的质量（0-1分），考虑以下因素：
            - 期刊/会议声誉
            - 引用次数
            - 研究方法
            - 创新性
            
            论文信息：
            标题：{paper.title}
            期刊：{paper.journal}
            引用次数：{paper.citations}
            年份：{paper.year}
            
            请只返回一个0-1之间的数字，表示质量评分。
            """
            
            try:
                quality_response = await self.llm_service.generate(quality_prompt)
                paper.quality_score = float(quality_response.strip())
            except:
                paper.quality_score = 0.5
        
        return papers
    
    async def _generate_search_summary(self, query: str, papers: List[Paper]) -> str:
        """
        生成检索结果摘要
        
        Args:
            query: 检索查询
            papers: 论文列表
            
        Returns:
            str: 摘要
        """
        if not papers:
            return f'未找到与"{query}"相关的文献。'
        
        # 准备论文信息
        paper_info = []
        for i, paper in enumerate(papers[:10], 1):
            paper_info.append(f"{i}. {paper.title} ({paper.year}) - {paper.journal}")
        
        prompt = f"""
        为以下文献检索结果生成一个简洁的摘要：
        
        检索查询：{query}
        找到论文数量：{len(papers)}
        
        主要论文：
        {chr(10).join(paper_info)}
        
        请生成一个200字左右的摘要，概括检索结果的主要内容和趋势。
        """
        
        summary = await self.llm_service.generate(prompt)
        return summary
    
    async def _save_to_vector_store(self, papers: List[Paper]) -> None:
        """
        保存论文到向量存储
        
        Args:
            papers: 论文列表
        """
        for paper in papers:
            # 准备文档内容
            content = f"""
            标题：{paper.title}
            作者：{', '.join(paper.authors)}
            摘要：{paper.abstract}
            关键词：{', '.join(paper.keywords)}
            """
            
            # 准备元数据
            metadata = {
                "paper_id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "journal": paper.journal,
                "doi": paper.doi,
                "citations": paper.citations,
                "relevance_score": paper.relevance_score,
                "quality_score": paper.quality_score,
            }
            
            # 保存到向量存储
            await self.vector_store.add_document(
                content=content,
                metadata=metadata,
                doc_id=f"paper_{paper.id}",
            )
    
    async def analyze_paper(self, paper_id: str) -> Dict[str, Any]:
        """
        分析论文
        
        Args:
            paper_id: 论文ID
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        self._logger.info(f"Analyzing paper: {paper_id}")
        
        # 从向量存储获取论文
        paper_doc = await self.vector_store.get_document(f"paper_{paper_id}")
        if not paper_doc:
            raise ValueError(f"Paper {paper_id} not found")
        
        # 提取论文信息
        content = paper_doc.get("content", "")
        metadata = paper_doc.get("metadata", {})
        
        # 使用LLM分析论文
        analysis_prompt = f"""
        请对以下论文进行详细分析：
        
        {content}
        
        请提供以下分析：
        1. 研究目的和问题
        2. 研究方法
        3. 主要发现和贡献
        4. 局限性和不足
        5. 未来研究方向
        6. 与其他研究的关系
        7. 实际应用价值
        
        请用结构化的方式输出分析结果。
        """
        
        analysis = await self.llm_service.generate(analysis_prompt)
        
        # 提取关键信息
        key_findings_prompt = f"""
        从以下论文分析中提取关键发现（最多5条）：
        
        {analysis}
        
        请以列表形式输出，每条发现一行。
        """
        
        key_findings_response = await self.llm_service.generate(key_findings_prompt)
        key_findings = [line.strip() for line in key_findings_response.split('\n') if line.strip()]
        
        # 提取研究方法
        methodology_prompt = f"""
        从以下论文分析中提取研究方法：
        
        {analysis}
        
        请简洁地描述研究方法。
        """
        
        methodology = await self.llm_service.generate(methodology_prompt)
        
        # 提取局限性
        limitations_prompt = f"""
        从以下论文分析中提取局限性（最多3条）：
        
        {analysis}
        
        请以列表形式输出，每条局限性一行。
        """
        
        limitations_response = await self.llm_service.generate(limitations_prompt)
        limitations = [line.strip() for line in limitations_response.split('\n') if line.strip()]
        
        # 提取未来工作
        future_work_prompt = f"""
        从以下论文分析中提取未来研究方向（最多3条）：
        
        {analysis}
        
        请以列表形式输出，每条方向一行。
        """
        
        future_work_response = await self.llm_service.generate(future_work_prompt)
        future_work = [line.strip() for line in future_work_response.split('\n') if line.strip()]
        
        return {
            "paper_id": paper_id,
            "title": metadata.get("title", ""),
            "analysis": analysis,
            "key_findings": key_findings,
            "methodology": methodology,
            "limitations": limitations,
            "future_work": future_work,
        }
    
    async def summarize_papers(self, papers: List[Dict[str, Any]]) -> str:
        """
        总结多篇论文
        
        Args:
            papers: 论文列表
            
        Returns:
            str: 总结
        """
        self._logger.info(f"Summarizing {len(papers)} papers")
        
        # 准备论文信息
        paper_summaries = []
        for i, paper in enumerate(papers, 1):
            paper_summaries.append(f"""
            论文{i}：
            标题：{paper.get('title', '')}
            作者：{', '.join(paper.get('authors', []))}
            年份：{paper.get('year', '')}
            摘要：{paper.get('abstract', '')}
            """)
        
        prompt = f"""
        请对以下{len(papers)}篇论文进行综合总结：
        
        {chr(10).join(paper_summaries)}
        
        请提供：
        1. 研究主题概述
        2. 主要研究趋势
        3. 共同发现
        4. 研究差异
        5. 研究空白
        6. 未来方向
        
        请用500字左右进行总结。
        """
        
        summary = await self.llm_service.generate(prompt)
        return summary
    
    async def generate_literature_review(
        self,
        topic: str,
        papers: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        生成文献综述
        
        Args:
            topic: 研究主题
            papers: 论文列表，如果为空则自动检索
            
        Returns:
            str: 文献综述
        """
        self._logger.info(f"Generating literature review for: {topic}")
        
        # 如果没有提供论文，自动检索
        if not papers:
            search_result = await self.search_literature(topic, max_results=30)
            papers = [paper.dict() for paper in search_result.papers]
        
        # 准备论文信息
        paper_info = []
        for i, paper in enumerate(papers, 1):
            paper_info.append(f"""
            [{i}] {paper.get('title', '')} ({paper.get('year', '')})
            作者：{', '.join(paper.get('authors', []))}
            摘要：{paper.get('abstract', '')}
            """)
        
        prompt = f"""
        请为以下研究主题生成一篇学术文献综述：
        
        研究主题：{topic}
        
        参考文献：
        {chr(10).join(paper_info)}
        
        请按照以下结构生成文献综述：
        1. 引言（研究背景和意义）
        2. 研究现状（按主题分类讨论）
        3. 研究方法（主要研究方法）
        4. 主要发现（关键研究成果）
        5. 研究空白（现有研究的不足）
        6. 未来方向（未来研究方向）
        7. 结论
        
        请使用学术写作风格，适当引用参考文献。
        """
        
        review = await self.llm_service.generate(prompt)
        return review
    
    async def generate_citations(
        self,
        papers: List[Dict[str, Any]],
        style: str = "APA",
    ) -> List[str]:
        """
        生成引用
        
        Args:
            papers: 论文列表
            style: 引用格式 (APA, MLA, Chicago, IEEE, Harvard)
            
        Returns:
            List[str]: 引用列表
        """
        self._logger.info(f"Generating citations in {style} style")
        
        citations = []
        
        for paper in papers:
            prompt = f"""
            请将以下论文信息转换为{style}格式的引用：
            
            标题：{paper.get('title', '')}
            作者：{', '.join(paper.get('authors', []))}
            年份：{paper.get('year', '')}
            期刊：{paper.get('journal', '')}
            卷号：{paper.get('volume', '')}
            期号：{paper.get('issue', '')}
            页码：{paper.get('pages', '')}
            DOI：{paper.get('doi', '')}
            
            请只输出格式化后的引用，不要添加其他内容。
            """
            
            citation = await self.llm_service.generate(prompt)
            citations.append(citation.strip())
        
        return citations
    
    async def add_to_favorites(self, paper_id: str) -> Dict[str, Any]:
        """
        添加到收藏
        
        Args:
            paper_id: 论文ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        # 从向量存储获取论文
        paper_doc = await self.vector_store.get_document(f"paper_{paper_id}")
        if not paper_doc:
            raise ValueError(f"Paper {paper_id} not found")
        
        metadata = paper_doc.get("metadata", {})
        
        # 创建论文对象
        paper = Paper(
            id=paper_id,
            title=metadata.get("title", ""),
            authors=metadata.get("authors", []),
            year=metadata.get("year"),
            journal=metadata.get("journal", ""),
            doi=metadata.get("doi", ""),
            citations=metadata.get("citations", 0),
        )
        
        # 添加到收藏
        self._favorite_papers[paper_id] = paper
        
        self._logger.info(f"Paper {paper_id} added to favorites")
        
        return {
            "paper_id": paper_id,
            "title": paper.title,
            "message": "论文已添加到收藏",
        }
    
    async def get_favorites(self) -> List[Dict[str, Any]]:
        """
        获取收藏的论文
        
        Returns:
            List[Dict[str, Any]]: 收藏的论文列表
        """
        favorites = []
        for paper in self._favorite_papers.values():
            favorites.append({
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "journal": paper.journal,
                "citations": paper.citations,
            })
        
        return favorites
    
    def get_search_history(self) -> List[Dict[str, Any]]:
        """
        获取检索历史
        
        Returns:
            List[Dict[str, Any]]: 检索历史
        """
        history = []
        for result in self._search_history:
            history.append({
                "query": result.query,
                "total_results": result.total_results,
                "search_time": result.search_time,
                "timestamp": datetime.now().isoformat(),
            })
        
        return history
    
    def clear_search_history(self) -> None:
        """清空检索历史"""
        self._search_history.clear()
        self._logger.info("Search history cleared")
    
    def clear_favorites(self) -> None:
        """清空收藏"""
        self._favorite_papers.clear()
        self._logger.info("Favorites cleared")
