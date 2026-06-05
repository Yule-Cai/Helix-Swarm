# core/toolkit.py
import re
import time
import random
import requests
from rich.console import Console
from rich.panel import Panel

console = Console()

class HermesToolkit:
    @staticmethod
    def redact(text: str) -> str:
        """🛡️ 隐私打码器：自动拦截并屏蔽敏感 API Key 和 密码"""
        if not isinstance(text, str): return str(text)
        # 屏蔽类似 sk-xxxx 的 API Key (保留前4位和后4位，中间打码)
        text = re.sub(
            r'(sk-[a-zA-Z0-9]{4})[a-zA-Z0-9]{20,}([a-zA-Z0-9]{4})', 
            r'\1***[REDACTED]***\2', 
            text
        )
        # 屏蔽 JWT Tokens
        text = re.sub(r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', '[JWT_TOKEN_REDACTED]', text)
        # 屏蔽明文密码配置
        text = re.sub(r'(?i)(password|secret|passwd)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', r'\1 = "***"', text)
        return text

    @staticmethod
    def jittered_request(url, payload, headers, timeout=None, max_retries=4):
        """🔄 智能重试引擎：带指数退避和 Jitter 抖动的抗压网络请求"""
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=timeout)
                # 如果遇到 429(限流) 或 5xx(服务器崩溃)，主动抛出异常触发重试
                if response.status_code == 429:
                    raise requests.exceptions.HTTPError(f"HTTP 429: API 速率限制 (Rate Limit)")
                if response.status_code >= 500:
                    raise requests.exceptions.HTTPError(f"HTTP {response.status_code}: 云端服务器异常")
                return response
                
            except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                if attempt == max_retries - 1:
                    raise e # 最后一次还是失败，就认命抛出
                
                # 核心黑科技：指数退避 + 随机抖动 (Jitter)
                # 避免多个 Agent 同时重试导致服务器雪崩
                sleep_time = (1.5 ** attempt) + random.uniform(0.5, 2.0)
                console.print(f"[dim yellow]⚠️ 网络抖动/限流拦截 ({e}) | [bold]{sleep_time:.1f}秒[/]后启动第 {attempt+2}/{max_retries} 次重试...[/]")
                time.sleep(sleep_time)

    @staticmethod
    def diagnose_error(error_msg: str) -> str:
        """🛠️ 智能报错诊断机：把生涩的英文报错翻译成极客修复建议"""
        error_msg = str(error_msg).lower()
        advice = ""
        if "timeout" in error_msg:
            advice = "💡 诊断：大模型思考时间过长，或者网络线路拥堵。如果是本地模型，请检查显卡负载。"
        elif "429" in error_msg or "quota" in error_msg or "insufficient_quota" in error_msg:
            advice = "💡 诊断：当前 API 免费额度已耗尽，或请求频率过高。👉 建议：输入 /local 临时切回本地免费算力。"
        elif "connection refused" in error_msg:
            advice = "💡 诊断：本地 LM Studio / Ollama 服务未启动。👉 建议：请去后台点一下 'Start Server'。"
        elif "401" in error_msg:
            advice = "💡 诊断：API Key 无效或未授权。👉 建议：使用 /set api_key <你的密钥> 重新设置。"
        else:
            advice = "💡 诊断：未知网络或解析异常，请检查终端日志输出。"
            
        return advice

    # ==========================================
    # 🚀 核心新增：实时余额嗅探器 (三核全平台兼容+优雅降级版)
    # ==========================================
    @staticmethod
    def get_api_balance() -> str:
        """嗅探当前 API 的真实余额"""
        from core.config import config
        import requests
        
        active_cfg = config.get_active()
        api_url = active_cfg.get("url", "")
        api_key = active_cfg.get("api_key", "")
        
        if not api_key: return "0"

        try:
            # 1. 针对 OpenRouter
            if "openrouter" in api_url.lower():
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = requests.get("https://openrouter.ai/api/v1/auth/key", headers=headers, timeout=3)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    limit = data.get("limit")
                    usage = data.get("usage", 0)
                    if limit is None: return f"${usage:.4f} (无上限)"
                    return f"${limit - usage:.4f}"
            
            # 2. 本地免费模型
                        # 2. 本地免费模型
            elif "localhost" in api_url or "127.0.0.1" in api_url:
                try:
                    from core.config import config
                    current_lang = str(config.data.get("lang", "zh")).lower().strip()
                except Exception:
                    current_lang = "zh"

                if current_lang.startswith("en"):
                    return "∞ (local compute)"

                return "∞ (本地算力)"
                
            # 3. 🎯 中转站爆破探针
            elif "/v1" in api_url:
                base_url = api_url.split("/v1")[0]
                headers = {"Authorization": f"Bearer {api_key}"}
                
                # 🔪 方案 A: 伪装成 OpenAI 官方客户端
                try:
                    resp_oa = requests.get(f"{base_url}/v1/dashboard/billing/subscription", headers=headers, timeout=2)
                    if resp_oa.status_code == 200 and "hard_limit_usd" in resp_oa.json():
                        return f"${resp_oa.json()['hard_limit_usd']:.3f}"
                except Exception: pass
                
                # 🔪 方案 B: OneAPI 原生底层接口
                try:
                    resp_one = requests.get(f"{base_url}/api/user/self", headers=headers, timeout=2)
                    if resp_one.status_code == 200 and "data" in resp_one.json():
                        data = resp_one.json()["data"]
                        if "quota" in data:
                            return f"${(data['quota'] / 500000.0):.3f}"
                except Exception: pass

                # 🔪 方案 C: 祖传 OpenAI 旧版查账接口
                try:
                    resp_old = requests.get(f"{base_url}/v1/dashboard/billing/credit_grants", headers=headers, timeout=2)
                    if resp_old.status_code == 200 and "total_available" in resp_old.json():
                        return f"${resp_old.json()['total_available']:.3f}"
                except Exception: pass
            
            # 🛡️ 优雅降级：如果所有门都敲不开，不要报丑陋的错，保持 CLI 输出简洁
            return "Web Only"
            
        except Exception:
            return "Offline"