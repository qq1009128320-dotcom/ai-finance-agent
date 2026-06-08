"""
AI智投量化平台 v4 - API v1 Router
"""

from fastapi import APIRouter
from api.v1.endpoints import quant, strategy, backtest, health, ai, builder

api_router = APIRouter()

api_router.include_router(quant.router, prefix="/quant", tags=["量化分析"])
api_router.include_router(strategy.router, prefix="/strategy", tags=["策略管理"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["回测"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI策略"])
api_router.include_router(health.router, prefix="/system", tags=["系统"])
api_router.include_router(builder.router, prefix="/builder", tags=["策略编辑器"])

__all__ = ["api_router"]
