"""
AI智投量化平台 v4 - API v1: Health Endpoint
"""

from fastapi import APIRouter
from datetime import datetime
from core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    健康检查
    
    返回服务状态信息。
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "services": {
            "quant_engine": "ok",
            "data_service": "ok",
            "ai_service": "ok" if settings.DEEPSEEK_API_KEY else "disabled",
            "strategy_storage": "ok",
        }
    }


@router.get("/ready")
async def readiness_check():
    """
    就绪检查
    
    检查所有依赖服务是否就绪。
    """
    from services.data import data_service
    
    try:
        # 测试数据服务
        data_service.get_quotes_engine()
        data_status = "ready"
    except Exception:
        data_status = "unavailable"
    
    return {
        "status": "ready" if data_status == "ready" else "degraded",
        "data_service": data_status,
        "timestamp": datetime.now().isoformat(),
    }
