"""LLM Client — 统一调用，支持重试、JSON输出、图片视觉（multimodal）、取消信号"""
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
        timeout:     int = 600,      # 本地模型生成慢，给足时间
        max_retries: int = 3,
    ):
        self.model_name  = model_name
        self.max_retries = max_retries
        self.timeout     = timeout
        self._cancel_event: threading.Event | None = None   # 由 executor 注入
        self.client = OpenAI(
            base_url=api_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=0,
        )
        print(f"🔌 [LLM] 已连接 {api_url}  model={model_name}  timeout={timeout}s")

    def set_cancel_event(self, event: threading.Event):
        """让 executor 注入取消信号，调用 LLM 前先检查。"""
        self._cancel_event = event

    def _check_cancel(self):
        if self._cancel_event and self._cancel_event.is_set():
            raise CancelledError("任务已取消")

    def chat(
        self,
        system:       str,
        user:         str,
        temperature:  float = 0.7,
        max_tokens:   int   = 2048,
        image_paths:  list[str] | None = None,
    ) -> str:
        self._check_cancel()   # 调用前检查取消

        user_content = _build_user_content(user, image_paths or [])
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content},
        ]

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            self._check_cancel()   # 每次重试前也检查
            try:
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content.strip()

            except CancelledError:
                raise   # 取消信号直接往上抛

            except (APIConnectionError, APITimeoutError) as e:
                last_err = e
                wait = min(10 * attempt, 30)
                print(f"⚠️  [LLM] 超时(第{attempt}次)，{wait}s后重试… ({e})")
                # 等待期间也检查取消
                for _ in range(wait):
                    if self._cancel_event and self._cancel_event.is_set():
                        raise CancelledError("任务已取消（等待重试期间）")
                    time.sleep(1)

            except RateLimitError as e:
                last_err = e
                print("⚠️  [LLM] 限流，5s后重试…")
                time.sleep(5)

            except Exception as e:
                print(f"❌ [LLM] 未知错误: {type(e).__name__}: {e}")
                if image_paths and isinstance(user_content, list):
                    print("⚠️  [LLM] multimodal 失败，降级为纯文字模式重试…")
                    messages = [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ]
                    try:
                        self._check_cancel()
                        resp = self.client.chat.completions.create(
                            model=self.model_name, messages=messages,
                            temperature=temperature, max_tokens=max_tokens,
                        )
                        print("✅ [LLM] 纯文字降级成功")
                        return resp.choices[0].message.content.strip()
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
