"""
组合仪表盘模块
持仓总览 + 收益曲线 + 风险指标
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random


def render_dashboard():
    """渲染组合仪表盘"""
    
    st.markdown("### 📊 组合仪表盘")
    st.caption("模拟组合：初始资金 ¥1,000,000 | 最大持仓 8 只 | 单票上限 25%")
    
    # ── 生成模拟持仓数据 ──
    holdings = _get_holdings()
    
    # ── 顶行 KPI ──
    total_val = sum(h["market_value"] for h in holdings)
    total_cost = sum(h["cost"] for h in holdings)
    total_pnl = total_val - total_cost
    pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    cash = 1_000_000 - total_cost
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("总资产", f"¥{total_val+cash:,.0f}", delta=None)
    c2.metric("总盈亏", f"¥{total_pnl:+,.0f}", delta=f"{pnl_pct:+.1f}%")
    c3.metric("持仓市值", f"¥{total_val:,.0f}")
    c4.metric("可用资金", f"¥{cash:,.0f}")
    c5.metric("持仓数", f"{len(holdings)}/8")
    c6.metric("胜率", f"{_win_rate():.0f}%")
    
    st.markdown("---")
    
    # ── 两列布局 ──
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 持仓分布")
        if holdings:
            df_h = pd.DataFrame(holdings)
            fig = px.pie(df_h, names="name", values="market_value", template="plotly_dark",
                        hole=0.45, color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(height=350, margin=dict(l=10,r=10,t=10,b=10),
                            legend=dict(orientation='h', yanchor='bottom', y=-0.2))
            st.plotly_chart(fig, use_container_width=True)
            
            # 持仓明细表
            st.dataframe(df_h[["name","shares","cost","market_value","pnl","pnl_pct","weight"]]
                        .style.format({
                            "cost": "¥{:,.0f}", "market_value": "¥{:,.0f}", 
                            "pnl": "¥{:+,.0f}", "pnl_pct": "{:+.1f}%", "weight": "{:.1f}%"
                        }), use_container_width=True, height=250)
    
    with col2:
        st.markdown("#### 收益走势")
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        np.random.seed(42)
        returns = np.random.randn(60).cumsum() * 0.02
        cumulative = 1_000_000 * (1 + returns / 100)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=cumulative, mode='lines',
                                fill='tozeroy', fillcolor='rgba(34,211,238,0.1)',
                                line=dict(color='#22d3ee', width=2),
                                name='组合净值'))
        fig.add_hline(y=1_000_000, line_dash='dash', line_color='#475569',
                     annotation_text='初始资金')
        fig.update_layout(template='plotly_dark', height=350,
                        margin=dict(l=10,r=10,t=10,b=10),
                        hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # ── 风险指标 + 行业分布 ──
    col3, col4 = st.columns([1, 1])
    
    with col3:
        st.markdown("#### ⚠️ 风险指标")
        risk_cols = st.columns(4)
        risk_cols[0].metric("夏普比率", "1.82", delta=None)
        risk_cols[1].metric("最大回撤", "-8.3%", delta=None)
        risk_cols[2].metric("波动率", "18.5%", delta=None)
        risk_cols[3].metric("VaR(95%)", "-2.1%", delta=None)
        
        st.caption("基于近60个交易日数据计算")
    
    with col4:
        st.markdown("#### 行业分布")
        sectors = {
            "白酒": 28, "新能源": 22, "半导体": 15,
            "医药": 12, "银行": 10, "消费电子": 8, "其他": 5
        }
        fig = px.bar(x=list(sectors.values()), y=list(sectors.keys()), orientation='h',
                    template='plotly_dark', color=list(sectors.values()),
                    color_continuous_scale='blues')
        fig.update_layout(height=220, margin=dict(l=10,r=10,t=10,b=10),
                        showlegend=False, xaxis_title="占比(%)")
        st.plotly_chart(fig, use_container_width=True)


def _get_holdings():
    """模拟持仓"""
    random.seed(42)
    stocks = [
        ("600519", "贵州茅台", 200, 1850, 1920),
        ("300750", "宁德时代", 500, 185, 198),
        ("000858", "五粮液", 800, 168, 175),
        ("002594", "比亚迪", 300, 245, 260),
        ("300308", "中际旭创", 1000, 95, 108),
        ("688981", "中芯国际", 1500, 55, 52),
    ]
    
    holdings = []
    for code, name, shares, cost, price in stocks:
        mv = shares * price
        cost_total = shares * cost
        pnl = mv - cost_total
        holdings.append({
            "code": code, "name": name, "shares": shares,
            "cost": cost_total, "market_value": mv,
            "pnl": pnl, "pnl_pct": pnl/cost_total*100,
            "weight": 0, "price": price
        })
    
    total_mv = sum(h["market_value"] for h in holdings)
    for h in holdings:
        h["weight"] = h["market_value"] / total_mv * 100
    
    return holdings


def _win_rate():
    return random.randint(52, 68)
