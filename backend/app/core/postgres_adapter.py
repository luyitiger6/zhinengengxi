"""
PostgreSQL 数据库适配器
"""
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.database_adapter import DatabaseAdapter


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL 数据库适配器"""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.conn: Optional[psycopg2.connection] = None

    def connect(self) -> None:
        self.conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            cursor_factory=RealDictCursor
        )

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        if not self.conn:
            self.connect()

        with self.conn.cursor() as cursor:
            cursor.execute(sql, params or ())

            if sql.strip().upper().startswith('SELECT'):
                return cursor.fetchall()

            self.conn.commit()
            return [{"rows_affected": cursor.rowcount}]

    def get_tables(self) -> List[str]:
        if not self.conn:
            self.connect()

        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT table_name FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"""
            )
            return [row['table_name'] for row in cursor.fetchall()]

    def get_schema(self, table: str) -> Dict[str, Any]:
        if not self.conn:
            self.connect()

        with self.conn.cursor() as cursor:
            # 获取列信息
            cursor.execute(
                """SELECT column_name, data_type, is_nullable, column_default
                   FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = %s
                   ORDER BY ordinal_position""",
                (table,)
            )
            columns = cursor.fetchall()

            # 获取主键
            cursor.execute(
                """SELECT a.attname as column_name
                   FROM pg_index i
                   JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                   JOIN pg_class c ON c.oid = i.indrelid
                   WHERE i.indrelid = %s::regclass AND i.indisprimary
                   AND a.attnum > 0 AND NOT a.attisdropped""",
                (table,)
            )
            primary_keys = [row['column_name'] for row in cursor.fetchall()]

            # 获取外键
            cursor.execute(
                """SELECT
                       kcu.column_name,
                       ccu.table_name AS referenced_table,
                       ccu.column_name AS referenced_column
                   FROM information_schema.key_column_usage kcu
                   JOIN information_schema.constraint_column_usage ccu
                     ON ccu.constraint_name = kcu.constraint_name
                   WHERE kcu.table_name = %s AND kcu.table_schema = 'public'
                     AND ccu.table_schema = 'public'""",
                (table,)
            )
            foreign_keys = cursor.fetchall()

        return {
            "table_name": table,
            "columns": [
                {
                    "name": col['column_name'],
                    "type": col['data_type'],
                    "nullable": col['is_nullable'] == 'YES',
                    "primary_key": col['column_name'] in primary_keys,
                    "default": col['column_default']
                }
                for col in columns
            ],
            "foreign_keys": [
                {
                    "column": fk['column_name'],
                    "references": f"{fk['referenced_table']}.{fk['referenced_column']}"
                }
                for fk in foreign_keys
            ]
        }
