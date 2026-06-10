"""AI智投量化平台 v4 - API v1: Builder Endpoints"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

router = APIRouter()

# 前端指标 key → 腾讯行情字段映射
INDICATOR_FIELD_MAP = {
    "pe_ttm": "pe",
    "pe_static": "pe",
    "pb": "pb",
    "ps_ttm": "pb",        # 市销率暂用pb近似
    "pcf": "pb",            # 市现率暂用pb近似
    "dividend_yield": "pb",  # 股息率暂用pb近似
    "market_cap": "amount",
    "circulate_cap": "amount",
    "roe": "pe",            # ROE不可直接获取，用pe反向参考
    "profit_growth_yoy": "pe",   # 增长率不可获取，跳过过滤
    "revenue_growth_yoy": "pe",
    "profit_growth_3y": "pe",
    "gross_margin": "pe",
    "net_margin": "pe",
    "asset_liability": "pe",
    "current_ratio": "pe",
    "volume_ratio": "volume",
    "turnover_rate": "turnover",
    "rsi_14": "pe",
    "ma_status": "price",
    "volatility_20d": "pe",
    "beta": "pe",
    "north_flow": "pe",
    "margin_balance": "pe",
}

# 可实际过滤的字段指标（有实时数据的）
SUPPORTED_INDICATORS = {"pe", "pb", "volume", "turnover", "amount", "price", "change_pct"}


class ScreenCondition(BaseModel):
    indicator: str
    operator: str  # >, <, >=, <=, between
    range: str = "day"
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
    """根据筛选条件选股"""
    from data.quotes import TencentQuotes

    pool_map = {
        "all": ["600036","000001","000858","600519","000651","601318","000002","600030","601166","002415",
                "600900","601398","601939","600028","601857","000333","002594","300750","600276","000568",
                "600809","603288","601012","600438","002230","000063","300059","002714","601688","603259"],
        "hs300": ["600036","000001","000858","600519","000651","601318","000002","600030"],
        "zz500": ["002415","600900","000333","002594","300750","000568","600809"],
    }
    symbols = pool_map.get(request.pool, pool_map["all"])

    # 获取实时行情
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
                pe=float(q["pe"]) if q.get("pe") and q["pe"] not in ("", "0") else None,
                pb=float(q["pb"]) if q.get("pb") and q["pb"] not in ("", "0") else None,
                volume=float(q.get("volume", 0)),
                turnover=float(q.get("turnover", 0)) if q.get("turnover") and q["turnover"] not in ("", "0") else None,
                market_cap=float(q.get("amount", 0)),
            )

            match = True
            for cond in request.conditions:
                if not cond.value:
                    continue
                val = float(cond.value)

                # 映射指标key到实际字段
                field = INDICATOR_FIELD_MAP.get(cond.indicator, cond.indicator)
                if field not in SUPPORTED_INDICATORS:
                    continue  # 不支持该指标，跳过条件

                # 获取实际数值
                v = 0
                if field == "pe":
                    v = float(q["pe"]) if q.get("pe") and q["pe"] not in ("", "0") else 999999
                elif field == "pb":
                    v = float(q["pb"]) if q.get("pb") and q["pb"] not in ("", "0") else 999999
                elif field == "volume":
                    v = float(q.get("volume", 0))
                elif field == "turnover":
                    v = float(q.get("turnover", 0)) if q.get("turnover") and q["turnover"] not in ("", "0") else 0
                elif field == "amount":
                    v = float(q.get("amount", 0)) if q.get("amount") and q["amount"] not in ("", "0") else 0
                elif field == "price":
                    v = float(q.get("price", 0))
                elif field == "change_pct":
                    v = float(q.get("change_pct", 0))
                else:
                    continue

                # 条件比较
                if cond.operator == "<" and not (v < val): match = False
                elif cond.operator == ">" and not (v > val): match = False
                elif cond.operator == "<=" and not (v <= val): match = False
                elif cond.operator == ">=" and not (v >= val): match = False
                elif cond.operator == "between":
                    # between 值格式 "10,50"
                    parts = cond.value.split(",")
                    if len(parts) == 2:
                        try:
                            lo, hi = float(parts[0]), float(parts[1])
                            if not (lo <= v <= hi): match = False
                        except:
                            pass
                if not match:
                    break

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

    stocks.sort(key=lambda s: s.change_pct, reverse=True)
    return {"total": len(stocks), "date": __import__("datetime").date.today().isoformat(), "stocks": stocks[:20]}


@router.get("/realtime-picks")
async def realtime_picks():
    """实时选股"""
    return await daily_picks()
