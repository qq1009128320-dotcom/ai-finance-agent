"""
统一数据源路由层 (Data Router)
================================
三层多源数据架构：实时行情层 + 历史数据层 + 基本面层
自动降级：主源失败 -> 备用源 -> 本地缓存

设计原则：
1. 统一接口：上层代码无需关心数据来源
2. 自动降级：任一数据源失败不影响核心功能
3. 本地缓存：减少 API 调用，断网可用
4. 数据校验：完整性检查，异常数据自动降级
"""

import os
import json
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from functools import wraps
import hashlib

import pandas as pd
import numpy as np

# -- 缓存工具 --
try:
    import pyarrow.parquet as pq
    _PYARROW_AVAILABLE = True
except ImportError:
    _PYARROW_AVAILABLE = False

# -- 数据源导入 --
# 实时行情
try:
    from data.quotes import TencentQuotes
    _TENCENT_AVAILABLE = True
except ImportError:
    _TENCENT_AVAILABLE = False

# Tushare
try:
    import tushare as ts
    _TUSHARE_AVAILABLE = True
except ImportError:
    _TUSHARE_AVAILABLE = False

# akshare (备用)
try:
    import akshare as ak
    _AKSHARE_AVAILABLE = True
except ImportError:
    _AKSHARE_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════
# 装饰器：重试 + 降级 + 缓存
# ═══════════════════════════════════════════════════════════════

def with_retry(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        warnings.warn(f"{func.__name__} 第{attempt+1}次失败: {e}, 重试中...")
                        import time
                        time.sleep(delay * (attempt + 1))  # 指数退避
            raise last_error
        return wrapper
    return decorator


def with_cache(cache_dir: str = None, ttl_hours: int = 24):
    """
    本地缓存装饰器
    
    Args:
        cache_dir: 缓存目录
        ttl_hours: 缓存有效期（小时）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存 key
            key_data = f"{func.__name__}:{args}:{kwargs}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()[:16]
            
            cache_dir = cache_dir or os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'cache', 'router'
            )
            os.makedirs(cache_dir, exist_ok=True)
            
            cache_file = os.path.join(cache_dir, f"{cache_key}.parquet")
            
            # 检查缓存是否有效
            if os.path.exists(cache_file):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
                if datetime.now() - file_mtime < timedelta(hours=ttl_hours):
                    try:
                        df = pd.read_parquet(cache_file)
                        return df
                    except Exception:
                        pass  # 缓存损坏，重新获取
            
            # 执行函数并缓存
            result = func(*args, **kwargs)
            
            if result is not None and _PYARROW_AVAILABLE:
                try:
                    if isinstance(result, pd.DataFrame):
                        result.to_parquet(cache_file, index=False)
                    elif isinstance(result, dict):
                        # 字典转 DataFrame 缓存
                        df = pd.DataFrame([result])
                        df.to_parquet(cache_file, index=False)
                except Exception:
                    pass  # 缓存失败不影响主流程
            
            return result
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════
# 数据源基类
# ═══════════════════════════════════════════════════════════════

class DataSource:
    """数据源基类"""
    
    name: str = "base"
    priority: int = 0  # 优先级，数字越大优先级越高
    is_available: bool = False
    last_error: Optional[str] = None
    
    def health_check(self) -> bool:
        """健康检查"""
        return self.is_available
    
    def get_quotes(self, symbols: List[str]) -> Optional[List[Dict]]:
        """获取实时行情"""
        raise NotImplementedError
    
    def get_kline(self, symbol: str, period: str = 'day', 
                  start_date: str = None, end_date: str = None,
                  count: int = 100) -> Optional[pd.DataFrame]:
        """获取 K 线数据"""
        raise NotImplementedError
    
    def get_financials(self, symbol: str) -> Optional[Dict]:
        """获取财务数据"""
        raise NotImplementedError
    
    def get_index_data(self, index_code: str, 
                       start_date: str = None, 
                       end_date: str = None) -> Optional[pd.DataFrame]:
        """获取指数数据"""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════
# 实时行情数据源
# ═══════════════════════════════════════════════════════════════

class TencentQuotesSource(DataSource):
    """腾讯财经实时行情源"""
    
    name = "tencent"
    priority = 10
    is_available = _TENCENT_AVAILABLE
    
    def __init__(self):
        if _TENCENT_AVAILABLE:
            self.client = TencentQuotes()
        else:
            self.client = None
    
    def health_check(self) -> bool:
        if not self.client:
            return False
        try:
            # 测试请求
            result = self.client.get_quotes(['sh000001'])
            return result is not None and len(result) > 0
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def get_quotes(self, symbols: List[str]) -> Optional[List[Dict]]:
        """获取实时行情"""
        if not self.client:
            return None
        try:
            return self.client.get_quotes(symbols)
        except Exception as e:
            self.last_error = str(e)
            return None
    
    def get_kline(self, symbol: str, period: str = 'day',
                  start_date: str = None, end_date: str = None,
                  count: int = 100) -> Optional[pd.DataFrame]:
        """获取 K 线（腾讯只提供有限历史）"""
        if not self.client:
            return None
        try:
            data = self.client.get_kline([symbol], period=period, count=count)
            if symbol in data and data[symbol]:
                df = pd.DataFrame(data[symbol], 
                                 columns=['trade_date', 'open', 'close', 'high', 'low', 'volume'])
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                for col in ['open', 'close', 'high', 'low', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                return df
        except Exception as e:
            self.last_error = str(e)
        return None


class MootdxSource(DataSource):
    """mootdx 实时行情源（备用）"""
    
    name = "mootdx"
    priority = 5
    is_available = False  # 需要手动检查
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        try:
            import mootdx
            from mootdx import quotes as mq
            self.client = mq
            self.is_available = True
        except ImportError:
            self.is_available = False
    
    def health_check(self) -> bool:
        if not self.is_available:
            return False
        try:
            # 测试连接
            from mootdx import client as mc
            with mc.Client().connect() as conn:
                return True
        except Exception:
            self.last_error = "mootdx 连接失败"
            return False
    
    def get_quotes(self, symbols: List[str]) -> Optional[List[Dict]]:
        if not self.client:
            return None
        try:
            from mootdx import quotes as mq
            # mootdx 需要不同格式
            results = mq.quotes(self.client, symbols=symbols)
            return results
        except Exception as e:
            self.last_error = str(e)
            return None


# ═══════════════════════════════════════════════════════════════
# 历史数据源
# ═══════════════════════════════════════════════════════════════

class TushareSource(DataSource):
    """Tushare 历史数据源（主源）"""
    
    name = "tushare"
    priority = 10
    is_available = _TUSHARE_AVAILABLE
    
    def __init__(self, token: str = None):
        self.token = token or os.environ.get('TUSHARE_TOKEN')
        self.pro = None
        if self.token and _TUSHARE_AVAILABLE:
            ts.set_token(self.token)
            try:
                self.pro = ts.pro_api()
                self.is_available = True
            except Exception as e:
                self.last_error = f"Tushare API 初始化失败: {e}"
                self.is_available = False
    
    def health_check(self) -> bool:
        if not self.pro:
            return False
        try:
            # 测试 API
            df = self.pro.stock_basic(exchange='SZSE', fields='ts_code,symbol,name')
            return df is not None and not df.empty
        except Exception as e:
            self.last_error = str(e)
            return False
    
    @with_cache(ttl_hours=24)
    def get_kline(self, symbol: str, period: str = 'day',
                  start_date: str = None, end_date: str = None,
                  count: int = 100) -> Optional[pd.DataFrame]:
        """获取股票日 K 线"""
        if not self.pro:
            return None
        
        end_date = end_date or datetime.now().strftime('%Y%m%d')
        if start_date is None:
            # 默认获取 count 天
            start_date = (datetime.now() - timedelta(days=count*1.2)).strftime('%Y%m%d')
        
        # 转换代码格式 (600000 -> 600000.SH)
        if '.' not in symbol:
            if symbol.startswith(('6', '9')):
                ts_code = f"{symbol}.SH"
            else:
                ts_code = f"{symbol}.SZ"
        else:
            ts_code = symbol
        
        try:
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df = df.sort_values('trade_date').reset_index(drop=True)
                # 重命名列以匹配统一格式
                df = df.rename(columns={
                    'trade_date': 'trade_date',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'pre_close': 'pre_close',
                    'change': 'change',
                    'pct_chg': 'pct_chg',
                    'vol': 'volume',
                    'amount': 'amount'
                })
                return df
        except Exception as e:
            self.last_error = str(e)
        return None
    
    @with_cache(ttl_hours=24)
    def get_index_data(self, index_code: str,
                       start_date: str = None,
                       end_date: str = None) -> Optional[pd.DataFrame]:
        """获取指数日行情"""
        if not self.pro:
            return None
        
        end_date = end_date or datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*3)).strftime('%Y%m%d')
        
        try:
            df = self.pro.index_daily(ts_code=index_code, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df = df.sort_values('trade_date').reset_index(drop=True)
                return df
        except Exception as e:
            self.last_error = str(e)
        return None
    
    @with_cache(ttl_hours=168)  # 7 天
    def get_financials(self, symbol: str) -> Optional[Dict]:
        """获取财务数据"""
        if not self.pro:
            return None
        
        # 转换代码格式
        if '.' not in symbol:
            if symbol.startswith(('6', '9')):
                ts_code = f"{symbol}.SH"
            else:
                ts_code = f"{symbol}.SZ"
        else:
            ts_code = symbol
        
        result = {}
        try:
            # 基本财务指标
            df = self.pro.fina_indicator(ts_code=ts_code, limit=4)
            if df is not None and not df.empty:
                latest = df.iloc[0]
                result['roe'] = latest.get('roe', None)
                result['gross_margin'] = latest.get('gross_margin', None)
                result['net_margin'] = latest.get('net_margin', None)
                result['pe'] = latest.get('pe', None)
                result['pb'] = latest.get('pb', None)
                result['ps'] = latest.get('ps', None)
                result['total_revenue'] = latest.get('total_revenue', None)
                result['net_profit'] = latest.get('net_profit', None)
            
            # 资产负债表摘要
            df_bs = self.pro.balance(ts_code=ts_code, limit=1)
            if df_bs is not None and not df_bs.empty:
                bs = df_bs.iloc[0]
                result['total_assets'] = bs.get('total_assets', None)
                result['total_liabilities'] = bs.get('total_liabilities', None)
                result['total_equity'] = bs.get('total_equity', None)
                result['debt_ratio'] = bs.get('total_liabilities', 0) / bs.get('total_assets', 1) if bs.get('total_assets') else None
            
            # 利润表摘要
            df_is = self.pro.income(ts_code=ts_code, limit=1)
            if df_is is not None and not df_is.empty:
                is_ = df_is.iloc[0]
                result['revenue'] = is_.get('revenue', None)
                result['operating_profit'] = is_.get('operating_profit', None)
                result['net_profit'] = is_.get('net_profit', result.get('net_profit'))
            
        except Exception as e:
            self.last_error = str(e)
        
        return result if result else None
    
    @with_cache(ttl_hours=168)
    def get_stock_basic(self) -> Optional[pd.DataFrame]:
        """获取股票基本信息"""
        if not self.pro:
            return None
        try:
            df = self.pro.stock_basic(exchange='', list_status='L', 
                                       fields='ts_code,symbol,name,area,industry,list_date')
            return df
        except Exception as e:
            self.last_error = str(e)
            return None
    
    @with_cache(ttl_hours=168)
    def get_futures_index(self, index_code: str,
                          start_date: str = None,
                          end_date: str = None) -> Optional[pd.DataFrame]:
        """获取股指期货主力连续数据（已禁用，Tushare 权限不足）"""
        self.last_error = "期货数据源已禁用：Tushare 权限不足，腾讯财经期货接口格式未确认"
        return pd.DataFrame()  # 返回空 DataFrame 而非 None，避免上层代码崩溃


class AkshareSource(DataSource):
    """akshare 历史数据源（备用）"""
    
    name = "akshare"
    priority = 3
    is_available = _AKSHARE_AVAILABLE
    
    def __init__(self):
        pass
    
    def health_check(self) -> bool:
        if not self.is_available:
            return False
        try:
            # 测试请求
            df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20240110")
            return df is not None and not df.empty
        except Exception as e:
            self.last_error = str(e)
            return False
    
    @with_cache(ttl_hours=24)
    def get_kline(self, symbol: str, period: str = 'day',
                  start_date: str = None, end_date: str = None,
                  count: int = 100) -> Optional[pd.DataFrame]:
        """获取股票日 K 线"""
        if not self.is_available:
            return None
        
        end_date = end_date or datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=count*1.2)).strftime('%Y%m%d')
        
        try:
            # akshare 格式转换
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                     start_date=start_date, end_date=end_date, adjust="qfq")
            if df is not None and not df.empty:
                df = df.rename(columns={
                    '日期': 'trade_date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount'
                })
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                return df
        except Exception as e:
            self.last_error = str(e)
        return None


# ═══════════════════════════════════════════════════════════════
# 统一数据路由层
# ═══════════════════════════════════════════════════════════════

class DataManager:
    """
    统一数据管理器
    
    使用示例：
        dm = DataManager(tushare_token="your_token")
        
        # 实时行情（自动降级）
        quotes = dm.get_quotes(['600036', '000001'])
        
        # K 线数据（Tushare 主，akshare 备）
        df = dm.get_kline('600036', count=250)
        
        # 财务数据
        fin = dm.get_financials('600036')
        
        # 股指期货
        df_if = dm.get_futures_index('IF')
    """
    
    def __init__(self, tushare_token: str = None, cache_dir: str = None):
        """
        Args:
            tushare_token: Tushare Pro Token
            cache_dir: 缓存目录
        """
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'cache'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 初始化数据源（按优先级排序）
        self.sources = {
            'realtime': [
                TencentQuotesSource(),
                MootdxSource(),
            ],
            'history': [
                TushareSource(token=tushare_token),
                AkshareSource(),
            ],
            'fundamental': [
                TushareSource(token=tushare_token),
                AkshareSource(),
            ],
        }
        
        # 健康检查
        self._health_check_all()
    
    def _health_check_all(self):
        """所有数据源健康检查"""
        for category, sources in self.sources.items():
            for source in sources:
                source.is_available = source.health_check()
    
    def _get_source(self, category: str) -> Optional[DataSource]:
        """获取可用的数据源（按优先级）"""
        for source in self.sources.get(category, []):
            if source.is_available:
                return source
        return None
    
    def get_quotes(self, symbols: List[str]) -> Optional[List[Dict]]:
        """
        获取实时行情（自动降级）
        
        优先级: 腾讯 -> mootdx
        """
        for source in self.sources['realtime']:
            if source.is_available:
                result = source.get_quotes(symbols)
                if result:
                    return result
        
        warnings.warn(f"所有实时行情源不可用，symbols: {symbols}")
        return None
    
    def get_kline(self, symbol: str, period: str = 'day',
                  start_date: str = None, end_date: str = None,
                  count: int = 250) -> Optional[pd.DataFrame]:
        """
        获取 K 线数据（自动降级）
        
        优先级: Tushare -> akshare
        """
        for source in self.sources['history']:
            if source.is_available:
                result = source.get_kline(symbol, period, start_date, end_date, count)
                if result is not None and not result.empty:
                    # 数据完整性检查
                    if self._validate_kline(result):
                        return result
                    else:
                        warnings.warn(f"{source.name} 数据不完整，尝试备用源")
        
        warnings.warn(f"所有历史数据源不可用，symbol: {symbol}")
        return None
    
    def _validate_kline(self, df: pd.DataFrame, min_rows: int = 20) -> bool:
        """K 线数据完整性检查"""
        if df is None or df.empty:
            return False
        if len(df) < min_rows:
            return False
        
        # 检查关键列
        required_cols = ['trade_date', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            return False
        
        # 检查空值比例
        for col in ['open', 'high', 'low', 'close']:
            null_ratio = df[col].isna().sum() / len(df)
            if null_ratio > 0.1:  # 超过 10% 空值认为数据不完整
                return False
        
        return True
    
    def get_financials(self, symbol: str) -> Optional[Dict]:
        """
        获取财务数据（自动降级）
        
        优先级: Tushare -> akshare
        """
        for source in self.sources['fundamental']:
            if source.is_available:
                result = source.get_financials(symbol)
                if result:
                    return result
        
        warnings.warn(f"所有财务数据源不可用，symbol: {symbol}")
        return None
    
    def get_index_data(self, index_code: str,
                       start_date: str = None,
                       end_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取指数数据
        
        优先级: Tushare -> akshare
        """
        for source in self.sources['history']:
            if source.is_available:
                if hasattr(source, 'get_index_data'):
                    result = source.get_index_data(index_code, start_date, end_date)
                    if result is not None and not result.empty:
                        return result
        
        # 回退到 get_kline（某些源把指数当股票处理）
        return self.get_kline(index_code, start_date=start_date, end_date=end_date)
    
    def get_futures_index(self, index_code: str,
                          start_date: str = None,
                          end_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取股指期货主力连续数据
        
        优先级: Tushare
        """
        source = self._get_source('history')
        if source and hasattr(source, 'get_futures_index'):
            return source.get_futures_index(index_code, start_date, end_date)
        
        warnings.warn(f"期货数据源不可用，index_code: {index_code}")
        return None
    
    def get_stock_basic(self) -> Optional[pd.DataFrame]:
        """获取股票基本信息"""
        source = self._get_source('history')
        if source and hasattr(source, 'get_stock_basic'):
            return source.get_stock_basic()
        return None
    
    def get_all_sources_status(self) -> Dict:
        """获取所有数据源状态"""
        status = {}
        for category, sources in self.sources.items():
            status[category] = {
                s.name: {
                    'available': s.is_available,
                    'priority': s.priority,
                    'last_error': s.last_error
                }
                for s in sources
            }
        return status
    
    def refresh_health(self):
        """刷新所有数据源健康状态"""
        self._health_check_all()


# ═══════════════════════════════════════════════════════════════
# 便捷入口
# ═══════════════════════════════════════════════════════════════

_global_manager: Optional[DataManager] = None

def get_data_manager(tushare_token: str = None) -> DataManager:
    """获取全局数据管理器（单例）"""
    global _global_manager
    if _global_manager is None:
        # 从环境变量或参数读取 token
        token = tushare_token or os.environ.get('TUSHARE_TOKEN')
        _global_manager = DataManager(tushare_token=token)
    return _global_manager


def get_quotes(symbols: List[str]) -> Optional[List[Dict]]:
    """便捷函数：获取实时行情"""
    return get_data_manager().get_quotes(symbols)


def get_kline(symbol: str, count: int = 250) -> Optional[pd.DataFrame]:
    """便捷函数：获取 K 线"""
    return get_data_manager().get_kline(symbol, count=count)


def get_financials(symbol: str) -> Optional[Dict]:
    """便捷函数：获取财务数据"""
    return get_data_manager().get_financials(symbol)


def get_futures_index(index_code: str) -> Optional[pd.DataFrame]:
    """便捷函数：获取股指期货"""
    return get_data_manager().get_futures_index(index_code)


# ═══════════════════════════════════════════════════════════════
# 测试脚本
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("数据源路由层 - 健康检查")
    print("=" * 60)
    
    # 从 .env.tushare 读取 token
    token = None
    env_file = os.path.join(os.path.dirname(__file__), '.env.tushare')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith('TUSHARE_TOKEN='):
                    token = line.strip().split('=', 1)[1]
    
    dm = DataManager(tushare_token=token)
    
    # 显示所有源状态
    status = dm.get_all_sources_status()
    for category, sources in status.items():
        print(f"\n【{category}】")
        for name, info in sources.items():
            icon = "✅" if info['available'] else "❌"
            print(f"  {icon} {name} (优先级:{info['priority']})")
            if info['last_error']:
                print(f"     错误: {info['last_error'][:50]}")
    
    # 测试实时行情
    print("\n" + "=" * 60)
    print("测试实时行情")
    print("=" * 60)
    quotes = dm.get_quotes(['600036', '000001', 'sh000001'])
    if quotes:
        for q in quotes[:3]:
            print(f"  {q.get('code', '')} {q.get('name', '')}: {q.get('price', '')}")
    else:
        print("  无数据")
    
    # 测试 K 线
    print("\n" + "=" * 60)
    print("测试 K 线数据 (600036)")
    print("=" * 60)
    df = dm.get_kline('600036', count=30)
    if df is not None and not df.empty:
        print(f"  数据行数: {len(df)}")
        print(f"  日期范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")
        print(f"  最新收盘价: {df['close'].iloc[-1]:.2f}")
    else:
        print("  无数据")
    
    # 测试财务数据
    print("\n" + "=" * 60)
    print("测试财务数据 (600036)")
    print("=" * 60)
    fin = dm.get_financials('600036')
    if fin:
        for k, v in fin.items():
            if v is not None:
                print(f"  {k}: {v}")
    else:
        print("  无数据")
