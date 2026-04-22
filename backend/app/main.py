"""
智能数据库查询系统 - FastAPI 后端入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, config, history
from app.core.database import init_db

app = FastAPI(
    title="智能数据库查询系统",
    description="基于大模型的NL2SQL可视化系统",
    version="0.1.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
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
    """启动时初始化数据库"""
    await init_db()


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
