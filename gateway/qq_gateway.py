"""
QQ 网关 — 基于 NapCatQQ / OneBot v11 协议
让 Helix Swarm 通过 QQ 接收指令、回复结果。

架构：
  NapCatQQ（跑着你的 QQ 号）
       ↕  WebSocket / HTTP
  本网关（Python）
       ↕  HTTP
  Helix Swarm（web_ui.py）

支持两种连接模式（二选一）：
  Mode A — 反向 WS（推荐）：NapCat 主动连接本网关的 WS Server
  Mode B — 正向 WS：        本网关主动连接 NapCat 的 WS Server

安装依赖：
  pip install websockets aiohttp

启动（先启动 Helix Swarm，再启动本网关）：
  python gateway/qq_gateway.py              # 反向 WS 模式（默认）
  python gateway/qq_gateway.py --mode forward  # 正向 WS 模式
"""
from __future__ import annotations
import asyncio
import json
import sys
import argparse
import threading
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ── 配置 ─────────────────────────────────────────────────────

def load_config() -> dict:
    cfg_path = ROOT / "config.json"
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

CFG = load_config()

# NapCat HTTP API 地址（用于发送消息）
NAPCAT_HTTP_URL  = CFG.get("qq_napcat_http",    "http://127.0.0.1:3000")
# NapCat 正向 WS 地址（Mode B 用）
NAPCAT_WS_URL    = CFG.get("qq_napcat_ws",      "ws://127.0.0.1:3001")
# 本网关反向 WS 监听地址（Mode A 用）
GATEWAY_WS_HOST  = CFG.get("qq_gateway_host",   "127.0.0.1")
GATEWAY_WS_PORT  = CFG.get("qq_gateway_port",   6700)
# NapCat access token（在 NapCat WebUI 里设置）
ACCESS_TOKEN     = CFG.get("qq_access_token",   "")
# 白名单：只响应这些 QQ 号（空列表 = 响应所有人）
ALLOWLIST        = set(str(x) for x in CFG.get("qq_allowlist", []))
# Helix Swarm 地址
HELIX_URL        = CFG.get("qq_helix_url",      "http://127.0.0.1:5000")
# Agent 模式还是 Chat 模式（True=多 Agent 规划，False=直接 LLM 对话）
AGENT_MODE       = CFG.get("qq_agent_mode",     False)


# ── Helix Swarm 客户端 ───────────────────────────────────────

class HelixClient:
    """
    向 Helix Swarm 的 /run SSE 接口发送消息，阻塞等待最终结果。
    在独立线程中调用（不阻塞异步事件循环）。
    """

    def __init__(self, base_url: str = HELIX_URL, agent_mode: bool = AGENT_MODE):
        self.base_url   = base_url.rstrip("/")
        self.agent_mode = agent_mode

    def ask(self, message: str, timeout: int = 180) -> str:
        url    = f"{self.base_url}/run"
        params = {
    "q":    message,
    "mode": "" if self.agent_mode else "chat",
}
        last_body   = ""
        card_chunks = []

        try:
            with requests.get(url, params=params, stream=True,
                              timeout=timeout) as resp:
                for raw in resp.iter_lines():
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="ignore")
                    if not line.startswith("data: "):
                        continue
                    try:
                        print(f"[DEBUG SSE] {line}")
                        data = json.loads(line[6:])
                        role = data.get("role", "")
                        body = data.get("body", "")
                        if role in ("assistant", "system") and body:
                            last_body = body
                        elif role in ("card", "info") and body:
                            card_chunks.append(body)
                    except json.JSONDecodeError:
                        pass
        except requests.exceptions.ReadTimeout:
            return "（响应超时，任务可能仍在后台执行）"
        except Exception as e:
            return f"（连接 Helix Swarm 失败：{e}）"

        return last_body or "\n".join(card_chunks) or "（任务已提交，暂无文字结果）"


# ── OneBot v11 消息发送 ──────────────────────────────────────

def send_private_msg(user_id: str, message: str):
    """
    通过 NapCat HTTP API 发送私聊消息。
    长消息自动分段（QQ 单条限制约 4500 字）。
    """
    headers = {}
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"

    segments = _split_message(message, max_len=4000)
    for i, seg in enumerate(segments):
        prefix = f"[{i+1}/{len(segments)}]\n" if len(segments) > 1 else ""
        payload = {
            "user_id": int(user_id),
            "message": prefix + seg,
        }
        try:
            r = requests.post(
                f"{NAPCAT_HTTP_URL}/send_private_msg",
                json=payload,
                headers=headers,
                timeout=10,
            )
            data = r.json()
            if data.get("retcode", 0) != 0:
                print(f"⚠️  [QQ] 发送失败: {data}")
        except Exception as e:
            print(f"⚠️  [QQ] HTTP 发送异常: {e}")
        if len(segments) > 1:
            time.sleep(0.4)  # 分段间隔，避免风控


def _split_message(text: str, max_len: int = 4000) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts = []
    while text:
        parts.append(text[:max_len])
        text = text[max_len:]
    return parts


# ── 消息处理核心 ─────────────────────────────────────────────

_helix = HelixClient()
# 防止同一个用户的重复消息并发处理
_processing: set[str] = set()


def handle_message(event: dict):
    """
    处理 OneBot v11 message 事件（在独立线程中运行）。
    目前只处理私聊消息（message_type == "private"）。
    群消息需要 @机器人 才响应，避免刷屏。
    """
    msg_type = event.get("message_type", "")
    user_id  = str(event.get("user_id", ""))
    group_id = str(event.get("group_id", ""))

    # 提取纯文本内容
    raw_message = event.get("raw_message", "")
    if not raw_message:
        # 兼容 message 数组格式
        segments = event.get("message", [])
        if isinstance(segments, list):
            raw_message = "".join(
                seg.get("data", {}).get("text", "")
                for seg in segments
                if seg.get("type") == "text"
            )
        elif isinstance(segments, str):
            raw_message = segments

    content = raw_message.strip()
    if not content:
        return

    # 白名单过滤
    if ALLOWLIST and user_id not in ALLOWLIST:
        return

    # 群消息：只响应 @机器人 的消息，去掉 @ 后处理
    if msg_type == "group":
        self_id = str(event.get("self_id", ""))
        at_self = f"[CQ:at,qq={self_id}]"
        if at_self not in raw_message:
            return
        content = content.replace(at_self, "").strip()
        if not content:
            return

    reply_target = user_id  # 私聊回到用户，群聊也回到用户私聊（简单实现）

    # 防并发：同一用户同时只处理一条
    if reply_target in _processing:
        send_private_msg(reply_target, "⏳ 上一条消息还在处理中，请稍候…")
        return
    _processing.add(reply_target)

    print(f"📨 [QQ] {user_id} ({msg_type}): {content}")

    def _worker():
        try:
            send_private_msg(reply_target, "⏳ Helix Swarm 处理中，请稍候…")
            result = _helix.ask(content)
            send_private_msg(reply_target, result)
        finally:
            _processing.discard(reply_target)

    threading.Thread(target=_worker, daemon=True).start()


# ── Mode A：反向 WebSocket 服务器（推荐）───────────────────

async def reverse_ws_server():
    """
    启动 WebSocket 服务器，等待 NapCat 连接进来。
    NapCat 配置：网络配置 → 新建 → WebSocket 客户端
                 URL = ws://127.0.0.1:6700
    """
    try:
        import websockets
    except ImportError:
        print("❌ 请先安装：pip install websockets")
        return

    async def handler(ws):
        remote = ws.remote_address
        print(f"✅ [QQ] NapCat 已连接: {remote}")
        try:
            async for raw in ws:
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                post_type = event.get("post_type", "")
                if post_type == "message":
                    # 在线程池里跑，不阻塞 WS 接收
                    loop = asyncio.get_event_loop()
                    loop.run_in_executor(None, handle_message, event)
                elif post_type == "meta_event":
                    # 心跳，忽略
                    pass
        except Exception as e:
            print(f"⚠️  [QQ] WS 连接断开: {e}")
        finally:
            print(f"🔌 [QQ] NapCat 断开: {remote}")

    print(f"🚀 [QQ] 反向 WS 服务器启动 ws://{GATEWAY_WS_HOST}:{GATEWAY_WS_PORT}")
    print(f"   请在 NapCat WebUI → 网络配置 → 新建 → WebSocket 客户端")
    print(f"   URL 填：ws://{GATEWAY_WS_HOST}:{GATEWAY_WS_PORT}")
    print()

    async with websockets.serve(handler, GATEWAY_WS_HOST, GATEWAY_WS_PORT):
        await asyncio.Future()  # 永远运行


# ── Mode B：正向 WebSocket 客户端 ───────────────────────────

async def forward_ws_client():
    """
    主动连接 NapCat 的 WS 服务器。
    NapCat 配置：网络配置 → 新建 → WebSocket 服务端，端口 3001
    """
    try:
        import websockets
    except ImportError:
        print("❌ 请先安装：pip install websockets")
        return

    headers = {}
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"

    print(f"🔌 [QQ] 正在连接 NapCat: {NAPCAT_WS_URL}")

    while True:
        try:
            async with websockets.connect(
                NAPCAT_WS_URL,
                additional_headers=headers,
            ) as ws:
                print(f"✅ [QQ] 已连接 NapCat WS")
                async for raw in ws:
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if event.get("post_type") == "message":
                        loop = asyncio.get_event_loop()
                        loop.run_in_executor(None, handle_message, event)
        except Exception as e:
            print(f"⚠️  [QQ] WS 断开，5 秒后重连: {e}")
            await asyncio.sleep(5)


# ── 注册到 Flask（可选，不单独启动时用）────────────────────

def register_routes(app):
    """
    把 QQ 网关的 HTTP Polling 回调注册到现有 Flask app。
    适合不想单独跑网关进程的场景。

    NapCat 配置：网络配置 → 新建 → HTTP 上报
                 URL = http://127.0.0.1:5000/qq/callback
    """
    from flask import request, jsonify

    @app.route("/qq/callback", methods=["POST"])
    def qq_callback():
        # 验证 token
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if ACCESS_TOKEN and token != ACCESS_TOKEN:
            return jsonify({"code": 403}), 403

        try:
            event = request.get_json(force=True) or {}
        except Exception:
            return jsonify({"code": 400}), 400

        if event.get("post_type") == "message":
            threading.Thread(
                target=handle_message, args=(event,), daemon=True
            ).start()

        return jsonify({"code": 0})

    print("✅ [QQ] HTTP 回调路由已注册：POST /qq/callback")


# ── 入口 ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Helix Swarm QQ 网关")
    parser.add_argument(
        "--mode",
        choices=["reverse", "forward", "http"],
        default="reverse",
        help=(
            "连接模式：\n"
            "  reverse — 反向 WS，NapCat 连接本网关（推荐）\n"
            "  forward — 正向 WS，本网关连接 NapCat\n"
            "  http    — HTTP 上报，配合 web_ui.py 使用"
        ),
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  Helix Swarm QQ 网关")
    print("=" * 50)
    print(f"  模式：{args.mode}")
    print(f"  Helix Swarm：{HELIX_URL}")
    print(f"  NapCat HTTP：{NAPCAT_HTTP_URL}")
    if ALLOWLIST:
        print(f"  白名单：{', '.join(ALLOWLIST)}")
    else:
        print("  白名单：未设置（响应所有人）")
    print()

    if args.mode == "reverse":
        asyncio.run(reverse_ws_server())
    elif args.mode == "forward":
        asyncio.run(forward_ws_client())
    elif args.mode == "http":
        print("HTTP 模式需要配合 web_ui.py 使用。")
        print("请在 web_ui.py 中添加：")
        print("  from gateway.qq_gateway import register_routes")
        print("  register_routes(app)")
        print()
        print("然后在 NapCat WebUI 设置 HTTP 上报 URL：")
        print(f"  http://你的IP:5000/qq/callback")


if __name__ == "__main__":
    main()
