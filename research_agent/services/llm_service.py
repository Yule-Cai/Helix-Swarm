"""
LLM服务

提供大语言模型调用服务，支持 Anthropic Claude 和 OpenAI GPT。
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from loguru import logger

# 延迟导入，避免未安装时报错
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class LLMService:
    """
    LLM服务

    提供大语言模型调用服务，支持：
    - Anthropic Claude (claude-3-opus, claude-3-sonnet, claude-3-haiku)
    - OpenAI GPT (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)
    - 本地兼容 API (通过 base_url 配置)

    Features:
        - 多模型支持
        - 异步调用
        - 重试机制
        - 缓存支持
        - 流式输出
        - Tool Use 支持
    """

    # 支持的模型提供商
    PROVIDERS = {
        "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "claude-3.5-sonnet"],
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    }

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 60,
        provider: Optional[str] = None,
    ):
        """
        初始化LLM服务

        Args:
            model: 模型名称
            api_key: API密钥（默认从环境变量读取）
            base_url: API基础URL
            max_retries: 最大重试次数
            timeout: 超时时间
            provider: 提供商 (anthropic/openai)，自动检测
        """
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self._logger = logger.bind(module="LLMService")

        # 自动检测提供商
        self.provider = provider or self._detect_provider(model)

        # 设置 API key
        self.api_key = api_key or self._get_default_api_key()

        # 设置 base_url
        self.base_url = base_url

        # 初始化客户端
        self._client = None
        self._init_client()

        # 缓存
        self._cache: Dict[str, str] = {}
        self._cache_enabled = True

        # 统计
        self._total_calls = 0
        self._total_tokens = 0

    def _detect_provider(self, model: str) -> str:
        """自动检测模型提供商"""
        model_lower = model.lower()
        if "claude" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower or "o1" in model_lower:
            return "openai"
        else:
            # 默认使用 OpenAI 兼容接口
            return "openai"

    def _get_default_api_key(self) -> Optional[str]:
        """获取默认 API key"""
        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        else:
            return os.getenv("OPENAI_API_KEY")

    def _init_client(self):
        """初始化 API 客户端"""
        if self.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                self._logger.warning("anthropic package not installed. Run: pip install anthropic")
                return
            self._client = AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.timeout,
            )
        else:
            if not OPENAI_AVAILABLE:
                self._logger.warning("openai package not installed. Run: pip install openai")
                return
            kwargs = {"api_key": self.api_key, "timeout": self.timeout}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = AsyncOpenAI(**kwargs)

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

    async def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        带工具调用的生成

        Args:
            messages: 消息列表
            tools: 工具定义列表
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            Dict: 包含 content 和 tool_calls 的响应
        """
        if self.provider == "anthropic":
            return await self._call_anthropic_with_tools(
                messages=messages,
                tools=tools,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            return await self._call_openai_with_tools(
                messages=messages,
                tools=tools,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

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
        if not self._client:
            raise RuntimeError(f"LLM client not initialized. Please install {'anthropic' if self.provider == 'anthropic' else 'openai'} package.")

        for attempt in range(self.max_retries):
            try:
                if self.provider == "anthropic":
                    return await self._call_anthropic(messages, temperature, max_tokens, stop)
                else:
                    return await self._call_openai(messages, temperature, max_tokens, stop)
            except Exception as e:
                self._logger.warning(f"API call attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 指数退避

    async def _call_anthropic(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stop: Optional[List[str]],
    ) -> str:
        """调用 Anthropic API"""
        # 提取 system prompt
        system_prompt = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        kwargs = {
            "model": self.model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if stop:
            kwargs["stop_sequences"] = stop

        response = await self._client.messages.create(**kwargs)

        # 提取文本内容
        content = response.content[0].text if response.content else ""

        # 更新 token 统计
        if hasattr(response, 'usage'):
            self._total_tokens += response.usage.input_tokens + response.usage.output_tokens

        return content

    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stop: Optional[List[str]],
    ) -> str:
        """调用 OpenAI API"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            kwargs["stop"] = stop

        response = await self._client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content or ""

        # 更新 token 统计
        if hasattr(response, 'usage') and response.usage:
            self._total_tokens += response.usage.total_tokens

        return content

    async def _call_anthropic_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """调用 Anthropic API with tools"""
        # 转换工具格式
        anthropic_tools = []
        for tool in tools:
            func = tool.get("function", {})
            anthropic_tools.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {}),
            })

        # 提取 system prompt
        if not system_prompt:
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                    messages = [m for m in messages if m["role"] != "system"]
                    break

        kwargs = {
            "model": self.model,
            "messages": messages,
            "tools": anthropic_tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)

        # 解析响应
        result = {"content": "", "tool_calls": []}

        for block in response.content:
            if block.type == "text":
                result["content"] += block.text
            elif block.type == "tool_use":
                result["tool_calls"].append({
                    "id": block.id,
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    }
                })

        return result

    async def _call_openai_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """调用 OpenAI API with tools"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = await self._client.chat.completions.create(**kwargs)

        message = response.choices[0].message
        result = {"content": message.content or "", "tool_calls": []}

        if message.tool_calls:
            for tc in message.tool_calls:
                result["tool_calls"].append({
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                })

        return result

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
        if not self._client:
            raise RuntimeError("LLM client not initialized")

        if self.provider == "anthropic":
            # Anthropic 流式调用
            system_prompt_val = None
            user_messages = []
            if system_prompt:
                system_prompt_val = system_prompt
            user_messages.append({"role": "user", "content": prompt})

            kwargs = {
                "model": self.model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if system_prompt_val:
                kwargs["system"] = system_prompt_val

            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        else:
            # OpenAI 流式调用
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

    def _get_cache_key(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """生成缓存键"""
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
        """获取统计信息"""
        return {
            "total_calls": self._total_calls,
            "total_tokens": self._total_tokens,
            "cache_size": len(self._cache),
            "cache_enabled": self._cache_enabled,
            "model": self.model,
            "provider": self.provider,
        }

    def set_model(self, model: str) -> None:
        """设置模型"""
        self.model = model
        self.provider = self._detect_provider(model)
        self._init_client()
        self._logger.info(f"Model set to: {model}")

    def set_api_key(self, api_key: str) -> None:
        """设置API密钥"""
        self.api_key = api_key
        self._init_client()
        self._logger.info("API key set")

    def set_base_url(self, base_url: str) -> None:
        """设置API基础URL"""
        self.base_url = base_url
        self._init_client()
        self._logger.info(f"Base URL set to: {base_url}")


# 便捷工厂函数
def create_llm_service(
    model: str = "gpt-4o-mini",
    provider: Optional[str] = None,
    **kwargs
) -> LLMService:
    """
    创建 LLM 服务实例

    Args:
        model: 模型名称
        provider: 提供商 (anthropic/openai)
        **kwargs: 其他参数

    Returns:
        LLMService 实例
    """
    return LLMService(model=model, provider=provider, **kwargs)
