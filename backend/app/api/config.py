"""
配置相关 API - 模型配置和数据库配置
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()


class ModelConfig(BaseModel):
    api_key: Optional[str] = None
    base_url: str
    model: str
    temperature: float = 0
    max_tokens: int = 2000


class DatabaseConfig(BaseModel):
    type: str  # sqlite, mysql, postgresql
    path: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    name: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None


@router.get("/model")
async def get_model_config():
    """获取模型配置"""
    return {
        "api_key": settings.LLM_API_KEY if settings.LLM_API_KEY else "",
        "base_url": settings.LLM_BASE_URL,
        "model": settings.LLM_MODEL,
        "temperature": 0,
        "max_tokens": 2000
    }


@router.post("/model")
async def update_model_config(config: ModelConfig):
    """更新模型配置（仅内存生效，重启后恢复）"""
    # 更新 settings（仅当前进程有效）
    if config.api_key is not None:
        settings.LLM_API_KEY = config.api_key if config.api_key else None
    if config.base_url:
        settings.LLM_BASE_URL = config.base_url
    if config.model:
        settings.LLM_MODEL = config.model

    return {
        "success": True,
        "message": "模型配置已更新（注意：重启服务后恢复默认）",
        "config": {
            "api_key": "***" if settings.LLM_API_KEY else "",
            "base_url": settings.LLM_BASE_URL,
            "model": settings.LLM_MODEL
        }
    }


@router.get("/database")
async def get_database_config():
    """获取数据库配置"""
    return {
        "type": settings.DB_TYPE,
        "path": settings.DB_PATH if settings.DB_TYPE == "sqlite" else None,
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "name": settings.DB_NAME,
        "user": settings.DB_USER,
        "password": "***" if settings.DB_PASSWORD else None
    }


@router.post("/database")
async def update_database_config(config: DatabaseConfig):
    """更新数据库配置（仅内存生效，重启后恢复）"""
    if config.type:
        settings.DB_TYPE = config.type
    if config.path is not None:
        settings.DB_PATH = config.path
    if config.host is not None:
        settings.DB_HOST = config.host
    if config.port is not None:
        settings.DB_PORT = config.port
    if config.name is not None:
        settings.DB_NAME = config.name
    if config.user is not None:
        settings.DB_USER = config.user
    if config.password is not None:
        settings.DB_PASSWORD = config.password

    return {
        "success": True,
        "message": "数据库配置已更新（注意：重启服务后恢复默认）",
        "config": {
            "type": settings.DB_TYPE,
            "path": settings.DB_PATH if settings.DB_TYPE == "sqlite" else None,
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "name": settings.DB_NAME
        }
    }


@router.get("/database/tables")
async def get_database_tables():
    """获取数据库表列表"""
    from app.core.database_adapter import get_db_adapter

    try:
        adapter = get_db_adapter()
        tables = adapter.get_tables()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/schema/{table_name}")
async def get_table_schema(table_name: str):
    """获取表结构"""
    from app.core.database_adapter import get_db_adapter

    try:
        adapter = get_db_adapter()
        schema = adapter.get_schema(table_name)
        return schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
