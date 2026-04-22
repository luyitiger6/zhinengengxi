"""
NL2SQL 核心逻辑 - 使用 requests 直接调用 oneapi
"""
import requests
from typing import Optional, List, Dict, Any, Tuple
from app.core.config import settings
from app.core.database import get_db_adapter
from app.core.security import validate_sql

# 全局 session
_session: Optional[requests.Session] = None


def get_session() -> requests.Session:
    """获取 HTTP session"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json"
        })
    return _session


def get_llm_response(prompt: str, system_prompt: str = None) -> Tuple[str, str]:
    """
    调用 LLM 获取响应

    Args:
        prompt: 用户 prompt
        system_prompt: 系统 prompt

    Returns:
        (response_text, error)
    """
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        session = get_session()
        response = session.post(
            f"{settings.LLM_BASE_URL}/chat/completions",
            json={
                "model": settings.LLM_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 2048,
            },
            timeout=60
        )

        if response.status_code != 200:
            return "", f"LLM API 错误: {response.status_code} - {response.text[:200]}"

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        return content.strip(), ""

    except requests.exceptions.Timeout:
        return "", "LLM 请求超时"
    except Exception as e:
        return "", f"LLM 请求失败: {str(e)}"


def get_database_schema() -> str:
    """获取数据库 schema 描述"""
    adapter = get_db_adapter()
    tables = adapter.get_tables()

    schema_parts = []
    for table in tables:
        schema = adapter.get_schema(table)
        cols = [f"  - {c['name']}: {c['type']}" for c in schema['columns']]
        schema_parts.append(f"表名: {table}\n" + "\n".join(cols))

    return "\n\n".join(schema_parts) if schema_parts else "暂无表"


# NL2SQL prompt 模板
NL2SQL_PROMPT = """你是一个SQL专家，根据用户的自然语言问题生成SQL查询语句。

数据库 schema:
{schema}

注意事项:
1. 只生成 SELECT 查询语句
2. 不要包含任何危险操作(DROP, DELETE, TRUNCATE等)
3. 使用正确的SQL语法

{context}

用户问题: {question}

请生成对应的 SQL 查询语句（只返回SQL，不要其他内容）:
"""


async def nl2sql(question: str, context: str = "") -> Tuple[str, str]:
    """
    自然语言转 SQL

    Args:
        question: 用户问题
        context: 对话上下文（可选）

    Returns:
        (sql, error)
    """
    try:
        # 获取数据库 schema
        schema = get_database_schema()

        # 构建 prompt
        context_section = f"对话历史:\n{context}\n" if context else ""
        prompt_text = NL2SQL_PROMPT.format(
            schema=schema,
            context=context_section,
            question=question
        )

        # 调用 LLM
        response_text, error = get_llm_response(
            prompt=prompt_text,
            system_prompt="你是一个SQL专家，只返回SQL语句，不要其他内容。"
        )

        if error:
            return "", error

        # 提取 SQL
        sql = response_text.strip()

        # 移除可能的 markdown 代码块
        if sql.startswith("```sql"):
            sql = sql[5:]
        elif sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()

        # 安全校验
        is_safe, error_msg = validate_sql(sql)
        if not is_safe:
            return "", f"SQL安全校验失败: {error_msg}"

        return sql, ""

    except Exception as e:
        return "", f"NL2SQL处理失败: {str(e)}"


async def execute_query(sql: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    执行 SQL 查询

    Args:
        sql: SQL 语句

    Returns:
        (results, error)
    """
    try:
        # 安全校验
        is_safe, error_msg = validate_sql(sql)
        if not is_safe:
            return [], f"SQL安全校验失败: {error_msg}"

        # 执行查询
        adapter = get_db_adapter()
        results = adapter.execute(sql)

        return results, ""

    except Exception as e:
        return [], f"SQL执行失败: {str(e)}"


async def add_query_to_history(conversation_id: int, natural_language: str, sql: str):
    """添加查询到历史"""
    from app.core.database import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO query_history (conversation_id, natural_language, sql_query, executed)
           VALUES (?, ?, ?, 1)""",
        (conversation_id, natural_language, sql)
    )
    conn.commit()
    conn.close()

    # 同时添加到向量库
    try:
        from app.core.vector_store import get_vector_store
        vector_store = get_vector_store()
        vector_store.add_query(
            query=natural_language,
            sql=sql,
            metadata={"conversation_id": conversation_id}
        )
    except Exception as e:
        print(f"向量库添加失败: {e}")


async def get_relevant_queries(question: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    获取相关的历史查询（使用 Qdrant 向量库）
    """
    try:
        from app.core.vector_store import get_vector_store
        vector_store = get_vector_store()
        return vector_store.search_similar(question, limit)
    except Exception as e:
        print(f"向量搜索失败: {e}")

    # 降级：使用数据库模糊匹配
    from app.core.database import get_db_connection

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        keywords = [w for w in question if len(w) > 1]
        if not keywords:
            return []

        pattern = f"%{'%'.join(keywords[:3])}%"
        cursor.execute(
            """SELECT natural_language, sql_query, created_at
               FROM query_history
               WHERE natural_language LIKE ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (pattern, limit)
        )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    except Exception:
        return []
