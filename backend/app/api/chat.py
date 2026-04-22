"""
聊天相关 API
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/send")
async def send_message():
    """发送消息（待实现）"""
    return {"message": "NL2SQL chat endpoint"}


@router.get("/stream/{conversation_id}")
async def stream_chat():
    """流式聊天（待实现）"""
    return {"message": "SSE streaming endpoint"}
