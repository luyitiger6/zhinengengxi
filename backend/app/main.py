"""
智能数据库查询系统 - FastAPI 后端入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, config, history
from app.core.database import init_db
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="基于大模型的NL2SQL可视化系统",
    version=settings.APP_VERSION
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api/chat", tags=["聊天"])
app.include_router(config.router, prefix="/api/config", tags=["配置"])
app.include_router(history.router, prefix="/api/history", tags=["历史"])


@app.on_event("startup")
async def startup():
    """启动时初始化"""
    await init_db()

    # 初始化向量库
    try:
        from app.core.vector_store import get_vector_store
        vector_store = get_vector_store()
        vector_store.init_collection()
        print("向量库初始化完成")
    except Exception as e:
        print(f"向量库初始化失败: {e}")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "智能数据库查询系统 API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
