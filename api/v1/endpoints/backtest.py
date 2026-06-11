"""
AI智投量化平台 v4 - API v1: Backtest Endpoints
免责声明：本平台仅供学习研究，不构成任何投资建议。
"""

from fastapi import APIRouter, HTTPException
from core.models import BacktestRequest, BacktestResponse
from services.backtest import backtest_service

router = APIRouter()


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    运行策略回测（需要用户确认风险声明）

    先检查用户是否已确认风险声明，再执行回测。
    required parameter: confirmed=True
    """
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="请先确认已阅读风险提示：回测结果不代表实盘表现，投资有风险。")
    try:
        return backtest_service.run_backtest(request)
    except Exception as e:
        import traceback
        print(f"[backtest/run ERROR] {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"回测失败: {str(e)}")


@router.post("/validate-and-run")
async def validate_and_run_backtest(request: BacktestRequest):
    """
    验证并运行回测（需要用户确认风险声明）

    先验证策略代码，确认用户已阅读风险提示，再执行回测。
    required parameter: confirmed=True
    """
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="请先确认已阅读风险提示：回测结果不代表实盘表现，投资有风险。")
    from services.strategy import strategy_service

    # 验证
    is_valid, msg = strategy_service.validate_code(request.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"策略代码无效: {msg}")

    # 运行回测
    try:
        return backtest_service.run_backtest(request)
    except Exception as e:
        import traceback
        print(f"[backtest/validate-and-run ERROR] {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"回测失败: {str(e)}")
