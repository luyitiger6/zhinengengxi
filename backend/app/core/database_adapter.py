"""
数据库适配器接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import sqlite3
import os


class DatabaseAdapter(ABC):
    """数据库适配器抽象基类"""

    @abstractmethod
    def connect(self) -> None:
        """建立连接"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    def execute(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行SQL查询"""
        pass

    @abstractmethod
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        pass

    @abstractmethod
    def get_schema(self, table: str) -> Dict[str, Any]:
        """获取表结构"""
        pass


class SQLiteAdapter(DatabaseAdapter):
    """SQLite数据库适配器"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute(sql, params or ())

        # SELECT查询返回结果
        if sql.strip().upper().startswith('SELECT'):
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        # 其他查询返回影响的行数
        self.conn.commit()
        return [{"rows_affected": cursor.rowcount}]

    def get_tables(self) -> List[str]:
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        return [row[0] for row in cursor.fetchall()]

    def get_schema(self, table: str) -> Dict[str, Any]:
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [dict(row) for row in cursor.fetchall()]

        cursor.execute(f"PRAGMA foreign_keys({table})")
        fk = cursor.fetchone()

        return {
            "table_name": table,
            "columns": columns,
            "has_foreign_keys": bool(fk and fk[0])
        }


def create_adapter(db_type: str, **kwargs) -> DatabaseAdapter:
    """工厂函数：创建数据库适配器"""
    from app.core.mysql_adapter import MySQLAdapter
    from app.core.postgres_adapter import PostgreSQLAdapter

    adapters = {
        "sqlite": SQLiteAdapter,
        "mysql": MySQLAdapter,
        "postgresql": PostgreSQLAdapter,
    }

    adapter_class = adapters.get(db_type.lower())
    if not adapter_class:
        raise ValueError(f"不支持的数据库类型: {db_type}")

    return adapter_class(**kwargs)


def create_adapter_from_env() -> DatabaseAdapter:
    """根据环境变量创建数据库适配器"""
    from app.core.config import settings

    db_type = settings.DB_TYPE.lower()

    if db_type == "sqlite":
        db_path = settings.DB_PATH
        # 支持相对路径
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", db_path)
        return SQLiteAdapter(db_path)

    elif db_type == "mysql":
        return MySQLAdapter(
            host=settings.DB_HOST or "localhost",
            port=settings.DB_PORT or 3306,
            database=settings.DB_NAME or "zhinengengxi",
            user=settings.DB_USER or "root",
            password=settings.DB_PASSWORD or ""
        )

    elif db_type == "postgresql":
        return PostgreSQLAdapter(
            host=settings.DB_HOST or "localhost",
            port=settings.DB_PORT or 5432,
            database=settings.DB_NAME or "zhinengengxi",
            user=settings.DB_USER or "postgres",
            password=settings.DB_PASSWORD or ""
        )

    raise ValueError(f"不支持的数据库类型: {db_type}")
