"""
EventBus — 事件总线（Pub/Sub + 链路追踪）
========================================
特性：
  - Pub/Sub 模式：任意组件 publish，任意组件 subscribe
  - 链路追踪：每个事件携带 trace_id / span_id / parent_span_id
  - 异步分发：后台线程分发，不阻塞发布方
  - 历史缓存：最近 N 条事件可回放
  - 过滤订阅：按 event_type 前缀过滤
"""
from __future__ import annotations
import time
import uuid
import queue
import threading
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger("event_bus")


# ── 数据结构 ──────────────────────────────────────────────────

@dataclass
class TraceContext:
    """链路追踪上下文"""
    trace_id:   str = field(default_factory=lambda: uuid.uuid4().hex)
    span_id:    str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    parent_span_id: Optional[str] = None
    depth:      int = 0           # 嵌套深度

    def child(self) -> "TraceContext":
        """派生子 Span，用于嵌套调用"""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=uuid.uuid4().hex[:8],
            parent_span_id=self.span_id,
            depth=self.depth + 1,
        )

    def to_dict(self) -> dict:
        return {
            "trace_id":       self.trace_id,
            "span_id":        self.span_id,
            "parent_span_id": self.parent_span_id,
            "depth":          self.depth,
        }


@dataclass
class Event:
    """事件对象"""
    type:    str                              # 事件类型，如 "agent.coder.start"
    payload: dict = field(default_factory=dict)
    trace:   TraceContext = field(default_factory=TraceContext)
    ts:      float = field(default_factory=time.time)
    id:      str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict:
        return {
            "id":      self.id,
            "type":    self.type,
            "payload": self.payload,
            "trace":   self.trace.to_dict(),
            "ts":      self.ts,
        }


# ── 订阅者 ───────────────────────────────────────────────────

class Subscription:
    def __init__(self, sub_id: str, prefix: str, handler: Callable[[Event], None],
                 queue_size: int = 200):
        self.sub_id  = sub_id
        self.prefix  = prefix            # 只接收 type.startswith(prefix) 的事件
        self.handler = handler
        self.q: queue.Queue = queue.Queue(maxsize=queue_size)
        self._active = True

    def matches(self, event: Event) -> bool:
        return self._active and event.type.startswith(self.prefix)

    def deliver(self, event: Event):
        try:
            self.q.put_nowait(event)
        except queue.Full:
            logger.warning(f"[EventBus] 订阅 {self.sub_id} 队列已满，丢弃事件 {event.type}")

    def cancel(self):
        self._active = False


# ── EventBus 核心 ─────────────────────────────────────────────

class EventBus:
    """
    全局事件总线（单例推荐）

    用法示例：
        bus = EventBus()

        # 订阅
        sub = bus.subscribe("agent.", lambda e: print(e.type, e.payload))

        # 发布（带追踪上下文）
        trace = TraceContext()
        bus.publish("agent.coder.start", {"task": "写贪吃蛇"}, trace=trace)

        # 取消订阅
        bus.unsubscribe(sub)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
        return cls._instance

    def _init(self):
        self._subs:    list[Subscription] = []
        self._subs_lock = threading.RLock()
        self._history: list[Event] = []
        self._history_max = 500
        self._dispatch_q: queue.Queue = queue.Queue(maxsize=2000)
        self._running = True
        self._dispatcher = threading.Thread(target=self._dispatch_loop,
                                            name="EventBus-Dispatcher",
                                            daemon=True)
        self._dispatcher.start()
        logger.info("[EventBus] 已启动")

    # ── 发布 ──────────────────────────────────────────────────

    def publish(self, event_type: str, payload: dict = None,
                trace: TraceContext = None) -> Event:
        """
        发布事件。非阻塞，事件入队后立即返回。

        :param event_type: 事件类型字符串，如 "agent.coder.start"
        :param payload:    任意字典数据
        :param trace:      追踪上下文；不传则自动创建根 Span
        :return:           Event 对象（含 id/trace 信息）
        """
        evt = Event(
            type=event_type,
            payload=payload or {},
            trace=trace or TraceContext(),
        )
        try:
            self._dispatch_q.put_nowait(evt)
        except queue.Full:
            logger.error("[EventBus] 分发队列满，事件丢弃")
        return evt

    # ── 订阅 ──────────────────────────────────────────────────

    def subscribe(self, prefix: str, handler: Callable[[Event], None],
                  queue_size: int = 200) -> Subscription:
        """
        订阅事件。

        :param prefix:     事件类型前缀过滤，如 "agent." 或 "" (全部)
        :param handler:    回调函数 (Event) -> None，在独立线程中调用
        :param queue_size: 内部队列容量
        """
        sub = Subscription(
            sub_id=uuid.uuid4().hex[:8],
            prefix=prefix,
            handler=handler,
            queue_size=queue_size,
        )
        with self._subs_lock:
            self._subs.append(sub)
        # 为该订阅者启动消费线程
        t = threading.Thread(target=self._consume_loop, args=(sub,),
                             name=f"EventBus-Sub-{sub.sub_id}", daemon=True)
        t.start()
        return sub

    def subscribe_queue(self, prefix: str = "", queue_size: int = 200) -> "QueueSubscription":
        """
        队列订阅模式（供 SSE 等阻塞消费使用）。
        调用方自己从 .q 取事件，无需传 handler。
        """
        qs = QueueSubscription(prefix=prefix, queue_size=queue_size)
        with self._subs_lock:
            self._subs.append(qs)
        return qs

    def unsubscribe(self, sub: "Subscription"):
        sub.cancel()
        with self._subs_lock:
            self._subs = [s for s in self._subs if s._active]

    # ── 历史查询 ──────────────────────────────────────────────

    def get_history(self, prefix: str = "", limit: int = 100) -> list[Event]:
        """回放最近事件"""
        with self._subs_lock:
            events = [e for e in self._history if e.type.startswith(prefix)]
        return events[-limit:]

    def get_trace(self, trace_id: str) -> list[Event]:
        """查询某条链路的所有事件，按时间排序"""
        with self._subs_lock:
            events = [e for e in self._history if e.trace.trace_id == trace_id]
        return sorted(events, key=lambda e: e.ts)

    # ── 内部 ──────────────────────────────────────────────────

    def _dispatch_loop(self):
        while self._running:
            try:
                evt = self._dispatch_q.get(timeout=1)
            except queue.Empty:
                continue
            # 存历史
            with self._subs_lock:
                self._history.append(evt)
                if len(self._history) > self._history_max:
                    self._history = self._history[-self._history_max:]
                active_subs = [s for s in self._subs if s.matches(evt)]
            # 分发
            for sub in active_subs:
                sub.deliver(evt)

    def _consume_loop(self, sub: Subscription):
        while sub._active:
            try:
                evt = sub.q.get(timeout=1)
                try:
                    sub.handler(evt)
                except Exception as e:
                    logger.exception(f"[EventBus] 订阅 {sub.sub_id} handler 异常: {e}")
            except queue.Empty:
                continue

    def shutdown(self):
        self._running = False
        with self._subs_lock:
            for s in self._subs:
                s.cancel()


class QueueSubscription(Subscription):
    """队列式订阅，调用方自行 .q.get() 消费事件"""
    def __init__(self, prefix: str = "", queue_size: int = 200):
        super().__init__(
            sub_id=uuid.uuid4().hex[:8],
            prefix=prefix,
            handler=lambda e: None,   # 占位
            queue_size=queue_size,
        )

    def get(self, timeout: float = 5) -> Optional[Event]:
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None


# ── 模块级单例 ────────────────────────────────────────────────
bus = EventBus()


# ── 常用事件类型常量 ──────────────────────────────────────────
class EventType:
    # 系统
    SYSTEM_START    = "system.start"
    SYSTEM_ERROR    = "system.error"
    # 任务生命周期
    TASK_PLAN       = "task.plan"
    TASK_START      = "task.start"
    TASK_DONE       = "task.done"
    TASK_FAILED     = "task.failed"
    TASK_GRAPH_DONE = "task.graph.done"
    # Agent
    AGENT_START     = "agent.start"      # agent.{name}.start
    AGENT_RESULT    = "agent.result"     # agent.{name}.result
    AGENT_ERROR     = "agent.error"      # agent.{name}.error
    # 记忆
    MEMORY_STORE    = "memory.store"
    MEMORY_RECALL   = "memory.recall"
    # 技能库
    SKILL_HIT       = "skill.hit"
    SKILL_CREATED   = "skill.created"
    # 学习
    LEARN_START     = "learn.start"
    LEARN_DONE      = "learn.done"