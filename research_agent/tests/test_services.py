"""
服务测试

测试各种服务功能。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from research_agent.services.llm_service import LLMService
from research_agent.services.search_service import SearchService
from research_agent.services.storage_service import StorageService


class TestLLMService:
    """LLM服务测试类"""
    
    @pytest.fixture
    def service(self):
        """创建测试LLM服务"""
        return LLMService(api_key="test_key", model="gpt-3.5-turbo")
    
    @pytest.mark.asyncio
    async def test_generate(self, service):
        """测试生成"""
        result = await service.generate("测试提示")
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, service):
        """测试带系统提示的生成"""
        result = await service.generate(
            "测试提示",
            system_prompt="你是一个测试助手"
        )
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_generate_with_context(self, service):
        """测试带上下文的生成"""
        context = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"},
        ]
        
        result = await service.generate_with_context(
            "测试提示",
            context=context
        )
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_cache(self, service):
        """测试缓存"""
        # 设置缓存
        service._cache["test_key"] = "test_value"
        
        # 获取缓存
        result = service._cache.get("test_key")
        
        assert result == "test_value"
    
    def test_set_model(self, service):
        """测试设置模型"""
        service.set_model("gpt-4")
        
        assert service.model == "gpt-4"
    
    def test_set_api_key(self, service):
        """测试设置API密钥"""
        service.set_api_key("new_key")
        
        assert service.api_key == "new_key"
    
    def test_set_base_url(self, service):
        """测试设置基础URL"""
        service.set_base_url("https://api.example.com")
        
        assert service.base_url == "https://api.example.com"
    
    def test_get_stats(self, service):
        """测试获取统计"""
        stats = service.get_stats()
        
        assert "total_calls" in stats
        assert "total_tokens" in stats
        assert "cache_size" in stats
        assert "cache_enabled" in stats
        assert "model" in stats


class TestSearchService:
    """搜索服务测试类"""
    
    @pytest.fixture
    def service(self):
        """创建测试搜索服务"""
        return SearchService()
    
    @pytest.mark.asyncio
    async def test_search(self, service):
        """测试搜索"""
        results = await service.search("测试查询")
        
        assert results is not None
        assert isinstance(results, list)
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_search_with_sources(self, service):
        """测试带来源的搜索"""
        results = await service.search("测试查询", sources=["semantic_scholar"])
        
        assert results is not None
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(r["source"] == "semantic_scholar" for r in results)
    
    @pytest.mark.asyncio
    async def test_search_with_limit(self, service):
        """测试带限制的搜索"""
        results = await service.search("测试查询", limit=3)
        
        assert results is not None
        assert isinstance(results, list)
        assert len(results) <= 3
    
    def test_cache(self, service):
        """测试缓存"""
        # 设置缓存
        service._cache["test_key"] = ["result1", "result2"]
        
        # 获取缓存
        result = service._cache.get("test_key")
        
        assert len(result) == 2
    
    def test_add_source(self, service):
        """测试添加来源"""
        service.add_source("academic")
        
        assert "academic" in service.sources
    
    def test_remove_source(self, service):
        """测试移除来源"""
        service.add_source("academic")
        service.remove_source("academic")
        
        assert "academic" not in service.sources
    
    def test_set_max_results(self, service):
        """测试设置最大结果数"""
        service.set_max_results(20)
        
        assert service.max_results == 20
    
    def test_get_stats(self, service):
        """测试获取统计"""
        stats = service.get_stats()
        
        assert "total_searches" in stats
        assert "cache_size" in stats
        assert "cache_enabled" in stats
        assert "sources" in stats


class TestStorageService:
    """存储服务测试类"""
    
    @pytest.fixture
    def service(self, tmp_path):
        """创建测试存储服务"""
        return StorageService(storage_dir=str(tmp_path))
    
    def test_save_and_load(self, service):
        """测试保存和加载"""
        # 保存数据
        service.save("test_key", {"data": "测试数据"})
        
        # 加载数据
        result = service.load("test_key")
        
        assert result == {"data": "测试数据"}
    
    def test_save_and_load_list(self, service):
        """测试保存和加载列表"""
        # 保存列表
        service.save("test_list", [1, 2, 3, 4, 5])
        
        # 加载列表
        result = service.load("test_list")
        
        assert result == [1, 2, 3, 4, 5]
    
    def test_load_nonexistent(self, service):
        """测试加载不存在的数据"""
        result = service.load("nonexistent")
        
        assert result is None
    
    def test_delete(self, service):
        """测试删除"""
        # 保存数据
        service.save("test_key", "test_value")
        
        # 删除数据
        service.delete("test_key")
        
        # 验证删除
        result = service.load("test_key")
        assert result is None
    
    def test_exists(self, service):
        """测试存在性检查"""
        # 保存数据
        service.save("test_key", "test_value")
        
        # 检查存在性
        assert service.exists("test_key") is True
        assert service.exists("nonexistent") is False
    
    def test_list_keys(self, service):
        """测试列出键"""
        # 保存多个数据
        service.save("key1", "value1")
        service.save("key2", "value2")
        service.save("key3", "value3")
        
        # 列出键
        keys = service.list_keys()
        
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys
    
    def test_cache(self, service):
        """测试缓存"""
        # 设置缓存
        service._cache["test_key"] = "test_value"
        
        # 获取缓存
        result = service._cache.get("test_key")
        
        assert result == "test_value"
    
    def test_export_import(self, service, tmp_path):
        """测试导出和导入"""
        # 保存数据
        service.save("key1", "value1")
        service.save("key2", "value2")
        
        # 导出
        export_path = str(tmp_path / "export.json")
        service.export_data("key1", filepath=export_path)
        
        # 删除原数据
        service.delete("key1")
        
        # 导入
        service.import_data(export_path, "key1")
        
        # 验证
        assert service.load("key1") == "value1"
    
    def test_backup(self, service):
        """测试备份"""
        # 保存数据
        service.save("key1", "value1")
        
        # 验证备份目录存在
        assert service.backup_enabled is True
    
    def test_get_stats(self, service):
        """测试获取统计"""
        stats = service.get_stats()
        
        assert "total_reads" in stats
        assert "total_writes" in stats
        assert "cache_size" in stats
        assert "storage_dir" in stats
        assert "auto_save" in stats
        assert "backup_enabled" in stats
    
    def test_get_storage_size(self, service):
        """测试获取存储大小"""
        # 保存数据
        service.save("key1", "value1")
        service.save("key2", "value2")
        
        # 获取大小
        size = service.get_storage_size()
        
        assert "total_size_bytes" in size
        assert "total_size_mb" in size
        assert "file_count" in size
        assert size["total_size_bytes"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])