"""
后端配置文件
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "智能数据库查询系统"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS配置
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]

    # LLM配置 (MiniMax via oneapi)
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "http://localhost:3000/v1"
    LLM_MODEL: str = "MiniMax-M2.7-highspeed"

    # 数据库配置
    DB_TYPE: str = "sqlite"  # sqlite, mysql, postgresql
    DB_PATH: str = "data/zhinengengxi.db"
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None

    # Qdrant配置
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "query_history"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
