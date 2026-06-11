"""
AI智投量化平台 v4 - Quantitative Analysis Service
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.data import data_service
from core.models import (
    QuantAnalysisRequest, QuantAnalysisResponse,
    FactorScore, DimensionReport, StockSnapshot,
    MarketScanRequest, MarketScanResponse
)


class QuantService:
    """量化分析服务"""
    
    def __init__(self):
        # 导入量化引擎 — run_analysis 是便捷入口，按需创建引擎
        from quant_engine import run_analysis
        self.run_analysis = run_analysis
        self._quant_engine_module_ready = True
    
    def analyze_stock(self, request: QuantAnalysisRequest) -> QuantAnalysisResponse:
        """
        单股量化分析
        
        Args:
            request: 分析请求
        
        Returns:
            分析结果
        """
        symbol = request.symbol
        print(f"[quant] analyzing symbol: {repr(symbol)}")
        
        # 获取行情数据
        quote_data = data_service.get_quote(symbol)
        if "error" in quote_data:
            raise ValueError(f"无法获取{symbol}行情数据")
        
        # 获取K线数据
        kline_raw = data_service.get_kline(
            symbol, 
            period=request.period, 
            count=request.count
        )
        
        if not kline_raw or len(kline_raw) < 20:
            raise ValueError(f"{symbol} K线数据不足")
        
        # 解析K线数据 — 部分K线含第7列分红信息，只取前6列
        cols = ["date", "open", "close", "high", "low", "volume"]
        kline_clean = [bar[:6] for bar in kline_raw]
        df = pd.DataFrame(kline_clean, columns=cols)
        for c in ["open", "close", "high", "low", "volume"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        
        # 运行量化分析
        name = quote_data.get("name", symbol)
        price = float(quote_data.get("price", 0))
        change_pct = float(quote_data.get("change_pct", 0))
        result = self.run_analysis(symbol, name, df, price, change_pct)
        
        # 构建响应
        response = QuantAnalysisResponse(
            symbol=symbol,
            name=name,
            price=float(quote_data.get("price", 0)),
            change_pct=float(quote_data.get("change_pct", 0)),
            timestamp=datetime.now().isoformat(),
            total_score=result.total_score,
            rating=self._score_to_rating(result.total_score),
            confidence=self._get_confidence(result),
            dimensions=self._build_dimensions(result),
            factor_distribution=self._build_factor_distribution(result.factor_distribution),
            risk_metrics=self._convert_numpy(result.risk_metrics),
            entry_zone=self._convert_numpy(result.entry_zone) if result.entry_zone else None,
            exit_zone=self._convert_numpy(result.exit_zone) if result.exit_zone else None,
            recommendation=result.recommendation or "观望",
            position_advice=result.position_advice,
            signal_summary=result.signal_summary,
            triggers=self._convert_numpy(result.triggers) if result.triggers else None,
            tech_snapshot=self._convert_numpy(result.tech_snapshot) if result.tech_snapshot else None,
            relative_strength=self._convert_numpy(result.relative_strength) if result.relative_strength else None,
            financial_summary=self._convert_numpy(result.financial_summary) if result.financial_summary else None,
            news_sentiment=self._convert_numpy(result.news_sentiment) if result.news_sentiment else None,
        )
        
        return response
    
    def _score_to_rating(self, score: float) -> str:
        """评分转评级"""
        if score >= 90:
            return "AAA"
        elif score >= 80:
            return "AA"
        elif score >= 70:
            return "A"
        elif score >= 60:
            return "BBB"
        elif score >= 50:
            return "BB"
        elif score >= 40:
            return "B"
        else:
            return "CCC"
    
    def _get_confidence(self, result) -> str:
        """获取置信度"""
        # 基于因子一致性判断置信度
        factor_dist = result.factor_distribution
        bullish = factor_dist.get("bullish", 0)
        bearish = factor_dist.get("bearish", 0)
        total = bullish + bearish + factor_dist.get("neutral", 0)
        
        if total == 0:
            return "low"
        
        consensus = abs(bullish - bearish) / total
        if consensus > 0.6:
            return "high"
        elif consensus > 0.3:
            return "medium"
        else:
            return "low"
    
    def _build_dimensions(self, result) -> List[DimensionReport]:
        """构建维度报告 — 将quant_engine的dataclass DimensionReport转换为Pydantic模型"""
        dimensions = []
        for dim in result.dimensions:
            # quant_engine.DimensionReport is a dataclass, convert to Pydantic DimensionReport
            factors = []
            for f in dim.factors:  # 展示所有因子
                # f is a dataclass FactorScore, convert to Pydantic FactorScore
                factors.append(FactorScore(
                    name=f.name,
                    value=float(f.value),
                    score=float(f.score),
                    signal=f.signal,
                    weight=float(f.weight),
                    contribution=float(f.contribution),
                    detail=f.detail,
                ))
            
            dimensions.append(DimensionReport(
                name=dim.name,
                total_score=float(dim.total_score),
                max_score=float(dim.max_score),
                factors=factors,
                summary=dim.summary,
                strengths=dim.strength,
                weaknesses=dim.weakness,
            ))
        return dimensions
    
    def _build_factor_distribution(self, factor_dist: dict) -> Dict[str, int]:
        """构建因子信号分布 — 提取bullish/bearish/neutral计数"""
        result = {}
        for key in ['bullish', 'bearish', 'neutral']:
            val = factor_dist.get(key, 0)
            if isinstance(val, (int, float)):
                result[key] = int(val)
        return result
    
    def _convert_numpy(self, obj: Any) -> Any:
        """递归将numpy类型转换为Python原生类型"""
        import numpy as np
        if isinstance(obj, dict):
            return {k: self._convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy(v) for v in obj]
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return self._convert_numpy(obj.tolist())
        return obj
    
    def scan_market(self, request: MarketScanRequest) -> MarketScanResponse:
        """
        全市场扫描
        
        Args:
            request: 扫描请求
        
        Returns:
            扫描结果
        """
        import akshare as ak
        
        # 本地缓存：常用A股代码列表
        LOCAL_STOCKS = [
            "600036", "000001", "000858", "600519", "000651",
            "601318", "000002", "600030", "601166", "002415",
            "600900", "601398", "601939", "600028", "601857",
            "000333", "002594", "300750", "600276", "000568",
            "600809", "603288", "601012", "600438", "002230",
            "000063", "300059", "002714", "601688", "603259",
            "600000", "600016", "600031", "600104", "600309",
            "600585", "600887", "000100", "000157", "000338",
        ]
        
        # 根据scope获取股票列表
        try:
            stock_zh_a_spot_df = ak.stock_zh_a_spot_em(timeout=10)
            
            if stock_zh_a_spot_df is None or len(stock_zh_a_spot_df) == 0:
                raise ValueError("akshare返回空数据")
            
            # 提取代码列表
            all_codes = stock_zh_a_spot_df["代码"].astype(str).tolist()
            
            if request.scope == "top200":
                symbols_to_scan = all_codes[:200]
            elif request.scope == "top500":
                symbols_to_scan = all_codes[:500]
            else:
                symbols_to_scan = all_codes
            
            # 如果数据量太少，补充本地缓存
            if len(symbols_to_scan) < 50:
                existing = set(symbols_to_scan)
                for code in LOCAL_STOCKS:
                    if code not in existing:
                        symbols_to_scan.append(code)
                        
        except Exception as e:
            print(f"[scan_market] akshare error: {e}, falling back to local cache")
            symbols_to_scan = LOCAL_STOCKS.copy()
        
        # 限制最大扫描数量（避免超时）
        max_scan = min(len(symbols_to_scan), 200)
        symbols_to_scan = symbols_to_scan[:max_scan]
        
        snapshots = []
        scores = []
        
        for symbol in symbols_to_scan:
            try:
                quote = data_service.get_quote(symbol)
                if "error" not in quote:
                    change = float(quote.get("change_pct", 0))
                    volume = float(quote.get("volume", 0))
                    price = float(quote.get("price", 0))
                    turnover = float(quote.get("turnover", 0))
                    amplitude = float(quote.get("amplitude", 0))
                    amount = float(quote.get("amount", 0))

                    # 多维评分（近似28因子中的关键维度）
                    score = 50.0

                    # ① 涨跌幅因子（趋势维度）
                    score += change * 1.5

                    # ② 量价关系（资金维度）
                    if volume > 0 and price > 0:
                        vol_ratio = volume / 1e6  # 百万手为单位
                        if change > 2:
                            score += min(10, vol_ratio)   # 放量上涨加分
                        elif change < -2:
                            score -= min(8, vol_ratio)   # 放量下跌减分

                    # ③ 换手率加权（活跃度维度）
                    if turnover > 0:
                        if turnover > 5:  # 高换手
                            score += 3 if change > 0 else -3
                        elif turnover > 2:
                            score += 1

                    # ④ 振幅信号（波动维度）
                    if amplitude > 0:
                        if amplitude > 8:  # 大幅波动
                            score += 2 if change > 0 else -2
                        elif amplitude > 4:
                            score += 1

                    # ⑤ 成交额强度
                    if amount > 1e8:  # 过亿成交
                        score += 2 if change > 0 else -1

                    score = max(0, min(100, score))
                    
                    snapshot = StockSnapshot(
                        symbol=symbol,
                        name=quote.get("name", symbol),
                        price=quote.get("price", 0),
                        change_pct=change,
                        volume=volume,
                        score=round(score, 1),
                        rating="BBB" if score >= 60 else "BB",
                        signal="buy" if score >= 70 else ("sell" if score < 40 else "hold"),
                    )
                    snapshots.append(snapshot)
                    scores.append(score)
            except Exception:
                continue
        
        # 排序
        if request.sort_by == "score":
            snapshots.sort(key=lambda x: x.score, reverse=True)
        elif request.sort_by == "change":
            snapshots.sort(key=lambda x: x.change_pct, reverse=True)
        elif request.sort_by == "volume":
            snapshots.sort(key=lambda x: x.volume, reverse=True)
        
        # 分离强势和弱势
        sorted_by_score = sorted(snapshots, key=lambda x: x.score, reverse=True)
        n = len(sorted_by_score)
        top_stocks = sorted_by_score[:max(1, n//3)]
        weak_stocks = sorted_by_score[-max(1, n//3):]
        
        bullish = sum(1 for s in snapshots if s.signal == "buy")
        bearish = sum(1 for s in snapshots if s.signal == "sell")
        neutral = n - bullish - bearish
        
        return MarketScanResponse(
            timestamp=datetime.now().isoformat(),
            total_stocks=len(snapshots),
            avg_score=round(sum(scores) / len(scores), 1) if scores else 50,
            bullish_count=bullish,
            bearish_count=bearish,
            neutral_count=neutral,
            top_stocks=top_stocks,
            weak_stocks=weak_stocks,
        )


# 全局量化服务实例
quant_service = QuantService()
