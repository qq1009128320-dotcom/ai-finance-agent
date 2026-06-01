"""
AI智投量化平台 v4 - API v1: Strategy Endpoints
"""

from fastapi import APIRouter, HTTPException
from core.models import (
    StrategyCreateRequest, StrategyResponse, StrategyListResponse,
    StrategyValidateRequest, StrategyValidateResponse
)
from services.strategy import strategy_service

router = APIRouter()


@router.post("/create", response_model=StrategyResponse)
async def create_strategy(request: StrategyCreateRequest):
    """
    创建/保存策略
    
    - **name**: 策略名称
    - **code**: 策略代码（必须包含init和handle_data函数）
    - **description**: 策略描述
    - **tags**: 标签列表
    
    返回保存后的策略信息。
    """
    try:
        return strategy_service.create_strategy(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.get("/list", response_model=StrategyListResponse)
async def list_strategies():
    """
    获取所有策略列表
    
    返回已保存的策略列表，按创建时间倒序排列。
    """
    return strategy_service.list_strategies()


@router.get("/get/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: str):
    """
    获取单个策略
    
    - **strategy_id**: 策略ID
    
    返回策略详情。
    """
    result = strategy_service.get_strategy(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return result


@router.post("/validate", response_model=StrategyValidateResponse)
async def validate_strategy(request: StrategyValidateRequest):
    """
    验证策略代码
    
    - **code**: 策略代码
    
    返回验证结果（是否有效、错误信息）。
    """
    is_valid, msg = strategy_service.validate_code(request.code)
    return StrategyValidateResponse(is_valid=is_valid, message=msg)


@router.delete("/delete/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """
    删除策略
    
    - **strategy_id**: 策略ID
    
    删除指定策略。
    """
    result = strategy_service.delete_strategy(strategy_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return {"message": f"策略 {strategy_id} 已删除"}


@router.put("/update/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    code: str,
    name: str = None,
    description: str = None
):
    """
    更新策略
    
    - **strategy_id**: 策略ID
    - **code**: 新策略代码
    - **name**: 新名称（可选）
    - **description**: 新描述（可选）
    
    返回更新后的策略信息。
    """
    try:
        return strategy_service.update_strategy(
            strategy_id, code, name, description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
