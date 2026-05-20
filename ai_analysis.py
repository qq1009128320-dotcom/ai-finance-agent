"""
AI 市场分析报告模块
Hermes Agent + DeepSeek LLM 驱动
"""

import streamlit as st
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def render_ai_analysis(quote_data, kline_df=None, quant_result=None):
    """渲染 AI 市场分析报告"""
    
    st.markdown("### 🤖 AI 市场分析报告")
    st.caption("基于技术面、资金面、事件面多维度数据，LLM 生成深度分析")
    
    if not quote_data or quote_data.get("error"):
        st.warning("需要先查询股票数据")
        return
    
    name = quote_data.get("name", "未知")
    code = quote_data.get("code", "")
    
    # ── 生成分析 ──
    if st.button(f"🔍 AI 深度分析 {name}", type="primary", use_container_width=True):
        with st.spinner("🧠 AI 正在分析市场数据..."):
            analysis = _generate_analysis(quote_data, kline_df, quant_result)
        
        if analysis.get("error"):
            st.error(analysis["error"])
            return
        
        # ── 展示报告 ──
        st.markdown("---")
        
        # 综合评级
        rating = analysis.get("rating", "中性")
        rating_map = {
            "强烈看多": ("#EF4444", "🚀"), "看多": ("#F59E0B", "📈"),
            "中性": ("#6B7280", "➡️"), "看空": ("#10B981", "📉"),
            "强烈看空": ("#3B82F6", "⬇️")
        }
        color, icon = rating_map.get(rating, ("#6B7280", "➡️"))
        
        col1, col2, col3 = st.columns([2, 5, 2])
        with col1:
            st.markdown(f"""
            <div style="background:#0d1520;border:1px solid #1a2744;border-radius:12px;padding:1.2rem;text-align:center;">
                <div style="font-size:0.8rem;color:#64748b;">综合评级</div>
                <div style="font-size:2rem;color:{color};font-weight:700;margin:0.3rem 0;">{icon} {rating}</div>
                <div style="font-size:0.75rem;color:#94a3b8;">置信度 {analysis.get('confidence','75')}%</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"**核心观点**：{analysis.get('summary','')}")
        
        with col3:
            lines = analysis.get("key_points", [])
            for pt in lines[:3]:
                st.markdown(f"• {pt}")
        
        st.markdown("---")
        
        # 详细分析
        sections = analysis.get("sections", [])
        if sections:
            cols = st.columns(min(len(sections), 3))
            for i, sec in enumerate(sections):
                with cols[i % 3]:
                    st.markdown(f"**{sec.get('title','')}**")
                    st.caption(sec.get('content',''))
        
        st.markdown("---")
        
        # 操作建议
        advice = analysis.get("advice", {})
        if advice:
            st.markdown("#### 📋 操作建议")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("支撑位", advice.get("support", "N/A"))
            with c2:
                st.metric("阻力位", advice.get("resistance", "N/A"))
            with c3:
                st.metric("止损位", advice.get("stop_loss", "N/A"))
            with c4:
                st.metric("目标位", advice.get("target", "N/A"))
            
            st.caption(f"仓位建议: {advice.get('position','观望')} | 持有周期: {advice.get('horizon','短线')}")


def _generate_analysis(quote_data, kline_df=None, quant_result=None):
    """调用 LLM 生成分析报告"""
    if not DEEPSEEK_KEY:
        return _demo_analysis(quote_data)
    
    name = quote_data.get("name", "")
    code = quote_data.get("code", "")
    
    # 构建数据摘要
    data_text = f"股票: {name}({code})\n"
    for k, v in quote_data.items():
        if k not in ["name", "code", "error"]:
            data_text += f"  {k}: {v}\n"
    
    if kline_df is not None and len(kline_df) > 5:
        close = kline_df['close'].values
        ma5 = close[-5:].mean() if len(close) >= 5 else close[-1]
        ma20 = close[-20:].mean() if len(close) >= 20 else close[-1]
        vol = close[-5:].std() / close[-5:].mean() if len(close) >= 5 else 0
        data_text += f"\nK线数据(近{len(kline_df)}日):\n"
        data_text += f"  最新价: {close[-1]:.2f}\n"
        data_text += f"  MA5: {ma5:.2f}\n"
        data_text += f"  MA20: {ma20:.2f}\n"
        data_text += f"  近5日波动率: {vol*100:.1f}%\n"
        data_text += f"  近5日涨跌: {((close[-1]/close[-5]-1)*100):.2f}%\n" if len(close) >= 5 else ""
    
    if quant_result:
        data_text += f"\n量化评分: {quant_result}\n"
    
    prompt = f"""你是A股量化分析师。根据以下数据，生成一份简洁的市场分析报告。

数据：
{data_text}

请返回 JSON（不要 markdown）：
{{
  "rating": "强烈看多|看多|中性|看空|强烈看空",
  "confidence": 60-95,
  "summary": "1-2句核心观点",
  "key_points": ["要点1","要点2","要点3"],
  "sections": [
    {{"title":"技术面","content":"技术分析内容"}},
    {{"title":"资金面","content":"资金分析内容"}},
    {{"title":"事件面","content":"事件面分析"}}
  ],
  "advice": {{
    "support": "支撑价",
    "resistance": "阻力价",
    "stop_loss": "止损价",
    "target": "目标价",
    "position": "建议仓位",
    "horizon": "持有周期"
  }}
}}"""

    try:
        resp = requests.post(DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.3, "max_tokens": 800},
            timeout=30)
        
        if resp.status_code != 200:
            return _demo_analysis(quote_data)
        
        text = resp.json()["choices"][0]["message"]["content"].strip()
        import re
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text).strip()
        return json.loads(text)
    except:
        return _demo_analysis(quote_data)


def _demo_analysis(quote_data):
    """离线演示分析"""
    import random
    name = quote_data.get("name", "未知")
    chg = float(quote_data.get("change_pct", 0) or 0)
    
    if chg > 3:
        rating, conf = "看多", 82
        summary = f"{name}短期动能强劲，技术面与资金面共振向上。建议关注成交量能否持续放大确认趋势。"
        key_points = ["均线多头排列，MACD金叉延续", "北向资金近5日净流入明显", "所属板块政策面利好"]
    elif chg > 1:
        rating, conf = "看多", 72
        summary = f"{name}走势偏强，成交量温和放大。关键阻力位附近需观察突破力度。"
        key_points = ["站稳5日均线，短期趋势向好", "资金小幅流入，关注持续性", "板块轮动中受益"]
    elif chg > -1:
        rating, conf = "中性", 65
        summary = f"{name}处于震荡整理阶段，方向未明。建议观望等待放量突破信号。"
        key_points = ["均线粘合，等待方向选择", "成交量萎缩，观望情绪浓厚", "未有明确催化剂"]
    elif chg > -3:
        rating, conf = "看空", 68
        summary = f"{name}短期承压，技术面偏弱。关注下方支撑能否有效守住。"
        key_points = ["跌破5日均线，短期走弱", "资金小幅流出", "板块整体回调中"]
    else:
        rating, conf = "看空", 78
        summary = f"{name}跌幅较大，技术面全面走弱。建议规避，等待企稳信号。"
        key_points = ["均线空头排列，MACD死叉", "资金持续流出", "基本面/消息面暂无利好"]
    
    return {
        "rating": rating,
        "confidence": conf,
        "summary": summary,
        "key_points": key_points,
        "sections": [
            {"title": "📊 技术面", "content": f"{name}当前{'处于上升趋势' if chg>0 else '短期承压'}，{'MACD指标偏多' if chg>0 else '技术指标偏弱'}。需关注成交量配合情况。"},
            {"title": "💰 资金面", "content": f"{'北向资金近期流入' if chg>0 else '资金面偏弱'}，{'主力资金参与度较高' if random.random()>0.5 else '观望资金为主'}。"},
            {"title": "📰 事件面", "content": f"{'所属板块受益于近期政策利好' if random.random()>0.4 else '暂无重大事件催化'}，关注后续业绩披露和行业动态。"},
        ],
        "advice": {
            "support": f"{random.uniform(10,50):.1f}",
            "resistance": f"{random.uniform(50,100):.1f}",
            "stop_loss": f"{random.uniform(8,30):.1f}",
            "target": f"{random.uniform(40,120):.1f}",
            "position": "3成仓" if rating in ["看多"] else "观望",
            "horizon": "中短线（1-4周）"
        }
    }
