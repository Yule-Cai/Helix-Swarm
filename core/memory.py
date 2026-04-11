"""
MemPalaceManager — 记忆宫殿（ChromaDB 向量存储，v1 原版）
兼容 v2 的 Memory 轻量接口，优先使用 ChromaDB；
若 ChromaDB 不可用则自动降级为 JSON 文件存储。
"""
import uuid
import time
import os
import json

# ── 配置 ──────────────────────────────────────────────────────
DEFAULT_N_RESULTS  = 2
DISTANCE_THRESHOLD = 1.5
DB_STORAGE_PATH    = "./mem_palace_db"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM_DIR  = os.path.join(BASE_DIR, "memory")


class MemPalaceManager:
    """
    记忆宫殿管理器（工业级隔离与阈值过滤版）。
    优先使用 ChromaDB 向量存储；ChromaDB 未安装时降级为 JSON。
    """

    def __init__(self, project_name: str = "default"):
        safe_name = "".join(
            c if c.isalnum() or c in ("_", "-") else "_"
            for c in project_name
        ).strip("_")
        if not safe_name or len(safe_name) < 3:
            safe_name = f"proj_{safe_name}_db"[:63]
        self.collection_name = safe_name

        # 尝试初始化 ChromaDB
        self._chroma = None
        try:
            import chromadb
            db_path = os.path.join(BASE_DIR, "mem_palace_db")
            self._chroma = chromadb.PersistentClient(path=db_path)
        except Exception:
            pass  # 降级为 JSON

        # JSON 降级路径
        os.makedirs(MEM_DIR, exist_ok=True)
        self._json_path = os.path.join(MEM_DIR, f"{safe_name}.json")
        self._json_data: list = self._load_json()

    # ── JSON 后端 ─────────────────────────────────────────────

    def _load_json(self) -> list:
        if not os.path.exists(self._json_path):
            return []
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_json(self):
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(self._json_data[-300:], f, ensure_ascii=False, indent=2)

    # ── 存储 ─────────────────────────────────────────────────

    def store_memory(self, content: str, summary: str = ""):
        if self._chroma:
            try:
                col = self._chroma.get_or_create_collection(name=self.collection_name)
                col.add(
                    documents=[content],
                    metadatas=[{"summary": summary, "timestamp": time.time()}],
                    ids=[str(uuid.uuid4())],
                )
                return
            except Exception:
                pass
        # JSON 降级
        self._json_data.append({
            "content":    content,
            "summary":    summary or content[:60],
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self._save_json()

    # 兼容 v2 Memory 接口
    def store(self, content: str, summary: str = "", tags: list = None):
        self.store_memory(content, summary)

    # ── 召回 ─────────────────────────────────────────────────

    def recall(self, query: str, n_results: int = DEFAULT_N_RESULTS) -> str:
        if self._chroma:
            try:
                col = self._chroma.get_collection(name=self.collection_name)
                if col.count() == 0:
                    return ""
                results = col.query(
                    query_texts=[query],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"],
                )
                if results["documents"] and results["documents"][0]:
                    docs      = results["documents"][0]
                    metas     = results["metadatas"][0]
                    distances = results["distances"][0]
                    parts = []
                    for i, doc in enumerate(docs):
                        if distances[i] > DISTANCE_THRESHOLD:
                            continue
                        summ = metas[i].get("summary", "无摘要")
                        parts.append(f"- [经验摘要: {summ}]: {doc[:300]}…")
                    return "【记忆宫殿】\n" + "\n".join(parts) if parts else ""
            except Exception:
                pass
        # JSON 降级：关键词匹配
        if not self._json_data:
            return ""
        qw = set(query.lower().split())
        scored = []
        for item in self._json_data:
            text = (item.get("content", "") + " " + item.get("summary", "")).lower()
            score = sum(1 for w in qw if w in text)
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored:
            return ""
        return "\n".join(
            f"[记忆] {item.get('summary', '')}"
            for _, item in scored[:n_results]
        )

    # 兼容 v2 Memory 接口
    def store_error_solution(self, error: str, solution: str):
        self.store_memory(
            content=f"错误：{error[:300]}\n解决：{solution[:300]}",
            summary="错误修复记录",
        )

    def recall_error(self, error_msg: str) -> str:
        return self.recall(error_msg, n_results=1)

    # ── 结构化检索（供 TaskPlanner 使用）────────────────────────
    def search_structured(self, query: str, n_results: int = 3) -> list[dict]:
        """
        返回结构化的记忆条目列表，每条含 summary / content / score。
        比 recall() 更适合注入 Planner prompt。
        """
        results = []

        if self._chroma:
            try:
                col = self._chroma.get_collection(name=self.collection_name)
                if col.count() == 0:
                    return []
                raw = col.query(
                    query_texts=[query],
                    n_results=min(n_results, col.count()),
                    include=["documents", "metadatas", "distances"],
                )
                for i, doc in enumerate(raw["documents"][0]):
                    dist = raw["distances"][0][i]
                    if dist > DISTANCE_THRESHOLD:
                        continue
                    results.append({
                        "summary": raw["metadatas"][0][i].get("summary", ""),
                        "content": doc[:400],
                        "score":   round(1 - dist / DISTANCE_THRESHOLD, 2),
                    })
                return results
            except Exception:
                pass

        # JSON 降级
        if not self._json_data:
            return []
        qw = set(query.lower().split())
        scored = []
        for item in self._json_data:
            text  = (item.get("content", "") + " " + item.get("summary", "")).lower()
            score = sum(1 for w in qw if w in text)
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "summary": item.get("summary", ""),
                "content": item.get("content", "")[:400],
                "score":   score,
            }
            for score, item in scored[:n_results]
        ]