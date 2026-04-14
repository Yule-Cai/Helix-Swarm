"""
微信网关 — 让 Helix Swarm 通过微信接收指令、回复结果

支持两种接入方式：
  1. 企业微信（推荐）：官方 API，稳定，不会封号
     需要：企业微信账号 + 应用 corpid/corpsecret/agentid
     
  2. 个人微信（itchat）：扫码登录，有封号风险，适合个人玩
     需要：pip install itchat-uos

用法：
  python gateway/wechat_gateway.py --mode wecom   # 企业微信
  python gateway/wechat_gateway.py --mode itchat  # 个人微信

或者在 web_ui.py 启动时自动拉起（见 README）。
"""
from __future__ import annotations
import os
import sys
import json
import time
import threading
import argparse
import requests
from pathlib import Path

# 把项目根目录加入 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ── 配置加载 ─────────────────────────────────────────────────

def load_config() -> dict:
    cfg_path = ROOT / "config.json"
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ── 请求 Helix Swarm 本地 HTTP 接口 ─────────────────────────

class HelixClient:
    """
    通过 HTTP SSE 向 Helix Swarm 发送任务，收集完整响应后返回文本。
    """

    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self.base_url = base_url.rstrip("/")

    def ask(self, message: str, timeout: int = 120) -> str:
        """
        发送消息，阻塞等待 SSE 流结束，返回拼接后的纯文本结果。
        """
        url     = f"{self.base_url}/run"
        params  = {"message": message, "agent_mode": "false"}
        result  = []
        last_body = ""

        try:
            with requests.get(url, params=params, stream=True,
                              timeout=timeout) as resp:
                for raw in resp.iter_lines():
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="ignore")
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            body = data.get("body", "")
                            role = data.get("role", "")
                            if role == "assistant" and body:
                                last_body = body
                            elif role in ("card", "info") and body:
                                result.append(body)
                        except json.JSONDecodeError:
                            pass
        except requests.exceptions.ReadTimeout:
            return "（响应超时，任务可能仍在后台执行）"
        except Exception as e:
            return f"（连接 Helix Swarm 失败：{e}）"

        # 优先返回 assistant 最后一条，其次拼接 card 内容
        if last_body:
            return last_body
        return "\n".join(result) if result else "（任务已提交，无文字结果）"


# ═══════════════════════════════════════════════════════════
# 模式 1：企业微信网关
# ═══════════════════════════════════════════════════════════

class WeComGateway:
    """
    企业微信应用消息网关。
    需要在企业微信管理后台创建"自建应用"并开启接收消息功能。

    config.json 新增字段：
      "wecom_corpid":     "ww...",
      "wecom_corpsecret": "xxx",
      "wecom_agentid":    1000001,
      "wecom_token":      "xxx",      # 企业微信回调验证 token
      "wecom_aeskey":     "xxx"       # 企业微信回调加解密 key
    """

    TOKEN_URL    = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    SEND_URL     = "https://qyapi.weixin.qq.com/cgi-bin/message/send"

    def __init__(self, cfg: dict):
        self.corpid      = cfg.get("wecom_corpid", "")
        self.corpsecret  = cfg.get("wecom_corpsecret", "")
        self.agentid     = cfg.get("wecom_agentid", 0)
        self.helix       = HelixClient()
        self._token      = ""
        self._token_exp  = 0
        self._lock       = threading.Lock()

    # ── AccessToken 管理（自动刷新）──────────────────────────

    def _get_token(self) -> str:
        with self._lock:
            if time.time() < self._token_exp - 60:
                return self._token
            resp = requests.get(self.TOKEN_URL, params={
                "corpid": self.corpid, "corpsecret": self.corpsecret
            }, timeout=10).json()
            self._token     = resp.get("access_token", "")
            self._token_exp = time.time() + resp.get("expires_in", 7200)
            return self._token

    # ── 发送消息给指定用户 ───────────────────────────────────

    def send(self, to_user: str, content: str):
        """
        发送文本消息。content 超过 2048 字时自动截断（企业微信限制）。
        """
        token = self._get_token()
        if not token:
            print("❌ [WeCom] 获取 AccessToken 失败")
            return

        # 企业微信文本消息限制 2048 字符
        if len(content) > 2000:
            content = content[:2000] + "\n…（内容过长已截断）"

        payload = {
            "touser":  to_user,
            "msgtype": "text",
            "agentid": self.agentid,
            "text":    {"content": content},
        }
        resp = requests.post(
            self.SEND_URL,
            params={"access_token": token},
            json=payload,
            timeout=10,
        ).json()
        if resp.get("errcode", 0) != 0:
            print(f"⚠️  [WeCom] 发送失败: {resp}")

    # ── 处理回调消息（需配合 Flask 路由使用）────────────────

    def handle_callback(self, from_user: str, content: str):
        """
        处理用户发来的消息，异步调用 Helix 并回复。
        在独立线程中运行，不阻塞 webhook 响应。
        """
        def _worker():
            print(f"📨 [WeCom] {from_user}: {content}")
            self.send(from_user, "⏳ 处理中，请稍候…")
            result = self.helix.ask(content)
            self.send(from_user, result)

        threading.Thread(target=_worker, daemon=True).start()

    # ── 启动（注册 Flask 路由）──────────────────────────────

    def register_routes(self, app):
        """
        将企业微信回调路由注册到现有 Flask app。
        在 web_ui.py 中调用：gateway.register_routes(app)
        """
        from flask import request, make_response

        @app.route("/wechat/wecom", methods=["GET", "POST"])
        def wecom_callback():
            # GET：企业微信验证 URL 有效性
            if request.method == "GET":
                # 简单回显 echostr（生产环境需做签名验证）
                return request.args.get("echostr", "ok")

            # POST：接收消息
            try:
                import xml.etree.ElementTree as ET
                xml_data = request.data
                root     = ET.fromstring(xml_data)
                msg_type = root.findtext("MsgType", "")
                from_user = root.findtext("FromUserName", "")
                content   = ""
                if msg_type == "text":
                    content = root.findtext("Content", "").strip()
                elif msg_type == "voice":
                    content = root.findtext("Recognition", "").strip()  # 语音转文字
                if content:
                    self.handle_callback(from_user, content)
            except Exception as e:
                print(f"⚠️  [WeCom] 解析回调失败: {e}")
            return make_response("", 200)

        print("✅ [WeCom] 路由已注册：POST /wechat/wecom")


# ═══════════════════════════════════════════════════════════
# 模式 2：个人微信网关（itchat）
# ═══════════════════════════════════════════════════════════

class ItchatGateway:
    """
    个人微信网关（基于 itchat-uos）。
    ⚠️  风险提示：个人微信不提供官方 API，使用第三方工具有被封号风险。
                  建议只在测试/个人用途场景使用，不要用主号。

    安装：pip install itchat-uos

    config.json 新增字段（可选）：
      "itchat_hotreload": true,    # 是否保存登录状态，下次免扫码
      "itchat_allowlist": []       # 白名单：只响应这些好友的消息（空=全部响应）
    """

    def __init__(self, cfg: dict):
        self.hotreload = cfg.get("itchat_hotreload", True)
        self.allowlist = set(cfg.get("itchat_allowlist", []))
        self.helix     = HelixClient()

    def start(self):
        try:
            import itchat
            from itchat.content import TEXT
        except ImportError:
            print("❌ [itchat] 未安装 itchat-uos，请运行：pip install itchat-uos")
            return

        @itchat.msg_register(TEXT)
        def handle_text(msg):
            sender = msg["FromUserName"]
            name   = msg["User"].get("NickName", sender)
            content = msg["Content"].strip()

            # 白名单过滤
            if self.allowlist and name not in self.allowlist:
                return

            # 过滤掉自己发的消息
            if msg.get("ToUserName") == "filehelper":
                return

            print(f"📨 [itchat] {name}: {content}")
            # 先回复"处理中"
            itchat.send("⏳ Helix Swarm 处理中，请稍候…", toUserName=sender)

            # 异步调用 Helix
            def _worker():
                result = self.helix.ask(content)
                # itchat 单条消息限制约 2000 字
                if len(result) > 1800:
                    # 分段发送
                    chunks = [result[i:i+1800] for i in range(0, len(result), 1800)]
                    for i, chunk in enumerate(chunks):
                        prefix = f"[{i+1}/{len(chunks)}] " if len(chunks) > 1 else ""
                        itchat.send(prefix + chunk, toUserName=sender)
                        time.sleep(0.5)
                else:
                    itchat.send(result, toUserName=sender)

            threading.Thread(target=_worker, daemon=True).start()

        print("📱 [itchat] 请扫描二维码登录个人微信…")
        itchat.auto_login(hotReload=self.hotreload)
        print("✅ [itchat] 登录成功，开始监听消息")
        itchat.run(blockThread=True)


# ═══════════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Helix Swarm 微信网关")
    parser.add_argument(
        "--mode", choices=["wecom", "itchat"], default="itchat",
        help="接入模式：wecom（企业微信）或 itchat（个人微信）"
    )
    parser.add_argument(
        "--helix-url", default="http://127.0.0.1:5000",
        help="Helix Swarm 的 HTTP 地址（默认 http://127.0.0.1:5000）"
    )
    args = parser.parse_args()

    cfg = load_config()

    if args.mode == "itchat":
        print("🚀 启动个人微信网关（itchat 模式）")
        print("   先确保 Helix Swarm 已运行：python web_ui.py")
        print()
        gw = ItchatGateway(cfg)
        gw.start()

    elif args.mode == "wecom":
        print("🚀 企业微信模式需要配合 web_ui.py 使用")
        print("   请在 web_ui.py 中调用：")
        print("     from gateway.wechat_gateway import WeComGateway")
        print("     WeComGateway(cfg).register_routes(app)")
        print()
        print("   并在企业微信后台将回调 URL 设置为：")
        print("     http://你的公网IP:5000/wechat/wecom")


if __name__ == "__main__":
    main()
