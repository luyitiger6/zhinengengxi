"""
历史记录相关 API
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import get_db_connection

router = APIRouter()


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class QueryHistoryResponse(BaseModel):
    id: int
    natural_language: str
    sql_query: str
    executed: bool
    error: Optional[str]
    created_at: str


@router.get("/conversations")
async def list_conversations(limit: int = 50, offset: int = 0):
    """获取对话列表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 获取对话列表（带消息数）
    cursor.execute(
        """SELECT c.id, c.title, c.created_at, c.updated_at,
                  (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) as msg_count
           FROM conversations c
           ORDER BY c.updated_at DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    )

    conversations = []
    for row in cursor.fetchall():
        conversations.append({
            "id": row[0],
            "title": row[1],
            "created_at": row[2],
            "updated_at": row[3],
            "message_count": row[4]
        })

    conn.close()
    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int):
    """获取单个对话详情"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT id, title, created_at, updated_at
           FROM conversations WHERE id = ?""",
        (conversation_id,)
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="对话不存在")

    conversation = {
        "id": row[0],
        "title": row[1],
        "created_at": row[2],
        "updated_at": row[3]
    }

    conn.close()
    return conversation


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: int, limit: int = 100, offset: int = 0):
    """获取消息历史"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT id, role, content, created_at
           FROM messages
           WHERE conversation_id = ?
           ORDER BY created_at ASC
           LIMIT ? OFFSET ?""",
        (conversation_id, limit, offset)
    )

    messages = []
    for row in cursor.fetchall():
        messages.append({
            "id": row[0],
            "role": row[1],
            "content": row[2],
            "created_at": row[3]
        })

    conn.close()
    return {"messages": messages}


@router.post("/conversations")
async def create_conversation(title: str = "新对话"):
    """创建新对话"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO conversations (title) VALUES (?)",
        (title,)
    )
    conv_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"id": conv_id, "title": title}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int):
    """删除对话（软删除，可选）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 删除关联消息
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    # 删除对话
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()

    if not deleted:
        raise HTTPException(status_code=404, detail="对话不存在")

    return {"success": True, "conversation_id": conversation_id}


@router.get("/query-history")
async def get_query_history(
    conversation_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
):
    """获取查询历史"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if conversation_id:
        cursor.execute(
            """SELECT id, conversation_id, natural_language, sql_query, executed, error, created_at
               FROM query_history
               WHERE conversation_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (conversation_id, limit, offset)
        )
    else:
        cursor.execute(
            """SELECT id, conversation_id, natural_language, sql_query, executed, error, created_at
               FROM query_history
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset)
        )

    history = []
    for row in cursor.fetchall():
        history.append({
            "id": row[0],
            "conversation_id": row[1],
            "natural_language": row[2],
            "sql_query": row[3],
            "executed": bool(row[4]),
            "error": row[5],
            "created_at": row[6]
        })

    conn.close()
    return {"history": history}


@router.get("/query-history/search")
async def search_query_history(keyword: str, limit: int = 20):
    """搜索查询历史"""
    conn = get_db_connection()
    cursor = conn.cursor()

    pattern = f"%{keyword}%"
    cursor.execute(
        """SELECT id, conversation_id, natural_language, sql_query, executed, error, created_at
           FROM query_history
           WHERE natural_language LIKE ? OR sql_query LIKE ?
           ORDER BY created_at DESC
           LIMIT ?""",
        (pattern, pattern, limit)
    )

    history = []
    for row in cursor.fetchall():
        history.append({
            "id": row[0],
            "conversation_id": row[1],
            "natural_language": row[2],
            "sql_query": row[3],
            "executed": bool(row[4]),
            "error": row[5],
            "created_at": row[6]
        })

    conn.close()
    return {"history": history}
