"""
Tool Use Loop 模块

实现完整的工具调用循环，让 LLM 可以：
1. 调用工具（bash、文件读写、搜索等）
2. 解析返回结果
3. 基于结果继续推理
4. 支持多轮工具调用
"""

import json
import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger

from .registry import registry


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class ToolUseResult:
    """工具使用循环结果"""
    final_response: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    iterations: int = 0
    total_tokens: int = 0


class ToolUseLoop:
    """
    工具使用循环

    实现 LLM 与工具的交互循环：
    1. LLM 生成响应（可能包含工具调用）
    2. 执行工具调用
    3. 将结果返回给 LLM
    4. LLM 继续推理或生成最终响应

    Features:
        - 支持多轮工具调用
        - 工具调用超时处理
        - 错误处理和重试
        - 调用历史追踪
    """

    def __init__(
        self,
        llm_service,
        max_iterations: int = 10,
        tool_timeout: int = 60,
        verbose: bool = True,
    ):
        """
        初始化工具使用循环

        Args:
            llm_service: LLM 服务实例
            max_iterations: 最大迭代次数
            tool_timeout: 工具调用超时时间（秒）
            verbose: 是否显示详细信息
        """
        self.llm_service = llm_service
        self.max_iterations = max_iterations
        self.tool_timeout = tool_timeout
        self.verbose = verbose
        self._logger = logger.bind(module="ToolUseLoop")

    async def run(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        context: Optional[List[Dict]] = None,
    ) -> ToolUseResult:
        """
        运行工具使用循环

        Args:
            user_input: 用户输入
            system_prompt: 系统提示
            tools: 工具定义列表（如果为 None，使用注册表中的所有工具）
            context: 上下文消息列表

        Returns:
            ToolUseResult: 循环结果
        """
        # 获取工具定义
        if tools is None:
            tools = self._get_all_tool_schemas()

        # 构建消息
        messages = []
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": user_input})

        result = ToolUseResult(final_response="")

        for iteration in range(self.max_iterations):
            result.iterations = iteration + 1

            if self.verbose:
                self._logger.info(f"Iteration {iteration + 1}/{self.max_iterations}")

            # 调用 LLM
            try:
                response = await self.llm_service.generate_with_tools(
                    messages=messages,
                    tools=tools,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=4000,
                )
            except Exception as e:
                self._logger.error(f"LLM call failed: {e}")
                result.final_response = f"Error: LLM call failed - {str(e)}"
                break

            # 检查是否有工具调用
            tool_calls = response.get("tool_calls", [])

            if not tool_calls:
                # 没有工具调用，循环结束
                result.final_response = response.get("content", "")
                break

            # 执行工具调用
            if self.verbose:
                self._logger.info(f"Executing {len(tool_calls)} tool calls")

            # 添加 assistant 消息（包含工具调用）
            messages.append({
                "role": "assistant",
                "content": response.get("content", ""),
                "tool_calls": tool_calls,
            })

            # 执行每个工具调用
            for tool_call in tool_calls:
                tc = await self._execute_tool_call(tool_call)
                result.tool_calls.append(tc)

                # 添加工具结果到消息
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tc.result if tc.success else f"Error: {tc.error}",
                })

        return result

    async def _execute_tool_call(self, tool_call: Dict) -> ToolCall:
        """
        执行单个工具调用

        Args:
            tool_call: 工具调用信息

        Returns:
            ToolCall: 执行结果
        """
        tc_id = tool_call.get("id", "")
        func = tool_call.get("function", {})
        name = func.get("name", "")
        args_str = func.get("arguments", "{}")

        # 解析参数
        try:
            if isinstance(args_str, str):
                args = json.loads(args_str)
            else:
                args = args_str
        except json.JSONDecodeError:
            args = {}

        tc = ToolCall(id=tc_id, name=name, arguments=args)

        if self.verbose:
            self._logger.info(f"  Calling tool: {name}({json.dumps(args)[:100]})")

        # 执行工具
        import time
        start_time = time.time()

        try:
            # 使用 asyncio.wait_for 实现超时
            result = await asyncio.wait_for(
                self._run_tool(name, args),
                timeout=self.tool_timeout,
            )
            tc.result = str(result)
            tc.duration = time.time() - start_time

            if self.verbose:
                self._logger.info(f"  Tool {name} completed in {tc.duration:.2f}s")

        except asyncio.TimeoutError:
            tc.error = f"Tool {name} timed out after {self.tool_timeout}s"
            tc.duration = self.tool_timeout
            self._logger.warning(tc.error)

        except Exception as e:
            tc.error = str(e)
            tc.duration = time.time() - start_time
            self._logger.error(f"Tool {name} failed: {e}")

        return tc

    async def _run_tool(self, name: str, args: Dict) -> str:
        """
        异步运行工具

        Args:
            name: 工具名称
            args: 工具参数

        Returns:
            str: 工具执行结果
        """
        # 在线程池中执行同步工具
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: registry.execute(name, json.dumps(args))
        )
        return result

    def _get_all_tool_schemas(self) -> List[Dict]:
        """获取所有注册工具的 schema"""
        return list(registry.schemas.values())

    def get_tool_schemas(self, tool_names: List[str]) -> List[Dict]:
        """获取指定工具的 schema"""
        schemas = []
        for name in tool_names:
            schema = registry.get_schema(name)
            if schema:
                schemas.append(schema)
        return schemas


class ToolUseLoopWithReflection(ToolUseLoop):
    """
    带反思的工具使用循环

    在工具调用失败时，让 LLM 分析错误并决定是否重试。
    """

    def __init__(
        self,
        llm_service,
        max_iterations: int = 10,
        max_retries: int = 3,
        tool_timeout: int = 60,
        verbose: bool = True,
    ):
        super().__init__(llm_service, max_iterations, tool_timeout, verbose)
        self.max_retries = max_retries

    async def _execute_tool_call(self, tool_call: Dict) -> ToolCall:
        """执行工具调用，失败时进行反思和重试"""
        tc_id = tool_call.get("id", "")
        func = tool_call.get("function", {})
        name = func.get("name", "")
        args_str = func.get("arguments", "{}")

        try:
            if isinstance(args_str, str):
                args = json.loads(args_str)
            else:
                args = args_str
        except json.JSONDecodeError:
            args = {}

        tc = ToolCall(id=tc_id, name=name, arguments=args)

        for retry in range(self.max_retries):
            if retry > 0:
                if self.verbose:
                    self._logger.info(f"  Retrying {name} (attempt {retry + 1}/{self.max_retries})")

                # 让 LLM 分析错误并调整参数
                args = await self._reflect_and_fix(name, args, tc.error)
                tc.arguments = args

            import time
            start_time = time.time()

            try:
                result = await asyncio.wait_for(
                    self._run_tool(name, args),
                    timeout=self.tool_timeout,
                )
                tc.result = str(result)
                tc.duration = time.time() - start_time
                tc.error = None
                return tc

            except asyncio.TimeoutError:
                tc.error = f"Tool {name} timed out after {self.tool_timeout}s"
                tc.duration = self.tool_timeout

            except Exception as e:
                tc.error = str(e)
                tc.duration = time.time() - start_time

        return tc

    async def _reflect_and_fix(
        self,
        tool_name: str,
        original_args: Dict,
        error: str,
    ) -> Dict:
        """
        让 LLM 分析错误并修复参数

        Args:
            tool_name: 工具名称
            original_args: 原始参数
            error: 错误信息

        Returns:
            Dict: 修复后的参数
        """
        prompt = f"""The tool call failed. Analyze the error and suggest fixed parameters.

Tool: {tool_name}
Original Parameters: {json.dumps(original_args, indent=2)}
Error: {error}

Please respond with ONLY a JSON object containing the fixed parameters."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are an expert at debugging tool calls. Provide corrected parameters in JSON format.",
                temperature=0.3,
                max_tokens=500,
            )

            # 解析响应
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            return json.loads(json_str.strip())

        except Exception:
            return original_args


# 便捷函数
async def run_with_tools(
    user_input: str,
    llm_service,
    system_prompt: Optional[str] = None,
    tools: Optional[List[str]] = None,
    max_iterations: int = 10,
) -> str:
    """
    运行工具使用循环的便捷函数

    Args:
        user_input: 用户输入
        llm_service: LLM 服务实例
        system_prompt: 系统提示
        tools: 工具名称列表（可选）
        max_iterations: 最大迭代次数

    Returns:
        str: 最终响应
    """
    loop = ToolUseLoop(llm_service, max_iterations=max_iterations)

    tool_schemas = None
    if tools:
        tool_schemas = loop.get_tool_schemas(tools)

    result = await loop.run(
        user_input=user_input,
        system_prompt=system_prompt,
        tools=tool_schemas,
    )

    return result.final_response
