"""
配置相关 API
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/model")
async def get_model_config():
    """获取模型配置（待实现）"""
    return {
        "api_key": "",
        "base_url": "http://localhost:3000/v1",
        "model": "MiniMax-M2.7-highspeed"
    }


@router.post("/model")
async def update_model_config():
    """更新模型配置（待实现）"""
    return {"message": "Model config update endpoint"}


@router.get("/database")
async def get_database_config():
    """获取数据库配置（待实现）"""
    return {"type": "sqlite", "path": ""}


@router.post("/database")
async def update_database_config():
    """更新数据库配置（待实现）"""
    return {"message": "Database config update endpoint"}
