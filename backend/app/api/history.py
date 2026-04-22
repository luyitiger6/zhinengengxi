"""
历史记录相关 API
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/conversations")
async def list_conversations():
    """获取对话列表（待实现）"""
    return {"conversations": []}


@router.get("/conversations/{conversation_id}/messages")
async def get_messages():
    """获取消息历史（待实现）"""
    return {"messages": []}


@router.get("/query-history")
async def get_query_history():
    """获取查询历史（待实现）"""
    return {"history": []}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation():
    """删除对话（待实现）"""
    return {"success": True}
