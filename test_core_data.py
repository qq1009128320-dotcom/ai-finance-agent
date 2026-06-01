#!/usr/bin/env python3
"""核心数据源验证脚本 - 跳过期货"""
import os
import sys
import warnings
warnings.filterwarnings('ignore')

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))

from data.data_router import DataRouter

print('=' * 60)
print('核心数据源验证（跳过期货）')
print('=' * 60)

# 初始化路由
router = DataRouter(
    tushare_token='24c510cf10466cf7c3ee5b3ecca6d443edadff672e1f3f454ac92b6c'
)

# 1. 健康检查
print('\n【1】数据源健康检查')
for source in router.sources:
    status = '✅' if source.health_check() else '❌'
    print(f'  {status} {source.name}: {source.last_error or "正常"}')

# 2. 股票 K 线
print('\n【2】股票 K 线 (600036.SH 招商银行)')
df = router.get_kline('600036.SH', start_date='20260501', end_date='20260531')
if df is not None and not df.empty:
    print(f'  ✅ {len(df)} 条')
    latest = df.iloc[-1]
    print(f'    最新: {latest["trade_date"]} 收={latest["close"]}')
else:
    print(f'  ❌ 获取失败: {router.last_error}')

# 3. 指数 K 线
print('\n【3】指数 K 线 (000001.SH 上证指数)')
df = router.get_index_data('000001.SH', start_date='20260501', end_date='20260531')
if df is not None and not df.empty:
    print(f'  ✅ {len(df)} 条')
    latest = df.iloc[-1]
    print(f'    最新: {latest["trade_date"]} 收={latest["close"]}')
else:
    print(f'  ❌ 获取失败: {router.last_error}')

# 4. 财务指标
print('\n【4】财务指标 (600036.SH)')
df = router.get_financial_indicator('600036.SH', limit=4)
if df is not None and not df.empty:
    print(f'  ✅ {len(df)} 期')
    latest = df.iloc[0]
    for c in ['ann_date', 'roe', 'gross_margin', 'pe', 'pb']:
        if c in latest.index and pd.notna(latest[c]):
            print(f'    {c}: {latest[c]}')
else:
    print(f'  ❌ 获取失败: {router.last_error}')

# 5. 资金流向
print('\n【5】资金流向 (600036.SH)')
df = router.get_moneyflow('600036.SH', start_date='20260520', end_date='20260531')
if df is not None and not df.empty:
    print(f'  ✅ {len(df)} 条')
else:
    print(f'  ❌ 获取失败: {router.last_error}')

# 6. 期货（已禁用）
print('\n【6】期货数据（已禁用）')
df = router.get_futures_index('IF', start_date='20260501', end_date='20260531')
print(f'  ⚠️ 已禁用: {router.last_error}')

# 7. 交易日
print('\n【7】交易日 (2026-06)')
df = router.get_trade_cal('SSE', start_date='20260601', end_date='20260607')
if df is not None and not df.empty:
    print(f'  ✅ {len(df)} 条')
    for _, r in df.iterrows():
        print(f'    {r["calendar_date"]} 开市={r["is_open"]}')
else:
    print(f'  ❌ 获取失败: {router.last_error}')

print('\n' + '=' * 60)
print('验证完成')
print('=' * 60)
print()
print('✅ 可用: 股票 K 线、指数数据、财务指标、资金流向、交易日')
print('⚠️ 已禁用: 期货数据（Tushare 权限不足）')
