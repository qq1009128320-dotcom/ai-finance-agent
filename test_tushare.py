#!/usr/bin/env python3
"""Tushare 数据源验证脚本"""
import tushare as ts
import pandas as pd

ts.set_token('24c510cf10466cf7c3ee5b3ecca6d443edadff672e1f3f454ac92b6c')
pro = ts.pro_api()

print('=' * 60)
print('Tushare 数据源验证报告')
print('=' * 60)

# 1. 股票基础数据
print('\n【1】股票基础数据')
df = pro.stock_basic(exchange='SZSE', fields='ts_code,symbol,name,industry,list_date', limit=5)
print(f'  ✅ 获取 {len(df)} 条')
for _, r in df.iterrows():
    print(f'    {r.ts_code} {r.name} [{r.industry}]')

# 2. 日 K 线
print('\n【2】日 K 线 (600036.SH 招商银行)')
df = pro.daily(ts_code='600036.SH', start_date='20260501', end_date='20260601')
print(f'  ✅ 获取 {len(df)} 条')
if len(df) > 0:
    d = df.sort_values('trade_date').iloc[-1]
    print(f'    最新: {d.trade_date} 开={d.open} 收={d.close} 量={d.vol}')

# 3. 财务指标
print('\n【3】财务指标 (600036.SH)')
df = pro.fina_indicator(ts_code='600036.SH', limit=2)
print(f'  ✅ 获取 {len(df)} 期')
if len(df) > 0:
    d = df.iloc[0]
    print(f'    报告期: {d.ann_date}')
    for c in ['roe', 'gross_margin', 'net_margin', 'pe', 'pb', 'ps', 'total_revenue', 'net_profit']:
        if c in d.index and pd.notna(d[c]):
            print(f'    {c}: {d[c]}')

# 4. 股指期货
print('\n【4】股指期货')
for code, name in [('IF', '沪深300'), ('IH', '上证50'), ('IC', '中证500'), ('IM', '中证1000')]:
    df = pro.futures_index(index_code=code, start_date='20260501', end_date='20260601')
    if len(df) > 0:
        d = df.iloc[-1]
        print(f'  ✅ {code}({name}): 收={d.close} 持仓={d.open_interest} 量={d.volume}')
    else:
        df2 = pro.futures_index(index_code=code, start_date='20250101', end_date='20260601')
        if len(df2) > 0:
            d = df2.iloc[-1]
            print(f'  ✅ {code}({name}): 最新{d.trade_date} 收={d.close}')
        else:
            print(f'  ⚠️ {code}({name}): 无数据')

# 5. 指数数据
print('\n【5】指数数据 (000001.SH 上证指数)')
df = pro.index_daily(ts_code='000001.SH', start_date='20260501', end_date='20260601')
if len(df) > 0:
    d = df.iloc[-1]
    print(f'  ✅ 获取 {len(df)} 条，最新收={d.close}')
else:
    df2 = pro.index_daily(ts_code='000001.SH', start_date='20250101', end_date='20260601')
    if len(df2) > 0:
        d = df2.iloc[-1]
        print(f'  ✅ 宽范围: 最新{d.trade_date} 收={d.close}')
    else:
        print(f'  ⚠️ 无数据')

# 6. 行业分类
print('\n【6】行业分类')
df = pro.stock_classify(classify_type='S', limit=5)
if len(df) > 0:
    print(f'  ✅ 获取 {len(df)} 条')
    for _, r in df.iterrows():
        print(f'    {r.ts_code} -> {r.industry}')
else:
    print(f'  ⚠️ 无数据')

# 7. 概念板块
print('\n【7】概念板块')
df = pro.stock_classify(classify_type='C', limit=5)
if len(df) > 0:
    print(f'  ✅ 获取 {len(df)} 条')
    for _, r in df.iterrows():
        print(f'    {r.ts_code} -> {r.concept}')
else:
    print(f'  ⚠️ 无数据')

print('\n' + '=' * 60)
print('验证完成 ✅')
print('=' * 60)
