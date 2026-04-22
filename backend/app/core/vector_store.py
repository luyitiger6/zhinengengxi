"""
Qdrant向量库模块
"""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import hashlib


class VectorStore:
    """Qdrant向量存储"""

    def __init__(self, host: str = "localhost", port: int = 6333, collection: str = "query_history"):
        self.client = QdrantClient(host=host, port=port)
        self.collection = collection
        self.vector_size = 768  # 默认向量维度

    def init_collection(self) -> None:
        """初始化集合"""
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
        # 简单实现：使用query的hash作为ID（实际应用中应使用embedding）
        point_id = hashlib.md5(query.encode()).hexdigest()

        payload = {
            "query": query,
            "sql": sql,
            "metadata": metadata or {}
        }

        # 注意：这里需要embedding服务，实际应调用embedding API
        # 暂时使用零向量占位
        vector = [0.0] * self.vector_size

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
        # 注意：实际应使用query的embedding
        vector = [0.0] * self.vector_size

        results = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=limit
        )

        return [
            {
                "id": result.id,
                "score": result.score,
                **result.payload
            }
            for result in results
        ]

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
