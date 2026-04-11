from __future__ import annotations
import os
import json
import time
import threading
import queue
from datetime import datetime

DEFAULT_TOPICS = [
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
]

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(BASE_DIR, "learning_reports")
# 进度存档文件：记录上次学到哪个 topic，以及累计学习数
PROGRESS_FILE = os.path.join(BASE_DIR, "learning_progress.json")

_ICONS = {
    "start":   "🚀",
    "search":  "🔍",
    "extract": "🧠",
    "save":    "💾",
    "done":    "✅",
    "warn":    "⚠️",
    "wait":    "⏳",
    "stop":    "🛑",
    "report":  "📋",
}


class LearningScheduler:
    def __init__(self, llm_client, search_agent, memory_palace, config: dict):
        self.llm      = llm_client
        self.searcher = search_agent
        self.memory   = memory_palace
        self.config   = config

        self._running  = False
        self._thread   = None
        self._stop_evt = threading.Event()
        self._status   = {"state": "idle", "progress": "", "learned": 0, "started_at": None}
        self._lock     = threading.Lock()

        self._log_q: queue.Queue = queue.Queue(maxsize=500)
        self._subscribers: list[queue.Queue] = []
        self._sub_lock = threading.Lock()

        os.makedirs(REPORT_DIR, exist_ok=True)

    # ── 进度持久化 ────────────────────────────────
    def _load_progress(self) -> dict:
        """加载上次的学习进度，没有则返回默认值。"""
        if not os.path.exists(PROGRESS_FILE):
            return {"idx": 0, "total_learned": 0, "completed_topics": []}
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"idx": 0, "total_learned": 0, "completed_topics": []}

    def _save_progress(self, idx: int, total_learned: int, completed_topics: list):
        """将当前进度写入磁盘。"""
        data = {
            "idx":               idx,
            "total_learned":     total_learned,
            "completed_topics":  completed_topics,
            "last_saved":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  [Learning] 进度保存失败: {e}")

    # ── 日志广播 ─────────────────────────────────
    def _log(self, level: str, text: str, topic: str = ""):
        entry = {
            "time":  datetime.now().strftime("%H:%M:%S"),
            "icon":  _ICONS.get(level, "•"),
            "level": level,
            "text":  text,
            "topic": topic,
        }
        if self._log_q.full():
            try: self._log_q.get_nowait()
            except: pass
        self._log_q.put(entry)
        with self._sub_lock:
            dead = []
            for q in self._subscribers:
                try:
                    q.put_nowait(entry)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._subscribers.remove(q)
        print(f"{entry['icon']} [Learning] {text}")

    def subscribe(self, replay_last: int = 20) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=200)
        history = list(self._log_q.queue)
        for entry in history[-replay_last:]:
            try:
                q.put_nowait(entry)
            except Exception:
                break
        with self._sub_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._sub_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def get_recent_logs(self, n: int = 50) -> list:
        logs = list(self._log_q.queue)
        return logs[-n:]

    # ── 状态管理 ─────────────────────────────────
    def get_status(self) -> dict:
        with self._lock:
            return dict(self._status)

    def _set_status(self, **kwargs):
        with self._lock:
            self._status.update(kwargs)

    # ── 启停 ─────────────────────────────────────
    def start(self):
        if self._running:
            return {"ok": False, "msg": "学习模式已在运行中"}
        self._stop_evt.clear()
        self._running = True

        # 加载上次进度，恢复 learned 计数
        progress = self._load_progress()
        total_learned = progress.get("total_learned", 0)

        self._set_status(
            state="running",
            learned=total_learned,          # 从历史累计值恢复，不清零
            started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            progress="正在从上次进度继续…" if total_learned > 0 else "正在初始化…",
        )
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return {"ok": True, "msg": f"自主学习模式已启动（已累计学习 {total_learned} 个主题）"}

    def stop(self):
        if not self._running:
            return {"ok": False, "msg": "学习模式未在运行"}
        self._stop_evt.set()
        self._running = False
        self._set_status(state="stopping", progress="正在保存学习进度…")
        return {"ok": True, "msg": "正在停止，稍后完成收尾工作"}

    def reset_progress(self):
        """清空进度，下次从头开始。"""
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        self._set_status(learned=0)
        return {"ok": True, "msg": "学习进度已重置，下次将从头开始"}

    # ── 核心学习循环 ──────────────────────────────
    def _loop(self):
        topics   = self.config.get("learning_topics", DEFAULT_TOPICS)
        interval = self.config.get("learning_interval_sec", 120)

        # 从磁盘恢复进度
        progress          = self._load_progress()
        idx               = progress.get("idx", 0)
        total_learned     = progress.get("total_learned", 0)
        completed_topics  = progress.get("completed_topics", [])

        report = []   # 本次会话新学的内容

        self._log("start",
                  f"学习模式启动，共 {len(topics)} 个主题，"
                  f"从第 {idx % len(topics) + 1} 个继续，"
                  f"历史累计已学 {total_learned} 个")

        try:
            while not self._stop_evt.is_set():
                topic      = topics[idx % len(topics)]
                topic_num  = idx % len(topics) + 1
                idx       += 1

                self._set_status(progress=f"[{topic_num}/{len(topics)}] 正在学习：{topic}")
                self._log("start", f"第 {idx} 轮，主题 {topic_num}/{len(topics)}", topic)

                try:
                    knowledge = self._learn_one_topic(topic)
                    if knowledge:
                        self.memory.store_memory(
                            content=knowledge["content"],
                            summary=knowledge["summary"],
                        )
                        report.append(knowledge)
                        total_learned    += 1
                        completed_topics.append({
                            "topic":      topic,
                            "learned_at": knowledge["learned_at"],
                        })
                        # 每学一个就保存一次进度
                        self._save_progress(idx, total_learned, completed_topics[-200:])
                        self._set_status(learned=total_learned,
                                         progress=f"累计已学 {total_learned} 个主题")
                        self._log("save",
                                  f"已存入记忆库（累计 {total_learned} 个）：{knowledge['summary']}",
                                  topic)
                    else:
                        self._log("warn", "本轮未获得有效知识", topic)
                        # 即使没学到内容，也推进 idx 并保存，避免卡在同一 topic
                        self._save_progress(idx, total_learned, completed_topics[-200:])

                    if getattr(self.searcher, '_rate_limited', False):
                        self._log("wait", "GitHub API 限流，等待 1 小时后恢复…")
                        self._set_status(progress="GitHub API 限流，等待恢复…")
                        self._stop_evt.wait(timeout=3600)
                        if hasattr(self.searcher, 'reset_rate_limit'):
                            self.searcher.reset_rate_limit()
                        self._log("start", "限流已重置，继续学习")

                except Exception as e:
                    self._log("warn", f"学习出错：{e}", topic)
                    # 出错也保存进度，避免下次重复踩坑
                    self._save_progress(idx, total_learned, completed_topics[-200:])

                if not self._stop_evt.is_set():
                    self._log("wait", f"等待 {interval}s 后学习下一个主题…")
                    self._stop_evt.wait(timeout=interval)

        finally:
            # 停止时最终保存一次
            self._save_progress(idx, total_learned, completed_topics[-200:])
            self._save_report(report)
            self._set_status(state="idle", progress=f"已停止，累计学习 {total_learned} 个主题")
            self._running = False
            self._log("report",
                      f"本次新学 {len(report)} 个，历史累计 {total_learned} 个，进度已保存")
            # autoDream：整合本次学习成果到全局记忆索引
            if report:
                self._auto_dream(report)

    # ── 单主题学习 ────────────────────────────────
    def _learn_one_topic(self, topic: str) -> dict | None:
        import re

        self._log("search", "GitHub 搜索中…", topic)
        raw = self.searcher.run(topic)
        if not raw or "❌" in raw:
            self._log("warn", "GitHub 搜索失败或无结果", topic)
            return None

        repo_count = raw.count("⭐")
        code_count = raw.count("📄")
        self._log("search", f"搜到 {repo_count} 个仓库，{code_count} 个代码文件", topic)

        self._log("extract", "LLM 正在提炼知识…", topic)
        prompt = (
            f"你是技术知识提炼专家。\n主题：{topic}\n\n"
            f"GitHub 搜索内容：\n{raw[:3000]}\n\n"
            f"请用中文提炼：\n"
            f"1. 核心概念（2-3句）\n"
            f"2. 关键 API 或函数（3-5个）\n"
            f"3. 最佳实践（2-3条）\n"
            f"4. 常见错误和解决方案（1-2条）\n"
            f"5. 一句话摘要\n\n直接输出，每部分用标题分隔。"
        )
        knowledge_text = self.llm.chat(
            system="你是专业技术知识提炼专家。",
            user=prompt,
            temperature=0.3,
            max_tokens=1024,
        )

        if not knowledge_text or knowledge_text == "{}":
            self._log("warn", "LLM 提炼失败，跳过", topic)
            return None

        summary_match = re.search(r'5[.、）)]\s*一句话摘要[：:]\s*(.+)', knowledge_text)
        summary = summary_match.group(1).strip() if summary_match else f"{topic} 相关知识"

        self._log("done", f"提炼完成：{summary[:40]}", topic)

        return {
            "topic":      topic,
            "summary":    summary,
            "content":    knowledge_text,
            "raw_refs":   raw[:500],
            "learned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    # ── autoDream：整合学习成果 ───────────────────────────────
    def _auto_dream(self, report: list):
        """
        仿 Claude Code autoDream：
        把本次学习的知识整合进全局记忆索引，消除矛盾，转化为精炼指针。
        """
        if not self.llm or not report:
            return
        try:
            from core.project_memory import GlobalMemoryIndex
        except ImportError:
            return

        self._log("report", f"autoDream 启动，整合 {len(report)} 个主题的知识…")
        summaries = "\n".join(
            f"- [{item['topic']}] {item['summary']}"
            for item in report if item.get("summary")
        )
        global_mem = GlobalMemoryIndex(self.llm)
        existing   = global_mem.load()
        prompt = (
            f"本次学习摘要：\n{summaries}\n\n"
            f"当前全局记忆：\n{existing if existing else '（空）'}\n\n"
            "任务：\n"
            "1. 从本次学习中提炼 3-5 条最有价值的通用开发经验（每条≤150字符）\n"
            "2. 只输出新增条目（每行以 - 开头），不要泛泛而谈\n"
            "3. 专注于可直接行动的技术知识"
        )
        try:
            result = self.llm.chat(
                system="你是技术知识蒸馏专家。输出精炼、可操作的知识指针。",
                user=prompt, temperature=0.2, max_tokens=400,
            )
            if not result or result.strip() == "{}":
                return
            added = 0
            for line in result.splitlines():
                line = line.strip().lstrip("-•* ").strip()
                if line and len(line) > 10:
                    global_mem.append(line)
                    added += 1
            self._log("save", f"autoDream 完成，新增 {added} 条全局知识")
        except Exception as e:
            self._log("warn", f"autoDream 失败: {e}")

    # ── 报告 ─────────────────────────────────────
    def _save_report(self, report: list):
        if not report:
            return
        filename = os.path.join(
            REPORT_DIR,
            f"learning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_topics": len(report),
                "items": report,
            }, f, ensure_ascii=False, indent=2)

    def list_reports(self) -> list:
        reports = []
        for fname in sorted(os.listdir(REPORT_DIR), reverse=True):
            if fname.endswith(".json"):
                fpath = os.path.join(REPORT_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    reports.append({
                        "filename":     fname,
                        "generated_at": data.get("generated_at", ""),
                        "total_topics": data.get("total_topics", 0),
                    })
                except Exception:
                    pass
        return reports

    def get_report(self, filename: str) -> dict:
        safe  = os.path.basename(filename)
        fpath = os.path.join(REPORT_DIR, safe)
        if not os.path.exists(fpath):
            return {}
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)