"""
AI智投量化平台 v4 - API v1: Quant Endpoints
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
        import traceback
        print(f"[quant/analyze ValueError] {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        print(f"[quant/analyze ERROR] {traceback.format_exc()}")
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
    获取支持的交易标的列表（仅示例）
    """
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


@router.get("/symbols/all")
async def get_all_symbols(scope: str = "top200"):
    """
    获取全市场A股股票代码列表
    
    - **scope**: 范围 top200 | top500 | all
    """
    import akshare as ak
    
    # 本地缓存：常用A股代码列表（从akshare定期同步）
    LOCAL_STOCKS = [
        {"symbol": "600036", "name": "招商银行", "exchange": "SH"},
        {"symbol": "000001", "name": "平安银行", "exchange": "SZ"},
        {"symbol": "000858", "name": "五粮液", "exchange": "SZ"},
        {"symbol": "600519", "name": "贵州茅台", "exchange": "SH"},
        {"symbol": "000651", "name": "格力电器", "exchange": "SZ"},
        {"symbol": "601318", "name": "中国平安", "exchange": "SH"},
        {"symbol": "000002", "name": "万科A", "exchange": "SZ"},
        {"symbol": "600030", "name": "中信证券", "exchange": "SH"},
        {"symbol": "601166", "name": "兴业银行", "exchange": "SH"},
        {"symbol": "002415", "name": "海康威视", "exchange": "SZ"},
        {"symbol": "600900", "name": "长江电力", "exchange": "SH"},
        {"symbol": "601398", "name": "工商银行", "exchange": "SH"},
        {"symbol": "601939", "name": "建设银行", "exchange": "SH"},
        {"symbol": "600028", "name": "中国石化", "exchange": "SH"},
        {"symbol": "601857", "name": "中国石油", "exchange": "SH"},
        {"symbol": "000333", "name": "美的集团", "exchange": "SZ"},
        {"symbol": "002594", "name": "比亚迪", "exchange": "SZ"},
        {"symbol": "300750", "name": "宁德时代", "exchange": "SZ"},
        {"symbol": "600276", "name": "恒瑞医药", "exchange": "SH"},
        {"symbol": "000568", "name": "泸州老窖", "exchange": "SZ"},
        {"symbol": "600809", "name": "山西汾酒", "exchange": "SH"},
        {"symbol": "603288", "name": "海天味业", "exchange": "SH"},
        {"symbol": "601012", "name": "隆基绿能", "exchange": "SH"},
        {"symbol": "600438", "name": "通威股份", "exchange": "SH"},
        {"symbol": "002230", "name": "科大讯飞", "exchange": "SZ"},
        {"symbol": "000063", "name": "中兴通讯", "exchange": "SZ"},
        {"symbol": "300059", "name": "东方财富", "exchange": "SZ"},
        {"symbol": "002714", "name": "牧原股份", "exchange": "SZ"},
        {"symbol": "601688", "name": "华泰证券", "exchange": "SH"},
        {"symbol": "603259", "name": "药明康德", "exchange": "SH"},
        {"symbol": "600000", "name": "浦发银行", "exchange": "SH"},
        {"symbol": "600016", "name": "民生银行", "exchange": "SH"},
        {"symbol": "600031", "name": "三一重工", "exchange": "SH"},
        {"symbol": "600104", "name": "上汽集团", "exchange": "SH"},
        {"symbol": "600309", "name": "万华化学", "exchange": "SH"},
        {"symbol": "600585", "name": "海螺水泥", "exchange": "SH"},
        {"symbol": "600887", "name": "伊利股份", "exchange": "SH"},
        {"symbol": "000100", "name": "TCL科技", "exchange": "SZ"},
        {"symbol": "000157", "name": "中联重科", "exchange": "SZ"},
        {"symbol": "000338", "name": "潍柴动力", "exchange": "SZ"},
    ]
    
    try:
        # 从akshare获取A股实时行情（包含所有A股）
        stock_zh_a_spot_df = ak.stock_zh_a_spot_em(timeout=10)
        
        if stock_zh_a_spot_df is None or len(stock_zh_a_spot_df) == 0:
            raise ValueError("akshare返回空数据")
        
        # 提取代码和名称
        symbols = []
        for _, row in stock_zh_a_spot_df.iterrows():
            code = str(row.get("代码", ""))
            name = str(row.get("名称", ""))
            exchange = "SH" if code.startswith("6") else "SZ"
            symbols.append({"symbol": code, "name": name, "exchange": exchange})
        
        # 如果数据量太少，补充本地缓存
        if len(symbols) < 50:
            existing = {s["symbol"] for s in symbols}
            for s in LOCAL_STOCKS:
                if s["symbol"] not in existing:
                    symbols.append(s)
        
        # 按范围截取
        if scope == "top200":
            symbols = symbols[:200]
        elif scope == "top500":
            symbols = symbols[:500]
        # all: 返回全部
        
        return {
            "symbols": symbols,
            "total": len(symbols),
            "scope": scope,
        }
    except Exception as e:
        # 降级：使用本地缓存
        print(f"[symbols/all] akshare failed: {e}, using local cache ({len(LOCAL_STOCKS)} stocks)")
        
        all_symbols = LOCAL_STOCKS.copy()
        if scope == "top200":
            all_symbols = all_symbols[:200]
        elif scope == "top500":
            all_symbols = all_symbols[:500]
        
        return {
            "symbols": all_symbols,
            "total": len(all_symbols),
            "scope": scope,
            "source": "local_cache",
            "warning": "akshare连接失败，使用本地缓存数据",
        }
