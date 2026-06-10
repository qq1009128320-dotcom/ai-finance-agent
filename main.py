#!/usr/bin/env python3
"""
AI智投量化平台 v4 - FastAPI Backend Server
=============================================================

AI智投量化平台后端服务

启动方式:
    python main.py                  # 开发模式（前端由 Vite dev server 提供）
    PRODUCTION=true python main.py  # 生产模式（前端由 FastAPI 直接提供）
    uvicorn main:app --host 0.0.0.0 --port 8000

API文档:
    http://localhost:8000/docs  # Swagger UI
    http://localhost:8000/redoc # ReDoc
"""

import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings, PROJECT_ROOT
from api.v1 import api_router

# 生产模式标志：通过环境变量 PRODUCTION=true 开启
IS_PRODUCTION = os.environ.get("PRODUCTION", "").lower() in ("true", "1", "yes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"=" * 60)
    print(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  模式: {'生产模式' if IS_PRODUCTION else '开发模式'}")
    print(f"  启动时间: {__import__('datetime').datetime.now().isoformat()}")
    print(f"=" * 60)
    
    # 初始化策略目录
    from core.config import STRATEGY_DIR
    STRATEGY_DIR.mkdir(exist_ok=True, parents=True)

    # 生产模式：检查前端构建目录
    if IS_PRODUCTION:
        frontend_dist = PROJECT_ROOT / "frontend" / "dist"
        if frontend_dist.exists():
            print(f"  前端静态文件: {frontend_dist}")
        else:
            print(f"  ⚠️ 前端构建目录不存在: {frontend_dist}")
            print(f"  请先执行: cd frontend && npm install && npm run build")
    
    yield
    
    # 关闭时
    print("\n服务器关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## AI智投量化平台 v4

AI智投量化平台，支持：

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


# 生产模式：挂载前端静态文件 + SPA 路由支持
if IS_PRODUCTION:
    FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
    
    if FRONTEND_DIST.exists():
        # 挂载 assets 等静态资源
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")
        app.mount("/favicon.ico", StaticFiles(directory=str(FRONTEND_DIST)), name="favicon")
        
        # SPA 回退路由：所有非 API 路径返回 index.html
        @app.api_route("/{path:path}", methods=["GET"])
        async def serve_frontend(path: str):
            # 排除 API 路径
            if path.startswith("api/") or path.startswith("docs") or path.startswith("redoc") or path.startswith("openapi"):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            
            index_file = FRONTEND_DIST / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Frontend not built"}, status_code=500)
    else:
        # 前端未构建，定义一个友好的提示路由
        @app.get("/")
        async def frontend_not_built():
            return {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "status": "frontend_not_built",
                "message": "前端尚未构建，请在 frontend/ 目录中执行: npm install && npm run build",
                "docs": "/docs",
                "api": "/api/v1",
            }


# 非生产模式：根路径返回API信息
if not IS_PRODUCTION:
    @app.get("/")
    async def root():
        """根路径 - 返回API信息"""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "api": "/api/v1",
        }


# 健康检查（需要放在通配路由之前）
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
        reload=not IS_PRODUCTION,
        log_level=settings.LOG_LEVEL.lower(),
    )
