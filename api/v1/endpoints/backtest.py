"""
AI智投量化平台 v4 - API v1: Backtest Endpoints
"""

from fastapi import APIRouter, HTTPException
from core.models import BacktestRequest, BacktestResponse
from services.backtest import backtest_service

router = APIRouter()


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    运行策略回测
    
    - **code**: 策略代码（必须包含init和handle_data函数）
    - **symbol**: 回测标的（如 600036）
    - **start_date**: 开始日期（可选）
    - **end_date**: 结束日期（可选）
    - **initial_capital**: 初始资金（默认100000）
    
    返回回测结果，包括收益率、交易记录等。
    """
    try:
        return backtest_service.run_backtest(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回测失败: {str(e)}")


@router.post("/validate-and-run")
async def validate_and_run_backtest(request: BacktestRequest):
    """
    验证并运行回测
    
    先验证策略代码，再执行回测。
    """
    from services.strategy import strategy_service
    
    # 验证
    is_valid, msg = strategy_service.validate_code(request.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"策略代码无效: {msg}")
    
    # 运行回测
    return backtest_service.run_backtest(request)
