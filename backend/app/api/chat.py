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
    """对话上下文管理器（内存中）"""

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


def get_or_create_conversation(conv_id: Optional[int] = None) -> int:
    """获取或创建数据库对话"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if conv_id:
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,))
        if cursor.fetchone():
            conn.close()
            return conv_id

    # 创建新对话
    title = f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    cursor.execute("INSERT INTO conversations (title) VALUES (?)", (title,))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def save_message(conv_id: int, role: str, content: str):
    """保存消息到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conv_id, role, content)
    )
    conn.commit()
    conn.close()


@router.post("/send")
async def send_message(request: ChatRequest):
    """
    发送消息（非流式，用于测试）
    """
    # 校验用户输入（禁止SQL输入）
    is_valid, error_msg = validate_user_input(request.message)
    if not is_valid:
        return {
            "conversation_id": request.conversation_id,
            "response": error_msg,
            "sql": None,
        }

    conv_id = get_or_create_conversation(request.conversation_id)
    context_conv_id = context.get_or_create(str(conv_id))

    # 保存用户消息
    context.add_message(context_conv_id, "user", request.message)
    save_message(conv_id, "user", request.message)

    # 获取上下文用于多轮对话
    ctx = context.get_context(context_conv_id)

    # NL2SQL 处理
    sql, error = await nl2sql(request.message, context=ctx)

    if error:
        response_content = f"抱歉，处理失败: {error}"
    elif sql:
        # 执行查询
        results, exec_error = await execute_query(sql)

        if exec_error:
            response_content = f"SQL执行失败: {exec_error}"
        else:
            # 保存查询历史
            await add_query_to_history(conv_id, request.message, sql)

            if results:
                response_content = f"SQL: {sql}\n\n结果:\n{json.dumps(results, ensure_ascii=False, indent=2)}"
            else:
                response_content = f"SQL: {sql}\n\n查询成功，但没有返回结果"

    else:
        response_content = "抱歉，无法理解您的问题"

    # 保存助手消息
    context.add_message(context_conv_id, "assistant", response_content, sql if sql else None)
    save_message(conv_id, "assistant", response_content)

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
    conv_id = get_or_create_conversation(request.conversation_id)
    context_conv_id = context.get_or_create(str(conv_id))

    # 如果是对话中第一次发送用户消息，更新标题为消息摘要
    if request.conversation_id is None:
        title = request.message[:20] + "..." if len(request.message) > 20 else request.message
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conv_id))
        conn.commit()
        conn.close()

    async def generate() -> AsyncGenerator[str, None]:
        # 如果是新建对话，返回对话ID给前端
        if request.conversation_id is None:
            yield json.dumps({"type": "conversation", "id": conv_id, "title": request.message[:20]}, ensure_ascii=False) + "\n"

        # 保存用户消息到上下文
        context.add_message(context_conv_id, "user", request.message)

        # 发送用户消息确认
        yield json.dumps({"type": "user_message", "content": request.message}, ensure_ascii=False) + "\n"

        # 获取上下文
        ctx = context.get_context(context_conv_id)

        # NL2SQL 处理（带上下文）
        sql, error = await nl2sql(request.message, context=ctx)

        if error:
            yield json.dumps({"type": "error", "content": error}, ensure_ascii=False) + "\n"
            save_message(conv_id, "assistant", f"错误: {error}")
            return

        if not sql:
            yield json.dumps({"type": "assistant", "content": "抱歉，无法理解您的问题"}, ensure_ascii=False) + "\n"
            save_message(conv_id, "assistant", "抱歉，无法理解您的问题")
            return

        # 执行查询
        results, exec_error = await execute_query(sql)

        if exec_error:
            yield json.dumps({"type": "error", "content": exec_error}, ensure_ascii=False) + "\n"
            save_message(conv_id, "assistant", f"错误: {exec_error}")
            return

        # 使用 LLM 流式生成自然语言回答
        from app.core.nl2sql import get_llm_response_stream

        results_str = str(results) if results else "无结果"
        result_prompt = f"""用户问题: {request.message}
执行的SQL: {sql}
查询结果: {results_str}

请根据查询结果，用自然语言回答用户的问题。回答要简洁明了。"""

        full_response = ""
        thinking_content = ""
        for event in get_llm_response_stream(
            prompt=result_prompt,
            system_prompt="你是一个友好的数据查询助手，根据SQL查询结果用自然语言回答用户的问题。"
        ):
            if isinstance(event, tuple) and event[0] == "thinking":
                thinking_content += event[1]
                yield json.dumps({"type": "thinking", "content": event[1]}, ensure_ascii=False) + "\n"
            else:
                full_response += event
                yield json.dumps({"type": "assistant", "content": event}, ensure_ascii=False) + "\n"

        # 保存助手消息到上下文和数据库
        context.add_message(context_conv_id, "assistant", full_response, sql)
        save_message(conv_id, "assistant", full_response)

        # 保存查询历史
        await add_query_to_history(conv_id, request.message, sql)

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
