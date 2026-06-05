"""
脚本执行器模块

提供安全的脚本执行环境，支持超时和内存限制。
包含 LLM 错误分析与自动修复功能。
"""

import subprocess
import json
import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """执行结果数据类"""
    success: bool
    stdout: str
    stderr: str
    error: Optional[str] = None
    exit_code: int = 0
    fix_suggestions: Optional[list] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'error': self.error,
            'exit_code': self.exit_code,
            'fix_suggestions': self.fix_suggestions,
            'retry_count': self.retry_count,
        }


class ScriptExecutor:
    """脚本执行器类

    提供安全的脚本执行环境，支持：
    - 超时和内存限制
    - LLM 错误分析
    - 自动修复建议
    - 失败重试
    """

    def __init__(
        self,
        timeout: int = 300,
        memory_limit: Optional[int] = None,
        llm_service=None,
        max_retries: int = 3,
        enable_llm_analysis: bool = True,
    ):
        """
        初始化脚本执行器

        Args:
            timeout: 超时时间（秒），默认300秒（5分钟）
            memory_limit: 内存限制（MB），暂未实现
            llm_service: LLM 服务实例（用于错误分析）
            max_retries: 最大重试次数
            enable_llm_analysis: 是否启用 LLM 错误分析
        """
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.llm_service = llm_service
        self.max_retries = max_retries
        self.enable_llm_analysis = enable_llm_analysis and llm_service is not None

    def execute(self, script_path: str) -> Dict[str, Any]:
        """
        执行脚本并返回结果

        Args:
            script_path: 脚本路径（必须是有效的 Python 脚本）

        Returns:
            包含执行结果的字典
        """
        result = self._execute_once(script_path)

        # 如果失败且启用了 LLM 分析，尝试分析并重试
        if not result.success and self.enable_llm_analysis:
            result = self._execute_with_llm_retry(script_path, result)

        return result.to_dict()

    async def execute_async(self, script_path: str) -> Dict[str, Any]:
        """
        异步执行脚本并返回结果

        Args:
            script_path: 脚本路径

        Returns:
            包含执行结果的字典
        """
        result = await self._execute_once_async(script_path)

        # 如果失败且启用了 LLM 分析，尝试分析并重试
        if not result.success and self.enable_llm_analysis:
            result = await self._execute_with_llm_retry_async(script_path, result)

        return result.to_dict()

    def _execute_once(self, script_path: str) -> ExecutionResult:
        """执行一次脚本"""
        try:
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                error=None if result.returncode == 0 else result.stderr,
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                stdout='',
                stderr='',
                error=f'Script execution timeout after {self.timeout} seconds',
                exit_code=-1,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout='',
                stderr='',
                error=str(e),
                exit_code=-1,
            )

    async def _execute_once_async(self, script_path: str) -> ExecutionResult:
        """异步执行一次脚本"""
        try:
            process = await asyncio.create_subprocess_exec(
                'python', script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ExecutionResult(
                    success=False,
                    stdout='',
                    stderr='',
                    error=f'Script execution timeout after {self.timeout} seconds',
                    exit_code=-1,
                )

            return ExecutionResult(
                success=process.returncode == 0,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                error=None if process.returncode == 0 else stderr.decode('utf-8', errors='replace'),
                exit_code=process.returncode,
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout='',
                stderr='',
                error=str(e),
                exit_code=-1,
            )

    def _execute_with_llm_retry(
        self,
        script_path: str,
        initial_result: ExecutionResult,
    ) -> ExecutionResult:
        """使用 LLM 分析错误并重试"""
        current_result = initial_result

        for retry in range(self.max_retries):
            # 分析错误
            analysis = self._analyze_error_with_llm(
                script_path,
                current_result.stderr or current_result.error or "",
                current_result.stdout,
            )

            if not analysis:
                break

            # 应用修复
            if analysis.get("fix_applied"):
                current_result = self._execute_once(script_path)
                current_result.retry_count = retry + 1
                current_result.fix_suggestions = analysis.get("suggestions", [])

                if current_result.success:
                    return current_result
            else:
                # 无法自动修复
                current_result.fix_suggestions = analysis.get("suggestions", [])
                break

        return current_result

    async def _execute_with_llm_retry_async(
        self,
        script_path: str,
        initial_result: ExecutionResult,
    ) -> ExecutionResult:
        """异步版本：使用 LLM 分析错误并重试"""
        current_result = initial_result

        for retry in range(self.max_retries):
            # 分析错误
            analysis = await self._analyze_error_with_llm_async(
                script_path,
                current_result.stderr or current_result.error or "",
                current_result.stdout,
            )

            if not analysis:
                break

            # 应用修复
            if analysis.get("fix_applied"):
                current_result = await self._execute_once_async(script_path)
                current_result.retry_count = retry + 1
                current_result.fix_suggestions = analysis.get("suggestions", [])

                if current_result.success:
                    return current_result
            else:
                current_result.fix_suggestions = analysis.get("suggestions", [])
                break

        return current_result

    def _analyze_error_with_llm(
        self,
        script_path: str,
        stderr: str,
        stdout: str,
    ) -> Optional[Dict[str, Any]]:
        """使用 LLM 分析错误"""
        if not self.llm_service or not stderr:
            return None

        try:
            # 读取脚本内容
            script_content = ""
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
            except Exception:
                pass

            prompt = f"""Analyze this Python script execution error and provide fix suggestions.

Script Path: {script_path}

Script Content (first 2000 chars):
{script_content[:2000]}

Error Output (stderr):
{stderr[:1000]}

Standard Output (stdout):
{stdout[:500]}

Please respond in JSON format:
{{
    "error_type": "syntax|import|runtime|timeout|memory|other",
    "root_cause": "Brief description of the root cause",
    "suggestions": ["suggestion1", "suggestion2"],
    "fix_applied": false,
    "fix_description": "Description of suggested fix"
}}

If the error can be automatically fixed by modifying the script, set fix_applied to true and provide the fix_description.
Otherwise, set fix_applied to false and provide suggestions for manual fixing."""

            # 同步调用 LLM
            loop = asyncio.new_event_loop()
            response = loop.run_until_complete(
                self.llm_service.generate(
                    prompt=prompt,
                    system_prompt="You are an expert Python debugger. Analyze errors and provide actionable fix suggestions.",
                    temperature=0.3,
                    max_tokens=500,
                )
            )
            loop.close()

            # 解析响应
            try:
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0]

                return json.loads(json_str.strip())
            except json.JSONDecodeError:
                return {
                    "error_type": "unknown",
                    "root_cause": response[:200],
                    "suggestions": ["Check the error message and fix manually"],
                    "fix_applied": False,
                }

        except Exception as e:
            print(f"LLM error analysis failed: {e}")
            return None

    async def _analyze_error_with_llm_async(
        self,
        script_path: str,
        stderr: str,
        stdout: str,
    ) -> Optional[Dict[str, Any]]:
        """异步版本：使用 LLM 分析错误"""
        if not self.llm_service or not stderr:
            return None

        try:
            script_content = ""
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
            except Exception:
                pass

            prompt = f"""Analyze this Python script execution error and provide fix suggestions.

Script Path: {script_path}

Script Content (first 2000 chars):
{script_content[:2000]}

Error Output (stderr):
{stderr[:1000]}

Standard Output (stdout):
{stdout[:500]}

Please respond in JSON format:
{{
    "error_type": "syntax|import|runtime|timeout|memory|other",
    "root_cause": "Brief description of the root cause",
    "suggestions": ["suggestion1", "suggestion2"],
    "fix_applied": false,
    "fix_description": "Description of suggested fix"
}}"""

            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are an expert Python debugger. Analyze errors and provide actionable fix suggestions.",
                temperature=0.3,
                max_tokens=500,
            )

            try:
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0]

                return json.loads(json_str.strip())
            except json.JSONDecodeError:
                return {
                    "error_type": "unknown",
                    "root_cause": response[:200],
                    "suggestions": ["Check the error message and fix manually"],
                    "fix_applied": False,
                }

        except Exception as e:
            print(f"LLM error analysis failed: {e}")
            return None

    def set_timeout(self, seconds: int) -> None:
        """设置脚本执行超时时间"""
        self.timeout = seconds

    def set_memory_limit(self, mb: int) -> None:
        """设置内存限制（暂未实现）"""
        self.memory_limit = mb

    def set_llm_service(self, llm_service) -> None:
        """设置 LLM 服务"""
        self.llm_service = llm_service
        self.enable_llm_analysis = llm_service is not None
