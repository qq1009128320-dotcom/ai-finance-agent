#!/usr/bin/env python3
"""
AI Quantitative Strategy Platform v4 - FastAPI Backend Server
=============================================================

AI辅助量化策略平台后端服务

启动方式:
    python main.py              # 开发模式
    uvicorn main:app --reload   # 开发模式（热重载）
    uvicorn main:app --host 0.0.0.0 --port 8000  # 生产模式

API文档:
    http://localhost:8000/docs  # Swagger UI
    http://localhost:8000/redoc # ReDoc
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings, PROJECT_ROOT
from api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"=" * 60)
    print(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  启动时间: {__import__('datetime').datetime.now().isoformat()}")
    print(f"=" * 60)
    
    # 初始化策略目录
    from core.config import STRATEGY_DIR
    STRATEGY_DIR.mkdir(exist_ok=True, parents=True)
    
    yield
    
    # 关闭时
    print("\n服务器关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## AI量化策略平台 v4

AI辅助的量化策略平台，支持：

- **量化分析**: 28因子综合评分、单股深度分析、全市场扫描
- **AI策略生成**: 自然语言描述生成可执行策略代码
- **策略回测**: 模拟历史交易验证策略有效性
- **策略管理**: 保存、加载、编辑、删除策略

### 快速开始

1. 调用 `/api/v1/ai/generate` 生成策略
2. 调用 `/api/v1/backtest/run` 回测策略
3. 调用 `/api/v1/strategy/create` 保存策略
    """,
    lifespan=lifespan,
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# 根路径
@app.get("/")
async def root():
    """根路径 - 返回API信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": "/api/v1",
    }


# 健康检查（根路径）
@app.get("/health")
async def health():
    """健康检查"""
    from datetime import datetime
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
