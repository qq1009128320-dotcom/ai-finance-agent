"""
AI Quantitative Strategy Platform v4 - API v1: Quant Endpoints
"""

from fastapi import APIRouter, HTTPException
from core.models import (
    QuantAnalysisRequest, QuantAnalysisResponse,
    MarketScanRequest, MarketScanResponse
)
from services.quant import quant_service

router = APIRouter()


@router.post("/analyze", response_model=QuantAnalysisResponse)
async def analyze_stock(request: QuantAnalysisRequest):
    """
    单股量化分析
    
    - **symbol**: 股票代码（如 600036）
    - **period**: K线周期（day/week/month）
    - **count**: K线数量（30-500）
    
    返回28因子综合量化评分报告。
    """
    try:
        return quant_service.analyze_stock(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/scan", response_model=MarketScanResponse)
async def scan_market(request: MarketScanRequest):
    """
    全市场扫描
    
    - **scope**: 扫描范围（top200/top500/all）
    - **min_score**: 最低评分
    - **sort_by**: 排序字段（score/volume/change）
    - **limit**: 返回数量
    
    返回市场情绪概览和强势/弱势个股列表。
    """
    try:
        return quant_service.scan_market(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"扫描失败: {str(e)}")


@router.get("/symbols")
async def get_symbols():
    """
    获取支持的交易标的列表
    
    返回A股股票代码列表。
    """
    # 简化版：返回示例列表
    # 完整实现应从akshare或tushare获取
    return {
        "symbols": [
            {"symbol": "600036", "name": "招商银行", "exchange": "SH"},
            {"symbol": "000001", "name": "平安银行", "exchange": "SZ"},
            {"symbol": "000858", "name": "五粮液", "exchange": "SZ"},
            {"symbol": "600519", "name": "贵州茅台", "exchange": "SH"},
            {"symbol": "000651", "name": "格力电器", "exchange": "SZ"},
        ],
        "total": 5,
        "note": "完整列表需接入数据源",
    }
