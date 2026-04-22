"""
MySQL 数据库适配器
"""
from typing import List, Dict, Any, Optional
import pymysql
from app.core.database_adapter import DatabaseAdapter


class MySQLAdapter(DatabaseAdapter):
    """MySQL 数据库适配器"""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        charset: str = "utf8mb4"
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.charset = charset
        self.conn: Optional[pymysql.Connection] = None

    def connect(self) -> None:
        self.conn = pymysql.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            charset=self.charset,
            cursorclass=pymysql.cursors.DictCursor
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
                   WHERE table_schema = %s AND table_type = 'BASE TABLE'""",
                (self.database,)
            )
            return [row['TABLE_NAME'] for row in cursor.fetchall()]

    def get_schema(self, table: str) -> Dict[str, Any]:
        if not self.conn:
            self.connect()

        with self.conn.cursor() as cursor:
            # 获取列信息
            cursor.execute(
                """SELECT column_name, data_type, is_nullable, column_key, column_default
                   FROM information_schema.columns
                   WHERE table_schema = %s AND table_name = %s
                   ORDER BY ordinal_position""",
                (self.database, table)
            )
            columns = cursor.fetchall()

            # 获取主键
            cursor.execute(
                """SELECT column_name
                   FROM information_schema.key_column_usage
                   WHERE table_schema = %s AND table_name = %s AND constraint_name = 'PRIMARY'""",
                (self.database, table)
            )
            primary_keys = [row['COLUMN_NAME'] for row in cursor.fetchall()]

            # 获取外键
            cursor.execute(
                """SELECT column_name, referenced_table_name, referenced_column_name
                   FROM information_schema.key_column_usage
                   WHERE table_schema = %s AND table_name = %s
                   AND referenced_table_name IS NOT NULL""",
                (self.database, table)
            )
            foreign_keys = cursor.fetchall()

        return {
            "table_name": table,
            "columns": [
                {
                    "name": col['COLUMN_NAME'],
                    "type": col['DATA_TYPE'],
                    "nullable": col['IS_NULLABLE'] == 'YES',
                    "primary_key": col['COLUMN_NAME'] in primary_keys,
                    "default": col['COLUMN_DEFAULT']
                }
                for col in columns
            ],
            "foreign_keys": [
                {
                    "column": fk['COLUMN_NAME'],
                    "references": f"{fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}"
                }
                for fk in foreign_keys
            ]
        }
