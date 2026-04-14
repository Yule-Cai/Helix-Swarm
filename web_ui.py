"""
Multi-Agent OS — 融合版 web_ui.py
架构：v2（Router → TaskGraph → TaskExecutor）
Agent：v1 全集（17个）+ v2 全集（13个）去重合并 = 17个
记忆：v1 MemPalaceManager（ChromaDB）+ EnhancedMemory（错误库+经验蒸馏）
事件：EventBus（Pub/Sub + 链路追踪）
UI接口：v1（610行）完整接口集
"""
from __future__ import annotations
import os, sys, json, uuid, queue, time, re, logging
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, Response, stream_with_context, jsonify

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── v2 核心架构 ───────────────────────────────────────────────
from llm.client          import LLMClient
from core.router         import Router, Intent
from core.task           import TaskPlanner
from core.executor       import TaskExecutor
from core.system_handler import SystemHandler
from core.skill_library  import SkillLibrary
from core.event_bus      import bus, TraceContext, EventType

# ── v1 记忆系统 ───────────────────────────────────────────────
from core.memory          import MemPalaceManager
from core.memory_enhanced import EnhancedMemory
from core.project_memory  import ProjectMemory, GlobalMemoryIndex

# ── v2 Agent 集 ───────────────────────────────────────────────
from agents.coder.agent       import CoderAgent
from agents.tester.agent      import TesterAgent
from agents.viewer.agent      import ViewerAgent
from agents.cleaner.agent     import CleanerAgent
from agents.debugger.agent    import DebuggerAgent
from agents.searcher.agent    import SearcherAgent
from agents.terminal.agent    import TerminalAgent
from agents.reviewer.agent    import ReviewerAgent
from agents.doc.agent         import DocAgent
from agents.writer.agent      import WriterAgent
from agents.skill.agent       import SkillAgent
from agents.browser.agent     import BrowserAgent
from agents.selfimprove.agent import SelfImproveAgent

# ── v1 独有 Agent ─────────────────────────────────────────────
from agents.statemanager.agent import StateManager
from agents.visualizer.agent   import VisualizerAgent
from agents.mcp.agent          import MCPUniversalAgent
from agents.plugin.agent       import GitHubSkillAgent

# ── v2 学习调度器 ─────────────────────────────────────────────
from core.learning_scheduler import LearningScheduler

app = Flask(__name__)

# ── 常量 ──────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE  = os.path.join(BASE_DIR, "history.json")
CONFIG_FILE   = os.path.join(BASE_DIR, "config.json")
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
MAX_QUEUE     = 200
MAX_ITER      = 25
THREAD_POOL   = ThreadPoolExecutor(max_workers=10)

# 支持视觉的图片扩展名
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "logs"),    exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "memory"),  exist_ok=True)

# ── 日志 ─────────────────────────────────────────────────────
metrics_log = logging.getLogger("metrics")
metrics_log.setLevel(logging.INFO)
if not metrics_log.handlers:
    h = RotatingFileHandler(
        os.path.join(BASE_DIR, "logs", "system_metrics.jsonl"),
        maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    metrics_log.addHandler(h)

# ── 配置 ─────────────────────────────────────────────────────
_DEFAULT_CONFIG = {
    # ── LLM 连接配置 ──────────────────────────────────────
    "llm_provider":            "lmstudio",  # lmstudio | api
    "llm_api_url":             "http://localhost:1234/v1",
    "llm_model":               "local-model",
    "llm_timeout":             600,
    # ── 外部 API 配置（provider=api 时生效）──────────────
    "api_key":                 "",           # 你的 API Key
    "api_url":                 "https://api.anthropic.com/v1",
    "api_model":               "claude-sonnet-4-20250514",
    # ── 功能开关 ──────────────────────────────────────────
    "search_enabled":          True,
    "search_source":           "github",
    "max_iterations":          25,
    "learning_enabled":        False,
    "learning_interval_sec":   120,
    "github_token":            "",
    "skill_library_enabled":   True,
    "enhanced_memory_enabled": True,
    "self_improve_enabled":    True,
    "self_improve_modify":     False,
    "auto_discover_agents":    True,
    # ── UI 偏好 ───────────────────────────────────────────
    "ui_language":             "zh",    # zh / en
    "ui_dark_mode":            False,
    "agent_mode_default":      True,    # True=Agent模式, False=普通聊天
    "disabled_agents":         [],      # 被用户关闭的 Agent 列表
    "learning_topics": [
        "python pygame game development",
        "python flask rest api",
        "python cli tool argparse",
        "python async asyncio",
        "python error handling best practices",
        "python unittest pytest",
        "python design patterns",
        "python web scraping beautifulsoup",
        "python data structure algorithm",
        "python file operations pathlib",
    ],
}

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        save_config(_DEFAULT_CONFIG)
        return dict(_DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in _DEFAULT_CONFIG.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(_DEFAULT_CONFIG)

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

_cfg = load_config()

# ── 全局单例 ──────────────────────────────────────────────────
_skill_library  = SkillLibrary()
_global_memory  = MemPalaceManager("global")

# ── 当前执行中的 executor（用于取消）────────────────────────
_current_executor     = None
_current_executor_lock = __import__("threading").Lock()

def _set_current_executor(ex):
    global _current_executor
    with _current_executor_lock:
        _current_executor = ex

def _get_current_executor():
    with _current_executor_lock:
        return _current_executor

# ── LLM 工厂 ─────────────────────────────────────────────────
def _make_llm() -> LLMClient:
    timeout  = int(os.environ.get("LLM_TIMEOUT", str(_cfg.get("llm_timeout", 600))))
    provider = _cfg.get("llm_provider", "lmstudio")

    if provider == "api":
        # 外部 API 模式（OpenAI 兼容格式）
        api_key   = os.environ.get("API_KEY",   _cfg.get("api_key",   ""))
        api_url   = os.environ.get("API_URL",   _cfg.get("api_url",   "https://api.anthropic.com/v1"))
        api_model = os.environ.get("API_MODEL", _cfg.get("api_model", "claude-sonnet-4-20250514"))
        return LLMClient(
            api_url    = api_url,
            model_name = api_model,
            api_key    = api_key if api_key else "not-needed",
            timeout    = timeout,
        )
    else:
        # LM Studio 本地模式（默认）
        return LLMClient(
            api_url    = os.environ.get("LLM_API_URL", _cfg.get("llm_api_url", "http://localhost:1234/v1")),
            model_name = os.environ.get("LLM_MODEL",   _cfg.get("llm_model",   "local-model")),
            timeout    = timeout,
        )

# ── LearningScheduler 懒加载 ──────────────────────────────────
_scheduler: LearningScheduler | None = None

def _get_scheduler() -> LearningScheduler:
    global _scheduler
    if _scheduler is None:
        try:
            llm    = _make_llm()
            mem    = MemPalaceManager("global_knowledge")
            search = SearcherAgent(llm)
            class _MemAdapter:
                def __init__(self, m): self.m = m
                def store_memory(self, content, summary): self.m.store_memory(content, summary)
                def recall(self, q): return self.m.recall(q)
            _scheduler = LearningScheduler(llm, search, _MemAdapter(mem), _cfg)
        except Exception as e:
            print(f"⚠️  LearningScheduler 初始化失败: {e}")
    return _scheduler

# ── 历史记录 ──────────────────────────────────────────────────
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── SSE 工具 ──────────────────────────────────────────────────
def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

# ── Agent 工厂（所有 v1 + v2 Agent 合并）────────────────────
def build_agents(llm: LLMClient) -> dict:
    all_agents = {
        "viewer":       ViewerAgent(),
        "cleaner":      CleanerAgent(),
        "coder":        CoderAgent(llm),
        "tester":       TesterAgent(llm),
        "debugger":     DebuggerAgent(llm),
        "terminal":     TerminalAgent(llm),
        "reviewer":     ReviewerAgent(llm),
        "doc":          DocAgent(llm),
        "writer":       WriterAgent(llm),
        "skill":        SkillAgent(llm),
        "browser":      BrowserAgent(llm),
        "selfimprove":  SelfImproveAgent(llm,
                            allow_modify=_cfg.get("self_improve_modify", False)),
        "statemanager": StateManager(llm),
        "visualizer":   VisualizerAgent(llm),
        "plugin":       GitHubSkillAgent(llm),
    }
    # searcher 始终加入（search_enabled 只控制自主学习，不影响 Agent 任务执行）
    all_agents["searcher"] = SearcherAgent(llm)
    # 过滤掉用户禁用的 Agent
    disabled = set(_cfg.get("disabled_agents", []))
    return {k: v for k, v in all_agents.items() if k not in disabled}

# ── 主页 ─────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# ── 核心运行接口 ──────────────────────────────────────────────
@app.route("/run")
def run():
    user_input = request.args.get("q", "").strip()
    chat_id    = request.args.get("cid", "").strip()
    force_chat = request.args.get("mode", "") == "chat"   # Agent模式关闭时前端传 mode=chat
    if not user_input:
        return Response(sse({"error": "empty"}), mimetype="text/event-stream")

    # 解析前端传来的图片文件名列表（逗号分隔），转为 workspace 内的绝对路径
    imgs_param   = request.args.get("imgs", "").strip()
    image_paths: list[str] = []
    if imgs_param:
        for fname in imgs_param.split(","):
            fname = fname.strip()
            if not fname:
                continue
            full = os.path.join(WORKSPACE_DIR, os.path.basename(fname))
            if os.path.isfile(full) and os.path.splitext(full)[1].lower() in IMAGE_EXTS:
                image_paths.append(full)

    msg_q = queue.Queue(maxsize=MAX_QUEUE)

    def background():
        collected = []

        def emit(role, title, body, kind="card"):
            item = {"role": role, "title": title, "body": body, "kind": kind}
            collected.append(item)
            msg_q.put(item)

        # 为本次请求创建根链路追踪
        root_trace = TraceContext()
        bus.publish(EventType.SYSTEM_START, {
            "user_input": user_input[:100],
            "chat_id":    chat_id,
        }, trace=root_trace)

        try:
            llm    = _make_llm()
            router = Router(llm)
            route  = router.route(user_input, has_images=bool(image_paths))

            # mode=chat 时强制走 CHAT 路径（用户关闭了 Agent 模式）
            if force_chat:
                from core.router import RouteResult
                route = RouteResult(Intent.CHAT, payload=user_input)

            # ── SYSTEM 路径 ───────────────────────────────────
            if route.intent == Intent.SYSTEM:
                handler = SystemHandler(_skill_library, "workspace")
                result  = handler.handle(route.action, route.payload)
                emit("system", "📋 系统查询", result, "chat")
                msg_q.put(None)
                return

            # ── CHAT 路径 ─────────────────────────────────────
            if route.intent == Intent.CHAT:
                mem_ctx = _global_memory.recall(user_input)
                ui_lang = _cfg.get("ui_language", "zh")
                if ui_lang == "en":
                    sys_prompt = ("You are an intelligent assistant for Multi-Agent OS. "
                                  "You can answer questions and have conversations. "
                                  "If the user wants to develop software, tell them to describe their requirements directly. "
                                  "Always respond in English.")
                else:
                    sys_prompt = ("你是 Multi-Agent OS 的智能助手，可以回答问题和闲聊。"
                                  "如果用户想开发软件，告诉他们直接描述需求。")
                if mem_ctx:
                    sys_prompt += (f"\n\nBackground context: {mem_ctx}" if ui_lang == "en"
                                   else f"\n\n参考背景：{mem_ctx}")
                reply = llm.chat(sys_prompt, user_input, temperature=0.7, max_tokens=512,
                                 image_paths=image_paths if image_paths else None)
                if not reply:
                    reply = "⚠️ 模型未返回内容。如果你发送了图片，请确认 LM Studio 中加载的模型支持视觉（Vision），例如 Gemma-4 需要在 LM Studio 里确认 Vision 功能已启用。"
                emit("system", "助手", reply, "chat")
                msg_q.put(None)
                return

            # ── DEV 路径 ─────────────────────────────────────
            # 1. 技能库召回
            skill_hint = ""
            matched_skill = None
            if _cfg.get("skill_library_enabled", True):
                matched_skill = _skill_library.find_relevant_skill(user_input)
                if matched_skill:
                    confidence = matched_skill.get("_confidence", 0)
                    skill_hint = (
                        "已有相关技能参考：" +
                        " → ".join(s.get("agent", "") for s in matched_skill.get("steps", [])[:6])
                    )
                    can_reuse = _skill_library.can_reuse_graph(matched_skill)
                    bus.publish(EventType.SKILL_HIT, {
                        "skill_name": matched_skill["name"],
                        "keywords":   matched_skill.get("keywords", []),
                        "confidence": confidence,
                    }, trace=root_trace)
                    emit("system", "🔮 技能库命中",
                         f"找到相关技能：**{matched_skill['name']}**\n"
                         f"关键词：{', '.join(matched_skill.get('keywords', []))}\n"
                         f"置信度：{confidence:.0%}"
                         + ("  ⚡ 直接复用任务图（跳过规划）" if can_reuse else ""),
                         "info")

            # 2. 记忆召回（ChromaDB 向量 + JSON 双后端）
            mem_ctx = _global_memory.recall(user_input)

            # 3. 初始化增强记忆（项目级）
            enhanced_mem = None

            # 4. 规划任务图
            planner = TaskPlanner(llm)
            ui_lang = _cfg.get("ui_language", "zh")

            # 技能库高置信度命中时直接复用任务图，跳过 Planner LLM 调用
            if matched_skill and _skill_library.can_reuse_graph(matched_skill):
                emit("planner", "⚡ Planner · 跳过规划", "技能库高置信度命中，直接复用历史任务图…", "info")
                graph = planner.rebuild_from_skill(user_input, matched_skill)
                _skill_library.update_usage(matched_skill["id"])
            else:
                emit("planner", "Planner · 规划中", "正在生成结构化任务图…", "running")
                plan_input = user_input
                if image_paths:
                    img_names = ", ".join(os.path.basename(p) for p in image_paths)
                    plan_input += (f"\n\n[Attached images in workspace]: {img_names}"
                                   if ui_lang == "en"
                                   else f"\n\n【附带图片】用户上传了以下图片（已在workspace中）：{img_names}，请在需要时参考这些图片。")
                if ui_lang == "en":
                    plan_input += "\n\n[Language requirement] All agent instructions, code comments, README, and outputs MUST be in English."
                graph = planner.plan(plan_input, skill_hint=skill_hint, memory=_global_memory)

            bus.publish(EventType.TASK_PLAN, {
                "project":  graph.project,
                "task_cnt": len(graph.tasks),
            }, trace=root_trace)
            emit("planner", "Planner · 任务图就绪",
                 f"项目：{graph.project}\n共 {len(graph.tasks)} 个任务\n\n{graph.summary()}",
                 "result")

            # 5. 初始化项目级增强记忆 + MEMORY.md
            enhanced_mem  = None
            project_mem   = None
            if _cfg.get("enhanced_memory_enabled", True):
                enhanced_mem = EnhancedMemory(project_name=graph.project, llm_client=llm)
            # ProjectMemory 始终初始化（不依赖 enhanced_memory_enabled）
            project_mem = ProjectMemory(graph.project, llm_client=llm)

            # 把全局记忆注入 Planner（补充 search_structured 的覆盖面）
            global_mem_ctx = GlobalMemoryIndex().load()
            if global_mem_ctx and not mem_ctx:
                graph.skill_hint = (graph.skill_hint + "\n\n" + global_mem_ctx).strip()

            # 6. 构建所有 Agent
            agents = build_agents(llm)

            # 7. 执行任务图
            executor = TaskExecutor(agents, msg_q, WORKSPACE_DIR,
                                    enhanced_memory=enhanced_mem,
                                    planner=planner,
                                    memory=_global_memory,
                                    project_memory=project_mem,
                                    llm=llm)
            _set_current_executor(executor)
            success  = executor.execute(graph, trace=root_trace)
            _set_current_executor(None)

            # 8. 封装技能
            if success and _cfg.get("skill_library_enabled", True):
                try:
                    steps = [{"agent": t.agent, "instruction": t.instruction,
                               "result": t.result[:200]}
                             for t in graph.tasks if t.result]
                    _skill_library.create_skill(
                        user_input, steps,
                        graph.tasks[-1].result if graph.tasks else "", llm,
                        task_graph=graph,   # ← 存储完整任务图
                    )
                    bus.publish(EventType.SKILL_CREATED, {
                        "project": graph.project,
                    }, trace=root_trace)
                    emit("system", "✨ 技能已封装",
                         "本次任务已存入技能库，下次类似需求可直接复用。", "info")
                except Exception as e:
                    print(f"⚠️  技能封装失败: {e}")

            # 9. 存入全局记忆（经验蒸馏已由 executor 异步处理，无需重复）
            if _cfg.get("enhanced_memory_enabled", True):
                try:
                    summary = f"{'成功' if success else '失败'}：{user_input[:60]}"
                    _global_memory.store_memory(user_input, summary)
                except Exception:
                    pass

        except Exception as e:
            bus.publish(EventType.SYSTEM_ERROR, {"error": str(e)}, trace=root_trace)
            msg_q.put({"role": "system", "title": "系统错误", "body": str(e), "kind": "error"})
        finally:
            if chat_id and collected:
                history = load_history()
                for entry in history:
                    if entry["id"] == chat_id:
                        entry["messages"].append({"role": "user", "body": user_input})
                        entry["messages"].extend(collected)
                        save_history(history)
                        break
            msg_q.put(None)

    THREAD_POOL.submit(background)

    def generate():
        while True:
            try:
                item = msg_q.get(timeout=5)
            except queue.Empty:
                yield ": heartbeat\n\n"
                continue
            if item is None:
                yield sse({"kind": "done"})
                break
            if item.get("kind") == "heartbeat":
                yield ": heartbeat\n\n"
            else:
                yield sse(item)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache",
                 "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"},
    )

# ── 历史记录接口 ──────────────────────────────────────────────
@app.route("/history", methods=["GET", "POST"])
def manage_history():
    if request.method == "GET":
        return jsonify(load_history())
    body    = request.get_json(silent=True) or {}
    history = load_history()
    entry   = {
        "id":         str(uuid.uuid4()),
        "title":      body.get("title", "新对话")[:40],
        "messages":   body.get("messages", []),
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    history.insert(0, entry)
    save_history(history)
    return jsonify(entry)

@app.route("/history/<cid>", methods=["GET", "PUT", "DELETE"])
def history_item(cid):
    history = load_history()
    if request.method == "DELETE":
        save_history([h for h in history if h["id"] != cid])
        return jsonify({"ok": True})
    entry = next((h for h in history if h["id"] == cid), None)
    if not entry:
        return jsonify({"error": "not found"}), 404
    if request.method == "GET":
        return jsonify(entry)
    body = request.get_json(silent=True) or {}
    if "title"    in body: entry["title"]    = body["title"][:40]
    if "messages" in body: entry["messages"] = body["messages"]
    save_history(history)
    return jsonify(entry)

# ── 配置接口 ──────────────────────────────────────────────────
@app.route("/config", methods=["GET", "POST"])
def manage_config():
    global _cfg
    if request.method == "GET":
        return jsonify(_cfg)
    body = request.get_json(silent=True) or {}
    for k in _DEFAULT_CONFIG:
        if k in body:
            _cfg[k] = body[k]
    save_config(_cfg)
    return jsonify(_cfg)

# ── 文件上传 ──────────────────────────────────────────────────
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "没有找到文件"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "文件名为空"}), 400
    safe_name = secure_filename(f.filename)
    f.save(os.path.join(WORKSPACE_DIR, safe_name))
    ext = os.path.splitext(safe_name)[1].lower()
    is_image = ext in IMAGE_EXTS
    return jsonify({"ok": True, "filename": safe_name, "is_image": is_image})

# ── Workspace 目录树 ──────────────────────────────────────────
@app.route("/workspace")
def workspace_tree():
    def tree(path, prefix=""):
        if not os.path.exists(path):
            return "(空)"
        result = ""
        items  = sorted(
            i for i in os.listdir(path)
            if not i.startswith(".") and i not in ("__pycache__", "system_metrics.jsonl")
        )
        for idx, item in enumerate(items):
            last      = idx == len(items) - 1
            connector = "└── " if last else "├── "
            result   += f"{prefix}{connector}{item}\n"
            full      = os.path.join(path, item)
            if os.path.isdir(full):
                result += tree(full, prefix + ("    " if last else "│   "))
        return result or "(空)"
    return jsonify({"tree": tree(WORKSPACE_DIR)})

# ── 技能库接口 ────────────────────────────────────────────────
@app.route("/skills")
def list_skills():
    return jsonify(_skill_library.list_skills())

@app.route("/skills/<skill_id>", methods=["DELETE"])
def delete_skill(skill_id):
    return jsonify({"ok": _skill_library.delete_skill(skill_id)})

# ── 错误解决方案库（v1 特色接口）────────────────────────────
@app.route("/error-solutions")
def error_solutions():
    mem = EnhancedMemory("_tmp")
    return jsonify(mem.list_error_solutions())

# ── 自我改进日志（v1 特色接口）───────────────────────────────
@app.route("/improve-logs")
def improve_logs():
    log_file = os.path.join(BASE_DIR, "improvement_log.json")
    if not os.path.exists(log_file):
        return jsonify([])
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify([])

# ── EventBus 接口 ─────────────────────────────────────────────
@app.route("/events/stream")
def events_stream():
    """SSE：订阅所有事件（实时链路监控）"""
    prefix = request.args.get("prefix", "")
    sub    = bus.subscribe_queue(prefix=prefix, queue_size=500)

    def generate():
        try:
            while True:
                evt = sub.get(timeout=5)
                if evt is None:
                    yield ": heartbeat\n\n"
                    continue
                yield f"data: {json.dumps(evt.to_dict(), ensure_ascii=False)}\n\n"
        finally:
            bus.unsubscribe(sub)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.route("/events/history")
def events_history():
    """查询事件历史"""
    prefix = request.args.get("prefix", "")
    limit  = int(request.args.get("limit", 100))
    events = bus.get_history(prefix=prefix, limit=limit)
    return jsonify([e.to_dict() for e in events])

@app.route("/events/trace/<trace_id>")
def event_trace(trace_id):
    """查询一条链路的完整事件序列"""
    events = bus.get_trace(trace_id)
    return jsonify([e.to_dict() for e in events])

# ── 自主学习接口 ──────────────────────────────────────────────
@app.route("/learning/start", methods=["POST"])
def learning_start():
    _cfg["learning_enabled"] = True
    save_config(_cfg)
    s = _get_scheduler()
    return jsonify(s.start() if s else {"ok": False, "msg": "调度器初始化失败"})

@app.route("/learning/stop", methods=["POST"])
def learning_stop():
    _cfg["learning_enabled"] = False
    save_config(_cfg)
    s = _get_scheduler()
    return jsonify(s.stop() if s else {"ok": False, "msg": "调度器未运行"})

@app.route("/task/cancel", methods=["POST"])
def task_cancel():
    """取消当前正在执行的任务图。"""
    ex = _get_current_executor()
    if ex:
        ex.cancel()
        return jsonify({"ok": True, "msg": "取消信号已发送，任务将在当前步骤完成后停止"})
    return jsonify({"ok": False, "msg": "当前没有正在执行的任务"})

@app.route("/learning/reset", methods=["POST"])
def learning_reset():
    """清空学习进度，下次启动从第一个主题重新开始。"""
    s = _get_scheduler()
    return jsonify(s.reset_progress() if s else {"ok": False, "msg": "调度器未初始化"})

@app.route("/learning/status")
def learning_status():
    s = _get_scheduler()
    return jsonify(s.get_status() if s else {"state": "unavailable"})

@app.route("/learning/reports")
def learning_reports():
    s = _get_scheduler()
    return jsonify(s.list_reports() if s else [])

@app.route("/learning/reports/<filename>")
def learning_report_detail(filename):
    s = _get_scheduler()
    if not s:
        return jsonify({"error": "调度器未初始化"}), 404
    data = s.get_report(filename)
    return jsonify(data) if data else (jsonify({"error": "不存在"}), 404)

@app.route("/learning/logs")
def learning_logs_sse():
    """SSE：实时推送学习日志"""
    s = _get_scheduler()
    if not s:
        return Response(sse({"error": "调度器未初始化"}), mimetype="text/event-stream")
    sub_q = s.subscribe()

    def generate():
        try:
            while True:
                try:
                    entry = sub_q.get(timeout=5)
                    yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            s.unsubscribe(sub_q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache",
                 "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"},
    )

@app.route("/learning/logs/recent")
def learning_logs_recent():
    s = _get_scheduler()
    return jsonify(s.get_recent_logs(50) if s else [])

# ── Agent 注册表接口 ──────────────────────────────────────────
# 英文描述
_AGENT_DESC_EN = {
    "viewer":       "Scan workspace directory structure",
    "cleaner":      "Clean up residual files or directories",
    "searcher":     "GitHub search: API docs, error solutions, code references",
    "terminal":     "Execute terminal commands (pip install, compile, etc.)",
    "coder":        "Write or modify code files",
    "tester":       "Run code to verify functionality, analyze errors",
    "debugger":     "Deep error analysis, output fix plan",
    "reviewer":     "Review code quality, add comments",
    "doc":          "Generate README.md documentation",
    "writer":       "Write novel/story content",
    "skill":        "Query skill library, recommend existing templates",
    "browser":      "Fetch web page content",
    "selfimprove":  "Analyze system weaknesses, output improvement suggestions",
    "statemanager": "Novel scene recorder: extract character states to JSON",
    "visualizer":   "Generate Mermaid flowcharts or architecture diagrams",
    "mcp":          "MCP universal agent: connect to any MCP Server",
    "plugin":       "Plugin agent: wrap third-party GitHub projects as capabilities",
}

@app.route("/agents")
def list_agents():
    """返回所有已注册 Agent 及其说明"""
    from core.task import TaskPlanner
    registry = TaskPlanner.AGENT_REGISTRY
    disabled = set(_cfg.get("disabled_agents", []))
    lang     = _cfg.get("ui_language", "zh")
    return jsonify({
        name: {
            "desc":    _AGENT_DESC_EN.get(name, desc) if lang == "en" else desc,
            "enabled": name not in disabled,
        }
        for name, desc in registry.items()
    })

@app.route("/agents/toggle", methods=["POST"])
def toggle_agent():
    """启用或禁用某个 Agent。"""
    body    = request.get_json(silent=True) or {}
    name    = body.get("name", "").strip()
    enabled = body.get("enabled", True)
    if not name:
        return jsonify({"error": "缺少 name 参数"}), 400
    disabled = list(_cfg.get("disabled_agents", []))
    if enabled and name in disabled:
        disabled.remove(name)
    elif not enabled and name not in disabled:
        disabled.append(name)
    _cfg["disabled_agents"] = disabled
    save_config(_cfg)
    return jsonify({"ok": True, "name": name, "enabled": enabled})

# ── 系统状态 ──────────────────────────────────────────────────
@app.route("/status")
def system_status():
    import platform
    handler = SystemHandler(_skill_library, "workspace")
    return jsonify({
        "version":     "merged-v1v2",
        "python":      platform.python_version(),
        "skills":      len(_skill_library.list_skills()),
        "agents":      17,
        "event_bus":   "running",
        "memory_backend": "chromadb+json",
        "platform":    platform.system(),
    })

# ── 启动 ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🌐 Multi-Agent OS 融合版启动…")
    print("📦 架构: v2 TaskGraph | Agent: 17个 | 记忆: ChromaDB+JSON | EventBus: 已启动")
    print("📌 http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False, threaded=True, port=5000)