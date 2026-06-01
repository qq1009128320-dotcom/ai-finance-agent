"""
AI Quantitative Strategy Platform v4 - Quantitative Analysis Service
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
        # 导入量化引擎
        from quant_engine import QuantAnalysisEngine, run_analysis
        self.quant_engine = QuantAnalysisEngine()
    
    def analyze_stock(self, request: QuantAnalysisRequest) -> QuantAnalysisResponse:
        """
        单股量化分析
        
        Args:
            request: 分析请求
        
        Returns:
            分析结果
        """
        symbol = request.symbol
        
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
        
        # 解析K线数据
        cols = ["date", "open", "close", "high", "low", "volume"]
        df = pd.DataFrame(kline_raw, columns=cols[:len(kline_raw[0])])
        for c in ["open", "close", "high", "low", "volume"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        
        # 运行量化分析
        name = quote_data.get("name", symbol)
        result = run_analysis(symbol, name, df)
        
        # 构建响应
        response = QuantAnalysisResponse(
            symbol=symbol,
            name=name,
            price=quote_data.get("price", 0),
            change_pct=quote_data.get("change_pct", 0),
            timestamp=datetime.now().isoformat(),
            total_score=result.get("total", 50),
            rating=self._score_to_rating(result.get("total", 50)),
            confidence=self._get_confidence(result),
            dimensions=self._build_dimensions(result),
            factor_distribution=result.get("factor_distribution", {}),
            risk_metrics=result.get("risk_metrics", {}),
            entry_zone=result.get("entry_zone"),
            exit_zone=result.get("exit_zone"),
            recommendation=result.get("advice", "观望"),
            position_advice=result.get("position_advice", ""),
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
    
    def _get_confidence(self, result: Dict) -> str:
        """获取置信度"""
        # 基于因子一致性判断置信度
        factor_dist = result.get("factor_distribution", {})
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
    
    def _build_dimensions(self, result: Dict) -> List[DimensionReport]:
        """构建维度报告"""
        dimensions = []
        
        # 从result中提取维度信息
        # 简化版：基于现有quant_engine的输出
        dims_data = result.get("dimensions", [])
        
        for dim in dims_data:
            if isinstance(dim, dict):
                factors = []
                for f in dim.get("factors", [])[:5]:  # 取前5个因子
                    if isinstance(f, dict):
                        factors.append(FactorScore(
                            name=f.get("name", ""),
                            value=f.get("value", 0),
                            score=f.get("score", 50),
                            signal=f.get("signal", "neutral"),
                            weight=f.get("weight", 0.1),
                            contribution=f.get("contribution", 0),
                            detail=f.get("detail", ""),
                        ))
                
                dimensions.append(DimensionReport(
                    name=dim.get("name", ""),
                    total_score=dim.get("total_score", 50),
                    max_score=dim.get("max_score", 100),
                    factors=factors,
                    summary=dim.get("summary", ""),
                    strengths=dim.get("strengths", []),
                    weaknesses=dim.get("weaknesses", []),
                ))
        
        return dimensions
    
    def scan_market(self, request: MarketScanRequest) -> MarketScanResponse:
        """
        全市场扫描
        
        Args:
            request: 扫描请求
        
        Returns:
            扫描结果
        """
        # 简化版：返回占位数据
        # 完整实现需要遍历所有股票并计算评分
        # 这里用top200作为示例
        
        from quotes import TencentQuotes
        engine = TencentQuotes()
        
        # 获取市场列表（简化：用已知股票代码）
        # 实际应该从akshare或tushare获取完整列表
        sample_symbols = [
            "600036", "000001", "000858", "600519", "000651",
            "601318", "000002", "600030", "601166", "002415",
        ]
        
        snapshots = []
        scores = []
        
        for symbol in sample_symbols[:request.limit]:
            try:
                quote = data_service.get_quote(symbol)
                if "error" not in quote:
                    # 简化评分：基于价格变化
                    change = quote.get("change_pct", 0)
                    score = 50 + change * 2  # 简单映射
                    
                    snapshot = StockSnapshot(
                        symbol=symbol,
                        name=quote.get("name", symbol),
                        price=quote.get("price", 0),
                        change_pct=change,
                        volume=quote.get("volume", 0),
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
