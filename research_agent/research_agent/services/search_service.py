"""
搜索服务

提供学术文献搜索服务。
"""

import asyncio
from typing import Any, Dict, List, Optional
from loguru import logger


class SearchService:
    """
    搜索服务
    
    提供学术文献搜索服务。
    
    Features:
        - 多数据源支持
        - 异步搜索
        - 结果缓存
        - 结果过滤
        - 结果排序
    """
    
    def __init__(
        self,
        sources: List[str] = None,
        max_results: int = 100,
        timeout: int = 30,
    ):
        """
        初始化搜索服务
        
        Args:
            sources: 数据源列表
            max_results: 最大结果数
            timeout: 超时时间
        """
        self.sources = sources or ["semantic_scholar", "arxiv", "pubmed"]
        self.max_results = max_results
        self.timeout = timeout
        self._logger = logger.bind(module="SearchService")
        
        # 缓存
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_enabled = True
        
        # 统计
        self._total_searches = 0
    
    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索文献
        
        Args:
            query: 搜索查询
            sources: 数据源列表
            limit: 结果数量限制
            offset: 偏移量
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        self._logger.info(f"Searching: {query}")
        
        # 检查缓存
        cache_key = self._get_cache_key(query, sources, limit, offset, filters)
        if self._cache_enabled and cache_key in self._cache:
            self._logger.debug("Cache hit")
            return self._cache[cache_key]
        
        # 确定数据源
        search_sources = sources or self.sources
        
        # 并行搜索多个数据源
        tasks = []
        for source in search_sources:
            task = self._search_source(source, query, limit, offset, filters)
            tasks.append(task)
        
        # 等待所有搜索完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_results = []
        for result in results:
            if isinstance(result, Exception):
                self._logger.error(f"Search error: {result}")
            elif isinstance(result, list):
                all_results.extend(result)
        
        # 去重
        unique_results = self._deduplicate(all_results)
        
        # 排序
        sorted_results = self._sort_results(unique_results)
        
        # 限制数量
        final_results = sorted_results[:limit]
        
        # 缓存结果
        if self._cache_enabled:
            self._cache[cache_key] = final_results
        
        # 更新统计
        self._total_searches += 1
        
        self._logger.info(f"Found {len(final_results)} results")
        
        return final_results
    
    async def _search_source(
        self,
        source: str,
        query: str,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        搜索单个数据源
        
        Args:
            source: 数据源
            query: 搜索查询
            limit: 结果数量限制
            offset: 偏移量
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        self._logger.debug(f"Searching {source}: {query}")
        
        # 模拟搜索延迟
        await asyncio.sleep(0.1)
        
        # 模拟搜索结果
        # 实际应用中应调用真实的API
        results = []
        
        if source == "semantic_scholar":
            results = await self._search_semantic_scholar(query, limit, offset, filters)
        elif source == "arxiv":
            results = await self._search_arxiv(query, limit, offset, filters)
        elif source == "pubmed":
            results = await self._search_pubmed(query, limit, offset, filters)
        elif source == "google_scholar":
            results = await self._search_google_scholar(query, limit, offset, filters)
        else:
            self._logger.warning(f"Unknown source: {source}")
        
        return results
    
    async def _search_semantic_scholar(
        self,
        query: str,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        搜索Semantic Scholar
        
        Args:
            query: 搜索查询
            limit: 结果数量限制
            offset: 偏移量
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        # 模拟结果
        results = []
        for i in range(min(limit, 5)):
            results.append({
                "id": f"ss_{offset + i}",
                "title": f"Semantic Scholar论文 {i+1}: {query}",
                "authors": [f"作者 {j+1}" for j in range(3)],
                "abstract": f"这是关于{query}的摘要...",
                "year": 2023 - i,
                "citation_count": 100 - i * 10,
                "source": "semantic_scholar",
                "url": f"https://www.semanticscholar.org/paper/{offset + i}",
                "doi": f"10.1234/ss.{offset + i}",
            })
        
        return results
    
    async def _search_arxiv(
        self,
        query: str,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        搜索arXiv
        
        Args:
            query: 搜索查询
            limit: 结果数量限制
            offset: 偏移量
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        # 模拟结果
        results = []
        for i in range(min(limit, 5)):
            results.append({
                "id": f"arxiv_{offset + i}",
                "title": f"arXiv论文 {i+1}: {query}",
                "authors": [f"作者 {j+1}" for j in range(3)],
                "abstract": f"这是关于{query}的arXiv摘要...",
                "year": 2023 - i,
                "citation_count": 50 - i * 5,
                "source": "arxiv",
                "url": f"https://arxiv.org/abs/{2301 + offset + i}.{12345 + i}",
                "categories": ["cs.AI", "cs.LG"],
            })
        
        return results
    
    async def _search_pubmed(
        self,
        query: str,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        搜索PubMed
        
        Args:
            query: 搜索查询
            limit: 结果数量限制
            offset: 偏移量
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        # 模拟结果
        results = []
        for i in range(min(limit, 5)):
            results.append({
                "id": f"pmid_{offset + i}",
                "title": f"PubMed论文 {i+1}: {query}",
                "authors": [f"作者 {j+1}" for j in range(3)],
                "abstract": f"这是关于{query}的PubMed摘要...",
                "year": 2023 - i,
                "citation_count": 80 - i * 8,
                "source": "pubmed",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{30000000 + offset + i}",
                "journal": "Journal of Medicine",
                "pmid": str(30000000 + offset + i),
            })
        
        return results
    
    async def _search_google_scholar(
        self,
        query: str,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        搜索Google Scholar
        
        Args:
            query: 搜索查询
            limit: 结果数量限制
            offset: 偏移量
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        # 模拟结果
        results = []
        for i in range(min(limit, 5)):
            results.append({
                "id": f"gs_{offset + i}",
                "title": f"Google Scholar论文 {i+1}: {query}",
                "authors": [f"作者 {j+1}" for j in range(3)],
                "abstract": f"这是关于{query}的Google Scholar摘要...",
                "year": 2023 - i,
                "citation_count": 200 - i * 20,
                "source": "google_scholar",
                "url": f"https://scholar.google.com/scholar?q={query}&offset={offset + i}",
            })
        
        return results
    
    def _deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去重
        
        Args:
            results: 搜索结果
            
        Returns:
            List[Dict[str, Any]]: 去重后的结果
        """
        seen_ids = set()
        unique_results = []
        
        for result in results:
            # 使用标题和作者作为去重键
            title = result.get("title", "").lower().strip()
            authors = tuple(sorted(result.get("authors", [])))
            key = (title, authors)
            
            if key not in seen_ids:
                seen_ids.add(key)
                unique_results.append(result)
        
        return unique_results
    
    def _sort_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        排序结果
        
        Args:
            results: 搜索结果
            
        Returns:
            List[Dict[str, Any]]: 排序后的结果
        """
        # 按引用次数和年份排序
        def sort_key(r):
            citations = r.get("citation_count", 0)
            year = r.get("year", 0)
            return (-citations, -year)
        
        return sorted(results, key=sort_key)
    
    def _get_cache_key(
        self,
        query: str,
        sources: Optional[List[str]],
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
    ) -> str:
        """
        生成缓存键
        
        Args:
            query: 搜索查询
            sources: 数据源列表
            limit: 结果数量限制
            offset: 偏移量
            filters: 过滤条件
            
        Returns:
            str: 缓存键
        """
        import hashlib
        
        key_parts = [
            query,
            str(sorted(sources) if sources else ""),
            str(limit),
            str(offset),
            str(sorted(filters.items()) if filters else ""),
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
        self._logger.info("Cache cleared")
    
    def enable_cache(self) -> None:
        """启用缓存"""
        self._cache_enabled = True
        self._logger.info("Cache enabled")
    
    def disable_cache(self) -> None:
        """禁用缓存"""
        self._cache_enabled = False
        self._logger.info("Cache disabled")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_searches": self._total_searches,
            "cache_size": len(self._cache),
            "cache_enabled": self._cache_enabled,
            "sources": self.sources,
        }
    
    def add_source(self, source: str) -> None:
        """
        添加数据源
        
        Args:
            source: 数据源名称
        """
        if source not in self.sources:
            self.sources.append(source)
            self._logger.info(f"Source added: {source}")
    
    def remove_source(self, source: str) -> None:
        """
        移除数据源
        
        Args:
            source: 数据源名称
        """
        if source in self.sources:
            self.sources.remove(source)
            self._logger.info(f"Source removed: {source}")
    
    def set_max_results(self, max_results: int) -> None:
        """
        设置最大结果数
        
        Args:
            max_results: 最大结果数
        """
        self.max_results = max_results
        self._logger.info(f"Max results set to: {max_results}")