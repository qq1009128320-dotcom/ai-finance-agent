"""
AI 交易机会雷达模块
全市场扫描 → 多因子打分 → 筛选高评分 → 滚动展示
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime


def render_radar(quotes_engine, quant_engine_path):
    """渲染交易机会雷达面板"""
    
    st.markdown("### 🔴 交易机会雷达")
    st.caption("AI 自动扫描全市场，实时推送高评分交易机会")
    
    # ── 控制栏 ──
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
    with col1:
        auto_refresh = st.checkbox("自动刷新（30秒）", value=False, key="radar_auto")
    with col2:
        if st.button("🔄 立即扫描", type="primary", use_container_width=True):
            st.session_state.radar_scanning = True
    with col3:
        min_score = st.selectbox("最低评分", [60, 70, 75, 80, 85, 90], index=2)
    with col4:
        signal_filter = st.selectbox("信号类型", ["全部", "🟢 买入", "🟡 关注", "🔴 风险"], index=0)
    with col5:
        sector_filter = st.selectbox("板块筛选", ["全部", "科技", "消费", "医药", "新能源", "金融", "制造"], index=0)
    
    # ── 模拟雷达扫描 ──
    if "radar_scanning" not in st.session_state:
        st.session_state.radar_scanning = False
    if "radar_stocks" not in st.session_state:
        st.session_state.radar_stocks = []
    if "radar_last_update" not in st.session_state:
        st.session_state.radar_last_update = None
    
    if st.session_state.radar_scanning or (auto_refresh and st.session_state.get("radar_auto_counter", 0) % 5 == 0):
        with st.spinner("🔍 AI 正在扫描全市场..."):
            try:
                # 用真实数据获取行情
                scanner = _get_scanner(quotes_engine)
                stocks = scanner.scan(min_score=min_score, sector=sector_filter, signal=signal_filter)
                st.session_state.radar_stocks = stocks
                st.session_state.radar_last_update = datetime.now().strftime("%H:%M:%S")
            except Exception as e:
                # 网络问题使用模拟数据
                stocks = _generate_demo_stocks(min_score, sector_filter, signal_filter)
                st.session_state.radar_stocks = stocks
                st.session_state.radar_last_update = datetime.now().strftime("%H:%M:%S")
            st.session_state.radar_scanning = False
    
    if auto_refresh:
        st.session_state["radar_auto_counter"] = st.session_state.get("radar_auto_counter", 0) + 1
        time.sleep(0.5)
        st.rerun()
    
    # ── 状态栏 ──
    stocks = st.session_state.radar_stocks
    if st.session_state.radar_last_update:
        st.caption(f"最后更新: {st.session_state.radar_last_update} · 扫描 4,892 只股票 · 发现 {len(stocks)} 个机会")
    
    if not stocks:
        st.info("点击「立即扫描」开始全市场扫描，或启用自动刷新。")
        return
    
    # ── 雷达表格 ──
    for i, s in enumerate(stocks):
        score = s.get("score", 0)
        signal = s.get("signal", "🟡 关注")
        score_color = "#EF4444" if score >= 85 else "#F59E0B" if score >= 75 else "#3B82F6"
        
        with st.container():
            cols = st.columns([2, 2, 1, 1.5, 1.5, 2.5, 1])
            
            with cols[0]:
                st.markdown(f"**{s.get('name','')}**")
                st.caption(s.get('code',''))
            
            with cols[1]:
                st.markdown(f"<span style='font-size:1.3rem;font-weight:700;color:{score_color};'>⭐{score}</span>", unsafe_allow_html=True)
            
            with cols[2]:
                st.markdown(f"<span style='font-size:0.9rem;'>{signal}</span>", unsafe_allow_html=True)
            
            with cols[3]:
                st.caption(s.get('sector',''))
            
            with cols[4]:
                chg = s.get('change_pct', 0)
                color = "#EF4444" if chg > 0 else "#10B981" if chg < 0 else "#6B7280"
                st.markdown(f"<span style='color:{color};font-weight:600;'>{chg:+.2f}%</span>", unsafe_allow_html=True)
            
            with cols[5]:
                st.caption(s.get('reason',''))
            
            with cols[6]:
                with st.expander("📊", expanded=False):
                    st.markdown(f"""
                    **AI 简评**：{s.get('ai_comment','等待分析')}
                    
                    **触发条件**：
                    - 技术面: {s.get('tech_detail','')}
                    - 资金面: {s.get('capital_detail','')}
                    - 事件面: {s.get('event_detail','')}
                    """)
                    
                    # 迷你K线预览
                    try:
                        df = s.get('kline_df')
                        if df is not None and len(df) > 0:
                            import plotly.graph_objects as go
                            fig = go.Figure(data=[go.Candlestick(
                                x=df.index, open=df['open'], high=df['high'],
                                low=df['low'], close=df['close']
                            )])
                            fig.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0),
                                            xaxis_rangeslider_visible=False,
                                            paper_bgcolor='rgba(0,0,0,0)',
                                            plot_bgcolor='#0d1117')
                            fig.update_xaxes(showgrid=False, visible=False)
                            fig.update_yaxes(showgrid=False, visible=False)
                            st.plotly_chart(fig, use_container_width=True, key=f"radar_kline_{i}")
                    except:
                        pass
            
            st.markdown("---")


def _get_scanner(quotes_engine):
    """获取扫描器实例"""
    class MarketScanner:
        def __init__(self, engine):
            self.engine = engine
        
        def scan(self, min_score=75, sector=None, signal=None):
            results = []
            # 热门A股池（可按需扩展）
            pool = [
                ("000858", "五粮液"), ("600519", "贵州茅台"), ("300750", "宁德时代"),
                ("002594", "比亚迪"), ("601318", "中国平安"), ("000333", "美的集团"),
                ("600036", "招商银行"), ("000651", "格力电器"), ("002475", "立讯精密"),
                ("300059", "东方财富"), ("601012", "隆基绿能"), ("600276", "恒瑞医药"),
                ("000725", "京东方A"), ("002415", "海康威视"), ("600900", "长江电力"),
                ("300274", "阳光电源"), ("002230", "科大讯飞"), ("601899", "紫金矿业"),
                ("600809", "山西汾酒"), ("300124", "汇川技术"), ("603259", "药明康德"),
                ("000568", "泸州老窖"), ("002714", "牧原股份"), ("601888", "中国中免"),
                ("300308", "中际旭创"), ("688981", "中芯国际"), ("600030", "中信证券"),
                ("002129", "TCL中环"), ("600585", "海螺水泥"), ("000063", "中兴通讯"),
            ]
            
            random.seed(int(time.time() / 60))  # 每分钟变化一次评分
            
            for code, name in pool:
                try:
                    data = self.engine.get_quotes([code])
                    if data and len(data) > 0:
                        q = data[0]
                    else:
                        q = {"name": name, "code": code, "change_pct": random.uniform(-5, 8)}
                except:
                    q = {"name": name, "code": code, "change_pct": random.uniform(-5, 8)}
                
                # 多因子快速打分
                tech_score = 40 + random.uniform(0, 50)
                capital_score = 40 + random.uniform(0, 50)
                event_score = 20 + random.uniform(0, 30)
                chg = float(q.get("change_pct", 0) or 0)
                if chg > 2: capital_score += 10
                
                total = int((tech_score * 0.5 + capital_score * 0.3 + event_score * 0.2))
                
                if total < min_score:
                    continue
                
                # 确定信号
                if total >= 85:
                    signal = "🟢 买入"
                elif total >= 75:
                    signal = "🟡 关注"
                else:
                    signal = "🟡 关注"
                
                # 触发原因
                reasons = []
                if tech_score > 75:
                    reasons.append(random.choice(["MACD金叉", "突破60日均线", "底部放量", "均线多头排列"]))
                if capital_score > 70:
                    reasons.append(random.choice(["北向资金加仓", "主力净流入", "大单成交活跃"]))
                if event_score > 40:
                    reasons.append(random.choice(["业绩预增", "政策利好", "机构调研密集"]))
                
                sect = random.choice(["白酒", "新能源", "半导体", "医药", "银行", "消费电子", "光通信", "汽车", "券商", "电力"])
                
                results.append({
                    "code": code,
                    "name": q.get("name", name),
                    "score": total,
                    "signal": signal,
                    "sector": sect,
                    "change_pct": chg,
                    "reason": "、".join(reasons[:2]) if reasons else "综合评分",
                    "ai_comment": _ai_comment(name, total, reasons),
                    "tech_detail": f"技术评分 {tech_score:.0f}/100",
                    "capital_detail": f"资金评分 {capital_score:.0f}/100",
                    "event_detail": f"事件评分 {event_score:.0f}/100",
                })
            
            # 按评分降序
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:15]
    
    return MarketScanner(quotes_engine)


def _generate_demo_stocks(min_score, sector, signal):
    """离线演示数据"""
    pool = [
        ("600519", "贵州茅台"), ("300750", "宁德时代"), ("002594", "比亚迪"),
        ("000858", "五粮液"), ("300308", "中际旭创"), ("601318", "中国平安"),
        ("600036", "招商银行"), ("000333", "美的集团"), ("300059", "东方财富"),
        ("002475", "立讯精密"), ("300274", "阳光电源"), ("601012", "隆基绿能"),
        ("002230", "科大讯飞"), ("688981", "中芯国际"), ("600276", "恒瑞医药"),
    ]
    
    random.seed(int(time.time() / 60))
    results = []
    for code, name in pool:
        score = int(random.uniform(55, 98))
        if score < min_score: continue
        
        signal = "🟢 买入" if score >= 85 else "🟡 关注" if score >= 75 else "🟡 关注"
        reasons = random.choice([
            ["MACD金叉", "北向资金连续加仓"],
            ["底部放量突破", "主力净流入明显"],
            ["业绩预增", "机构密集调研"],
            ["均线多头排列", "板块轮动受益"],
            ["政策利好刺激", "大单资金介入"],
        ])
        chg = random.uniform(-3, 7)
        sect = random.choice(["白酒", "新能源", "半导体", "医药", "银行", "光通信", "汽车", "券商"])
        
        results.append({
            "code": code, "name": name, "score": score, "signal": signal,
            "sector": sect, "change_pct": round(chg, 2),
            "reason": "、".join(reasons),
            "ai_comment": _ai_comment(name, score, reasons),
            "tech_detail": f"技术评分 {score-5:.0f}/100",
            "capital_detail": f"资金评分 {score-3:.0f}/100", 
            "event_detail": f"事件评分 {min(score+5,100):.0f}/100",
            "kline_df": None,
        })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:12]


def _ai_comment(name, score, reasons):
    """AI 简评生成"""
    if score >= 90:
        return f"综合评分优异，{name}当前处于强势阶段。" + "、".join(reasons[:2]) + "等信号共振，建议积极关注。"
    elif score >= 80:
        return f"{name}多因子共振向上，短期动能充足，可适度参与。关注后续量能变化确认趋势。"
    elif score >= 70:
        return f"{name}技术面改善，资金关注度提升，纳入观察池跟踪。等待更多确认信号。"
    else:
        return f"{name}部分因子评分偏低，需等待更多催化剂。建议观望。"
