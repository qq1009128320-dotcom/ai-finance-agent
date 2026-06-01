# Tushare 股指期货数据源集成方案

## 一、方案概述

在现有 AI 金融决策智能体中，新增 Tushare 股指期货数据层，作为股票量化分析的**市场情绪与宏观参考指标**。

### 核心价值

| 用途 | 说明 |
|------|------|
| **市场情绪指标** | 股指期货升水/贴水 → 判断市场多空情绪 |
| **基差分析** | 期货-现货价差 → 预测短期市场方向 |
| **资金流向** | 持仓量变化 → 主力资金动向 |
| **跨市场联动** | IF↔沪深300成分股 / IH↔上证50成分股 / IC↔中证500成分股 / IM↔中证1000成分股 |
| **趋势确认** | 期货趋势与股票趋势背离 → 预警信号 |

---

## 二、技术架构设计

### 2.1 数据层结构

```
ai-finance-agent/
├── data/
│   ├── quotes.py              # 腾讯行情（现有）
│   ├── tushare_futures.py     # Tushare 期货数据（新增）
│   ├── .env.tushare           # Tushare Token 配置（新增）
│   └── cache/tushare/         # 本地缓存目录（自动创建）
├── layers/
│   └── signal.py              # 信号层（可新增期货信号因子）
├── quant_engine.py            # 量化引擎（新增期货因子）
└── app.py                     # 主程序（新增期货Tab）
```

### 2.2 数据流向

```
┌─────────────────────────────────────────────────────────┐
│                    Tushare API                           │
│  futures_index(IF/IH/IC/IM) → 主力连续日行情             │
│  futures_daily(symbol)      → 单合约日行情               │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              tushare_futures.py (数据层)                  │
│  - 初始化 Tushare 连接                                    │
│  - 获取4大股指期货主力连续数据                            │
│  - 计算基差、升贴水率、持仓量变化                         │
│  - 缓存到本地 Parquet                                     │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              quant_engine.py (量化引擎)                   │
│  - 新增「期货情绪」维度 (4个因子)                          │
│  - 基差率因子: 期货基差/现货 × 100%                       │
│  - 持仓量变化因子: 日持仓量变化率                         │
│  - 期现背离因子: 期货趋势与指数趋势差异                   │
│  - 跨品种强弱因子: IF/IH/IC/IM 相对强弱                   │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                  app.py (前端展示)                        │
│  - 新增「期货情绪」标签页                                  │
│  - 4大股指期货K线图 + 基差率曲线                          │
│  - 持仓量变化柱状图                                       │
│  - 升贴水率仪表盘                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 三、Tushare Token 配置

### 3.1 获取 Token

1. 访问 https://tushare.pro/user/token
2. 登录/注册账号
3. 复制你的 Pro Token

### 3.2 配置 Token

**方式一：环境变量（推荐）**

```bash
# 在 ~/.bashrc 或 ~/.zshrc 中添加
export TUSHARE_TOKEN="your_token_here"

# 或者临时设置
export TUSHARE_TOKEN="your_token_here"
```

**方式二：配置文件**

编辑 `data/.env.tushare`：

```
TUSHARE_TOKEN=your_token_here
```

**方式三：代码中直接传入**

```python
from data.tushare_futures import TushareFutures
tf = TushareFutures(token="your_token_here")
```

---

## 四、数据层代码：`data/tushare_futures.py`

文件已创建，核心功能：

### 4.1 初始化

```python
from data.tushare_futures import TushareFutures

# 从环境变量自动读取 token
tf = TushareFutures()

# 或手动传入
tf = TushareFutures(token="your_token_here")
```

### 4.2 获取股指期货数据

```python
# 获取单个品种主力连续数据（推荐）
df_if = tf.get_futures_index('IF')  # 沪深300股指期货
df_ih = tf.get_futures_index('IH')  # 上证50股指期货
df_ic = tf.get_futures_index('IC')  # 中证500股指期货
df_im = tf.get_futures_index('IM')  # 中证1000股指期货

# 一次性获取全部
all_data = tf.get_all_indices()  # {'IF': df, 'IH': df, 'IC': df, 'IM': df}

# 获取指定时间范围
df = tf.get_futures_index('IF', start_date='20240101', end_date='20241231')
```

### 4.3 计算基差和升贴水

```python
# 自动获取对应现货指数并计算基差
df_with_basis = tf.calculate_basis(df_if, index_code='IF')
# 新增列: basis, basis_rate, premium_discount

# 查看最新基差
latest = df_with_basis.iloc[-1]
print(f"基差: {latest['basis']:.2f}")
print(f"基差率: {latest['basis_rate']:.4f}%")
print(f"状态: {latest['premium_discount']}")
```

### 4.4 计算持仓量变化

```python
df_with_oi = tf.calculate_open_interest_change(df_if, window=5)
# 新增列: oi_change, oi_change_rate, oi_ma, oi_trend

latest = df_with_oi.iloc[-1]
print(f"持仓量: {latest['open_interest']}")
print(f"日变化: {latest['oi_change']}")
print(f"趋势: {latest['oi_trend']}")
```

### 4.5 获取市场情绪指标

```python
sentiment = tf.get_market_sentiment('IF')
# 返回:
{
    'index_code': 'IF',
    'index_name': '沪深300股指期货',
    'date': '2024-06-01',
    'close': 4200.5,
    'change_pct': 0.85,
    'basis_rate': 0.32,           # 基差率%
    'premium_discount': '升水',    # 升水/贴水/平价
    'open_interest': 125000,
    'oi_change': 2500,
    'oi_change_rate': 2.05,
    'oi_trend': '增仓',
    'volume': 350000,
    'vol_change_pct': 5.2,
    'sentiment': '看涨'            # 综合情绪: 强烈看涨/看涨/震荡/看跌/强烈看跌
}
```

### 4.6 跨品种强弱分析

```python
cross_df = tf.get_cross_analysis()
# 返回 DataFrame:
#   品种   名称          现价    1日涨跌幅%  5日涨跌幅%  基差率%  持仓量   成交量
#   IF    沪深300股指期货  4200.5   0.85      2.3       0.32   125000  350000
#   IH    上证50股指期货   2800.2   0.65      1.8      -0.15   85000   220000
#   IC    中证500股指期货  5800.8   1.20      3.5       0.55   95000   280000
#   IM    中证1000股指期货 6500.3   1.50      4.2       0.78   75000   190000
```

---

## 五、量化引擎集成：`quant_engine.py`

### 5.1 新增期货情绪因子

在 `FactorCalculator` 类中添加以下因子：

```python
# -- 期货情绪因子 (新增) --

def futures_basis_rate(self, basis_rate: float) -> FactorScore:
    """因子29: 股指期货基差率 — 市场情绪核心指标"""
    # 基差率 > 0.5%: 强烈升水 = 强烈看涨
    # 基差率 0~0.5%: 温和升水 = 看涨
    # 基差率 -0.5~0%: 温和贴水 = 看跌
    # 基差率 < -0.5%: 强烈贴水 = 强烈看跌
    
    if basis_rate > 0.5:
        score, signal = 90, "bullish"
        detail = f"强烈升水({basis_rate:.2f}%)，市场情绪极度乐观，多头力量强劲"
    elif basis_rate > 0.2:
        score, signal = 70, "bullish"
        detail = f"温和升水({basis_rate:.2f}%)，市场情绪偏多"
    elif basis_rate > 0:
        score, signal = 55, "bullish"
        detail = f"小幅升水({basis_rate:.2f}%)，情绪中性偏多"
    elif basis_rate > -0.2:
        score, signal = 45, "neutral"
        detail = f"小幅贴水({basis_rate:.2f}%)，情绪中性偏空"
    elif basis_rate > -0.5:
        score, signal = 30, "bearish"
        detail = f"温和贴水({basis_rate:.2f}%)，市场情绪偏空"
    else:
        score, signal = 15, "bearish"
        detail = f"强烈贴水({basis_rate:.2f}%)，市场情绪极度悲观"
    
    return FactorScore(
        name="股指期货基差率", value=basis_rate,
        score=score, signal=signal, weight=0.06,
        contribution=score * 0.06,
        detail=detail
    )


def futures_open_interest_trend(self, oi_change_rate: float, oi_trend: str) -> FactorScore:
    """因子30: 持仓量变化趋势 — 主力资金动向"""
    # 增仓上涨: 多头主动入场 (最看涨)
    # 增仓下跌: 空头主动入场 (最看跌)
    # 减仓上涨: 空头平仓 (次看涨)
    # 减仓下跌: 多头平仓 (次看跌)
    
    if oi_trend == '增仓':
        if oi_change_rate > 3:
            score, signal = 85, "bullish"
            detail = f"大幅增仓({oi_change_rate:.1f}%)，主力资金积极入场"
        elif oi_change_rate > 0:
            score, signal = 65, "bullish"
            detail = f"温和增仓({oi_change_rate:.1f}%)，资金流入中"
        else:
            score, signal = 55, "neutral"
            detail = f"小幅增仓({oi_change_rate:.1f}%)，资金小幅流入"
    else:  # 减仓
        if oi_change_rate < -3:
            score, signal = 25, "bearish"
            detail = f"大幅减仓({oi_change_rate:.1f}%)，主力资金撤离"
        elif oi_change_rate < 0:
            score, signal = 40, "neutral"
            detail = f"温和减仓({oi_change_rate:.1f}%)，资金小幅流出"
        else:
            score, signal = 50, "neutral"
            detail = f"持仓基本持平({oi_change_rate:.1f}%)，资金观望"
    
    return FactorScore(
        name="持仓量变化趋势", value=oi_change_rate,
        score=score, signal=signal, weight=0.05,
        contribution=score * 0.05,
        detail=detail
    )


def futures_cross_strength(self, cross_df: pd.DataFrame, target_index: str = 'IF') -> FactorScore:
    """因子31: 跨品种相对强弱 — 判断市场风格"""
    if cross_df is None or cross_df.empty or len(cross_df) < 4:
        return self._neutral_factor("跨品种强弱", 0.04, "数据不足")
    
    # 计算各品种5日收益率排名
    cross_df = cross_df.sort_values('5日涨跌幅%', ascending=False)
    rank = cross_df[cross_df['品种'] == target_index].index[0] if target_index in cross_df['品种'].values else 2
    rank_score = (4 - rank) / 3 * 100  # 第1名=100分, 第4名=0分
    
    # 计算强弱差
    max_ret = cross_df['5日涨跌幅%'].max()
    min_ret = cross_df['5日涨跌幅%'].min()
    spread = max_ret - min_ret
    
    if rank_score >= 75:
        score, signal = 80, "bullish"
        detail = f"领涨品种，5日收益率排名{4-rank+1}/4，市场风格偏向{target_index}对应板块"
    elif rank_score >= 50:
        score, signal = 55, "neutral"
        detail = f"居中品种，5日收益率排名{4-rank+1}/4，市场风格均衡"
    else:
        score, signal = 30, "bearish"
        detail = f"领跌品种，5日收益率排名{4-rank+1}/4，市场风格不偏向{target_index}对应板块"
    
    return FactorScore(
        name="跨品种相对强弱", value=rank_score,
        score=score, signal=signal, weight=0.04,
        contribution=score * 0.04,
        detail=detail
    )


def futures_divergence(self, future_ret: float, spot_ret: float) -> FactorScore:
    """因子32: 期现背离 — 趋势反转预警"""
    # 期货涨+现货跌: 背离看涨 (期货先行)
    # 期货跌+现货涨: 背离看跌 (期货先行)
    # 同向: 趋势一致
    
    divergence = future_ret - spot_ret
    
    if abs(divergence) < 0.5:
        score, signal = 50, "neutral"
        detail = f"期现同步，期货涨跌幅{future_ret:.2f}%, 现货涨跌幅{spot_ret:.2f}%"
    elif divergence > 1:
        score, signal = 75, "bullish"
        detail = f"期货强于现货({divergence:.2f}%)，期货先行看涨信号"
    elif divergence > 0:
        score, signal = 60, "bullish"
        detail = f"期货略强于现货({divergence:.2f}%)，偏多信号"
    elif divergence < -1:
        score, signal = 25, "bearish"
        detail = f"期货弱于现货({divergence:.2f}%)，期货先行看跌信号"
    else:
        score, signal = 40, "neutral"
        detail = f"期货略弱于现货({divergence:.2f}%)，偏空信号"
    
    return FactorScore(
        name="期现背离信号", value=divergence,
        score=score, signal=signal, weight=0.05,
        contribution=score * 0.05,
        detail=detail
    )
```

### 5.2 更新因子目录

在 `FACTOR_CATALOG` 中添加：

```python
FACTOR_CATALOG = {
    # ... 原有因子 ...
    
    # 期货情绪类 (新增)
    "股指期货基差率": "IF/IH/IC/IM基差率，升水=看涨情绪，贴水=看跌情绪，>0.5%=强烈信号",
    "持仓量变化趋势": "期货持仓量日变化率，增仓上涨=多头主动，增仓下跌=空头主动",
    "跨品种相对强弱": "IF/IH/IC/IM收益率排名，判断市场风格偏向",
    "期现背离信号": "期货与现货涨跌幅差异，背离预示趋势反转",
}
```

### 5.3 更新维度权重

将原5维度权重调整为6维度：

```python
dim_slices = [
    (0, 8, 0.38),    # 趋势研判: 8因子, 38%
    (8, 14, 0.22),   # 动量信号: 6因子, 22%
    (14, 19, 0.13),  # 波动风险: 5因子, 13%
    (19, 24, 0.10),  # 资金流向: 5因子, 10%
    (24, 28, 0.05),  # 形态识别: 4因子, 5%
    (28, 32, 0.12),  # 期货情绪: 4因子, 12% (新增)
]

dim_names = ["趋势研判", "动量信号", "波动风险", "资金流向", "形态识别", "期货情绪"]
```

---

## 六、前端集成：`app.py`

### 6.1 新增期货情绪标签页

在 `app.py` 的标签页中添加：

```python
# 在 st.tabs 中添加
tabs = st.tabs(["单股分析", "全市场扫描", "期货情绪", "投资组合", "设置"])

# -- 期货情绪标签页 --
with tabs[2]:
    st.markdown('<p class="section-title">股指期货情绪仪表盘</p>', unsafe_allow_html=True)
    
    # 初始化 Tushare
    try:
        from data.tushare_futures import TushareFutures
        tf = TushareFutures()
        
        # 获取四大股指期货数据
        col1, col2, col3, col4 = st.columns(4)
        
        for idx, (code, name) in enumerate(tf.FUTURE_INDICES.items()):
            with [col1, col2, col3, col4][idx]:
                sentiment = tf.get_market_sentiment(code)
                if 'error' not in sentiment:
                    # 情绪卡片
                    color = '#EF4444' if '涨' in sentiment['sentiment'] else ('#10B981' if '跌' in sentiment['sentiment'] else '#6B7280')
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #1E293B, #0F172A); 
                                border-radius: 12px; padding: 1rem; border-left: 4px solid {color};">
                        <div style="font-size: 0.85rem; color: #94A3B8;">{sentiment['index_name']}</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: #E2E8F0; margin: 0.5rem 0;">
                            {sentiment['close']:.2f}
                        </div>
                        <div style="font-size: 0.8rem; color: {'#EF4444' if sentiment['change_pct'] > 0 else '#10B981'};">
                            {sentiment['change_pct']:+.2f}%
                        </div>
                        <div style="margin-top: 0.5rem; font-size: 0.75rem;">
                            <div>基差率: {sentiment['basis_rate']:+.4f}% ({sentiment['premium_discount']})</div>
                            <div>持仓: {sentiment['open_interest']:,} ({sentiment['oi_trend']})</div>
                            <div style="font-weight: 600; color: {color}; margin-top: 0.3rem;">
                                情绪: {sentiment['sentiment']}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # K线图
        st.markdown('<p class="section-title" style="margin-top: 2rem;">股指期货K线图</p>', unsafe_allow_html=True)
        
        selected = st.selectbox("选择品种", list(tf.FUTURE_INDICES.keys()), 
                               format_func=lambda x: f"{x} - {tf.FUTURE_INDICES[x]}")
        
        df = tf.get_futures_index(selected)
        if df is not None and not df.empty:
            # 计算基差
            df_basis = tf.calculate_basis(df, index_code=selected)
            
            # K线图
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df_basis['trade_date'],
                open=df_basis['open'], high=df_basis['high'],
                low=df_basis['low'], close=df_basis['close'],
                name='K线'
            ))
            fig.update_layout(height=400, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # 基差率曲线
        if 'basis_rate' in df_basis.columns:
            st.markdown('<p class="section-title">基差率走势</p>', unsafe_allow_html=True)
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df_basis['trade_date'],
                y=df_basis['basis_rate'],
                mode='lines',
                name='基差率%',
                line=dict(color='#38BDF8')
            ))
            fig2.add_hline(y=0, line_dash="dash", line_color="gray")
            fig2.update_layout(height=300, yaxis_title="基差率(%)")
            st.plotly_chart(fig2, use_container_width=True)
        
        # 跨品种强弱对比
        st.markdown('<p class="section-title" style="margin-top: 2rem;">跨品种强弱对比</p>', unsafe_allow_html=True)
        cross_df = tf.get_cross_analysis()
        if cross_df is not None and not cross_df.empty:
            st.dataframe(cross_df, use_container_width=True)
            
            # 柱状图
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(
                x=cross_df['品种'],
                y=cross_df['5日涨跌幅%'],
                name='5日涨跌幅%',
                marker_color=['#38BDF8', '#818CF8', '#F472B6', '#34D399']
            ))
            fig3.update_layout(height=300, yaxis_title="涨跌幅(%)")
            st.plotly_chart(fig3, use_container_width=True)
            
    except Exception as e:
        st.error(f"期货数据加载失败: {e}")
        st.info("请确保已安装 tushare: `pip install tushare` 并配置 TUSHARE_TOKEN")
```

---

## 七、依赖安装

```bash
# 安装 tushare
pip install tushare

# 安装 parquet 支持（用于缓存）
pip install pyarrow

# 安装 pandas 增强功能
pip install pandas numpy
```

### requirements.txt 更新

```
# 在原有依赖基础上添加
tushare>=2.0.0
pyarrow>=14.0.0
```

---

## 八、使用示例

### 8.1 快速查看市场情绪

```python
from data.tushare_futures import TushareFutures

tf = TushareFutures()

# 查看四大股指期货当前情绪
for code in ['IF', 'IH', 'IC', 'IM']:
    sentiment = tf.get_market_sentiment(code)
    print(f"{sentiment['index_name']}: {sentiment['sentiment']} | "
          f"基差率{sentiment['basis_rate']:+.4f}% | {sentiment['premium_discount']} | "
          f"持仓{sentiment['oi_trend']}")
```

### 8.2 获取个股对应股指期货参考

```python
# 根据股票所属指数获取对应期货情绪
def get_stock_futures_sentiment(stock_code: str) -> dict:
    """根据股票代码返回对应的股指期货情绪"""
    prefix = stock_code[0]
    
    if prefix in ('6', '9'):  # 上海主板
        if stock_code.startswith('600') or stock_code.startswith('601') or stock_code.startswith('603'):
            return TushareFutures().get_market_sentiment('IH')  # 上证50
        else:
            return TushareFutures().get_market_sentiment('IF')  # 沪深300
    elif prefix in ('0', '2'):  # 深圳
        return TushareFutures().get_market_sentiment('IF')  # 沪深300
    elif prefix == '3':  # 创业板
        return TushareFutures().get_market_sentiment('IC')  # 中证500
    elif prefix == '688':  # 科创板
        return TushareFutures().get_market_sentiment('IF')  # 沪深300
    elif prefix in ('8', '4') or stock_code.startswith('920'):  # 北交所
        return TushareFutures().get_market_sentiment('IM')  # 中证1000
    
    return None

# 使用
sentiment = get_stock_futures_sentiment('600036')  # 招商银行
print(f"招商银行对应股指期货情绪: {sentiment['sentiment']}")
```

### 8.3 量化策略中的期货信号

```python
def futures_signal_filter(stock_signal: str, futures_sentiment: dict) -> str:
    """
    结合期货情绪过滤股票信号
    
    Args:
        stock_signal: 股票量化信号 (bullish/bearish/neutral)
        futures_sentiment: 对应股指期货情绪
    
    Returns:
        过滤后的信号
    """
    if futures_sentiment is None:
        return stock_signal
    
    fs = futures_sentiment['sentiment']
    
    # 强烈背离时过滤
    if fs == '强烈看跌' and stock_signal == 'bullish':
        return 'neutral'  # 股票看涨但期货强烈看跌，谨慎
    elif fs == '强烈看涨' and stock_signal == 'bearish':
        return 'neutral'  # 股票看跌但期货强烈看涨，谨慎
    
    # 同向增强
    if ('涨' in fs and stock_signal == 'bullish') or ('跌' in fs and stock_signal == 'bearish'):
        return stock_signal  # 同向，保持原信号
    
    return stock_signal
```

---

## 九、注意事项

### 9.1 期货合约换月

- `futures_index` 返回的是主力连续数据，已自动处理换月
- `futures_daily` 返回单合约数据，到期后需要切换到下一合约

### 9.2 数据延迟

- Tushare 日行情数据通常在当晚收盘后更新
- 盘中实时数据建议使用腾讯行情或交易所官方数据

### 9.3 Token 权限

- 基础 Token 有调用频率限制（约60次/分钟）
- 高频使用建议升级 Token 等级

### 9.4 基差计算

- 基差 = 期货价格 - 现货指数价格
- 升水(正基差)通常表示市场看涨情绪
- 贴水(负基差)通常表示市场看跌情绪
- 但需注意：股指期货贴水是常态（对冲成本），不能简单理解为看跌

---

## 十、文件清单

| 文件 | 说明 |
|------|------|
| `data/tushare_futures.py` | Tushare 期货数据层（已创建） |
| `data/.env.tushare` | Token 配置文件（已创建） |
| `data/cache/tushare/` | 本地缓存目录（自动创建） |
| `quant_engine.py` | 需添加期货因子（见方案） |
| `app.py` | 需添加期货情绪Tab（见方案） |
| `requirements.txt` | 需添加 tushare, pyarrow |

---

## 十一、下一步行动

1. **配置 Token**: 将你的 Tushare Token 填入 `data/.env.tushare` 或设置环境变量
2. **安装依赖**: `pip install tushare pyarrow`
3. **测试数据层**: 运行测试脚本验证数据获取
4. **集成量化引擎**: 将期货因子添加到 `quant_engine.py`
5. **集成前端**: 在 `app.py` 中添加期货情绪标签页
6. **验证**: 启动应用，查看期货情绪数据是否正常显示
