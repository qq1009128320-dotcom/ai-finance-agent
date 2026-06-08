"""AI智投量化平台 v4 - API v1: Builder Endpoints"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

router = APIRouter()

class ScreenCondition(BaseModel):
    indicator: str
    operator: str  # >, <, >=, <=, between
    value: str

class ScreenRequest(BaseModel):
    pool: str = "all"
    conditions: List[ScreenCondition] = []
    condition_logic: str = "AND"
    limit: int = 50
    date: Optional[str] = None  # 历史日期 YYYY-MM-DD

class StockItem(BaseModel):
    symbol: str
    name: str
    price: float
    change_pct: float
    pe: Optional[float] = None
    pb: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None
    market_cap: Optional[float] = None

class ScreenResponse(BaseModel):
    total: int
    stocks: List[StockItem]


@router.post("/screen", response_model=ScreenResponse)
async def screen_stocks(request: ScreenRequest):
    """根据筛选条件回算历史选股"""
    from services.data import data_service
    from data.quotes import TencentQuotes

    pool_map = {
        "all": ["600036","000001","000858","600519","000651","601318","000002","600030","601166","002415",
                "600900","601398","601939","600028","601857","000333","002594","300750","600276","000568",
                "600809","603288","601012","600438","002230","000063","300059","002714","601688","603259"],
        "hs300": ["600036","000001","000858","600519","000651","601318","000002","600030"],
        "zz500": ["002415","600900","000333","002594","300750","000568","600809"],
    }
    symbols = pool_map.get(request.pool, pool_map["all"])

    # 获取实时行情（作为当前基本面数据参考）
    engine = TencentQuotes()
    quotes = engine.get_quotes(symbols)
    quote_map = {q.get("code", ""): q for q in quotes}

    stocks = []
    for sym in symbols:
        try:
            q = quote_map.get(sym, {})
            item = StockItem(
                symbol=sym,
                name=q.get("name", sym),
                price=float(q.get("price", 0)),
                change_pct=float(q.get("change_pct", 0)),
                volume=float(q.get("volume", 0)),
                turnover=float(q.get("turnover", 0)),
            )
            match = True
            for cond in request.conditions:
                val = float(cond.value) if cond.value else 0
                if cond.indicator == "pe":
                    v = float(q.get("pe", 0)) if q.get("pe") else 0
                elif cond.indicator == "volume_ratio":
                    v = float(q.get("volume", 0))
                elif cond.indicator == "market_cap":
                    v = float(q.get("amount", 0)) if q.get("amount") else 0
                elif cond.indicator == "turnover_rate":
                    v = float(q.get("turnover", 0)) if q.get("turnover") else 0
                else:
                    v = 0
                if cond.operator == "<" and not (v < val): match = False
                elif cond.operator == ">" and not (v > val): match = False
                elif cond.operator == "<=" and not (v <= val): match = False
                elif cond.operator == ">=" and not (v >= val): match = False
                if not match: break
            if match:
                stocks.append(item)
        except Exception:
            continue

    # 按涨跌幅排序
    stocks.sort(key=lambda s: s.change_pct, reverse=True)
    return ScreenResponse(total=len(stocks), stocks=stocks[:request.limit])


@router.get("/daily-picks")
async def daily_picks():
    """每日选股（基于当前行情）"""
    from services.data import data_service
    from data.quotes import TencentQuotes

    symbols = ["600036","000001","000858","600519","000651","601318","000002","600030",
               "601166","002415","600900","601398","601939","600028","601857",
               "000333","002594","300750","600276","000568","600809","603288",
               "601012","600438","002230","000063","300059","002714","601688","603259"]

    engine = TencentQuotes()
    quotes = engine.get_quotes(symbols)

    stocks = []
    for q in quotes:
        try:
            change = float(q.get("change_pct", 0))
            vol = float(q.get("volume", 0))
            price = float(q.get("price", 0))
            stocks.append(StockItem(
                symbol=q.get("code",""), name=q.get("name",""),
                price=price, change_pct=change, volume=vol,
            ))
        except:
            continue

    # 按涨跌幅排序
    stocks.sort(key=lambda s: s.change_pct, reverse=True)
    return {"total": len(stocks), "date": __import__("datetime").date.today().isoformat(), "stocks": stocks[:20]}


@router.get("/realtime-picks")
async def realtime_picks():
    """实时选股"""
    return await daily_picks()
