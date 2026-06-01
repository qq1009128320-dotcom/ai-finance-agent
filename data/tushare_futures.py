"""
Tushare 股指期货数据层
提供4大股指期货(IF/IH/IC/IM)的主力连续数据及衍生指标
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
import json

# -- Tushare 初始化 --
try:
    import tushare as ts
    _TUSHARE_AVAILABLE = True
except ImportError:
    _TUSHARE_AVAILABLE = False


class TushareFutures:
    """Tushare 股指期货数据获取器"""
    
    # 四大股指期货品种
    FUTURE_INDICES = {
        'IF': '沪深300股指期货',
        'IH': '上证50股指期货',
        'IC': '中证500股指期货',
        'IM': '中证1000股指期货',
    }
    
    # 对应的现货指数
    SPOT_INDICES = {
        'IF': '000300.SH',   # 沪深300
        'IH': '000016.SH',   # 上证50
        'IC': '000905.SH',   # 中证500
        'IM': '000852.SH',   # 中证1000
    }
    
    def __init__(self, token: Optional[str] = None, cache_dir: str = None):
        """
        Args:
            token: Tushare Pro Token (优先从环境变量读取)
            cache_dir: 本地缓存目录
        """
        if not _TUSHARE_AVAILABLE:
            raise ImportError("tushare 未安装: pip install tushare")
        
        # 从环境变量或参数获取 token
        self.token = token or os.environ.get('TUSHARE_TOKEN')
        if not self.token:
            raise ValueError("Tushare token 未设置，请设置 TUSHARE_TOKEN 环境变量或传入 token 参数")
        
        ts.set_token(self.token)
        self.pro = ts.pro_api()
        
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            'cache', 'tushare'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self._data_cache: Dict[str, pd.DataFrame] = {}
        
        # 检查期货接口权限（已禁用，Tushare 权限不足）
        self._futures_available = False
        self._futures_disabled_reason = "Tushare 期货接口需要更高积分等级，已禁用"
    
    def _check_futures_permission(self) -> bool:
        """检查期货接口权限（已禁用）"""
        return False
    
    # -- 基础数据获取 --
    
    def get_futures_index(
        self, 
        index_code: str, 
        start_date: str = None,
        end_date: str = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取股指期货主力连续日行情
        
        Args:
            index_code: 品种代码 IF/IH/IC/IM
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            use_cache: 是否使用本地缓存
        
        Returns:
            DataFrame 包含 trade_date, open, high, low, close, volume, amount, settle, open_interest
            如果期货数据不可用，返回空 DataFrame
        """
        if index_code not in self.FUTURE_INDICES:
            raise ValueError(f"不支持的股指期货品种: {index_code}, 支持: {list(self.FUTURE_INDICES.keys())}")
        
        # 期货数据已禁用
        if not self._futures_available:
            logger.warning(f"期货数据已禁用: {self._futures_disabled_reason}")
            return pd.DataFrame()  # 返回空 DataFrame 而非抛出异常
        
        end_date = end_date or datetime.now().strftime('%Y%m%d')
        start_date = start_date or (datetime.now() - timedelta(days=365*3)).strftime('%Y%m%d')
        
        cache_file = os.path.join(self.cache_dir, f"{index_code}_index_{start_date}_{end_date}.parquet")
        
        if use_cache and os.path.exists(cache_file):
            df = pd.read_parquet(cache_file)
            self._data_cache[index_code] = df
            return df
        
        # 调用 Tushare API
        df = self.pro.futures_index(
            index_code=index_code,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is not None and not df.empty:
            df = df.sort_values('trade_date').reset_index(drop=True)
            # 类型转换
            for col in ['open', 'high', 'low', 'close', 'settle', 'volume', 'amount', 'open_interest']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            
            # 缓存
            df.to_parquet(cache_file, index=False)
            self._data_cache[index_code] = df
        
        return df
    
    def get_futures_daily(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取单个期货合约日行情
        
        Args:
            symbol: 合约代码，如 IF2406 (沪深300 2024年6月合约)
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame
        """
        end_date = end_date or datetime.now().strftime('%Y%m%d')
        start_date = start_date or (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        cache_file = os.path.join(self.cache_dir, f"{symbol}_daily.parquet")
        
        if use_cache and os.path.exists(cache_file):
            df = pd.read_parquet(cache_file)
            return df
        
        df = self.pro.futures_daily(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is not None and not df.empty:
            df = df.sort_values('trade_date').reset_index(drop=True)
            for col in ['open', 'high', 'low', 'close', 'settle', 'volume', 'amount', 'open_interest']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.to_parquet(cache_file, index=False)
        
        return df
    
    def get_all_indices(
        self,
        start_date: str = None,
        end_date: str = None,
        use_cache: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        一次性获取四大股指期货数据
        
        Returns:
            Dict: { 'IF': df, 'IH': df, 'IC': df, 'IM': df }
        """
        results = {}
        for code in self.FUTURE_INDICES.keys():
            results[code] = self.get_futures_index(code, start_date, end_date, use_cache)
        return results
    
    # -- 衍生指标计算 --
    
    def calculate_basis(
        self,
        future_df: pd.DataFrame,
        spot_df: pd.DataFrame = None,
        index_code: str = 'IF'
    ) -> pd.DataFrame:
        """
        计算期货基差和升贴水率
        
        Args:
            future_df: 期货数据 DataFrame
            spot_df: 现货指数数据 (可选，从 Tushare 获取)
            index_code: 品种代码
        
        Returns:
            DataFrame 新增 basis, basis_rate, premium_discount 列
        """
        result = future_df.copy()
        
        # 获取现货数据
        if spot_df is None:
            spot_code = self.SPOT_INDICES.get(index_code)
            if spot_code:
                spot_df = self._get_stock_index(spot_code, 
                    future_df['trade_date'].min().strftime('%Y%m%d'),
                    future_df['trade_date'].max().strftime('%Y%m%d')
                )
        
        if spot_df is not None and not spot_df.empty:
            # 对齐日期
            spot_df = spot_df.rename(columns={'close': 'spot_close'})
            merged = result.merge(spot_df[['trade_date', 'spot_close']], on='trade_date', how='left')
            
            # 计算基差
            merged['basis'] = merged['close'] - merged['spot_close']
            merged['basis_rate'] = (merged['basis'] / merged['spot_close']) * 100
            
            # 升贴水: 正数=升水(看涨), 负数=贴水(看跌)
            merged['premium_discount'] = merged['basis_rate'].apply(
                lambda x: '升水' if x > 0 else ('贴水' if x < 0 else '平价')
            )
            
            return merged
        
        return result
    
    def calculate_open_interest_change(
        self,
        df: pd.DataFrame,
        window: int = 5
    ) -> pd.DataFrame:
        """
        计算持仓量变化
        
        Args:
            df: 期货数据
            window: 滚动窗口天数
        
        Returns:
            DataFrame 新增 oi_change, oi_change_rate, oi_trend 列
        """
        result = df.copy()
        
        result['oi_change'] = result['open_interest'].diff()
        result['oi_change_rate'] = result['open_interest'].pct_change() * 100
        result['oi_ma'] = result['open_interest'].rolling(window).mean()
        result['oi_trend'] = result['oi_ma'].diff().apply(
            lambda x: '增仓' if x > 0 else ('减仓' if x < 0 else '持平')
        )
        
        return result
    
    def get_market_sentiment(
        self,
        index_code: str = 'IF',
        lookback: int = 5
    ) -> Dict:
        """
        获取当前市场情绪指标
        
        Returns:
            Dict 包含基差率、升贴水状态、持仓量趋势、成交量变化等
        """
        df = self.get_futures_index(index_code)
        if df is None or df.empty:
            return {'error': '数据获取失败'}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # 计算基差
        spot_code = self.SPOT_INDICES.get(index_code)
        spot_df = None
        if spot_code:
            spot_df = self._get_stock_index(spot_code)
        
        if spot_df is not None and not spot_df.empty:
            latest_spot = spot_df.iloc[-1]['close']
            basis_rate = (latest['close'] - latest_spot) / latest_spot * 100
        else:
            basis_rate = 0
        
        # 持仓量变化
        oi_change = latest['open_interest'] - prev.get('open_interest', latest['open_interest'])
        oi_change_rate = (oi_change / prev.get('open_interest', 1)) * 100 if prev.get('open_interest') else 0
        
        # 价格趋势
        price_change = (latest['close'] - prev['close']) / prev['close'] * 100 if prev.get('close') else 0
        
        # 成交量变化
        vol_change = (latest['volume'] - prev.get('volume', latest['volume'])) / prev.get('volume', 1) * 100 if prev.get('volume') else 0
        
        return {
            'index_code': index_code,
            'index_name': self.FUTURE_INDICES[index_code],
            'date': latest['trade_date'].strftime('%Y-%m-%d'),
            'close': latest['close'],
            'change_pct': price_change,
            'basis_rate': round(basis_rate, 4),
            'premium_discount': '升水' if basis_rate > 0 else ('贴水' if basis_rate < 0 else '平价'),
            'open_interest': latest['open_interest'],
            'oi_change': round(oi_change, 0),
            'oi_change_rate': round(oi_change_rate, 4),
            'oi_trend': '增仓' if oi_change > 0 else ('减仓' if oi_change < 0 else '持平'),
            'volume': latest['volume'],
            'vol_change_pct': round(vol_change, 4),
            'sentiment': self._classify_sentiment(basis_rate, oi_change, price_change),
        }
    
    def _classify_sentiment(self, basis_rate: float, oi_change: float, price_change: float) -> str:
        """综合判断市场情绪"""
        score = 0
        # 基差: 升水+2, 贴水-2
        if basis_rate > 0.5: score += 2
        elif basis_rate < -0.5: score -= 2
        # 持仓量: 增仓+1, 减仓-1
        if oi_change > 0: score += 1
        elif oi_change < 0: score -= 1
        # 价格: 上涨+1, 下跌-1
        if price_change > 0: score += 1
        elif price_change < 0: score -= 1
        
        if score >= 3: return '强烈看涨'
        elif score >= 1: return '看涨'
        elif score >= -1: return '震荡'
        elif score >= -3: return '看跌'
        else: return '强烈看跌'
    
    def _get_stock_index(self, code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取股票指数数据（通过 index_daily）"""
        end_date = end_date or datetime.now().strftime('%Y%m%d')
        start_date = start_date or (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        df = self.pro.index_daily(ts_code=code, start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            df = df.sort_values('trade_date').reset_index(drop=True)
            df['trade_date'] = pd.to_datetime(df['trade_date'])
        return df
    
    # -- 跨品种分析 --
    
    def get_cross_analysis(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        四大股指期货跨品种强弱分析
        
        Returns:
            DataFrame 包含各品种的收益率、基差率、持仓量变化等对比
        """
        all_data = self.get_all_indices(start_date, end_date)
        
        results = []
        for code, df in all_data.items():
            if df is None or df.empty:
                continue
            
            latest = df.iloc[-1]
            prev = df.iloc[-5] if len(df) > 5 else df.iloc[0]  # 5日收益率
            
            # 计算收益率
            ret_1d = (latest['close'] - df.iloc[-2]['close']) / df.iloc[-2]['close'] * 100 if len(df) > 1 else 0
            ret_5d = (latest['close'] - prev['close']) / prev['close'] * 100
            
            # 基差率
            spot_df = self._get_stock_index(self.SPOT_INDICES[code])
            if spot_df is not None and not spot_df.empty:
                latest_spot = spot_df.iloc[-1]['close']
                basis_rate = (latest['close'] - latest_spot) / latest_spot * 100
            else:
                basis_rate = 0
            
            results.append({
                '品种': code,
                '名称': self.FUTURE_INDICES[code],
                '现价': latest['close'],
                '1日涨跌幅%': round(ret_1d, 4),
                '5日涨跌幅%': round(ret_5d, 4),
                '基差率%': round(basis_rate, 4),
                '持仓量': latest['open_interest'],
                '成交量': latest['volume'],
            })
        
        return pd.DataFrame(results)


# -- 便捷函数 --

def create_tushare_futures(token: str = None) -> TushareFutures:
    """创建 TushareFutures 实例"""
    return TushareFutures(token=token)
