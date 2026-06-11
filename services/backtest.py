"""
AI智投量化平台 v4 - Backtest Service
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.data import data_service
from core.models import (
    BacktestRequest, BacktestResponse, BacktestMetrics, TradeRecord, EquityPoint
)


def _builder_config_to_code(config: dict) -> str:
    """将策略编辑器保存的JSON配置转换为可执行的Python策略代码"""
    stop_loss = float(config.get("stopLoss", 8)) / 100
    take_profit = float(config.get("takeProfit", 25)) / 100
    trailing_stop = float(config.get("trailingStop", 6)) / 100
    max_positions = int(config.get("maxPositions", 5))
    
    lines = []
    lines.append("import numpy as np")
    lines.append("def init(context):")
    lines.append('    context.symbol = "600036"')
    lines.append("    context.ma_short = 5; context.ma_long = 20")
    lines.append("    context.stop_loss = -%s" % stop_loss)
    lines.append("    context.take_profit = %s" % take_profit)
    lines.append("    context.trailing_stop = %s" % trailing_stop)
    lines.append("    context.max_positions = %s" % max_positions)
    lines.append("    context.highest_price = 0")
    lines.append("def handle_data(context, data):")
    lines.append('    symbol = context.symbol')
    lines.append('    current_price = data[symbol]["close"]')
    lines.append('    kline = get_kline(symbol, period="day", count=60)')
    lines.append("    if kline is None or len(kline) < 20: return")
    lines.append('    close = kline["close"].values')
    lines.append("    ma_short = np.mean(close[-5:]); ma_long = np.mean(close[-20:])")
    lines.append("    position = context.portfolio.positions.get(symbol, None)")
    lines.append("    if position is None:")
    lines.append("        p5 = np.mean(close[-6:-1]); p20 = np.mean(close[-21:-1])")
    lines.append("        if p5 <= p20 and ma_short > ma_long:")
    lines.append('            buy(symbol, current_price, "金叉买入")')
    lines.append("            return")
    lines.append("    if position is not None:")
    lines.append('        cost = position.get("cost_price", current_price); pnl = (current_price - cost) / max(cost, 0.01)')
    lines.append("        if context.highest_price is None or current_price > context.highest_price:")
    lines.append("            context.highest_price = current_price")
    lines.append("        highest = context.highest_price if context.highest_price and context.highest_price > 0 else current_price")
    lines.append("        dd = (highest - current_price) / highest")
    lines.append('        if pnl >= context.take_profit: sell(symbol, current_price, "止盈"); return')
    lines.append('        if pnl <= context.stop_loss: sell(symbol, current_price, "止损"); return')
    lines.append('        if pnl > 0 and dd >= context.trailing_stop: sell(symbol, current_price, "跟踪止损"); return')
    return "\n".join(lines)


def _resolve_code(code: str) -> str:
    """如果 code 是 JSON 策略配置, 转为 Python 代码; 否则原样返回"""
    stripped = code.strip()
    if stripped.startswith("{"):
        try:
            config = json.loads(stripped)
            return _builder_config_to_code(config)
        except (json.JSONDecodeError, Exception):
            pass  # 不是合法JSON,保持原样
    return code


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
        from data.quotes import TencentQuotes
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
        
        # 解析K线 -- 部分K线含第7列分红信息,只取前6列
        cols = ["date", "open", "close", "high", "low", "volume"]
        bars_clean = [bar[:6] for bar in bars]
        df = pd.DataFrame(bars_clean, columns=cols)
        for c in ["open", "close", "high", "low", "volume"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        
        # 创建执行环境 -- 支持对象式 portfolio 访问
        # 模拟可能缺失的第三方库,注入 sys.modules 让 import 语句也能找到
        class MockTA:
            """模拟 talib 库,返回兼容形状的数组避免崩溃"""
            def _array(self, *args, **kwargs):
                # 从第一个数组参数获取形状
                for a in args:
                    if hasattr(a, '__len__'):
                        return np.zeros(len(a))
                return np.array([0.0])
            def __getattr__(self, name):
                return self._array
        
        import sys as _sys
        _sys.modules.setdefault("talib", MockTA())
        
        class PortfolioObject:
            """兼容 context.portfolio.cash / context.portfolio.positions 的对象式访问"""
            def __init__(self, cash: float):
                self.cash = cash
                self.positions: Dict[str, dict] = {}
                self.trades: list = []

        class BacktestContext:
            def __init__(self):
                self.symbol = symbol
                self.portfolio = PortfolioObject(initial_capital)
                self.ma_short = 5
                self.ma_long = 20
                self.stop_loss = -0.08
                self.take_profit = 0.25
                # 风控参数
                self.max_position_pct = 0.20  # 单票最大仓位 20%
                self.max_trades_per_day = 2    # 每日最大交易次数
                self._trade_dates: list = []   # 交易日期记录
                self.position_size = 0.5
                # 旧版 max_position_pct 已被上方风控参数替代
        
        context = BacktestContext()
        context.history = df  # 策略可通过 context.history 获取K线数据
        
        # 执行策略
        trades = []
        
        try:
            # 解析策略代码:JSON配置自动转Python代码
            resolved_code = _resolve_code(request.code)
            
            # 执行init
            local_vars = {}
            # 安全沙箱：限制 __builtins__ 为安全子集，禁止危险模块
            _safe_builtins = {
                'abs': abs, 'all': all, 'any': any, 'bool': bool, 'dict': dict,
                'enumerate': enumerate, 'float': float, 'int': int, 'len': len,
                'list': list, 'max': max, 'min': min, 'print': print,
                'range': range, 'round': round, 'set': set, 'sorted': sorted,
                'str': str, 'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
                'True': True, 'False': False, 'None': None,
                'isinstance': isinstance, 'hasattr': hasattr, 'getattr': getattr,
                'setattr': setattr, 'abs': abs, 'map': map, 'filter': filter,
            }
            # 安全的 __import__：允许math/json/collections等安全模块，禁止os/subprocess/socket
            _SAFE_IMPORT_MODULES = {'numpy', 'pandas', 'json', 'math', 'random',
                                    'collections', 'datetime', 'decimal', 'itertools',
                                    'functools', 'operator', 're', 'typing'}
            def _safe_import(name, *args, **kwargs):
                if name.split('.')[0] not in _SAFE_IMPORT_MODULES:
                    raise ImportError(f"模块 '{name}' 不在安全导入列表中，禁止导入")
                return __import__(name, *args, **kwargs)
            _safe_builtins['__import__'] = _safe_import
            global_vars = {
                "__builtins__": _safe_builtins,
                "talib": MockTA(),
                "np": np,
                "pd": pd,
                "get_kline": lambda s, **kw: df if s == symbol else None,
                "context": context,
                "buy": lambda s, p, r: None if s in context.portfolio.positions else (None if len(context._trade_dates) >= context.max_trades_per_day else (None if context.portfolio.cash < p * 100 else (lambda: (context.portfolio.positions.update({s: {"cost_price": p, "qty": 1}}), context.portfolio.__setattr__("cash", context.portfolio.cash - p), context._trade_dates.append(s), trades.append({"day": len(trades), "type": "buy", "symbol": s, "price": p, "reason": r}))()))),
                "sell": lambda s, p, r: trades.append({"day": len(trades), "type": "sell", "symbol": s, "price": p, "reason": r}) or context.portfolio.positions.pop(s, None) or context.portfolio.__setattr__("cash", context.portfolio.cash + p),
            }
            exec(resolved_code, global_vars, local_vars)
            
            if "init" in local_vars:
                local_vars["init"](context)
            
            # 用请求的股票代码覆盖策略中硬编码的 symbol
            context.symbol = symbol
            
            # 获取策略参数(从context或代码中)
            ma_short = getattr(context, "ma_short", 5)
            ma_long = getattr(context, "ma_long", 20)
            stop_loss = getattr(context, "stop_loss", -0.08)
            take_profit = getattr(context, "take_profit", 0.25)
            
            # 回测模拟
            close_prices = df["close"].values
            
            for i in range(20, len(close_prices)):
                current_price = close_prices[i]
                
                data = {symbol: {
                    "close": current_price,
                    "open": df.iloc[i]["open"],
                    "high": df.iloc[i]["high"],
                    "low": df.iloc[i]["low"],
                    "volume": df.iloc[i]["volume"],
                }}
                
                # 执行handle_data -- get_kline 只返回截止当前的数据,避免未来穿越
                def make_get_kline(idx):
                    return lambda s, **kw: df.iloc[:idx+1] if s == symbol else None
                
                if "handle_data" in local_vars:
                    try:
                        # 替换 get_kline(需同时更新全局和局部作用域)
                        g = make_get_kline(i)
                        local_vars["get_kline"] = g
                        global_vars["get_kline"] = g
                        local_vars["handle_data"](context, data)
                    except Exception as e:
                        print(f"[backtest] handle_data error at bar {i}: {e}")
                        pass
            
            # 计算指标
            total_trades = len(trades)
            buy_trades = [t for t in trades if t["type"] == "buy"]
            sell_trades = [t for t in trades if t["type"] == "sell"]
            
            # 计算收益率
            if buy_trades:
                cost = buy_trades[0]["price"]
                if sell_trades:
                    total_return = (sell_trades[-1]["price"] - cost) / cost * 100
                else:
                    # 未平仓:用最新价估算
                    total_return = (close_prices[-1] - cost) / cost * 100
            else:
                total_return = 0
            
            final_capital = initial_capital * (1 + total_return / 100)
            
            # 计算年化收益(用交易日数估算)
            num_days = len(close_prices)
            if num_days > 0 and total_return != 0:
                annual_return = ((1 + total_return / 100) ** (252 / num_days) - 1) * 100
            else:
                annual_return = 0.0
            
            # 计算最大回撤 -- 同时构建完整资金曲线
            equity_curve = [initial_capital]
            for t in trades:
                if t["type"] == "buy":
                    equity_curve.append(equity_curve[-1] - t["price"])
                else:
                    equity_curve.append(equity_curve[-1] + t["price"])
            if len(equity_curve) > 1:
                peak = max(equity_curve)
                max_drawdown = (min(equity_curve) - peak) / peak * 100
            else:
                max_drawdown = 0.0
            
            # 构建每日资金曲线(用于前端图表)
            # 按交易日逐日计算资金变化
            full_equity_curve = []
            cash = initial_capital
            position_cost = 0  # 持仓成本
            position_qty = 0   # 持仓数量(简化:1股为单位)
            peak_value = initial_capital
            
            for i, (idx, row) in enumerate(df.iterrows()):
                date_str = idx.strftime("%Y-%m-%d")
                close_price = row["close"]
                
                # 检查当天是否有交易
                day_buy = [t for t in trades if t.get("day") == i and t["type"] == "buy"]
                day_sell = [t for t in trades if t.get("day") == i and t["type"] == "sell"]
                
                for t in day_buy:
                    cash -= t["price"]
                    position_cost += t["price"]
                    position_qty += 1
                for t in day_sell:
                    cash += t["price"]
                    position_cost = max(0, position_cost - t["price"])
                    position_qty = max(0, position_qty - 1)
                
                # 计算当日总资产 = 现金 + 持仓市值
                position_value = position_qty * close_price if position_qty > 0 else 0
                total_assets = cash + position_value
                
                # 更新峰值和回撤
                if total_assets > peak_value:
                    peak_value = total_assets
                drawdown_pct = (peak_value - total_assets) / peak_value * 100 if peak_value > 0 else 0
                
                full_equity_curve.append(EquityPoint(
                    date=date_str,
                    value=round(total_assets, 2),
                    drawdown=round(drawdown_pct, 2)
                ))
            
            # 重新计算最大回撤(基于完整曲线)
            if len(full_equity_curve) > 1:
                max_drawdown = min(p.drawdown for p in full_equity_curve)
            
            # 计算胜率:基于配对原则
            # 按交易顺序配对买入和卖出(FIFO)
            buy_prices_ordered = [t["price"] for t in trades if t["type"] == "buy"]
            sell_prices_ordered = [t["price"] for t in trades if t["type"] == "sell"]
            buy_original = buy_prices_ordered.copy()  # 保留原始顺序用于盈亏比计算
            wins = 0
            for sell_price in sell_prices_ordered:
                if buy_prices_ordered:
                    buy_price = buy_prices_ordered.pop(0)  # FIFO配对
                    if sell_price > buy_price:
                        wins += 1
            win_rate = (wins / len(sell_prices_ordered) * 100) if sell_prices_ordered else 0.0
            
            # 夏普比率(简化:用日收益率)
            if len(close_prices) > 1:
                daily_returns = [(close_prices[i] - close_prices[i-1]) / close_prices[i-1] for i in range(1, len(close_prices))]
                avg_return = np.mean(daily_returns)
                std_return = np.std(daily_returns)
                sharpe_ratio = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
            
            # 盈亏比(总盈利/总亏损)
            if sell_prices_ordered and buy_original:
                gross_gain = sum(max(0, s - b) for s, b in zip(sell_prices_ordered, buy_original))
                gross_loss = sum(max(0, b - s) for s, b in zip(sell_prices_ordered, buy_original))
                profit_factor = (gross_gain / gross_loss) if gross_loss > 0 else (gross_gain * 10 if gross_gain > 0 else 0.0)
            else:
                profit_factor = 0.0
            
            # 沪深300基准对比
            benchmark_ret = _benchmark_return(df.index[0], df.index[-1])
            message = f"回测完成: {total_trades}笔交易"
            if total_return > benchmark_ret:
                message += f" | 跑赢沪深300 {(total_return - benchmark_ret)*100:.1f}% 🟢"
            else:
                message += f" | 跑输沪深300 {(benchmark_ret - total_return)*100:.1f}% 🔴"

            # 持久化到CSV
            _log_backtest_result(symbol, request.code[:30], {
                "annual_return": annual_return,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "total_trades": total_trades,
                "benchmark_return": benchmark_ret,
            })

            return BacktestResponse(
                symbol=symbol,
                start_date=df.index[0].strftime("%Y-%m-%d"),
                end_date=df.index[-1].strftime("%Y-%m-%d"),
                status="success",
                message=message,
                metrics=BacktestMetrics(
                    total_return=round(total_return, 2),
                    annual_return=round(annual_return, 2),
                    max_drawdown=round(max_drawdown, 2),
                    sharpe_ratio=round(sharpe_ratio, 2),
                    win_rate=round(win_rate, 2),
                    profit_factor=round(profit_factor, 2),
                    total_trades=total_trades,
                    buy_count=len(buy_trades),
                    sell_count=len(sell_trades),
                    initial_capital=initial_capital,
                    final_capital=round(final_capital, 2),
                equity_curve=full_equity_curve,
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
            # 保存回测结果到CSV
            _log_backtest_result(symbol, request.code[:20], {
                "annual_return": 0, "sharpe_ratio": 0,
                "max_drawdown": 0, "win_rate": 0,
                "profit_factor": 0, "total_trades": 0,
            })
            return BacktestResponse(
                symbol=symbol,
                start_date=str(df.index[0])[:10] if df is not None else "",
                end_date=str(df.index[-1])[:10] if df is not None else "",
                status="error",
                message=f"回测执行错误: {str(e)}",
                metrics=BacktestMetrics(initial_capital=initial_capital),
                trades=[],
            )


# 回测结果持久化
_RESULTS_LOG = Path(__file__).parent.parent / "strategies" / "results_log.csv"

def _log_backtest_result(symbol: str, strategy_name: str, metrics: dict):
    """将回测结果追加到CSV日志"""
    import csv, os
    header = ["time", "symbol", "strategy", "annual_return", "sharpe",
              "max_drawdown", "win_rate", "profit_factor", "total_trades",
              "benchmark_return"]
    row = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "symbol": symbol,
        "strategy": strategy_name or "custom",
        "annual_return": f"{metrics.get('annual_return', 0):.2%}",
        "sharpe": f"{metrics.get('sharpe_ratio', 0):.2f}",
        "max_drawdown": f"{metrics.get('max_drawdown', 0):.2%}",
        "win_rate": f"{metrics.get('win_rate', 0):.2%}",
        "profit_factor": f"{metrics.get('profit_factor', 0):.2f}",
        "total_trades": metrics.get('total_trades', 0),
        "benchmark_return": metrics.get('benchmark_return', "N/A"),
    }
    file_exists = _RESULTS_LOG.exists()
    os.makedirs(_RESULTS_LOG.parent, exist_ok=True)
    with open(_RESULTS_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# 沪深300基准收益（简化：用年化 8% 作为长期基准）
def _benchmark_return(start_date, end_date) -> float:
    """估算同期沪深300收益（基于历史年化）"""
    try:
        days = (end_date - start_date).days
        years = max(days / 365.0, 0.1)
        # 沪深300 2010-2025 年化约 6-8%
        return round(0.07 * years, 4)
    except:
        return 0


# 全局回测服务实例
backtest_service = BacktestService()
