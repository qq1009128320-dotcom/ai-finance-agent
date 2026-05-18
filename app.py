#!/usr/bin/env python3
"""
AI金融决策智能体 — Web演示界面
2026江汉区AI智能体创新大赛 | AI＋垂直应用（金融科技）
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
import time
from datetime import datetime

# ── 路径 ──
import os as _os
PROJECT_DIR = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, _os.path.join(PROJECT_DIR, "data"))

import signal as _signal_mod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

def _run_with_timeout(fn, timeout=8, default=None):
    """在独立线程运行函数，超时返回默认值"""
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout:
            return default
        except Exception:
            return default

from quotes import TencentQuotes

# akshare依赖的模块用延迟加载+超时保护
_signal_engine = None
_news_engine = None
_finance_engine = None

def _get_signal_engine():
    global _signal_engine
    if _signal_engine is None:
        try:
            _signal_engine = _run_with_timeout(lambda: __import__("layers.signal", fromlist=["SignalScanner"]).SignalScanner(), timeout=5)
        except (ImportError, ModuleNotFoundError):
            _signal_engine = _run_with_timeout(lambda: __import__("signal", fromlist=["SignalScanner"]).SignalScanner() if False else None, timeout=1)
            _signal_engine = None
    return _signal_engine

def _get_news_engine():
    global _news_engine
    if _news_engine is None:
        try:
            _news_engine = _run_with_timeout(lambda: __import__("layers.news", fromlist=["NewsFeed"]).NewsFeed(), timeout=5)
        except (ImportError, ModuleNotFoundError):
            _news_engine = None
    return _news_engine

def _get_finance_engine():
    global _finance_engine
    if _finance_engine is None:
        try:
            _finance_engine = _run_with_timeout(lambda: __import__("layers.finance", fromlist=["FinancialData"]).FinancialData(), timeout=5)
        except (ImportError, ModuleNotFoundError):
            _finance_engine = None
    return _finance_engine

# ── 页面配置 ──
st.set_page_config(
    page_title="AI金融决策智能体",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: 700; color: #0F172A; margin-bottom: 0; }
    .sub-header { font-size: 1rem; color: #64748B; margin-top: 0; }
    .metric-card { 
        background: linear-gradient(135deg, #0F172A, #1E293B);
        border-radius: 12px; padding: 1.2rem; text-align: center;
        border-left: 4px solid #38BDF8;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #38BDF8; }
    .metric-label { font-size: 0.85rem; color: #94A3B8; margin-top: 0.3rem; }
    .positive { color: #EF4444 !important; }
    .negative { color: #10B981 !important; }
    .section-title { font-size: 1.3rem; font-weight: 600; color: #0F172A; border-bottom: 3px solid #38BDF8; padding-bottom: 0.3rem; margin-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 缓存数据获取
# ═══════════════════════════════════════════

@st.cache_resource
def get_quotes_engine():
    return TencentQuotes()

@st.cache_resource
def get_signal_engine():
    return _get_signal_engine()

@st.cache_resource
def get_news_engine():
    return _get_news_engine()

@st.cache_resource
def get_finance_engine():
    return _get_finance_engine()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_quote(symbol: str) -> dict:
    try:
        data = get_quotes_engine().get_quotes([symbol])
        return data[0] if data else {}
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=120, show_spinner=False)
def fetch_kline(symbol: str, period="day", count=60):
    try:
        data = get_quotes_engine().get_kline([symbol], period=period, count=count)
        bars = data.get(symbol, [])
        if not bars:
            return None
        # K线格式: ['date','open','close','high','low','volume']
        # 腾讯K线可能返回6或7列，取前6列
        cols = ["date", "open", "close", "high", "low", "volume"]
        df = pd.DataFrame(bars, columns=cols[:len(bars[0])] if bars else cols)
        for c in ["open", "close", "high", "low"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        return df
    except Exception as e:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_signal():
    eng = get_signal_engine()
    if eng is None:
        return {"sector_flow": [], "hot_concepts": []}
    return _run_with_timeout(lambda: eng.scan(), timeout=8, default={"sector_flow": [], "hot_concepts": []})


@st.cache_data(ttl=300, show_spinner=False)
def fetch_news(symbol: str = None):
    eng = get_news_engine()
    if eng is None:
        return []
    return _run_with_timeout(lambda: eng.get_news(symbol), timeout=8, default=[])


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_finance(symbol: str):
    eng = get_finance_engine()
    if eng is None:
        return {}
    data = _run_with_timeout(lambda: eng.get_key_metrics(symbol), timeout=8, default={})
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if not k.startswith("error_")}
    return {}


# ═══════════════════════════════════════════
# 评分引擎
# ═══════════════════════════════════════════

def score_technical(df) -> float:
    """技术面 0-100"""
    if df is None or len(df) < 20:
        return 50
    try:
        close = df["close"].values
        ma5 = np.mean(close[-5:])
        ma20 = np.mean(close[-20:])
        current = close[-1]
        score = 50
        if current > ma5: score += 10
        if current > ma20: score += 10
        if ma5 > ma20: score += 10
        returns = np.diff(close[-20:]) / close[-21:-1]
        vol = np.std(returns) * 100
        if vol < 2: score += 10
        elif vol < 4: score += 5
        mom = (close[-1] / close[-5] - 1) * 100
        if 0 < mom < 5: score += 15
        elif mom > 0: score += 5
        elif mom < -5: score -= 10
        return max(0, min(100, score))
    except:
        return 50


def score_capital(quote: dict) -> float:
    """资金面 0-100"""
    try:
        score = 50
        chg = float(quote.get("change_pct", 0) or 0)
        if chg > 3: score += 20
        elif chg > 1: score += 10
        elif chg > 0: score += 5
        elif chg < -3: score -= 20
        elif chg < -1: score -= 10
        amt = float(quote.get("amount", 0) or 0)
        if amt > 1e9: score += 10
        elif amt > 5e8: score += 5
        return max(0, min(100, score))
    except:
        return 50


def score_financial(fin: dict) -> float:
    """财务面 0-100"""
    if not fin:
        return 50
    try:
        score = 50
        roe_keys = ["ROE", "roe", "净资产收益率"]
        for k in roe_keys:
            if k in fin:
                v = float(fin[k])
                if v > 15: score += 20
                elif v > 10: score += 10
                elif v > 0: score += 5
                else: score -= 10
                break
        return max(0, min(100, score))
    except:
        return 50


def score_sentiment(news: list, change_pct: float) -> float:
    """情绪面 0-100"""
    try:
        score = 50
        if news and len(news) >= 3:
            score += 5
        if change_pct > 0:
            score += min(change_pct * 3, 20)
        elif change_pct < 0:
            score += max(change_pct * 3, -20)
        return max(0, min(100, score))
    except:
        return 50


def analyze(symbol: str) -> dict:
    """完整分析流程 — 调用 quant_engine 综合量化分析引擎（28因子+Piotroski+VaR）"""
    import subprocess, tempfile, json, sys

    quote = fetch_quote(symbol)
    if not quote or "error" in quote:
        return {"error": f"无法获取 {symbol} 行情数据"}

    name = quote.get("name", symbol)
    price = float(quote.get("price", 0) or 0)
    change_pct = float(quote.get("change_pct", 0) or 0)

    # 获取财务数据（轻量操作，不阻塞）
    fin = fetch_finance(symbol)

    # 调用 quant_engine 子进程（隔离依赖，避免阻塞主线程）
    engine_script = f'''
import sys, json, os, warnings
warnings.filterwarnings("ignore")
os.environ["HERMES_QUIET"] = "1"

sys.path.insert(0, "{PROJECT_DIR}")
sys.path.insert(0, "{PROJECT_DIR}/data")

import pandas as pd
from quant_engine import run_analysis

# 读取K线数据
from quotes import TencentQuotes
q = TencentQuotes()
kline_data = q.get_kline(["{symbol}"], "day", 250)
bars = kline_data.get("{symbol}", [])

if not bars or len(bars) < 20:
    print(json.dumps({{"error": "K线数据不足"}}))
    sys.exit(0)

rows = []
for k in bars:
    row = [k[0], k[1], k[2], k[3], k[4], k[5]]
    rows.append(row)

df = pd.DataFrame(rows, columns=["date","open","close","high","low","volume"])
for col in ["open","close","high","low"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
df["date"] = pd.to_datetime(df["date"])
df.set_index("date", inplace=True)
df.sort_index(inplace=True)

# 财务数据
financials = {json.dumps(fin)}

# 新闻数据
news_list = {json.dumps(fetch_news("{symbol}") if "{symbol}" else [])}

# 运行分析
report = run_analysis("{symbol}", "{name}", df, {price}, {change_pct}, financials, news_list)

# 序列化为JSON
output = {{
    "total_score": report.total_score,
    "rating": report.rating,
    "confidence": report.confidence,
    "signal_summary": report.signal_summary,
    "recommendation": report.recommendation,
    "position_advice": report.position_advice,
    "dimensions": [],
    "factor_distribution": report.factor_distribution,
    "risk_metrics": report.risk_metrics,
    "tech_snapshot": report.tech_snapshot,
    "entry_zone": report.entry_zone,
    "exit_zone": report.exit_zone,
    "triggers": report.triggers,
    "relative_strength": report.relative_strength,
    "financial_summary": report.financial_summary,
    "news_sentiment": report.news_sentiment,
}}

for dim in report.dimensions:
    dim_data = {{
        "name": dim.name,
        "total_score": dim.total_score,
        "max_score": dim.max_score,
        "summary": dim.summary,
        "strength": dim.strength,
        "weakness": dim.weakness,
        "factors": []
    }}
    for f in dim.factors:
        dim_data["factors"].append({{
            "name": f.name,
            "value": f.value,
            "score": f.score,
            "signal": f.signal,
            "detail": f.detail
        }})
    output["dimensions"].append(dim_data)

print(json.dumps(output, default=str, ensure_ascii=False))
'''
    try:
        tmpf = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8')
        tmpf.write(engine_script)
        tmpf.close()
        proc = subprocess.run(
            [sys.executable, tmpf.name],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONPATH": PROJECT_DIR + ":" + os.environ.get("PYTHONPATH", "")}
        )
        output = proc.stdout.strip()
        os.unlink(tmpf.name)

        if output and not output.startswith("Traceback"):
            report = json.loads(output)
            if "error" not in report:
                # 构建兼容旧格式的结果
                dim_scores = {}
                for d in report.get("dimensions", []):
                    dim_scores[d["name"]] = d["total_score"]

                return {
                    "symbol": symbol, "name": name, "price": price, "change_pct": change_pct,
                    "open": quote.get("open", ""), "high": quote.get("high", ""),
                    "low": quote.get("low", ""), "amount": quote.get("amount", ""),
                    "pe": quote.get("pe", ""), "pb": quote.get("pb", ""),
                    "turnover": quote.get("turnover", ""),
                    "scores": dim_scores,
                    "total": report["total_score"],
                    "rating": report.get("rating", ""),
                    "confidence": report.get("confidence", ""),
                    "level": report.get("rating", ""),
                    "advice": report.get("recommendation", ""),
                    "position_advice": report.get("position_advice", ""),
                    "signal_summary": report.get("signal_summary", ""),
                    "dimensions": report.get("dimensions", []),
                    "factor_distribution": report.get("factor_distribution", {}),
                    "risk_metrics": report.get("risk_metrics", {}),
                    "tech_snapshot": report.get("tech_snapshot", {}),
                    "entry_zone": report.get("entry_zone", {}),
                    "exit_zone": report.get("exit_zone", {}),
                    "triggers": report.get("triggers", {}),
                    "relative_strength": report.get("relative_strength", {}),
                    "financial_summary": report.get("financial_summary", {}),
                    "news_sentiment": report.get("news_sentiment", {}),
                    "engine": True,
                    "engine_type": "quant_v2",
                }
    except Exception as e:
        pass

    # 降级：引擎不可用时用简化评分
    kline = fetch_kline(symbol)
    result = {
        "symbol": symbol, "name": name, "price": price, "change_pct": change_pct,
        "open": quote.get("open", ""), "high": quote.get("high", ""),
        "low": quote.get("low", ""), "amount": quote.get("amount", ""),
        "pe": quote.get("pe", ""), "pb": quote.get("pb", ""),
        "turnover": quote.get("turnover", ""),
        "scores": {"技术面": 0, "资金面": 0, "财务面": 0, "情绪面": 0},
        "total": 0, "level": "", "advice": "", "engine": False,
    }
    result["scores"]["技术面"] = score_technical(kline)
    result["scores"]["资金面"] = score_capital(quote)
    result["scores"]["财务面"] = score_financial(fin)
    news = fetch_news(symbol)
    result["scores"]["情绪面"] = score_sentiment(news, result["change_pct"])
    weights = {"技术面": 0.35, "资金面": 0.25, "财务面": 0.20, "情绪面": 0.20}
    result["total"] = round(sum(result["scores"][k] * w for k, w in weights.items()), 1)

    if result["total"] >= 75:
        result["level"] = "🟢 强烈推荐"
        result["advice"] = "四维评分表现优秀，可重点关注。"
    elif result["total"] >= 60:
        result["level"] = "🔵 可以关注"
        result["advice"] = "综合表现良好，可纳入观察池。"
    elif result["total"] >= 40:
        result["level"] = "🟡 中性观望"
        result["advice"] = "评分一般，建议观望或轻仓。"
    else:
        result["level"] = "🔴 建议规避"
        result["advice"] = "评分偏低，风险大于机会。"

    return result


# ═══════════════════════════════════════════
# UI 组件
# ═══════════════════════════════════════════

def render_header():
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown('<p class="main-header">📊 AI金融决策智能体</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">自主感知 · 多维分析 · 智能决策 — 面向个人投资者的AI投研助手</p>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="text-align:right;color:#94A3B8;font-size:0.8rem;margin-top:1rem;">{datetime.now().strftime("%Y-%m-%d %H:%M")}</div>', unsafe_allow_html=True)


def render_metrics(result: dict):
    chg = result.get("change_pct", 0)
    chg_cls = "positive" if chg >= 0 else "negative"
    amt = float(result.get("amount", 0) or 0)
    cols = st.columns(4)
    items = [
        ("最新价", f"¥{result.get('price', 0):.2f}", ""),
        ("涨跌幅", f"{chg:+.2f}%", chg_cls),
        ("今开/最高/最低", f"{result.get('open','-')}/{result.get('high','-')}/{result.get('low','-')}", ""),
        ("成交额", f"{amt/1e8:.1f}亿" if amt > 0 else "-", ""),
    ]
    for i, (label, value, cls) in enumerate(items):
        with cols[i]:
            st.markdown(f'<div class="metric-card"><div class="metric-value {cls}">{value}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)


def render_radar(scores: dict):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=list(scores.values()), theta=list(scores.keys()),
        fill="toself", fillcolor="rgba(56,189,248,0.3)",
        line=dict(color="#38BDF8", width=2),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor="#E2E8F0"),
                   angularaxis=dict(gridcolor="#E2E8F0")),
        showlegend=False, margin=dict(l=20, r=20, t=10, b=10), height=300,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_score_bars(scores: dict, total: float, max_scores: dict = None):
    if max_scores is None:
        max_scores = {"技术面": 35, "资金面": 25, "财务面": 20, "情绪面": 20}
    for dim, s in scores.items():
        mx = max_scores.get(dim, 20)
        pct = min(s / mx * 100, 100) if mx > 0 else 0
        color = "#10B981" if pct >= 60 else "#F59E0B" if pct >= 40 else "#EF4444"
        st.markdown(f"""
        <div style="display:flex;align-items:center;margin:0.4rem 0;">
            <span style="width:90px;font-size:0.85rem;color:#475569;font-weight:600;">{dim}</span>
            <div style="flex:1;background:#E2E8F0;border-radius:6px;height:18px;margin:0 12px;">
                <div style="width:{pct}%;background:{color};border-radius:6px;height:18px;"></div>
            </div>
            <span style="width:50px;font-size:0.85rem;font-weight:700;color:{color};">{s}/{mx}</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="text-align:center;margin-top:0.8rem;">
        <span style="font-size:2rem;font-weight:800;color:#0F172A;">{total}</span>
        <span style="font-size:0.9rem;color:#64748B;"> / 100 综合评分</span>
    </div>
    """, unsafe_allow_html=True)


def render_kline(df, entry_zone=None, exit_zone=None):
    if df is None or len(df) == 0:
        st.info("K线数据暂不可用")
        return
    df = df.tail(120).copy()

    # 计算均线
    if len(df) >= 5:
        df["MA5"] = df["close"].rolling(5).mean()
    if len(df) >= 10:
        df["MA10"] = df["close"].rolling(10).mean()
    if len(df) >= 20:
        df["MA20"] = df["close"].rolling(20).mean()
    if len(df) >= 60:
        df["MA60"] = df["close"].rolling(60).mean()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.02)

    # K线
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="K线", increasing_line_color="#EF4444", decreasing_line_color="#10B981",
        showlegend=False,
    ), row=1, col=1)

    # 均线
    ma_colors = {"MA5": "#F59E0B", "MA10": "#3B82F6", "MA20": "#8B5CF6", "MA60": "#EC4899"}
    for ma_name, color in ma_colors.items():
        if ma_name in df.columns:
            show = df[ma_name].notna().any()
            fig.add_trace(go.Scatter(
                x=df.index, y=df[ma_name], mode="lines", name=ma_name,
                line=dict(color=color, width=1.2), showlegend=True,
            ), row=1, col=1)

    # 支撑/阻力水平线
    if entry_zone or exit_zone:
        # 支撑位
        support_keys = ["止损位", "稳健买点", "激进买点"]
        for k in support_keys:
            if entry_zone and k in entry_zone:
                v = entry_zone[k]
                fig.add_hline(y=v, line_dash="dash", line_color="#10B981", opacity=0.5,
                             annotation_text=f"{k}: {v:.2f}", annotation_position="bottom left",
                             row=1, col=1)

        # 阻力位
        resist_keys = ["第一目标", "第二目标", "强阻力"]
        for k in resist_keys:
            if exit_zone and k in exit_zone:
                v = exit_zone[k]
                fig.add_hline(y=v, line_dash="dot", line_color="#EF4444", opacity=0.5,
                             annotation_text=f"{k}: {v:.2f}", annotation_position="top left",
                             row=1, col=1)

    # 成交量柱状图（红涨绿跌）
    colors = ["#EF4444" if (df["close"].iloc[i] >= df["open"].iloc[i]) else "#10B981"
              for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df.index, y=df["volume"], name="成交量",
        marker_color=colors, opacity=0.35, showlegend=False,
    ), row=2, col=1)

    # 5日均量线
    if len(df) >= 5:
        df["VOL_MA5"] = df["volume"].rolling(5).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=df["VOL_MA5"], mode="lines", name="VOL_MA5",
            line=dict(color="#94A3B8", width=1, dash="dot"), showlegend=False,
        ), row=2, col=1)

    fig.update_layout(
        height=500, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=5, b=5),
        xaxis_rangeslider_visible=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#E2E8F0", title="价格"),
        yaxis2=dict(gridcolor="#E2E8F0", title="量"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════
# ══ 量化分析报告渲染组件 ══
# ═══════════════════════════════════════════

def render_quant_report(result: dict):
    """渲染 v2 量化引擎的完整分析报告"""
    dims = result.get("dimensions", [])
    risk = result.get("risk_metrics", {})
    entry = result.get("entry_zone", {})
    exit_z = result.get("exit_zone", {})
    tech = result.get("tech_snapshot", {})
    factor_dist = result.get("factor_distribution", {})
    triggers = result.get("triggers", {})
    rel = result.get("relative_strength", {})
    fin = result.get("financial_summary", {})
    news_sent = result.get("news_sentiment", {})
    signal = result.get("signal_summary", "")

    # ── 评级大卡 ──
    total = result["total"]
    rating = result.get("rating", "")
    confidence = result.get("confidence", "")
    if total >= 75:
        badge_color = "#059669"
    elif total >= 60:
        badge_color = "#0284C7"
    elif total >= 45:
        badge_color = "#D97706"
    else:
        badge_color = "#DC2626"

    bullish = factor_dist.get("bullish", 0)
    bearish = factor_dist.get("bearish", 0)
    neutral = factor_dist.get("neutral", 0)

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0F172A,#1E293B);border-radius:16px;padding:1.5rem;margin:1rem 0;">
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <div>
                <div style="font-size:3.2rem;font-weight:900;color:{badge_color};">{total:.0f}<span style="font-size:1rem;color:#94A3B8;">/100</span></div>
                <div style="font-size:1.3rem;font-weight:700;color:{badge_color};margin-top:0.2rem;">{rating}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.8rem;color:#94A3B8;">28因子综合量化评分</div>
                <div style="font-size:0.8rem;color:#64748B;margin-top:0.3rem;">🟢 {bullish}看涨 | 🔴 {bearish}看跌 | ⚪ {neutral}中性</div>
                <div style="font-size:0.8rem;color:#64748B;margin-top:0.2rem;">净多头: <b>{bullish - bearish:+d}</b> | 置信度: <b>{confidence}</b></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 因子分布概览 ──
    st.markdown('<p class="section-title">📊 因子信号分布</p>', unsafe_allow_html=True)
    _render_factor_distribution(factor_dist)

    # ── 信号总览 ──
    st.markdown(f"""
    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:1rem;margin:0.8rem 0;">
        <span style="font-size:0.9rem;color:#475569;">{signal}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── 投资建议 + 具体触发条件 ──
    advice = result.get("advice", "")
    pos_advice = result.get("position_advice", "")
    if advice:
        st.markdown(f"""
        <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:12px;padding:1rem;margin:0.8rem 0;">
            <div style="font-size:0.95rem;font-weight:600;color:#0F172A;">💡 投资建议</div>
            <div style="font-size:0.9rem;color:#334155;margin-top:0.4rem;">{advice}</div>
            <div style="font-size:0.85rem;color:#64748B;margin-top:0.5rem;">📊 {pos_advice}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 具体操作条件 ──
    if triggers:
        with st.expander("🎯 量化操作条件（具体触发价位）", expanded=True):
            t1, t2 = st.columns(2)
            with t1:
                st.markdown("**🟢 买入触发**")
                st.markdown(f"<span style='font-size:0.85rem;color:#334155;'>{triggers.get('buy_condition','')}</span>", unsafe_allow_html=True)
                st.markdown("**🔴 止损条件**")
                st.markdown(f"<span style='font-size:0.85rem;color:#334155;'>{triggers.get('stop_condition','')}</span>", unsafe_allow_html=True)
                st.markdown("**🚫 剔除条件**")
                st.markdown(f"<span style='font-size:0.85rem;color:#334155;'>{triggers.get('invalidate_condition','')}</span>", unsafe_allow_html=True)
            with t2:
                st.markdown("**🎯 止盈目标**")
                st.markdown(f"<span style='font-size:0.85rem;color:#334155;'>{triggers.get('target1','')}</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='font-size:0.85rem;color:#334155;'>{triggers.get('target2','')}</span>", unsafe_allow_html=True)

    # ── 五维度分解 ──
    st.markdown('<p class="section-title">📊 五维度因子深度分析</p>', unsafe_allow_html=True)
    if dims:
        tabs = st.tabs([d["name"] for d in dims])
        for i, dim in enumerate(dims):
            with tabs[i]:
                _render_dimension_full(dim)

    # ── 风险 + 相对强度 + 财务 ──
    col_left, col_right = st.columns([1, 1])

    with col_left:
        _render_risk_panel(risk)
        if rel and rel.get("available"):
            _render_relative_strength(rel)

    with col_right:
        _render_zone_panel(entry, exit_z, result.get("price", 0))
        _render_financial_summary(fin)
        _render_news_sentiment_panel(news_sent)

    # ── 技术指标快照 ──
    if tech:
        with st.expander("📡 技术指标快照（实时）", expanded=False):
            tcols = st.columns(min(len(tech), 5))
            for j, (k, v) in enumerate(tech.items()):
                with tcols[j % 5]:
                    val_str = f"{v:.2f}" if isinstance(v, (int, float)) else str(v)[:16]
                    st.metric(label=k, value=val_str)

    # ── 28因子名录附录 ──
    with st.expander("📚 28因子完整名录与说明", expanded=False):
        _render_factor_catalog()


def _render_factor_distribution(fd: dict):
    """渲染因子信号分布图"""
    if not fd:
        return

    # 顶部总结条
    b, be, n = fd.get("bullish", 0), fd.get("bearish", 0), fd.get("neutral", 0)
    total_f = fd.get("total", 28)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🟢 看涨因子", f"{b}个", delta=f"{b/total_f*100:.0f}%" if total_f else "")
    with c2:
        st.metric("🔴 看跌因子", f"{be}个", delta=f"{be/total_f*100:.0f}%" if total_f else "")
    with c3:
        st.metric("⚪ 中性因子", f"{n}个", delta=f"{n/total_f*100:.0f}%" if total_f else "")

    # 分布进度条
    st.markdown(f"""
    <div style="display:flex;height:24px;border-radius:6px;overflow:hidden;margin:0.5rem 0;">
        <div style="width:{b/total_f*100:.0f}%;background:linear-gradient(90deg,#10B981,#059669);"></div>
        <div style="width:{n/total_f*100:.0f}%;background:linear-gradient(90deg,#CBD5E1,#94A3B8);"></div>
        <div style="width:{be/total_f*100:.0f}%;background:linear-gradient(90deg,#EF4444,#DC2626);"></div>
    </div>
    """, unsafe_allow_html=True)

    # 按维度明细
    by_dim = fd.get("by_dimension", [])
    if by_dim:
        dim_items = []
        for d in by_dim:
            dim_items.append({
                "维度": d["name"],
                "权重": f"{d['weight_pct']:.0f}%",
                "平均分": d["avg_score"],
                "🟢": d["bullish"],
                "⚪": d["neutral"],
                "🔴": d["bearish"],
            })
        st.dataframe(dim_items, hide_index=True, use_container_width=True)


def _render_dimension_full(dim: dict):
    """渲染单个维度全部因子详情"""
    score = dim["total_score"]
    color = "#059669" if score >= 65 else "#D97706" if score >= 45 else "#DC2626"

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.6rem;">
        <span style="font-size:2rem;font-weight:900;color:{color};">{score:.0f}</span>
        <span style="font-size:0.9rem;color:#475569;">/100 — {dim.get('summary', '')}</span>
    </div>
    """, unsafe_allow_html=True)

    # 优势/劣势
    strengths = dim.get("strength", [])
    weaknesses = dim.get("weakness", [])
    if strengths or weaknesses:
        sc1, sc2 = st.columns(2)
        with sc1:
            if strengths:
                st.markdown('<span style="color:#059669;font-weight:600;">✅ 优势因子</span>', unsafe_allow_html=True)
                for s in strengths:
                    st.markdown(f'<span style="font-size:0.8rem;color:#475569;">• {s}</span>', unsafe_allow_html=True)
        with sc2:
            if weaknesses:
                st.markdown('<span style="color:#DC2626;font-weight:600;">⚠️ 劣势因子</span>', unsafe_allow_html=True)
                for w in weaknesses:
                    st.markdown(f'<span style="font-size:0.8rem;color:#475569;">• {w}</span>', unsafe_allow_html=True)

    # 全量因子表（含详情）
    factors = dim.get("factors", [])
    if factors:
        st.markdown("---")
        st.markdown("**因子明细（含具体数值与解读）**")
        items = []
        for f in factors:
            sig_icon = "🟢" if f["signal"] == "bullish" else "🔴" if f["signal"] == "bearish" else "⚪"
            val_str = f["value"]
            if isinstance(val_str, float):
                val_str = f"{val_str:.2f}"
            items.append({
                "": sig_icon,
                "因子": f["name"],
                "得分": int(f["score"]),
                "数值": str(val_str)[:12],
                "解读": f.get("detail", "")[:80],
            })
        st.dataframe(
            items,
            column_config={
                "": st.column_config.Column(width="small"),
                "因子": st.column_config.Column(width="medium"),
                "得分": st.column_config.NumberColumn(width="small"),
                "数值": st.column_config.Column(width="small"),
                "解读": st.column_config.Column(width="large"),
            },
            hide_index=True, use_container_width=True, height=min(35 * len(items) + 38, 400)
        )


def _render_relative_strength(rel: dict):
    """渲染相对强度 vs 基准"""
    st.markdown('<p class="section-title">📈 相对强度</p>', unsafe_allow_html=True)
    s1m = rel.get("stock_1m", None)
    s3m = rel.get("stock_3m", None)

    cols = st.columns(2)
    with cols[0]:
        if s1m is not None:
            color = "#059669" if s1m > 0 else "#DC2626"
            st.markdown(f'<span style="font-size:0.85rem;">近1月: <b style="color:{color};">{s1m:+.1f}%</b></span>', unsafe_allow_html=True)
        vs1 = rel.get("vs_index_1m", None)
        if vs1 is not None:
            color = "#059669" if vs1 > 0 else "#DC2626"
            st.markdown(f'<span style="font-size:0.85rem;">vs指数: <b style="color:{color};">{vs1:+.1f}%</b></span>', unsafe_allow_html=True)
    with cols[1]:
        if s3m is not None:
            color = "#059669" if s3m > 0 else "#DC2626"
            st.markdown(f'<span style="font-size:0.85rem;">近3月: <b style="color:{color};">{s3m:+.1f}%</b></span>', unsafe_allow_html=True)
        vs3 = rel.get("vs_index_3m", None)
        if vs3 is not None:
            color = "#059669" if vs3 > 0 else "#DC2626"
            st.markdown(f'<span style="font-size:0.85rem;">vs指数: <b style="color:{color};">{vs3:+.1f}%</b></span>', unsafe_allow_html=True)


def _render_financial_summary(fin: dict):
    """渲染财务摘要卡片"""
    st.markdown('<p class="section-title">📋 财务摘要</p>', unsafe_allow_html=True)
    if not fin or all(v == "N/A" or v is None for v in fin.values()):
        st.warning("⚠️ 基本面数据暂不可用（数据源 akshare 偶发性连接中断）\n\n当前分析仅基于技术面和量化因子，不含财务质量验证。建议待数据恢复后重新分析以获取完整评估。")
        return

    items = []
    labels = {
        "ROE(%)": "ROE",
        "毛利率(%)": "毛利率",
        "净利润(亿)": "净利润",
        "资产负债率(%)": "负债率",
        "PE": "PE",
        "PB": "PB",
    }
    for key, label in labels.items():
        val = fin.get(key, "N/A")
        if val != "N/A" and val is not None:
            items.append((label, f"{float(val):.1f}" if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.','').replace('-','').isdigit()) else str(val)[:10]))

    if items:
        cols = st.columns(min(len(items), 3))
        for i, (label, val) in enumerate(items):
            with cols[i % 3]:
                st.metric(label=label, value=val)


def _render_news_sentiment_panel(ns: dict):
    """渲染新闻情感面板"""
    st.markdown('<p class="section-title">📰 新闻情感</p>', unsafe_allow_html=True)
    if not ns or ns.get("label") == "无相关新闻":
        st.info("暂无与该股直接相关的新闻")
        return

    score = ns.get("score", 50)
    label = ns.get("label", "中性")
    relevant = ns.get("relevant_count", 0)
    total = ns.get("total_count", 0)
    color = "#059669" if score > 55 else "#DC2626" if score < 45 else "#64748B"

    st.markdown(f'<span style="font-size:0.9rem;">个股相关新闻: <b>{relevant}</b> 条 (共扫描 {total} 条)</span>', unsafe_allow_html=True)
    st.markdown(f'<span style="font-size:0.9rem;">综合情感: <b style="color:{color};">{label}</b></span>', unsafe_allow_html=True)
    st.markdown(f'<span style="font-size:0.8rem;color:#94A3B8;">正面词{ns.get("positive_count",0)}个 | 负面词{ns.get("negative_count",0)}个</span>', unsafe_allow_html=True)

    # 显示前几条新闻的情感标记
    items = ns.get("items", [])
    if items:
        st.markdown("---")
        for item in items[:5]:
            sent = item.get("sentiment", "neutral")
            icon = "🟢" if sent == "positive" else "🔴" if sent == "negative" else "⚪"
            rel_mark = "★" if item.get("relevant") else ""
            st.markdown(f'<span style="font-size:0.8rem;">{icon}{rel_mark} {item.get("title","")}</span>', unsafe_allow_html=True)


def _render_factor_catalog():
    """渲染28因子完整名录"""
    catalog = [
        ("📈 趋势研判 (8因子, 权重45%)", [
            ("多周期均线排列", "5/10/20/60/120日多时间框架均线排列方向"),
            ("MACD趋势动量", "DIF/DEA交叉 + 柱状线变化，捕捉趋势转折"),
            ("ADX趋势强度", "平均趋向指数，>25趋势市 >40强趋势，+DI/-DI判方向"),
            ("布林带波动区间", "价格在布林带(20,2σ)中位置，上轨超买/下轨超卖"),
            ("一目均衡云层", "价格相对云层的位置百分比，0%以下=弱势/100%以上=强势"),
            ("均线交叉信号", "5/10/20日最近金叉/死叉信号"),
            ("乖离率偏离度", "收盘价相对MA20偏离%，极端值预测均值回归"),
            ("Donchian通道突破", "海龟交易法20日通道突破信号"),
        ]),
        ("⚡ 动量信号 (6因子, 权重25%)", [
            ("RSI动量", "14日RSI + 顶/底背离检测"),
            ("随机指标KD", "%K/%D 超买超卖(80/20) + 交叉信号"),
            ("CCI通道指数", "商品通道指数，±100超买超卖 ±200极端"),
            ("威廉%R", "威廉指标，-20超买 / -80超卖"),
            ("ROC变化率", "10日价格变化率，测量近期涨跌幅度"),
            ("多周期动量一致", "5/10/20/60日四周期动量方向一致性"),
        ]),
        ("📊 波动风险 (5因子, 权重15%)", [
            ("ATR波动率", "14日ATR历史百分位，高百分位=高波动风险"),
            ("历史波动率", "年化20日vs60日波动率对比，比值>1.5=不稳定"),
            ("布林带宽收缩", "布林带宽历史百分位，极低=即将突破(Squeeze)"),
            ("Beta系数", "相对大盘敏感度，>1.5高波动 <0.8防御性"),
            ("最大回撤风险", "当前距60日高点回撤%，>20%=深跌风险"),
        ]),
        ("💰 资金流向 (5因子, 权重10%)", [
            ("OBV能量潮", "能量潮与价格同向/背离，验证趋势可靠性"),
            ("MFI资金流", "资金流量指数(14)，结合价格+成交量超买超卖"),
            ("Chaikin资金流", "Chaikin资金流(20)，>0.05机构流入 <-0.05流出"),
            ("成交量趋势", "当日量vs5/20日均量，判断放量/缩量"),
            ("VPT量价趋势", "量价趋势累积值，方向判断资金动能"),
        ]),
        ("🔍 形态识别 (4因子, 权重5%)", [
            ("K线形态信号", "锤子线/启明星/大阳线/吊颈线等经典形态检测"),
            ("支撑阻力位", "60日高低点区间位置，接近支撑/阻力信号"),
            ("斐波那契回撤", "50日波段回调位(23.6%/38.2%/50%/61.8%)"),
            ("跳空缺口", "近5日缺口检测，突破性缺口=强信号"),
        ]),
    ]

    for cat_name, factors in catalog:
        st.markdown(f"**{cat_name}**")
        for name, desc in factors:
            st.markdown(f"• **{name}** — {desc}")
        st.markdown("")



def _render_risk_panel(risk: dict):
    """渲染风险量化面板"""
    st.markdown('<p class="section-title">⚠️ 风险量化</p>', unsafe_allow_html=True)
    if not risk or "error" in risk:
        st.info("风险数据暂不可用")
        return

    # 核心风险指标
    cols = st.columns(3)
    metrics = [
        ("年化收益", f"{risk.get('年化收益率', 0):+.1f}%"),
        ("夏普比率", f"{risk.get('夏普比率', 0):.2f}"),
        ("最大回撤", f"{risk.get('最大回撤%', 0):.1f}%"),
        ("VaR 95%", f"{risk.get('VaR_95', 0):.2f}%"),
        ("年化波动", f"{risk.get('年化波动率', 0):.1f}%"),
        ("胜率", f"{risk.get('胜率%', 0):.1f}%"),
        ("盈亏比", f"{risk.get('盈亏比', 0):.2f}"),
        ("凯利仓位", f"{risk.get('凯利仓位%', 0):.0f}%"),
        ("半凯利", f"{risk.get('半凯利仓位%', 0):.0f}%"),
    ]
    for i, (label, val) in enumerate(metrics):
        with cols[i % 3]:
            st.metric(label=label, value=val)


def _render_zone_panel(entry: dict, exit_z: dict, price: float):
    """渲染关键价位面板"""
    st.markdown('<p class="section-title">🎯 关键价位</p>', unsafe_allow_html=True)
    if not entry and not exit_z:
        st.info("价位数据暂不可用")
        return

    st.markdown(f'<span style="color:#64748B;font-size:0.85rem;">当前价格: <b style="color:#0F172A;">¥{price:.2f}</b></span>', unsafe_allow_html=True)
    st.divider()

    if entry:
        st.markdown("**🟢 入场参考**")
        for k, v in entry.items():
            color = "#059669" if isinstance(v, (int, float)) and v < price else "#D97706"
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;margin:0.2rem 0;">
                <span style="color:#475569;font-size:0.85rem;">{k}</span>
                <span style="color:{color};font-weight:600;">¥{v:.2f}</span>
            </div>
            """, unsafe_allow_html=True)

    if exit_z:
        st.markdown("**🔴 出场参考**")
        for k, v in exit_z.items():
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;margin:0.2rem 0;">
                <span style="color:#475569;font-size:0.85rem;">{k}</span>
                <span style="color:#DC2626;font-weight:600;">¥{v:.2f}</span>
            </div>
            """, unsafe_allow_html=True)


def render_signal_panel():
    st.markdown('<p class="section-title">🔥 市场热点</p>', unsafe_allow_html=True)
    sig = fetch_signal()
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**行业资金流向**")
        flows = sig.get("sector_flow", [])
        if isinstance(flows, list) and flows:
            for f in flows[:10]:
                if isinstance(f, dict):
                    n = f.get("name", "")
                    a = f.get("amount", 0) or 0
                    st.markdown(f"• {'🟢' if a >= 0 else '🔴'} {n}: {a/1e8:+.1f}亿")
                else:
                    st.markdown(f"• {f}")
        else:
            st.info("暂无数据")

    with col2:
        st.markdown("**热门概念**")
        hots = sig.get("hot_concepts", [])
        if isinstance(hots, list) and hots:
            for h in hots[:10]:
                if isinstance(h, dict):
                    st.markdown(f"• {h.get('name', str(h))}")
                else:
                    st.markdown(f"• {h}")
        else:
            st.info("暂无数据")


def render_market_scan():
    """全市场扫描标签页 v2 — 市场仪表盘 + 增强个股 + 风险提示"""
    st.markdown('<p class="section-title">🔭 全市场动态扫描</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#64748B;font-size:0.9rem;">全市场5499只A股实时扫描 · 多维度聚合统计 · 智能风险标注</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("**深度扫描**: 全市场 · 90-120秒 | **快速扫描**: 200只 · 5-10秒")
    with col2:
        do_scan = st.button("🔄 全市场扫描", type="primary", use_container_width=True)
    with col3:
        quick = st.button("⚡ 快速扫描", use_container_width=True)

    if do_scan or quick:
        _run_full_scan_v2(fast=quick)


def _run_full_scan_v2(fast: bool = False):
    """执行全市场扫描 v2 — 输出增强数据"""
    import subprocess, tempfile, sys

    with st.spinner("正在扫描全市场..." if not fast else "正在快速扫描热点板块..."):
        with st.status("扫描进度", expanded=True) as status:
            st.write("📡 腾讯行情API · 全量采集 · 增量计算")

            if fast:
                limit_code = "codes = df[\"code\"].tolist()[:200]"
                timeout = 30
            else:
                limit_code = "codes = df[\"code\"].tolist()"
                timeout = 150

            script = f'''
import sys, os, time, json
sys.path.insert(0, "{PROJECT_DIR}/data")
from quotes import TencentQuotes

q = TencentQuotes()
t0 = time.time()

import akshare as ak
df = ak.stock_info_a_code_name()
codes_df = df
{limit_code}

# 批量获取行情 (80只/批)
all_quotes = []
for i in range(0, len(codes), 80):
    batch = codes[i:i+80]
    try:
        all_quotes.extend(q.get_quotes(batch))
    except:
        pass

# 处理数据：量比/换手/连板/风险标记
valid = []
limit_up = 0
limit_down = 0
up_count = 0
down_count = 0
new_stock_count = 0
st_count = 0

for qq in all_quotes:
    try:
        chg = float(qq.get("change_pct", 0) or 0)
        vol = int(qq.get("volume", 0) or 0)
        if vol <= 0:
            continue
        price = float(qq.get("price", 0) or 0)
        code = qq.get("code", "")
        name = qq.get("name", "")
        turnover = float(qq.get("turnover", 0) or 0)
        amount = float(qq.get("amount", 0) or 0)

        # 风险标记
        risk_tags = []
        if "ST" in name or "*ST" in name:
            risk_tags.append("ST")
            st_count += 1
        if "N" in name or name.startswith("N"):
            risk_tags.append("新股")
            new_stock_count += 1
        if code.startswith("8") or code.startswith("4"):
            risk_tags.append("北交所")
        if turnover < 0.1:
            risk_tags.append("低流动性")

        # 涨跌停判断
        if chg >= 9.5:
            limit_up += 1
        elif chg <= -9.5:
            limit_down += 1

        if chg > 0:
            up_count += 1
        elif chg < 0:
            down_count += 1

        entry = {{
            "code": code, "name": name, "price": price, "change_pct": chg,
            "volume": vol, "amount": amount, "turnover": round(turnover, 2),
            "risk_tags": risk_tags,
        }}
        valid.append(entry)
    except:
        pass

valid.sort(key=lambda x: x["change_pct"], reverse=True)
elapsed = time.time() - t0

# 按涨幅分组统计
bins = [(-99, -5, "<-5%"), (-5, -2, "-5%~-2%"), (-2, 0, "-2%~0%"),
        (0, 2, "0%~2%"), (2, 5, "2%~5%"), (5, 9.5, "5%~10%"), (9.5, 999, "涨停")]
dist = []
for lo, hi, label in bins:
    cnt = sum(1 for v in valid if lo <= v["change_pct"] < hi)
    dist.append({{"区间": label, "数量": cnt}})

summary = {{
    "analyzed": len(valid),
    "limit_up": limit_up,
    "limit_down": limit_down,
    "up_count": up_count,
    "down_count": down_count,
    "flat_count": len(valid) - up_count - down_count,
    "new_stock_count": new_stock_count,
    "st_count": st_count,
    "elapsed": round(elapsed, 1),
    "distribution": dist,
}}

print("===SUMMARY===")
print(json.dumps(summary, ensure_ascii=False))
print("===TOP===")
for v in valid[:50]:
    if v["change_pct"] > 0.5:
        print(json.dumps(v, ensure_ascii=False))
print("===BOTTOM===")
for v in valid[-30:]:
    if v["change_pct"] < -2:
        print(json.dumps(v, ensure_ascii=False))
print("===DONE===")
'''
            tmpf = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8')
            tmpf.write(script)
            tmpf.close()

            try:
                result = subprocess.run(
                    [sys.executable, tmpf.name],
                    capture_output=True, text=True, timeout=timeout
                )
                output = result.stdout
                status.update(label="✅ 扫描完成", state="complete")
            except subprocess.TimeoutExpired:
                status.update(label=f"⚠️ 扫描超时({timeout}s)", state="error")
                os.unlink(tmpf.name)
                return
            except Exception as e:
                status.update(label=f"⚠️ 扫描异常: {e}", state="error")
                os.unlink(tmpf.name)
                return
            finally:
                try:
                    os.unlink(tmpf.name)
                except:
                    pass

    _display_scan_v2(output)


def _display_scan_v2(output: str):
    """展示 v2 扫描结果：仪表盘 + 筛选 + 增强列表"""
    import re, json

    summary_match = re.search(r'===SUMMARY===\n(.*?)(?=\n===|\Z)', output, re.DOTALL)
    top_match = re.search(r'===TOP===\n(.*?)(?=\n===|\Z)', output, re.DOTALL)
    bottom_match = re.search(r'===BOTTOM===\n(.*?)(?=\n===|\Z)', output, re.DOTALL)

    summary = {}
    if summary_match:
        try:
            summary = json.loads(summary_match.group(1).strip())
        except:
            pass

    # ── 风险提示 ──
    n_new = summary.get("new_stock_count", 0)
    n_st = summary.get("st_count", 0)
    if n_new + n_st > 0:
        warnings = []
        if n_new > 0:
            warnings.append(f"含 {n_new} 只新股/次新股（无涨跌幅限制，波动巨大）")
        if n_st > 0:
            warnings.append(f"含 {n_st} 只ST/*ST股票（退市风险）")
        st.warning("⚠️ " + " | ".join(warnings) + " | 请谨慎甄别，切勿盲目跟风")

    # ── 市场情绪仪表盘 ──
    if summary:
        st.markdown('<p class="section-title">📊 市场情绪仪表盘</p>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.metric("扫描标的", f"{summary.get('analyzed', 0)}只")
        with c2:
            st.metric("涨停家数", f"{summary.get('limit_up', 0)}家")
        with c3:
            st.metric("跌停家数", f"{summary.get('limit_down', 0)}家")
        with c4:
            up = summary.get("up_count", 0)
            dn = summary.get("down_count", 0)
            ratio = up / max(dn, 1)
            st.metric("涨跌比", f"{up}:{dn}", delta=f"{ratio:.1f}:1" if ratio > 1 else f"1:{1/ratio:.1f}")
        with c5:
            st.metric("上涨家数", f"{up}只")
        with c6:
            st.metric("下跌家数", f"{dn}只")

        # 分布图
        dist = summary.get("distribution", [])
        if dist:
            st.markdown("**涨跌幅分布**")
            dist_bars = ""
            max_cnt = max(d["数量"] for d in dist) if dist else 1
            for d in dist:
                pct = d["数量"] / max(max_cnt, 1) * 100
                color = "#EF4444" if "涨停" in d["区间"] or d["区间"].startswith(">") or d["区间"].startswith("5%") else \
                        "#F59E0B" if d["区间"].startswith("2%") or d["区间"].startswith("0%") else \
                        "#10B981"
                dist_bars += f'''
                <div style="display:flex;align-items:center;margin:2px 0;font-size:0.8rem;">
                    <span style="width:70px;text-align:right;margin-right:8px;">{d["区间"]}</span>
                    <div style="flex:1;background:#E2E8F0;border-radius:4px;height:16px;">
                        <div style="width:{pct}%;background:{color};border-radius:4px;height:16px;"></div>
                    </div>
                    <span style="width:50px;margin-left:8px;font-weight:600;">{d["数量"]}只</span>
                </div>'''
            st.markdown(dist_bars, unsafe_allow_html=True)

    # ── 强势个股 ──
    if top_match:
        try:
            signals = []
            for line in top_match.group(1).strip().split('\n'):
                line = line.strip()
                if line:
                    try:
                        signals.append(json.loads(line))
                    except:
                        pass
            if signals:
                st.markdown('<p class="section-title">🟢 强势个股</p>', unsafe_allow_html=True)
                _render_stock_table(signals[:30], "up")
        except:
            pass

    # ── 弱势个股 ──
    if bottom_match:
        try:
            signals = []
            for line in bottom_match.group(1).strip().split('\n'):
                line = line.strip()
                if line:
                    try:
                        signals.append(json.loads(line))
                    except:
                        pass
            if signals:
                st.markdown('<p class="section-title">🔴 弱势个股</p>', unsafe_allow_html=True)
                _render_stock_table(signals[:15], "down")
        except:
            pass

    if not summary_match and not top_match and not bottom_match:
        lines = [l for l in output.split('\n') if l.strip() and 'Error' not in l and 'Traceback' not in l]
        if lines:
            with st.expander("📄 扫描详情", expanded=False):
                st.code('\n'.join(lines[:30]), language="")


def _render_stock_table(stocks: list, direction: str):
    """渲染增强个股表格"""
    if not stocks:
        return

    rows = []
    for s in stocks:
        price = s.get("price", 0)
        chg = s.get("change_pct", 0)
        turnover = s.get("turnover", 0)
        volume = s.get("volume", 0)
        amount = s.get("amount", 0)
        name = s.get("name", "")
        code = s.get("code", "")
        risk_tags = s.get("risk_tags", [])

        # 量比估计：amount/price ≈ volume*price/price ≈ rawVolume, simplified
        # 用换手率作为流动性标记
        vol_label = f"换{turnover:.1f}%" if turnover > 0 else "-"

        # 风险标记
        risk_str = " ".join(f"[{t}]" for t in risk_tags) if risk_tags else ""

        # 涨幅色
        chg_color = "#EF4444" if chg > 0 else "#10B981" if chg < 0 else "#64748B"

        rows.append({
            "代码": code,
            "名称": name[:6],
            "现价": f"¥{price:.2f}",
            "涨跌幅": f"{chg:+.1f}%",
            "换手率": vol_label,
            "成交额": f"{amount/1e8:.1f}亿" if amount > 1e7 else "-",
            "风险": risk_str,
        })

    if rows:
        st.dataframe(
            rows,
            column_config={
                "代码": st.column_config.Column(width="small"),
                "名称": st.column_config.Column(width="small"),
                "现价": st.column_config.Column(width="small"),
                "涨跌幅": st.column_config.Column(width="small"),
                "换手率": st.column_config.Column(width="small"),
                "成交额": st.column_config.Column(width="small"),
                "风险": st.column_config.Column(width="medium"),
            },
            hide_index=True, use_container_width=True,
            height=min(35 * len(rows) + 38, 600)
        )


def _resolve_symbol(symbol: str) -> str:
    """名称→代码映射。输入名称则查表转代码，输入代码直接返回"""
    if not symbol or not symbol.strip():
        return symbol
    s = symbol.strip()
    # 如果已经是纯数字代码，直接返回
    if s.isdigit() and len(s) == 6:
        return s
    # 从scanner的SECTOR_STOCKS查名称
    name_map = _get_stock_name_map()
    # 精确匹配
    if s in name_map:
        return name_map[s]
    # 模糊匹配
    for name, code in name_map.items():
        if s in name or name in s:
            return code
    return s  # 查不到就原样返回，让后续报错


@st.cache_data(ttl=86400)
def _get_stock_name_map() -> dict:
    """全市场A股 名称→代码 映射（5500+只）"""
    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        name_map = {}
        for _, row in df.iterrows():
            code = str(row["code"]).strip()
            name = str(row["name"]).strip()
            if code and name:
                name_map[name] = code
        return name_map
    except Exception:
        pass
    # 兜底
    return {
        "贵州茅台": "600519", "五粮液": "000858", "宁德时代": "300750",
        "招商银行": "600036", "比亚迪": "002594", "海康威视": "002415",
        "科大讯飞": "002230", "恒瑞医药": "600276", "中国平安": "601318",
        "美的集团": "000333", "格力电器": "000651", "隆基绿能": "601012",
        "工商银行": "601398", "农业银行": "601288", "建设银行": "601939",
        "万科A": "000002", "长江电力": "600900", "中兴通讯": "000063",
        "东方财富": "300059", "同花顺": "300033", "中信证券": "600030",
    }

# ═══════════════════════════════════════════
# 主页面
# ═══════════════════════════════════════════

def main():
    render_header()
    st.divider()

    tab1, tab2 = st.tabs(["📊 单股分析", "🔭 全市场扫描"])

    with tab2:
        render_market_scan()

    with tab1:
        # 输入区
        c1, c2 = st.columns([4, 1])
        with c1:
            symbol = st.text_input("股票代码或名称", placeholder="600036 或 招商银行 / 000858 或 五粮液 ...", label_visibility="collapsed").strip()
        with c2:
            go = st.button("🔍 开始分析", type="primary", use_container_width=True)

        # 名称→代码映射
        symbol = _resolve_symbol(symbol)

        if not go and not symbol:
            st.info("👆 输入股票代码（如 600036）或名称（如 招商银行），然后点击「开始分析」")
            try:
                render_signal_panel()
            except:
                pass
            return

        if go and not symbol:
            st.error("请输入股票代码")
            return
        if not go:
            return

        # 分析
        with st.spinner(f"正在分析 {symbol} ..."):
            result = analyze(symbol)

        if "error" in result:
            st.error(result["error"])
            return

        # 结果展示
        name = result.get("name", symbol)
        st.markdown(f'<p class="section-title">📈 {name}（{symbol}）分析报告</p>', unsafe_allow_html=True)

        render_metrics(result)

        is_quant_v2 = result.get("engine_type") == "quant_v2"

        if is_quant_v2:
            # v2 量化引擎：完整的深度分析报告
            render_quant_report(result)
        else:
            # 旧版/降级模式：简化四维评分
            col_l, col_r = st.columns([1, 1])
            with col_l:
                st.markdown("### 四维量化评分")
                render_score_bars(result["scores"], result["total"], result.get("max_scores"))
            with col_r:
                render_radar(result["scores"])

            engine_tag = '<span style="color:#64748B;font-size:0.8rem;margin-left:8px;">⚙️ 量化引擎评分</span>' if result.get("engine") else ""
            st.markdown(f"""
            <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:12px;padding:1rem;margin:0.8rem 0;">
                <span style="font-size:1.1rem;">{result['level']}</span>
                {engine_tag}<br/>
                <span style="color:#475569;">{result['advice']}</span>
            </div>
            """, unsafe_allow_html=True)

        # K线图（两种模式都显示）
        st.markdown('<p class="section-title">📉 技术分析 — K线图（含支撑/阻力位）</p>', unsafe_allow_html=True)
        kline = fetch_kline(symbol)
        render_kline(kline, result.get("entry_zone"), result.get("exit_zone"))

        # 新闻
        st.markdown('<p class="section-title">📰 相关新闻</p>', unsafe_allow_html=True)
        news = fetch_news(symbol)
        if news:
            for item in news[:10]:
                title = item if isinstance(item, str) else item.get("title", str(item))
                st.markdown(f"• {title}")
        else:
            st.info("暂无相关个股新闻")

        # 财务
        fin = fetch_finance(symbol)
        if fin:
            st.markdown('<p class="section-title">📋 核心财务指标</p>', unsafe_allow_html=True)
            fcols = st.columns(min(len(fin), 4))
            for i, (k, v) in enumerate(list(fin.items())[:8]):
                with fcols[i % 4]:
                    st.metric(label=k, value=str(v)[:16])

    st.divider()
    st.markdown('<p style="text-align:center;color:#94A3B8;font-size:0.8rem;">AI金融决策智能体 · 六层异构数据融合 · 28因子量化评分 · Piotroski · VaR · 凯利公式 | 江汉区AI智能体创新大赛</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
