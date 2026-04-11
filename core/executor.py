"""
TaskExecutor — 任务执行引擎
新增：
  1. MEMORY.md 注入：每个 Agent 的 system prompt 头部注入项目记忆
  2. 并发执行：同一批无依赖的 task 用 ThreadPoolExecutor 并发跑
  3. 取消机制：cancel() 设置 Event，注入 LLMClient 使其立即中断正在进行的 LLM 调用
  4. 动态重规划：连续失败触发 TaskPlanner.replan()
  5. EventBus 链路追踪 + 经验蒸馏
"""
from __future__ import annotations
import os
import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.task        import TaskGraph, Task, TaskStatus
from core.event_bus   import bus, TraceContext, EventType
from llm.client       import CancelledError

REPLAN_THRESHOLD = 2
# 并发执行的最大线程数（本地模型串行，所以并发在 Agent 层面而非 LLM 层面）
MAX_WORKERS = 4

# 分析类 Agent：输出里天然含 Error/Exception，不能用关键词判断失败
_ANALYSIS_AGENTS = {"reviewer", "debugger", "doc", "selfimprove", "visualizer", "writer", "statemanager"}


class TaskExecutor:
    def __init__(self, agents: dict, msg_queue: queue.Queue, workspace: str,
                 enhanced_memory=None, planner=None, memory=None,
                 project_memory=None, llm=None):
        self.agents          = agents
        self.q               = msg_queue
        self.workspace       = workspace
        self.enhanced_memory = enhanced_memory
        self.planner         = planner
        self.memory          = memory
        self.project_memory  = project_memory
        self.llm             = llm   # LLMClient，用于注入取消信号
        self._cancel_event   = threading.Event()
        self._result_lock    = threading.Lock()

    def cancel(self):
        self._cancel_event.set()
        # 同时通知 LLM client 立即中断正在进行的调用
        if self.llm and hasattr(self.llm, 'set_cancel_event'):
            self.llm.set_cancel_event(self._cancel_event)

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def push(self, role: str, title: str, body: str, kind: str = "card"):
        try:
            self.q.put({"role": role, "title": title, "body": body, "kind": kind}, timeout=2)
        except queue.Full:
            pass

    # ── 加载 MEMORY.md 注入文本 ──────────────────────────────
    def _get_memory_injection(self) -> str:
        """返回要注入每个 Agent system prompt 的记忆文本。"""
        parts = []
        if self.project_memory:
            ctx = self.project_memory.load()
            if ctx:
                parts.append(ctx)
        return "\n\n".join(parts)

    # ── 主执行入口 ────────────────────────────────────────────
    def execute(self, graph: TaskGraph, trace: TraceContext = None) -> bool:
        self._cancel_event.clear()
        # 注入取消信号到 LLM client，让正在进行的 LLM 调用也能立即响应取消
        if self.llm and hasattr(self.llm, 'set_cancel_event'):
            self.llm.set_cancel_event(self._cancel_event)
        root_trace  = trace or TraceContext()
        project_dir = os.path.join(self.workspace, graph.project)
        os.makedirs(project_dir, exist_ok=True)

        bus.publish(EventType.TASK_START, {
            "project": graph.project, "goal": graph.goal, "tasks": len(graph.tasks),
        }, trace=root_trace)
        self.push("system", "🚀 任务启动",
                  f"项目：{graph.project}\n共 {len(graph.tasks)} 个任务\n\n{graph.summary()}",
                  "info")

        context:           dict[str, str] = {}
        execution_history: list[dict]     = []
        consecutive_fails: int            = 0
        max_rounds = len(graph.tasks) * 4
        rounds     = 0

        while not graph.is_complete() and rounds < max_rounds:
            if self.is_cancelled():
                self.push("system", "🛑 已取消", "用户取消了任务，已停止执行。", "info")
                for t in graph.tasks:
                    if t.status == TaskStatus.PENDING:
                        t.status = TaskStatus.SKIPPED
                self._distill(graph, execution_history, success=False)
                return False

            rounds += 1
            ready  = graph.get_ready_tasks()

            if not ready:
                if graph.has_failed():
                    replanned = self._try_replan(graph, context, consecutive_fails)
                    if replanned:
                        consecutive_fails = 0
                        continue
                    bus.publish(EventType.TASK_FAILED,
                                {"project": graph.project, "summary": graph.summary()},
                                trace=root_trace)
                    self.push("system", "❌ 任务失败",
                              "存在失败任务且重规划未能恢复，流程终止。", "error")
                    self._distill(graph, execution_history, success=False)
                    return False
                break

            # ── 并发执行当前批次 ──────────────────────────────
            try:
                if len(ready) == 1:
                    task = ready[0]
                    task_trace = root_trace.child()
                    success = self._run_task(task, context, project_dir, task_trace)
                    execution_history.append({
                        "agent": task.agent, "task": task.instruction, "result": task.result,
                    })
                    self._handle_task_result(task, context, consecutive_fails)
                    if success:
                        consecutive_fails = 0
                        context[task.id] = task.result
                    else:
                        consecutive_fails += 1
                        context[task.id] = task.result
                        if task.retry < task.max_retry:
                            task.retry  += 1
                            task.status  = TaskStatus.PENDING
                            self.push("system", f"♻️ 重试 [{task.id}]",
                                      f"{task.agent} 第{task.retry}次重试…", "info")
                else:
                    self.push("system", f"⚡ 并发执行 {len(ready)} 个任务",
                              " | ".join(f"[{t.id}]{t.agent}" for t in ready), "info")
                    with ThreadPoolExecutor(max_workers=min(len(ready), MAX_WORKERS)) as pool:
                        futures = {
                            pool.submit(self._run_task, task, context,
                                        project_dir, root_trace.child()): task
                            for task in ready
                        }
                        for future in as_completed(futures):
                            task = futures[future]
                            try:
                                success = future.result()
                            except CancelledError:
                                raise
                            execution_history.append({
                                "agent": task.agent, "task": task.instruction,
                                "result": task.result,
                            })
                            if success:
                                consecutive_fails = 0
                                with self._result_lock:
                                    context[task.id] = task.result
                            else:
                                consecutive_fails += 1
                                with self._result_lock:
                                    context[task.id] = task.result
                                if task.retry < task.max_retry:
                                    task.retry  += 1
                                    task.status  = TaskStatus.PENDING
                                    self.push("system", f"♻️ 重试 [{task.id}]",
                                              f"{task.agent} 第{task.retry}次重试…", "info")

            except CancelledError:
                # 取消信号触发，立即停止
                self.push("system", "🛑 已取消", "用户取消了任务，已立即停止。", "info")
                for t in graph.tasks:
                    if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                        t.status = TaskStatus.SKIPPED
                self._distill(graph, execution_history, success=False)
                return False

        if graph.is_complete():
            bus.publish(EventType.TASK_GRAPH_DONE,
                        {"project": graph.project, "success": True}, trace=root_trace)
            self.push("system", "✅ 全部完成",
                      f"项目 {graph.project} 所有任务执行完毕。", "finish")
            self._distill(graph, execution_history, success=True)
            # 更新 MEMORY.md
            self._update_project_memory(graph, execution_history, success=True)
            return True

        bus.publish(EventType.TASK_FAILED,
                    {"project": graph.project, "rounds": rounds}, trace=root_trace)
        self.push("system", "⚠️ 未完全完成",
                  f"执行了 {rounds} 轮后停止。\n{graph.summary()}", "error")
        self._distill(graph, execution_history, success=False)
        self._update_project_memory(graph, execution_history, success=False)
        return False

    def _handle_task_result(self, task, context, consecutive_fails):
        pass  # 已内联处理

    # ── MEMORY.md 更新（异步）────────────────────────────────
    def _update_project_memory(self, graph: TaskGraph, history: list, success: bool):
        if not self.project_memory:
            return
        def _run():
            try:
                self.project_memory.update(history, graph.goal, success)
            except Exception as e:
                print(f"⚠️ [Executor] MEMORY.md 更新失败: {e}")
        threading.Thread(target=_run, daemon=True).start()

    # ── 动态重规划 ────────────────────────────────────────────
    def _try_replan(self, graph: TaskGraph, context: dict, consecutive_fails: int) -> bool:
        if not self.planner or consecutive_fails < REPLAN_THRESHOLD:
            return False

        done_summary = self._compress_context(graph)
        failed_tasks = [
            t for t in graph.tasks
            if t.status == TaskStatus.FAILED and t.agent not in _ANALYSIS_AGENTS
        ]
        if not failed_tasks:
            return False

        failure_reason = "\n".join(f"{t.agent}: {t.result[:200]}" for t in failed_tasks)

        self.push("system", "🔄 动态重规划",
                  f"检测到连续失败，正在重新规划后续步骤…\n失败原因：{failure_reason[:200]}",
                  "info")

        try:
            new_tasks = self.planner.replan(
                original_goal     = graph.goal,
                project_name      = graph.project,
                completed_context = done_summary,
                failure_reason    = failure_reason,
                memory            = self.memory,
            )
        except Exception as e:
            self.push("system", "⚠️ 重规划失败", str(e), "error")
            return False

        if not new_tasks:
            return False

        for t in graph.tasks:
            if t.status == TaskStatus.FAILED:
                t.status = TaskStatus.SKIPPED
        graph.tasks = [t for t in graph.tasks if t.status != TaskStatus.PENDING]
        graph.tasks.extend(new_tasks)

        self.push("system", "✅ 重规划成功",
                  f"新增 {len(new_tasks)} 个任务：\n" +
                  "\n".join(f"- [{t.id}] {t.agent}: {t.instruction[:50]}" for t in new_tasks),
                  "info")
        return True

    def _compress_context(self, graph: TaskGraph) -> str:
        """语义压缩已完成任务的上下文，去掉冗余细节，只保留关键结论。"""
        lines = []
        for t in graph.tasks:
            if t.status not in (TaskStatus.DONE, TaskStatus.FAILED):
                continue
            result = t.result[:150]
            # 进一步压缩：只保留第一行（通常是结论行）
            first_line = result.splitlines()[0] if result else ""
            lines.append(f"[{t.agent}] {t.instruction[:40]}… → {first_line}")
        return "\n".join(lines)

    # ── 经验蒸馏（异步）─────────────────────────────────────
    def _distill(self, graph: TaskGraph, history: list, success: bool):
        if not self.enhanced_memory or not history:
            return
        def _run():
            try:
                self.enhanced_memory.distill_task_memory(graph.goal, history, success)
            except Exception as e:
                print(f"⚠️ [Executor] 经验蒸馏异常: {e}")
        threading.Thread(target=_run, daemon=True).start()

    # ── 单任务执行 ────────────────────────────────────────────
    def _run_task(self, task: Task, context: dict,
                  project_dir: str, trace: TraceContext) -> bool:
        agent = self.agents.get(task.agent)
        if not agent:
            task.status = TaskStatus.SKIPPED
            self.push("system", f"⏭️ 跳过 [{task.id}]",
                      f"未找到 Agent：{task.agent}，跳过此步骤。", "info")
            return True

        # 构建指令：注入前序结果
        instruction = task.instruction
        if task.depends:
            with self._result_lock:
                ctx_parts = [
                    f"[{dep_id}结果] {context[dep_id][:300]}"
                    for dep_id in task.depends
                    if dep_id in context and context[dep_id]
                ]
            if ctx_parts:
                instruction += "\n\n【前序结果参考】\n" + "\n".join(ctx_parts)

        # MEMORY.md 注入到指令前缀（让 Agent 执行时能看到项目记忆）
        mem_injection = self._get_memory_injection()
        if mem_injection:
            instruction = f"{mem_injection}\n\n{instruction}"

        task.status = TaskStatus.RUNNING
        bus.publish(f"agent.{task.agent}.start",
                    {"task_id": task.id, "instruction": task.instruction[:200]},
                    trace=trace)
        self.push(task.agent, f"▶ [{task.id}] {task.agent}", task.instruction, "running")

        t0 = time.time()
        try:
            if hasattr(agent, "run"):
                try:
                    result = agent.run(instruction, workspace_dir=project_dir)
                except TypeError:
                    result = agent.run(instruction)
            else:
                result = "❌ Agent 没有 run 方法"

            dur         = round(time.time() - t0, 2)
            task.result = str(result)

            # 按 Agent 类型判断失败
            if task.agent in _ANALYSIS_AGENTS:
                is_error = str(result).lstrip().startswith("❌")
            else:
                is_error = any(kw in str(result)
                               for kw in ["❌", "Error", "Traceback", "Exception"])
            task.status = TaskStatus.FAILED if is_error else TaskStatus.DONE

            bus.publish(f"agent.{task.agent}.result", {
                "task_id": task.id, "status": task.status.value,
                "dur": dur, "result": task.result[:300],
            }, trace=trace)

            icon = "✅" if task.status == TaskStatus.DONE else "❌"
            kind = "result" if task.status == TaskStatus.DONE else "error"
            self.push(task.agent, f"{icon} [{task.id}] {task.agent} ({dur}s)",
                      task.result, kind)
            return task.status == TaskStatus.DONE

        except CancelledError:
            # 用户取消，标记任务为 SKIPPED，不算失败
            task.status = TaskStatus.SKIPPED
            task.result = "已取消"
            self.push(task.agent, f"🛑 [{task.id}] {task.agent} 已取消", "", "info")
            raise   # 往上传递，让 execute() 循环感知到取消

        except Exception as e:
            dur         = round(time.time() - t0, 2)
            task.result = f"执行异常：{e}"
            task.status = TaskStatus.FAILED
            bus.publish(f"agent.{task.agent}.error",
                        {"task_id": task.id, "error": str(e), "dur": dur}, trace=trace)
            self.push(task.agent, f"❌ [{task.id}] {task.agent} ({dur}s)",
                      task.result, "error")
            return False