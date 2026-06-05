"""
LLM服务

提供大语言模型调用服务。
"""

import asyncio
from typing import Any, Dict, List, Optional
from loguru import logger


class LLMService:
    """
    LLM服务
    
    提供大语言模型调用服务。
    
    Features:
        - 多模型支持
        - 异步调用
        - 重试机制
        - 缓存支持
        - 流式输出
    """
    
    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """
        初始化LLM服务
        
        Args:
            model: 模型名称
            api_key: API密钥
            base_url: API基础URL
            max_retries: 最大重试次数
            timeout: 超时时间
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout = timeout
        self._logger = logger.bind(module="LLMService")
        
        # 缓存
        self._cache: Dict[str, str] = {}
        self._cache_enabled = True
        
        # 统计
        self._total_calls = 0
        self._total_tokens = 0
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stop: Optional[List[str]] = None,
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大token数
            stop: 停止词
            
        Returns:
            str: 生成的文本
        """
        # 检查缓存
        cache_key = self._get_cache_key(prompt, system_prompt, temperature, max_tokens)
        if self._cache_enabled and cache_key in self._cache:
            self._logger.debug("Cache hit")
            return self._cache[cache_key]
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 调用API
        response = await self._call_api(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
        )
        
        # 缓存结果
        if self._cache_enabled:
            self._cache[cache_key] = response
        
        # 更新统计
        self._total_calls += 1
        
        return response
    
    async def generate_with_context(
        self,
        prompt: str,
        context: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        带上下文生成文本
        
        Args:
            prompt: 用户提示
            context: 上下文消息列表
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            str: 生成的文本
        """
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加上下文
        messages.extend(context)
        
        # 添加当前提示
        messages.append({"role": "user", "content": prompt})
        
        # 调用API
        response = await self._call_api(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return response
    
    async def _call_api(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stop: Optional[List[str]] = None,
    ) -> str:
        """
        调用API
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            stop: 停止词
            
        Returns:
            str: API响应
        """
        # 这里是模拟实现
        # 实际应用中应调用真实的LLM API
        
        self._logger.info(f"Calling LLM API with {len(messages)} messages")
        
        # 模拟API调用延迟
        await asyncio.sleep(0.1)
        
        # 模拟响应
        # 实际应用中应使用openai或其他LLM客户端
        prompt = messages[-1]["content"] if messages else ""
        
        # 简单的模拟响应
        if "json" in prompt.lower():
            response = '{"result": "模拟JSON响应", "status": "success"}'
        elif "列表" in prompt or "list" in prompt.lower():
            response = "1. 第一项\n2. 第二项\n3. 第三项"
        else:
            response = f"这是对以下提示的模拟响应：\n\n{prompt[:100]}..."
        
        return response
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """
        流式生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            str: 生成的文本片段
        """
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 模拟流式输出
        response = await self._call_api(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # 分块输出
        chunk_size = 10
        for i in range(0, len(response), chunk_size):
            yield response[i:i+chunk_size]
            await asyncio.sleep(0.05)
    
    def _get_cache_key(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        生成缓存键
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            str: 缓存键
        """
        import hashlib
        
        key_parts = [
            prompt,
            system_prompt or "",
            str(temperature),
            str(max_tokens),
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
            "total_calls": self._total_calls,
            "total_tokens": self._total_tokens,
            "cache_size": len(self._cache),
            "cache_enabled": self._cache_enabled,
            "model": self.model,
        }
    
    def set_model(self, model: str) -> None:
        """
        设置模型
        
        Args:
            model: 模型名称
        """
        self.model = model
        self._logger.info(f"Model set to: {model}")
    
    def set_api_key(self, api_key: str) -> None:
        """
        设置API密钥
        
        Args:
            api_key: API密钥
        """
        self.api_key = api_key
        self._logger.info("API key set")
    
    def set_base_url(self, base_url: str) -> None:
        """
        设置API基础URL
        
        Args:
            base_url: API基础URL
        """
        self.base_url = base_url
        self._logger.info(f"Base URL set to: {base_url}")