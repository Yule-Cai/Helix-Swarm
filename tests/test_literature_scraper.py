"""
测试文献综述爬虫模块
"""
import pytest
from unittest.mock import Mock, patch
from src.idea_generation.literature_scraper import LiteratureScraper


class TestLiteratureScraper:
    """测试 LiteratureScraper 类"""
    
    def test_create_scraper(self):
        """测试创建 LiteratureScraper 实例"""
        scraper = LiteratureScraper()
        assert scraper is not None
        assert hasattr(scraper, 'search_arxiv')
        assert hasattr(scraper, 'parse_paper_metadata')
        assert hasattr(scraper, 'remove_duplicates')
    
    def test_search_arxiv_basic(self):
        """测试基本的 arXiv 查询"""
        scraper = LiteratureScraper()
        papers = scraper.search_arxiv("transformer", max_results=5)
        
        assert papers is not None
        assert isinstance(papers, list)
        assert len(papers) <= 5
    
    def test_search_arxiv_returns_metadata(self):
        """测试 arXiv 查询返回论文元数据"""
        scraper = LiteratureScraper()
        papers = scraper.search_arxiv("attention mechanism", max_results=2)
        
        if len(papers) > 0:
            paper = papers[0]
            # 检查必要的元数据字段
            assert 'title' in paper
            assert 'authors' in paper
            assert 'summary' in paper
            assert 'published' in paper
            assert 'arxiv_id' in paper
    
    def test_parse_paper_metadata(self):
        """测试解析论文元数据"""
        scraper = LiteratureScraper()
        
        # 模拟 arXiv 论文对象
        mock_paper = Mock()
        mock_paper.title = "Attention Is All You Need"
        mock_paper.authors = [Mock(name="Vaswani"), Mock(name="Shazeer")]
        mock_paper.summary = "We propose a new architecture..."
        mock_paper.published = "2017-06-12"
        mock_paper.entry_id = "1706.03762"
        mock_paper.pdf_url = "http://arxiv.org/pdf/1706.03762"
        
        metadata = scraper.parse_paper_metadata(mock_paper)
        
        assert metadata['title'] == "Attention Is All You Need"
        assert len(metadata['authors']) == 2
        assert "Vaswani" in str(metadata['authors'])
        assert metadata['arxiv_id'] == "1706.03762"
    
    def test_remove_duplicates(self):
        """测试去重功能"""
        scraper = LiteratureScraper()
        
        papers = [
            {'title': 'Paper A', 'arxiv_id': '1234.5678', 'authors': ['Author 1']},
            {'title': 'Paper B', 'arxiv_id': '8765.4321', 'authors': ['Author 2']},
            {'title': 'Paper A', 'arxiv_id': '1234.5678', 'authors': ['Author 1']},  # 重复
            {'title': 'Paper C', 'arxiv_id': '1111.2222', 'authors': ['Author 3']},
        ]
        
        unique_papers = scraper.remove_duplicates(papers)
        
        assert len(unique_papers) == 3
        arxiv_ids = [p['arxiv_id'] for p in unique_papers]
        assert arxiv_ids.count('1234.5678') == 1
    
    def test_rate_limiting(self):
        """测试速率限制处理"""
        scraper = LiteratureScraper(rate_limit_delay=0.1)  # 100ms 延迟
        
        # 执行多次查询，确保速率限制生效
        import time
        start = time.time()
        scraper.search_arxiv("test query", max_results=2)
        scraper.search_arxiv("another query", max_results=2)
        elapsed = time.time() - start
        
        # 至少应该有 100ms 的延迟
        assert elapsed >= 0.1
    
    def test_empty_query_result(self):
        """测试空查询结果"""
        scraper = LiteratureScraper()
        papers = scraper.search_arxiv("", max_results=5)
        
        assert isinstance(papers, list)
    
    def test_search_with_invalid_max_results(self):
        """测试无效的 max_results 参数"""
        scraper = LiteratureScraper()
        
        # max_results 应该至少为 1
        papers = scraper.search_arxiv("test", max_results=0)
        assert isinstance(papers, list)
