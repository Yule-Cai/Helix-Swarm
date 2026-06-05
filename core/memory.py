# core/memory.py
import sqlite3
import uuid
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# 延迟导入向量数据库
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class VectorMemory:
    """向量记忆存储

    使用 ChromaDB 实现语义搜索的长期记忆。
    如果 ChromaDB 不可用，则回退到基于关键词的简单搜索。
    """

    def __init__(self, persist_directory: str = "memory_vectors"):
        """
        初始化向量记忆

        Args:
            persist_directory: 持久化目录
        """
        self.persist_directory = persist_directory
        self._client = None
        self._collection = None
        self._init_vector_store()

    def _init_vector_store(self):
        """初始化向量存储"""
        if not CHROMADB_AVAILABLE:
            print("ChromaDB not installed. Vector search disabled. Install with: pip install chromadb")
            return

        try:
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(
                name="memory",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"Failed to initialize ChromaDB: {e}")
            self._client = None
            self._collection = None

    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        memory_id: Optional[str] = None,
    ) -> str:
        """
        添加记忆到向量存储

        Args:
            content: 记忆内容
            metadata: 元数据
            memory_id: 记忆 ID（可选）

        Returns:
            str: 记忆 ID
        """
        if not self._collection:
            return self._fallback_add(content, metadata, memory_id)

        memory_id = memory_id or hashlib.md5(content.encode()).hexdigest()
        metadata = metadata or {}
        metadata["timestamp"] = datetime.now().isoformat()

        try:
            self._collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[memory_id],
            )
            return memory_id
        except Exception as e:
            print(f"Failed to add memory: {e}")
            return memory_id

    def search_memory(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        语义搜索记忆

        Args:
            query: 搜索查询
            n_results: 返回结果数量
            filter_metadata: 元数据过滤条件

        Returns:
            List[Dict]: 匹配的记忆列表
        """
        if not self._collection:
            return self._fallback_search(query, n_results)

        try:
            kwargs = {
                "query_texts": [query],
                "n_results": min(n_results, self._collection.count()),
            }
            if filter_metadata:
                kwargs["where"] = filter_metadata

            results = self._collection.query(**kwargs)

            memories = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    memory = {
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "id": results['ids'][0][i] if results['ids'] else "",
                        "distance": results['distances'][0][i] if results['distances'] else 0,
                    }
                    memories.append(memory)

            return memories

        except Exception as e:
            print(f"Vector search failed: {e}")
            return self._fallback_search(query, n_results)

    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        if not self._collection:
            return False

        try:
            self._collection.delete(ids=[memory_id])
            return True
        except Exception:
            return False

    def get_memory_count(self) -> int:
        """获取记忆数量"""
        if not self._collection:
            return 0
        return self._collection.count()

    def clear(self) -> None:
        """清除所有记忆"""
        if self._client and self._collection:
            try:
                self._client.delete_collection("memory")
                self._collection = self._client.get_or_create_collection(
                    name="memory",
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception:
                pass

    def _fallback_add(
        self,
        content: str,
        metadata: Optional[Dict],
        memory_id: Optional[str],
    ) -> str:
        """回退方案：使用内存存储"""
        memory_id = memory_id or hashlib.md5(content.encode()).hexdigest()
        if not hasattr(self, '_fallback_store'):
            self._fallback_store = {}
        self._fallback_store[memory_id] = {
            "content": content,
            "metadata": metadata or {},
        }
        return memory_id

    def _fallback_search(self, query: str, n_results: int) -> List[Dict]:
        """回退方案：基于关键词搜索"""
        if not hasattr(self, '_fallback_store'):
            return []

        query_lower = query.lower()
        results = []

        for memory_id, memory in self._fallback_store.items():
            content = memory["content"].lower()
            # 简单的关键词匹配
            score = sum(1 for word in query_lower.split() if word in content)
            if score > 0:
                results.append({
                    "content": memory["content"],
                    "metadata": memory["metadata"],
                    "id": memory_id,
                    "distance": 1.0 / (1.0 + score),  # 转换为距离
                })

        # 按相关性排序
        results.sort(key=lambda x: x["distance"])
        return results[:n_results]


class MemoryManager:
    """记忆管理器

    支持：
    - SQLite 持久化对话历史
    - 向量记忆的语义搜索
    - 跨会话记忆检索
    """

    def __init__(
        self,
        db_path: str = "helix_state.db",
        vector_persist_dir: str = "memory_vectors",
    ):
        """
        初始化记忆管理器

        Args:
            db_path: SQLite 数据库路径
            vector_persist_dir: 向量记忆持久化目录
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        self.current_session_id = None

        # 初始化向量记忆
        self.vector_memory = VectorMemory(vector_persist_dir)

    def _init_db(self):
        """建表：管理会话和历史消息"""
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    started_at TIMESTAMP,
                    topic TEXT
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            ''')
            # 新增：长期记忆表
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS long_term_memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    category TEXT,
                    importance REAL DEFAULT 0.5,
                    created_at TIMESTAMP,
                    last_accessed TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')

    def start_new_session(self, topic: str = "New Chat"):
        """开启新纪元"""
        self.current_session_id = uuid.uuid4().hex
        with self.conn:
            self.conn.execute(
                "INSERT INTO sessions (id, started_at, topic) VALUES (?, ?, ?)",
                (self.current_session_id, datetime.now(), topic)
            )
        return self.current_session_id

    def save_message(self, role: str, content: str):
        """将一言一行刻入硬盘"""
        if not self.current_session_id:
            return
        if not content or str(content).strip() == "":
            return

        with self.conn:
            self.conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (self.current_session_id, role, str(content), datetime.now())
            )

        # 自动提取重要信息到向量记忆
        if role == "assistant" and len(content) > 100:
            self._extract_and_store_memory(content)

    def _extract_and_store_memory(self, content: str):
        """从对话中提取重要信息并存储到向量记忆"""
        # 简单的启发式：存储包含关键信息的内容
        keywords = ["结论", "发现", "重要", "关键", "总结", "结果", "决定", "计划"]
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in keywords):
            self.vector_memory.add_memory(
                content=content[:500],  # 限制长度
                metadata={
                    "session_id": self.current_session_id,
                    "type": "extracted",
                }
            )

    def save_long_term_memory(
        self,
        content: str,
        category: str = "general",
        importance: float = 0.5,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        保存长期记忆

        Args:
            content: 记忆内容
            category: 记忆类别
            importance: 重要性 (0-1)
            metadata: 元数据

        Returns:
            str: 记忆 ID
        """
        memory_id = hashlib.md5(content.encode()).hexdigest()

        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO long_term_memories
                   (id, content, category, importance, created_at, last_accessed, access_count, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, 0, ?)""",
                (memory_id, content, category, importance, datetime.now(), datetime.now(),
                 json.dumps(metadata) if metadata else None)
            )

        # 同时存储到向量记忆
        self.vector_memory.add_memory(
            content=content,
            metadata={"category": category, "importance": importance, **(metadata or {})},
            memory_id=memory_id,
        )

        return memory_id

    def search_long_term_memory(
        self,
        query: str,
        category: Optional[str] = None,
        n_results: int = 5,
    ) -> List[Dict]:
        """
        搜索长期记忆

        Args:
            query: 搜索查询
            category: 记忆类别过滤
            n_results: 返回结果数量

        Returns:
            List[Dict]: 匹配的记忆列表
        """
        # 使用向量搜索
        filter_metadata = {"category": category} if category else None
        results = self.vector_memory.search_memory(query, n_results, filter_metadata)

        # 更新访问记录
        for result in results:
            memory_id = result.get("id")
            if memory_id:
                with self.conn:
                    self.conn.execute(
                        "UPDATE long_term_memories SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?",
                        (datetime.now(), memory_id)
                    )

        return results

    def get_all_sessions(self) -> List[Dict]:
        """扫描并返回所有的历史纪元"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY started_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def load_session_history(self, session_id: str) -> List[Dict]:
        """恢复前世记忆"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,)
        )
        return [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]

    def set_active_session(self, session_id: str):
        """激活旧会话"""
        self.current_session_id = session_id

    def get_memory_stats(self) -> Dict:
        """获取记忆统计信息"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM long_term_memories")
        long_term_count = cursor.fetchone()[0]

        vector_count = self.vector_memory.get_memory_count()

        return {
            "sessions": session_count,
            "messages": message_count,
            "long_term_memories": long_term_count,
            "vector_memories": vector_count,
        }

    def close(self):
        """关闭连接"""
        self.conn.close()


# 实例化全局单例
memory = MemoryManager()
