"""
AI Quantitative Strategy Platform v4 - API v1: AI Endpoints
"""

from fastapi import APIRouter, HTTPException
from core.models import (
    AIStrategyGenerateRequest, AIStrategyGenerateResponse
)
from services.ai import ai_service

router = APIRouter()


@router.post("/generate", response_model=AIStrategyGenerateResponse)
async def generate_strategy(request: AIStrategyGenerateRequest):
    """
    AI生成交易策略
    
    - **prompt**: 策略描述（自然语言）
    - **style**: 策略风格（conservative/balanced/aggressive）
    
    返回AI生成的策略代码和说明。
    """
    try:
        return ai_service.generate(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/validate")
async def validate_ai_strategy(code: str):
    """
    验证AI生成的策略代码
    
    - **code**: 策略代码
    
    返回验证结果。
    """
    is_valid, msg = ai_service.validate(code)
    return {"is_valid": is_valid, "message": msg}
