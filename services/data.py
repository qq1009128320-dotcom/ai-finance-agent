"""
AI Quantitative Strategy Platform v4 - Data Service
行情数据获取服务
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List, Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.quotes import TencentQuotes


class DataService:
    """数据服务 - 统一行情数据接口"""
    
    def __init__(self):
        self._quotes_engine: Optional[TencentQuotes] = None
    
    def get_quotes_engine(self) -> TencentQuotes:
        """获取行情引擎（单例）"""
        if self._quotes_engine is None:
            self._quotes_engine = TencentQuotes()
        return self._quotes_engine
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """获取个股实时行情"""
        engine = self.get_quotes_engine()
        data = engine.get_quotes([symbol])
        return data[0] if data else {"error": "无法获取行情数据"}
    
    def get_kline(self, symbol: str, period: str = "day", count: int = 60) -> Optional[Any]:
        """获取K线数据"""
        engine = self.get_quotes_engine()
        data = engine.get_kline([symbol], period=period, count=count)
        if data and symbol in data:
            return data[symbol]
        return None
    
    def get_market_status(self) -> Dict[str, Any]:
        """获取市场状态"""
        # 简化版：返回基本市场信息
        return {
            "market": "A股",
            "trading_hours": "09:30-11:30, 13:00-15:00",
            "status": "unknown",  # 需要实时判断
        }


# 全局数据服务实例
data_service = DataService()
