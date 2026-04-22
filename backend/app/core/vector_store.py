"""
Qdrant向量库模块 - 查询历史推荐
"""
from typing import List, Dict, Any, Optional
import re
from collections import Counter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import hashlib


class VectorStore:
    """Qdrant向量存储"""

    def __init__(self, host: str = "localhost", port: int = 6333, collection: str = "query_history"):
        self.client = QdrantClient(host=host, port=port)
        self.collection = collection
        self.vector_size = 1536  # OpenAI embedding size (简化实现)

    def init_collection(self) -> bool:
        """初始化集合"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
            return True
        except Exception as e:
            print(f"Qdrant 初始化失败: {e}")
            return False

    def _get_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单分词：去除停用词，保留有意义的词
        stopwords = {'的', '了', '是', '在', '和', '与', '或', '有', '个', '我', '你', '他', '她', '它', '们', '这', '那', '什么', '怎么', '如何', '多少', '几个', '哪些', '哪个'}
        words = re.findall(r'[\w]+', text.lower())
        return [w for w in words if w not in stopwords and len(w) > 1]

    def _simple_vector(self, text: str) -> List[float]:
        """生成简单向量（词频统计）"""
        keywords = self._get_keywords(text)
        counter = Counter(keywords)

        # 使用固定大小的向量，基于词频
        # 这是一个简化实现，实际应使用真正的 embedding
        vector = [0.0] * self.vector_size
        for i, word_hash in enumerate(hashlib.md5(w.encode()).digest() for w in set(keywords)):
            idx = word_hash[i % 16] if isinstance(word_hash, bytes) else hash(word_hash) % self.vector_size
            vector[idx] = counter[keywords[i % len(keywords)] if keywords else 0] / max(len(keywords), 1)

        return vector

    def add_query(
        self,
        query: str,
        sql: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加查询到向量库

        Args:
            query: 自然语言查询
            sql: 生成的SQL
            metadata: 额外元数据

        Returns:
            point_id
        """
        point_id = hashlib.md5(query.encode()).hexdigest()

        payload = {
            "query": query,
            "sql": sql,
            "keywords": self._get_keywords(query),
            "metadata": metadata or {}
        }

        vector = self._simple_vector(query)

        try:
            self.client.upsert(
                collection_name=self.collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
        except Exception as e:
            print(f"Qdrant 添加失败: {e}")

        return point_id

    def search_similar(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索相似查询

        Args:
            query: 自然语言查询
            limit: 返回数量

        Returns:
            相似查询列表
        """
        keywords = self._get_keywords(query)

        # 1. 尝试使用 Qdrant 向量搜索
        try:
            vector = self._simple_vector(query)
            results = self.client.search(
                collection_name=self.collection,
                query_vector=vector,
                limit=limit
            )
            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "query": result.payload.get("query"),
                    "sql": result.payload.get("sql"),
                    "keywords": result.payload.get("keywords", [])
                }
                for result in results
            ]
        except Exception as e:
            print(f"Qdrant 搜索失败: {e}")

        # 2. 降级：使用关键词匹配
        return self._keyword_search(keywords, limit)

    def _keyword_search(
        self,
        keywords: List[str],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """基于关键词的搜索 - 内存实现"""
        if not keywords:
            return []

        try:
            # 获取所有记录并内存过滤
            all_results = self.get_all_queries(limit=100)
            matched = []

            for result in all_results:
                result_keywords = result.get("keywords", [])
                # 计算匹配的关键词数量
                matches = sum(1 for kw in keywords if kw in result_keywords)
                if matches > 0:
                    matched.append({
                        "id": result.get("id"),
                        "score": matches / len(keywords) if keywords else 0,
                        "query": result.get("query"),
                        "sql": result.get("sql"),
                        "keywords": result_keywords
                    })

            # 按匹配度排序
            matched.sort(key=lambda x: x["score"], reverse=True)
            return matched[:limit]

        except Exception as e:
            print(f"关键词搜索失败: {e}")
            return []

    def delete_query(self, point_id: str) -> bool:
        """删除查询记录"""
        try:
            self.client.delete(
                collection_name=self.collection,
                points=[point_id]
            )
            return True
        except Exception:
            return False

    def get_all_queries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有查询记录"""
        try:
            results = self.client.scroll(
                collection_name=self.collection,
                limit=limit
            )
            return [
                {
                    "id": result.id,
                    **result.payload
                }
                for result in results[0]
            ]
        except Exception:
            return []


# 全局实例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取向量存储实例"""
    global _vector_store
    if _vector_store is None:
        from app.core.config import settings
        _vector_store = VectorStore(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            collection=settings.QDRANT_COLLECTION
        )
    return _vector_store
