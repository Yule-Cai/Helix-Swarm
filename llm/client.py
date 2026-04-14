"""
LLM Client — 流式接收版
核心改动：改用 stream=True，模型一边生成一边接收
  - 不再等整个响应完成才返回，彻底解决本地模型超时问题
  - 每个 token 到达时检查取消信号，取消响应更及时
  - 保留 multimodal、重试、CancelledError 机制
"""
from __future__ import annotations
import os
import time
import json
import re
import base64
import threading
from pathlib import Path
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

def _ext_to_mime(ext: str) -> str:
    return {".jpg":"image/jpeg",".jpeg":"image/jpeg",
            ".png":"image/png",".gif":"image/gif",".webp":"image/webp"
            }.get(ext.lower(), "image/png")

def _encode_image(path: str) -> tuple[str, str]:
    ext  = Path(path).suffix.lower()
    mime = _ext_to_mime(ext)
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime

def _build_user_content(text: str, image_paths: list[str]) -> list | str:
    if not image_paths:
        return text
    parts: list = []
    for p in image_paths:
        if not os.path.isfile(p):
            continue
        data, mime = _encode_image(p)
        parts.append({"type":"image_url","image_url":{"url":f"data:{mime};base64,{data}","detail":"auto"}})
    parts.append({"type":"text","text":text})
    return parts if len(parts) > 1 else text


class CancelledError(Exception):
    """用户取消任务时抛出"""
    pass


class LLMClient:
    def __init__(
        self,
        api_url:     str = "http://localhost:1234/v1",
        model_name:  str = "local-model",
        api_key:     str = "not-needed",
        timeout:     int = 600,
        max_retries: int = 2,
    ):
        self.model_name  = model_name
        self.max_retries = max_retries
        self.timeout     = timeout
        self._cancel_event: threading.Event | None = None
        self.client = OpenAI(
            base_url=api_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=0,
        )
        print(f"🔌 [LLM] 已连接 {api_url}  model={model_name}  timeout={timeout}s")

    def set_cancel_event(self, event: threading.Event):
        self._cancel_event = event

    def _check_cancel(self):
        if self._cancel_event and self._cancel_event.is_set():
            raise CancelledError("任务已取消")

    # ── Token 统计 ────────────────────────────────────────────
    # 任务级别累加器，由 executor 调用 reset_usage() / get_usage() 管理
    _usage_prompt:     int = 0
    _usage_completion: int = 0
    _usage_calls:      int = 0

    def reset_usage(self):
        """每次任务开始前重置计数。"""
        self._usage_prompt     = 0
        self._usage_completion = 0
        self._usage_calls      = 0

    def get_usage(self) -> dict:
        """返回当前累计用量。"""
        return {
            "calls":      self._usage_calls,
            "prompt":     self._usage_prompt,
            "completion": self._usage_completion,
            "total":      self._usage_prompt + self._usage_completion,
        }

    def _add_usage(self, prompt: int, completion: int):
        self._usage_calls      += 1
        self._usage_prompt     += prompt
        self._usage_completion += completion

    # ── 流式接收核心 ──────────────────────────────────────────
    def _stream_chat(self, messages: list, temperature: float,
                     max_tokens: int) -> str:
        """
        优先用流式接收。
        加 stream_options include_usage=True 获取 token 用量。
        """
        try:
            chunks = []
            prompt_tokens = completion_tokens = 0
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                self._check_cancel()
                # 最后一个 chunk 携带 usage
                if hasattr(chunk, "usage") and chunk.usage:
                    prompt_tokens     = chunk.usage.prompt_tokens or 0
                    completion_tokens = chunk.usage.completion_tokens or 0
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        chunks.append(delta.content)
            result = "".join(chunks).strip()
            self._add_usage(prompt_tokens, completion_tokens)
            if result:
                return result
            raise ValueError("stream returned empty")
        except (CancelledError, KeyboardInterrupt):
            raise
        except Exception as stream_err:
            print(f"⚠️  [LLM] 流式失败，降级非流式: {stream_err}")
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            usage = resp.usage
            if usage:
                self._add_usage(usage.prompt_tokens or 0, usage.completion_tokens or 0)
            return resp.choices[0].message.content.strip()

    def chat(
        self,
        system:       str,
        user:         str,
        temperature:  float = 0.7,
        max_tokens:   int   = 2048,
        image_paths:  list[str] | None = None,
    ) -> str:
        self._check_cancel()

        user_content = _build_user_content(user, image_paths or [])
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content},
        ]

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            self._check_cancel()
            try:
                return self._stream_chat(messages, temperature, max_tokens)

            except CancelledError:
                raise

            except (APIConnectionError, APITimeoutError) as e:
                last_err = e
                wait = min(15 * attempt, 30)
                print(f"⚠️  [LLM] 连接错误(第{attempt}次)，{wait}s后重试… ({e})")
                for _ in range(wait):
                    if self._cancel_event and self._cancel_event.is_set():
                        raise CancelledError("任务已取消（等待重试期间）")
                    time.sleep(1)

            except RateLimitError as e:
                last_err = e
                print("⚠️  [LLM] 限流，5s后重试…")
                time.sleep(5)

            except Exception as e:
                print(f"❌ [LLM] 错误: {type(e).__name__}: {e}")
                # multimodal 降级
                if image_paths and isinstance(user_content, list):
                    print("⚠️  [LLM] multimodal 失败，降级为纯文字…")
                    messages = [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ]
                    try:
                        self._check_cancel()
                        return self._stream_chat(messages, temperature, max_tokens)
                    except CancelledError:
                        raise
                    except Exception as e2:
                        print(f"❌ [LLM] 降级也失败: {e2}")
                return ""

        print(f"❌ [LLM] 重试{self.max_retries}次失败: {last_err}")
        return ""

    def json_call(
        self,
        system:      str,
        user:        str,
        temperature: float = 0.1,
        max_tokens:  int   = 2048,
    ) -> dict:
        try:
            raw = self.chat(system, user, temperature, max_tokens)
        except CancelledError:
            return {}
        if not raw:
            return {}
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}