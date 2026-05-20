"""
A股特色数据面板
板块轮动热力图 + 北向资金 + 龙虎榜
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import random
import time
from datetime import datetime


def render_sector_heatmap():
    """板块轮动热力图"""
    st.markdown("### 🔥 板块轮动热力图")
    st.caption("行业板块涨跌幅一览，一眼看穿资金流向")
    
    # 模拟板块数据
    random.seed(int(time.time() / 300))
    
    sectors = {
        "白酒": random.uniform(-3, 5),
        "新能源": random.uniform(-4, 6),
        "半导体": random.uniform(-5, 4),
        "医药": random.uniform(-3, 3),
        "银行": random.uniform(-1, 2),
        "券商": random.uniform(-4, 5),
        "消费电子": random.uniform(-3, 4),
        "汽车": random.uniform(-2, 6),
        "光伏": random.uniform(-5, 5),
        "军工": random.uniform(-3, 3),
        "房地产": random.uniform(-4, 2),
        "煤炭": random.uniform(-2, 3),
        "电力": random.uniform(-1, 2),
        "通信": random.uniform(-3, 4),
        "传媒": random.uniform(-4, 3),
        "计算机": random.uniform(-5, 5),
        "机械": random.uniform(-2, 3),
        "化工": random.uniform(-3, 2),
        "农林牧渔": random.uniform(-2, 2),
        "有色金属": random.uniform(-3, 4),
    }
    
    # 按涨跌幅排序
    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
    
    # 准备热力图数据（4行x5列）
    n = len(sorted_sectors)
    rows, cols = 5, 4
    heatmap_data = [["" for _ in range(cols)] for _ in range(rows)]
    heatmap_values = [[0 for _ in range(cols)] for _ in range(rows)]
    heatmap_text = [["" for _ in range(cols)] for _ in range(rows)]
    
    for i, (name, val) in enumerate(sorted_sectors):
        r, c = i // cols, i % cols
        if r < rows:
            heatmap_data[r][c] = name
            heatmap_values[r][c] = val
            heatmap_text[r][c] = f"{name}<br>{val:+.2f}%"
    
    # 自定义颜色：红涨绿跌
    colorscale = [
        [0.0, '#10B981'], [0.3, '#34D399'], [0.45, '#1E293B'],
        [0.5, '#0F1724'], [0.55, '#1E293B'],
        [0.7, '#F87171'], [1.0, '#EF4444']
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_values,
        text=heatmap_text,
        texttemplate='%{text}',
        textfont=dict(size=12, color='white'),
        colorscale=colorscale,
        zmid=0,
        showscale=False,
        xgap=4, ygap=4,
        hoverinfo='text',
    ))
    
    fig.update_layout(
        template='plotly_dark',
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#0d1117',
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 领涨/领跌榜
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🟢 领涨板块**")
        for name, val in sorted_sectors[:5]:
            st.markdown(f"• {name} <span style='color:#EF4444;'>+{val:.2f}%</span>", unsafe_allow_html=True)
    with c2:
        st.markdown("**🔴 领跌板块**")
        for name, val in sorted_sectors[-5:]:
            st.markdown(f"• {name} <span style='color:#10B981;'>{val:.2f}%</span>", unsafe_allow_html=True)


def render_north_money():
    """北向资金监控"""
    st.markdown("### 💰 北向资金监控")
    st.caption("外资通过沪深港通买卖A股的情况")
    
    random.seed(int(time.time() / 300))
    
    # 今日/本周/本月
    c1, c2, c3, c4 = st.columns(4)
    today = random.uniform(-80, 120)
    week = random.uniform(-200, 300)
    month = random.uniform(-500, 800)
    total = 18450 + month
    
    c1.metric("今日净流入", f"{today:+.1f}亿", delta=None)
    c2.metric("本周净流入", f"{week:+.1f}亿", delta=None)
    c3.metric("本月净流入", f"{month:+.1f}亿", delta=None)
    c4.metric("累计净流入", f"{total:.0f}亿", delta=None)
    
    # 近10日净流入趋势
    dates = pd.date_range(end=datetime.now(), periods=10, freq='B')
    flows = np.cumsum(np.random.randn(10) * 30)
    
    fig = go.Figure()
    colors_flow = ['#EF4444' if v >= 0 else '#10B981' for v in flows]
    fig.add_trace(go.Bar(x=dates, y=flows, name='净流入(亿)', marker_color=colors_flow))
    fig.add_trace(go.Scatter(x=dates, y=np.cumsum(flows), name='累计',
                            line=dict(color='#22D3EE', width=2), yaxis='y2'))
    fig.update_layout(
        template='plotly_dark', height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(title='日净流入(亿)', gridcolor='#1e293b'),
        yaxis2=dict(title='累计(亿)', overlaying='y', side='right', gridcolor='#1e293b'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        hovermode='x unified',
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 北向重仓股
    st.caption("北向资金重仓TOP5")
    stocks = [
        ("贵州茅台", 1580, "+12.3亿"),
        ("宁德时代", 892, "+8.6亿"),
        ("美的集团", 756, "-3.2亿"),
        ("招商银行", 623, "+5.1亿"),
        ("五粮液", 589, "+2.8亿"),
    ]
    for name, hold, change in stocks:
        c = "#EF4444" if "+" in change else "#10B981"
        st.markdown(f"• **{name}** — 持仓 {hold}亿 <span style='color:{c};'>{change}</span>", unsafe_allow_html=True)


def render_dragon_tiger():
    """龙虎榜"""
    st.markdown("### 🐉 今日龙虎榜")
    st.caption("游资/机构大额买卖动向")
    
    random.seed(int(time.time() / 3600))
    
    data = []
    for _ in range(8):
        name = random.choice(["贵州茅台", "宁德时代", "中际旭创", "科大讯飞", 
                             "比亚迪", "隆基绿能", "药明康德", "中国平安",
                             "紫金矿业", "工业富联", "中科曙光", "浪潮信息"])
        buy = random.uniform(0.5, 8)
        sell = random.uniform(0.3, 6)
        net = buy - sell
        
        buyers = random.sample(["机构专用", "深股通", "沪股通", "游资-中信上海", 
                               "游资-华泰荣超", "游资-国泰君安", "QFII"], 2)
        data.append({
            "股票": name,
            "净买入(亿)": f"{net:+.2f}",
            "买入(亿)": f"{buy:.1f}",
            "卖出(亿)": f"{sell:.1f}",
            "买方": "、".join(buyers),
            "原因": random.choice(["业绩预增", "政策利好", "技术突破", "板块轮动", "超跌反弹"])
        })
    
    df = pd.DataFrame(data)
    df["净买入(亿)"] = pd.to_numeric(df["净买入(亿)"])
    df = df.sort_values("净买入(亿)", ascending=False)
    
    st.dataframe(df, use_container_width=True, hide_index=True)
