"""
聊天相关 API - NL2SQL 核心接口
"""
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.database import get_db_connection, get_db_adapter
from app.core.nl2sql import nl2sql, execute_query, add_query_to_history, get_relevant_queries
from app.core.security import validate_sql

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class ConversationContext:
    """对话上下文管理器"""

    def __init__(self):
        self.conversations: dict[str, list] = {}
        self.conversation_meta: dict[str, dict] = {}

    def get_or_create(self, conversation_id: Optional[str]) -> str:
        """获取或创建会话ID"""
        if conversation_id and conversation_id in self.conversations:
            return conversation_id

        conv_id = conversation_id or str(uuid.uuid4())
        self.conversations[conv_id] = []
        self.conversation_meta[conv_id] = {
            "created_at": datetime.now().isoformat()
        }
        return conv_id

    def add_message(self, conv_id: str, role: str, content: str, sql: str = None):
        """添加消息到上下文"""
        if conv_id not in self.conversations:
            self.get_or_create(conv_id)

        msg = {"role": role, "content": content}
        if sql:
            msg["sql"] = sql
        self.conversations[conv_id].append(msg)

    def get_context(self, conv_id: str, limit: int = 10) -> str:
        """获取对话上下文"""
        if conv_id not in self.conversations:
            return ""

        messages = self.conversations[conv_id][-limit:]
        context_parts = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "助手"
            context_parts.append(f"{role}: {msg['content']}")
            if "sql" in msg:
                context_parts.append(f"  [SQL]: {msg['sql']}")
        return "\n".join(context_parts)

    def clear(self, conv_id: str):
        """清除会话"""
        if conv_id in self.conversations:
            del self.conversations[conv_id]
        if conv_id in self.conversation_meta:
            del self.conversation_meta[conv_id]


# 全局上下文实例
context = ConversationContext()


@router.post("/send")
async def send_message(request: ChatRequest):
    """
    发送消息（非流式，用于测试）
    """
    conv_id = context.get_or_create(str(request.conversation_id) if request.conversation_id else None)

    # 保存用户消息
    context.add_message(conv_id, "user", request.message)

    # NL2SQL 处理
    sql, error = await nl2sql(request.message)

    if error:
        response_content = f"抱歉，处理失败: {error}"
    elif sql:
        # 执行查询
        results, exec_error = await execute_query(sql)

        if exec_error:
            response_content = f"SQL执行失败: {exec_error}"
        else:
            # 保存到数据库
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # 确保 conversation 存在
                cursor.execute(
                    """INSERT OR IGNORE INTO conversations (id, title) VALUES (?, ?)""",
                    (1, "默认对话")
                )

                cursor.execute(
                    """INSERT INTO messages (conversation_id, role, content)
                       VALUES (1, 'user', ?)""",
                    (request.message,)
                )
                cursor.execute(
                    """INSERT INTO messages (conversation_id, role, content)
                       VALUES (1, 'assistant', ?)""",
                    (f"执行成功，结果: {json.dumps(results, ensure_ascii=False)}",)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"保存历史失败: {e}")

            # 保存查询历史
            await add_query_to_history(1, request.message, sql)

            if results:
                response_content = f"SQL: {sql}\n\n结果:\n{json.dumps(results, ensure_ascii=False, indent=2)}"
            else:
                response_content = f"SQL: {sql}\n\n查询成功，但没有返回结果"

    else:
        response_content = "抱歉，无法理解您的问题"

    # 保存助手消息
    context.add_message(conv_id, "assistant", response_content, sql if sql else None)

    return {
        "conversation_id": conv_id,
        "response": response_content,
        "sql": sql if sql else None,
    }


@router.post("/stream")
async def stream_message(request: ChatRequest):
    """
    流式发送消息（SSE）
    """
    conv_id = context.get_or_create(str(request.conversation_id) if request.conversation_id else None)

    async def generate() -> AsyncGenerator[str, None]:
        # 保存用户消息
        context.add_message(conv_id, "user", request.message)

        # 发送用户消息确认
        yield json.dumps({"type": "user_message", "content": request.message}, ensure_ascii=False) + "\n"

        # NL2SQL 处理
        sql, error = await nl2sql(request.message)

        if error:
            yield json.dumps({"type": "error", "content": error}, ensure_ascii=False) + "\n"
            return

        if not sql:
            yield json.dumps({"type": "assistant", "content": "抱歉，无法理解您的问题"}, ensure_ascii=False) + "\n"
            return

        # 发送 SQL
        yield json.dumps({"type": "sql", "content": sql}, ensure_ascii=False) + "\n"

        # 执行查询
        results, exec_error = await execute_query(sql)

        if exec_error:
            yield json.dumps({"type": "error", "content": exec_error}, ensure_ascii=False) + "\n"
            return

        # 发送结果
        if results:
            result_text = f"查询成功，返回 {len(results)} 条结果:\n"
            for i, row in enumerate(results[:10], 1):
                result_text += f"\n{i}. {row}"
            if len(results) > 10:
                result_text += f"\n... 还有 {len(results) - 10} 条结果"
        else:
            result_text = "查询成功，但没有返回结果"

        yield json.dumps({"type": "assistant", "content": result_text}, ensure_ascii=False) + "\n"

        # 保存助手消息
        context.add_message(conv_id, "assistant", result_text, sql)

        # 保存到数据库
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO conversations (id, title) VALUES (1, '默认对话')"""
            )
            cursor.execute(
                """INSERT INTO messages (conversation_id, role, content) VALUES (1, 'user', ?)""",
                (request.message,)
            )
            cursor.execute(
                """INSERT INTO messages (conversation_id, role, content) VALUES (1, 'assistant', ?)""",
                (result_text,)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"保存历史失败: {e}")

        # 保存查询历史
        await add_query_to_history(1, request.message, sql)

        yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    context.clear(conversation_id)
    return {"success": True}


@router.get("/conversation/{conversation_id}/context")
async def get_conversation_context(conversation_id: str, limit: int = 10):
    """获取对话上下文"""
    ctx = context.get_context(conversation_id, limit)
    return {"conversation_id": conversation_id, "context": ctx}


@router.get("/relevant-queries")
async def get_relevant(question: str, limit: int = 3):
    """获取相关历史查询"""
    queries = await get_relevant_queries(question, limit)
    return {"queries": queries}
