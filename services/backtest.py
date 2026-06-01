"""
AI智投量化平台 v4 - Backtest Service
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.data import data_service
from core.models import (
    BacktestRequest, BacktestResponse, BacktestMetrics, TradeRecord
)


class BacktestService:
    """回测服务"""
    
    def run_backtest(self, request: BacktestRequest) -> BacktestResponse:
        """
        运行策略回测
        
        Args:
            request: 回测请求
        
        Returns:
            回测响应
        """
        from quotes import TencentQuotes
        import pandas as pd
        import numpy as np
        
        symbol = request.symbol
        initial_capital = request.initial_capital
        
        # 获取K线数据
        kline_raw = data_service.get_kline(symbol, period="day", count=500)
        
        if not kline_raw:
            return BacktestResponse(
                symbol=symbol,
                start_date="",
                end_date="",
                status="error",
                message=f"无法获取{symbol} K线数据",
                metrics=BacktestMetrics(initial_capital=initial_capital),
                trades=[],
            )
        
        bars = kline_raw
        if len(bars) < 60:
            return BacktestResponse(
                symbol=symbol,
                start_date="",
                end_date="",
                status="error",
                message=f"K线数据不足: 仅有{len(bars)}根",
                metrics=BacktestMetrics(initial_capital=initial_capital),
                trades=[],
            )
        
        # 解析K线
        cols = ["date", "open", "close", "high", "low", "volume"]
        df = pd.DataFrame(bars, columns=cols[:len(bars[0])])
        for c in ["open", "close", "high", "low", "volume"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        
        # 创建执行环境
        class BacktestContext:
            def __init__(self):
                self.symbol = symbol
                self.portfolio = {
                    "cash": initial_capital,
                    "positions": {},
                    "trades": []
                }
                self.ma_short = 5
                self.ma_long = 20
                self.stop_loss = -0.08
                self.take_profit = 0.25
        
        context = BacktestContext()
        
        # 执行策略
        trades = []
        
        try:
            # 执行init
            local_vars = {}
            exec(request.code, {
                "__builtins__": __builtins__,
                "np": np,
                "pd": pd,
                "get_kline": lambda s, p, c: df.reset_index().values.tolist() if s == symbol else None,
                "context": context,
                "buy": lambda s, p, r: trades.append({"day": 0, "type": "buy", "symbol": s, "price": p, "reason": r}),
                "sell": lambda s, p, r: trades.append({"day": 0, "type": "sell", "symbol": s, "price": p, "reason": r}),
            }, local_vars)
            
            if "init" in local_vars:
                local_vars["init"](context)
            
            # 获取策略参数（从context或代码中）
            ma_short = getattr(context, "ma_short", 5)
            ma_long = getattr(context, "ma_long", 20)
            stop_loss = getattr(context, "stop_loss", -0.08)
            take_profit = getattr(context, "take_profit", 0.25)
            
            # 回测模拟
            close_prices = df["close"].values
            position = None
            cost_price = 0
            
            for i in range(20, len(close_prices)):
                current_price = close_prices[i]
                
                # 计算指标
                ma_s = np.mean(close_prices[i-ma_short:i])
                ma_l = np.mean(close_prices[i-ma_long:i])
                
                data = {symbol: {"close": current_price}}
                
                # 执行handle_data
                if "handle_data" in local_vars:
                    try:
                        local_vars["handle_data"](context, data)
                    except Exception:
                        pass
            
            # 计算指标
            total_trades = len(trades)
            buy_trades = [t for t in trades if t["type"] == "buy"]
            sell_trades = [t for t in trades if t["type"] == "sell"]
            
            # 简化收益率计算
            if buy_trades and sell_trades:
                total_return = (sell_trades[-1]["price"] - buy_trades[0]["price"]) / buy_trades[0]["price"] * 100
            else:
                total_return = 0
            
            final_capital = initial_capital * (1 + total_return / 100)
            
            return BacktestResponse(
                symbol=symbol,
                start_date=df.index[0].strftime("%Y-%m-%d"),
                end_date=df.index[-1].strftime("%Y-%m-%d"),
                status="success",
                message=f"回测完成: {total_trades}笔交易",
                metrics=BacktestMetrics(
                    total_return=round(total_return, 2),
                    total_trades=total_trades,
                    buy_count=len(buy_trades),
                    sell_count=len(sell_trades),
                    initial_capital=initial_capital,
                    final_capital=round(final_capital, 2),
                ),
                trades=[TradeRecord(
                    day=t.get("day"),
                    type=t["type"],
                    symbol=t["symbol"],
                    price=t["price"],
                    reason=t["reason"],
                ) for t in trades[-20:]],  # 最后20笔
            )
            
        except Exception as e:
            return BacktestResponse(
                symbol=symbol,
                start_date=df.index[0].strftime("%Y-%m-%d"),
                end_date=df.index[-1].strftime("%Y-%m-%d"),
                status="error",
                message=f"回测执行错误: {str(e)}",
                metrics=BacktestMetrics(initial_capital=initial_capital),
                trades=[],
            )


# 全局回测服务实例
backtest_service = BacktestService()
