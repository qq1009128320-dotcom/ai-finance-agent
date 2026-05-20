"""
专业交互式 K 线图表模块
Plotly 实现：K线 + 成交量 + MA + MACD + BOLL + 缩放拖拽
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_pro_kline(df, entry_zone=None, exit_zone=None):
    """
    渲染专业交互式K线图
    df: DataFrame with columns [open, high, low, close, volume], date index
    """
    if df is None or len(df) < 5:
        return None
    
    # ── 计算技术指标 ──
    close = df['close'].values
    
    # MA
    ma5 = pd.Series(close).rolling(5).mean().values
    ma10 = pd.Series(close).rolling(10).mean().values
    ma20 = pd.Series(close).rolling(20).mean().values
    ma60 = pd.Series(close).rolling(60).mean().values if len(close) >= 60 else None
    
    # MACD
    ema12 = pd.Series(close).ewm(span=12).mean().values
    ema26 = pd.Series(close).ewm(span=26).mean().values
    dif = ema12 - ema26
    dea = pd.Series(dif).ewm(span=9).mean().values
    macd_bar = 2 * (dif - dea)
    
    # BOLL (20,2)
    ma20_series = pd.Series(close).rolling(20).mean()
    std20 = pd.Series(close).rolling(20).std()
    upper = (ma20_series + 2 * std20).values
    lower = (ma20_series - 2 * std20).values
    
    # 涨跌颜色
    colors = ['#EF4444' if close[i] >= df['open'].values[i] else '#10B981' 
              for i in range(len(close))]
    
    # ── 构建图表 ──
    # 4行: K线(大) + 成交量(小) + MACD(小) + (可选)BOLL宽度
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.22, 0.23],
        subplot_titles=("K线 & MA", "成交量", "MACD")
    )
    
    # ── Row 1: K线 + MA + BOLL ──
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name='K线',
        increasing_line_color='#EF4444', decreasing_line_color='#10B981',
        increasing_fillcolor='#EF4444', decreasing_fillcolor='#10B981',
        showlegend=True
    ), row=1, col=1)
    
    # MA 线
    fig.add_trace(go.Scatter(x=df.index, y=ma5, name='MA5',
                            line=dict(color='#F59E0B', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ma10, name='MA10',
                            line=dict(color='#22D3EE', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ma20, name='MA20',
                            line=dict(color='#A78BFA', width=1.5)), row=1, col=1)
    if ma60 is not None:
        fig.add_trace(go.Scatter(x=df.index, y=ma60, name='MA60',
                                line=dict(color='#F87171', width=1, dash='dash')), row=1, col=1)
    
    # BOLL
    fig.add_trace(go.Scatter(x=df.index, y=upper, name='BOLL上轨',
                            line=dict(color='#64748B', width=0.8, dash='dot'),
                            showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=lower, name='BOLL下轨',
                            line=dict(color='#64748B', width=0.8, dash='dot'),
                            fill='tonexty', fillcolor='rgba(100,116,139,0.05)',
                            showlegend=False), row=1, col=1)
    
    # 支撑/阻力位
    if entry_zone:
        for label, price in entry_zone.items():
            fig.add_hline(y=price, line_dash='dash', line_color='#10B981',
                         annotation_text=f"  {label}: {price}", 
                         annotation_position='right',
                         row=1, col=1)
    if exit_zone:
        for label, price in exit_zone.items():
            fig.add_hline(y=price, line_dash='dash', line_color='#EF4444',
                         annotation_text=f"  {label}: {price}",
                         annotation_position='right',
                         row=1, col=1)
    
    # ── Row 2: 成交量 ──
    fig.add_trace(go.Bar(
        x=df.index, y=df['volume'],
        name='成交量', marker_color=colors,
        showlegend=False
    ), row=2, col=1)
    
    # 成交量均线
    vol_ma5 = pd.Series(df['volume'].values).rolling(5).mean().values
    fig.add_trace(go.Scatter(x=df.index, y=vol_ma5, name='VOL MA5',
                            line=dict(color='#F59E0B', width=1),
                            showlegend=False), row=2, col=1)
    
    # ── Row 3: MACD ──
    # MACD 柱
    macd_colors = ['#EF4444' if v >= 0 else '#10B981' for v in macd_bar]
    fig.add_trace(go.Bar(x=df.index, y=macd_bar, name='MACD',
                        marker_color=macd_colors, showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=dif, name='DIF',
                            line=dict(color='#22D3EE', width=1)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=dea, name='DEA',
                            line=dict(color='#F59E0B', width=1)), row=3, col=1)
    # 零轴
    fig.add_hline(y=0, line_color='#475569', line_width=0.5, row=3, col=1)
    
    # ── 布局 ──
    fig.update_layout(
        template='plotly_dark',
        height=650,
        hovermode='x unified',
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(
            orientation='h', yanchor='top', y=1.12, xanchor='left', x=0,
            font=dict(size=10)
        ),
        xaxis_rangeslider_visible=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#0d1117',
        font=dict(color='#94a3b8', size=10),
    )
    
    # X轴
    fig.update_xaxes(showgrid=True, gridcolor='#1e293b', row=1, col=1)
    fig.update_xaxes(showgrid=True, gridcolor='#1e293b', row=2, col=1)
    fig.update_xaxes(showgrid=True, gridcolor='#1e293b', row=3, col=1)
    
    # Y轴
    fig.update_yaxes(showgrid=True, gridcolor='#1e293b', title_text='价格', row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor='#1e293b', title_text='成交量', row=2, col=1)
    fig.update_yaxes(showgrid=True, gridcolor='#1e293b', title_text='MACD', row=3, col=1)
    
    return fig
