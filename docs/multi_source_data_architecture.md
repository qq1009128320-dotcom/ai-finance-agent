# 多源数据架构完整方案

## 一、当前数据源诊断

### 1.1 现有方案痛点

| 数据源 | 优势 | 劣势 | 稳定性 |
|--------|------|------|--------|
| **腾讯财经** | 零依赖、实时、响应快 | 数据有限（无财务/宏观/行业） | ⭐⭐⭐⭐⭐ |
| **akshare** | 数据全面 | WSL 下偶断、依赖多、接口频繁变动 | ⭐⭐ |

### 1.2 数据缺口

| 数据类别 | 腾讯 | akshare | 缺口等级 |
|----------|------|---------|----------|
| 实时行情 | ✅ | ✅ | 无 |
| 日 K 线历史 | ⚠️ 有限 | ✅ | 中 |
| 复权因子 | ❌ | ✅ | 高 |
| **财务数据** | ❌ | ✅ | **极高** |
| **宏观经济** | ❌ | ⚠️ | **高** |
| **行业分类** | ❌ | ✅ | **高** |
| **概念板块** | ❌ | ✅ | **高** |
| **股指期货** | ❌ | ⚠️ | **高** |
| 资金流向 | ❌ | ⚠️ | 高 |
| 龙虎榜 | ❌ | ✅ | 中 |

### 1.3 稳定性根因

1. **网络层**: WSL NAT 模式 DNS 解析不稳定
2. **数据源层**: akshare 依赖多个第三方源，任一挂掉就影响功能
3. **应用层**: 无缓存、无重试、无降级、无数据校验

---

## 二、Tushare 数据源评估

### 2.1 数据覆盖对比

| 数据类别 | Tushare | 稳定性 | 备注 |
|----------|---------|--------|------|
| 股票基础数据 | ✅ 全面 | ⭐⭐⭐⭐⭐ | 免费 |
| 股票行情 | ✅ 全面 | ⭐⭐⭐⭐⭐ | 免费 |
| **财务数据** | ✅ 全面 | ⭐⭐⭐⭐⭐ | 免费 |
| **宏观经济** | ✅ 全面 | ⭐⭐⭐⭐ | 免费 |
| **行业/概念** | ✅ 全面 | ⭐⭐⭐⭐⭐ | 免费 |
| **股指期货** | ✅ 全面 | ⭐⭐⭐⭐⭐ | 免费 |
| 商品期货 | ✅ 全面 | ⭐⭐⭐⭐ | 免费 |
| 基金数据 | ✅ 全面 | ⭐⭐⭐⭐ | 免费 |
| 债券数据 | ✅ 全面 | ⭐⭐⭐⭐ | 免费 |
| 龙虎榜 | ✅ | ⭐⭐⭐⭐ | 免费 |
| 资金流向 | ✅ | ⭐⭐⭐⭐ | 免费 |
| 研报数据 | ⚠️ 部分 | ⭐⭐⭐ | 需积分 |
| 实时行情 | ❌ | - | T+1 延迟 |

### 2.2 Tushare 稳定性优势

| 维度 | Tushare | akshare |
|------|---------|---------|
| 官方维护 | ✅ 有 | ❌ 无 |
| SLA 保障 | ✅ 付费等级 | ❌ 无 |
| 接口文档 | ✅ 完善 | ⚠️ 分散 |
| 数据质量 | ✅ 清洗过 | ⚠️ 需自行清洗 |
| 调用限制 | ✅ 透明 | ❌ 不透明 |
| 错误处理 | ✅ 明确错误码 | ⚠️ 各种异常 |

### 2.3 Tushare 局限性

1. **实时行情延迟**: 日行情 T+1 更新，分钟线延迟 15 分钟
2. **部分数据需积分**: 高级数据（L2、研报、宏观高频）需要积分
3. **不能替代实时行情**: 实时行情仍需腾讯/交易所直连

---

## 三、三层多源数据架构

### 3.1 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    统一数据路由层 (Data Router)               │
│  统一接口: get_quotes(), get_kline(), get_financials()...    │
│  自动降级: 主源失败 → 备用源 → 本地缓存                      │
│  数据校验: 完整性检查，异常数据自动降级                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   实时行情层     │ │   历史数据层     │ │   基本面层      │
│   (高频/低延迟)  │ │   (中频/高可靠)  │ │   (低频/全面)   │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ 主源: 腾讯      │ │ 主源: Tushare   │ │ 主源: Tushare   │
│ 备用: mootdx    │ │ 备用: akshare   │ │ 备用: akshare   │
│                 │ │                 │ │                 │
│ ✅ 零依赖       │ │ ✅ 稳定可靠     │ │ ✅ 数据全面     │
│ ✅ 实时         │ │ ✅ 历史完整     │ │ ✅ 清洗过       │
│ ⚠️ 数据有限     │ │ ⚠️ T+1 延迟     │ │ ⚠️ T+1 延迟     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
              ┌─────────────────────────┐
              │      本地缓存层          │
              │  (Parquet/SQLite)       │
              │  - 减少 API 调用          │
              │  - 断网可用              │
              │  - 数据完整性校验        │
              │  - 24h 自动过期           │
              └─────────────────────────┘
```

### 3.2 数据源优先级

| 层级 | 主源 | 优先级 | 备用源 | 优先级 |
|------|------|--------|--------|--------|
| 实时行情 | 腾讯财经 | 10 | mootdx | 5 |
| 历史 K 线 | Tushare | 10 | akshare | 3 |
| 财务数据 | Tushare | 10 | akshare | 3 |
| 股指期货 | Tushare | 10 | - | - |
| 指数数据 | Tushare | 10 | akshare | 3 |

---

## 四、代码实现

### 4.1 统一数据路由层 (`data/data_router.py`)

文件已创建，核心功能：

#### 初始化

```python
from data.data_router import DataManager, get_data_manager

# 方式 1: 直接创建
dm = DataManager(tushare_token="your_token")

# 方式 2: 获取全局单例（自动从环境变量读取 token）
dm = get_data_manager()

# 方式 3: 从 .env.tushare 文件读取
dm = get_data_manager()  # 自动读取 data/.env.tushare
```

#### 健康检查

```python
# 查看所有数据源状态
status = dm.get_all_sources_status()
for category, sources in status.items():
    print(f"\n【{category}】")
    for name, info in sources.items():
        icon = "✅" if info['available'] else "❌"
        print(f"  {icon} {name} (优先级:{info['priority']})")
```

#### 实时行情（自动降级）

```python
# 自动使用腾讯，失败则降级到 mootdx
quotes = dm.get_quotes(['600036', '000001', 'sh000001'])
for q in quotes:
    print(f"{q['code']} {q['name']}: {q['price']} ({q['change_pct']}%)")
```

#### K 线数据（Tushare 主，akshare 备）

```python
# 自动使用 Tushare，失败则降级到 akshare
# 包含数据完整性校验和 24h 本地缓存
df = dm.get_kline('600036', count=250)
print(f"数据行数: {len(df)}")
print(f"日期范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")
```

#### 财务数据

```python
fin = dm.get_financials('600036')
# 返回:
{
    'roe': 0.15,
    'gross_margin': 0.25,
    'net_margin': 0.18,
    'pe': 8.5,
    'pb': 1.2,
    'total_revenue': 50000000000,
    'net_profit': 9000000000,
    'total_assets': 80000000000,
    'total_liabilities': 50000000000,
    'debt_ratio': 0.625,
    ...
}
```

#### 股指期货

```python
df_if = dm.get_futures_index('IF')
df_ih = dm.get_futures_index('IH')
df_ic = dm.get_futures_index('IC')
df_im = dm.get_futures_index('IM')
```

#### 便捷函数

```python
from data.data_router import get_quotes, get_kline, get_financials, get_futures_index

# 一行代码获取数据
quotes = get_quotes(['600036'])
df = get_kline('600036', count=250)
fin = get_financials('600036')
df_if = get_futures_index('IF')
```

### 4.2 核心特性

#### 自动降级

```python
# 伪代码逻辑
def get_kline(symbol, count=250):
    for source in [Tushare, Akshare]:  # 按优先级
        if source.is_available:
            result = source.get_kline(symbol, count=count)
            if validate(result):  # 数据完整性检查
                return result
            else:
                warn(f"{source.name} 数据不完整，尝试备用源")
    warn("所有数据源不可用")
    return None
```

#### 本地缓存

```python
# 装饰器自动缓存
@with_cache(ttl_hours=24)
def get_kline(...):
    ...

# 缓存目录: data/cache/router/
# 格式: Parquet（高效读取）
# 过期: 24 小时后自动重新获取
```

#### 数据完整性校验

```python
def _validate_kline(df, min_rows=20):
    # 检查行数
    if len(df) < min_rows: return False
    # 检查关键列
    required = ['trade_date', 'open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required): return False
    # 检查空值比例
    for col in ['open', 'high', 'low', 'close']:
        if df[col].isna().sum() / len(df) > 0.1: return False
    return True
```

#### 重试机制

```python
@with_retry(max_attempts=3, delay=1.0)
def get_quotes(...):
    ...
# 失败后指数退避重试：1s → 2s → 4s
```

---

## 五、集成到现有项目

### 5.1 修改 `data/quotes.py`

在 `TencentQuotes` 类基础上，添加 `data_router.py` 的导入支持：

```python
# data/quotes.py 末尾添加
from .data_router import DataManager, get_data_manager

# 兼容旧代码
def get_quotes_legacy(symbols):
    """兼容旧接口的实时行情获取"""
    dm = get_data_manager()
    return dm.get_quotes(symbols)
```

### 5.2 修改 `quant_engine.py`

#### 财务数据获取改为使用数据路由

```python
# 原代码（可能使用 akshare 直接调用）
# import akshare as ak
# df = ak.stock_financial_report_sina(stock=symbol)

# 新代码（使用数据路由，自动降级）
from data.data_router import get_data_manager

dm = get_data_manager()
fin = dm.get_financials(symbol)
# fin 包含: roe, gross_margin, pe, pb, total_revenue, net_profit 等
```

#### 添加期货情绪因子

```python
from data.data_router import get_futures_index

def get_futures_sentiment_for_stock(symbol: str) -> dict:
    """根据股票代码获取对应股指期货情绪"""
    prefix = symbol[0]
    
    if prefix in ('6', '9'):
        if symbol.startswith(('600', '601', '603')):
            index_code = 'IH'  # 上证 50
        else:
            index_code = 'IF'  # 沪深 300
    elif prefix in ('0', '2'):
        index_code = 'IF'
    elif prefix == '3':
        index_code = 'IC'  # 中证 500
    elif prefix == '688':
        index_code = 'IF'
    elif prefix in ('8', '4') or symbol.startswith('920'):
        index_code = 'IM'  # 中证 1000
    else:
        return None
    
    df = get_futures_index(index_code)
    if df is None or df.empty:
        return None
    
    # 计算基差率
    latest = df.iloc[-1]
    # ... 计算逻辑 ...
    
    return {
        'index_code': index_code,
        'basis_rate': basis_rate,
        'sentiment': sentiment,
        ...
    }
```

### 5.3 修改 `app.py`

#### 初始化数据管理器

```python
# app.py 顶部添加
from data.data_router import get_data_manager
import os

# 从 .env.tushare 读取 token
def load_tushare_token():
    env_file = os.path.join(os.path.dirname(__file__), 'data', '.env.tushare')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith('TUSHARE_TOKEN='):
                    return line.strip().split('=', 1)[1]
    return os.environ.get('TUSHARE_TOKEN')

# 初始化
TOKEN = load_tushare_token()
dm = get_data_manager()  # 使用全局单例
```

#### 替换数据获取代码

```python
# 原代码
# import akshare as ak
# df = ak.stock_zh_a_hist(symbol=symbol, ...)

# 新代码
df = dm.get_kline(symbol, count=250)
if df is None:
    st.error(f"无法获取 {symbol} 的 K 线数据，请检查数据源配置")
    st.stop()
```

---

## 六、依赖安装

```bash
# 安装 Tushare
pip install tushare

# 安装 Parquet 支持（缓存）
pip install pyarrow

# 安装 python-dotenv（可选，用于读取 .env 文件）
pip install python-dotenv
```

### requirements.txt 更新

```
# 在原有依赖基础上添加
tushare>=2.0.0
pyarrow>=14.0.0
python-dotenv>=1.0.0
```

---

## 七、Token 配置

### 7.1 获取 Token

1. 访问 https://tushare.pro/user/token
2. 注册/登录
3. 复制 Pro Token

### 7.2 配置方式（三选一）

**方式一：环境变量（推荐）**

```bash
# ~/.bashrc 或 ~/.zshrc
export TUSHARE_TOKEN="your_token_here"
```

**方式二：配置文件**

编辑 `data/.env.tushare`:
```
TUSHARE_TOKEN=your_token_here
```

**方式三：代码中传入**

```python
dm = DataManager(tushare_token="your_token_here")
```

---

## 十、Token 权限验证结果

> **测试时间**: 2026-06-01
> **Token**: `24c510cf...ac92b6c`

### 10.1 可用接口 ✅

| 接口 | 测试 | 结果 |
|------|------|------|
| `stock_basic` | 深交所股票基础 | ✅ 5 条 |
| `daily` | 600036.SH 日 K 线 | ✅ 18 条 (2026-05) |
| `adj_factor` | 复权因子 | ✅ 5861 条 |
| `fina_indicator` | 财务指标 | ✅ 4 期 |
| `index_daily` | 000001.SH 指数 K 线 | ✅ 18 条 |
| `index_basic` | 指数基本信息 | ✅ 5 条 |
| `moneyflow` | 资金流向 | ✅ 8 条 |
| `fund_basic` | 基金基本信息 | ✅ 3 条 |
| `trade_cal` | 交易日 | ✅ 7 条 |

### 10.2 不可用接口 ⚠️

| 接口 | 错误 | 原因 |
|------|------|------|
| `futures_basic` | 权限不足 | 需要更高积分 |
| `futures_daily` | 权限不足 | 需要更高积分 |
| `futures_index` | 权限不足 | 需要更高积分 |
| `macro_year` | 权限不足 | 需要更高积分 |
| `balance` | 权限不足 | 需要更高积分 |
| `income` | 权限不足 | 需要更高积分 |
| `cashflow` | 权限不足 | 需要更高积分 |

### 10.3 权限总结

```
✅ 股票核心数据: 全部可用
   - K 线 (daily): 可用
   - 复权因子 (adj_factor): 可用
   - 财务指标 (fina_indicator): 可用（基础指标）
   
✅ 指数数据: 全部可用
   - 指数 K 线 (index_daily): 可用
   - 指数基本信息 (index_basic): 可用
   
✅ 其他数据:
   - 资金流向 (moneyflow): 可用
   - 基金数据 (fund_basic): 可用
   - 交易日 (trade_cal): 可用
   
⚠️ 期货数据: 不可用
   - 原因：需要更高积分等级
   - 建议：使用腾讯财经/交易所直连获取期货实时数据
   
⚠️ 详细财务数据: 不可用
   - balance/income/cashflow 需要更高积分
   - 建议：使用 fina_indicator 基础指标
```

### 10.4 期货数据替代方案

由于当前 Token 无法获取期货数据，建议以下替代方案：

**方案 A: 腾讯财经期货接口（推荐）**
```python
# 腾讯财经也提供期货行情
# URL: http://qt.gtimg.cn/q=cffex_IF2606
# 需要自行解析返回格式
```

**方案 B: 升级 Tushare 积分**
- 访问 https://tushare.pro/member 升级积分
- 期货接口需要 3000+ 积分

**方案 C: 使用其他期货数据源**
- 交易所官网（CFFEX）
- 文华财经
- 博易大师

### 8.1 运行健康检查

```bash
cd /home/administrator/tools/ai-finance-agent
python3 data/data_router.py
```

输出示例：

```
============================================================
数据源路由层 - 健康检查
============================================================

【realtime】
  ✅ tencent (优先级:10)
  ❌ mootdx (优先级:5)

【history】
  ✅ tushare (优先级:10)
  ✅ akshare (优先级:3)

【fundamental】
  ✅ tushare (优先级:10)
  ✅ akshare (优先级:3)

============================================================
测试实时行情
============================================================
  sh000001 上证指数: 3100.50

============================================================
测试 K 线数据 (600036)
============================================================
  数据行数: 250
  日期范围: 2025-05-01 ~ 2026-06-01
  最新收盘价: 42.50

============================================================
测试财务数据 (600036)
============================================================
  roe: 0.15
  gross_margin: 0.25
  pe: 8.5
  ...
```

### 8.2 测试降级逻辑

```python
from data.data_router import DataManager

# 模拟 Tushare 不可用
dm = DataManager(tushare_token="invalid_token")
status = dm.get_all_sources_status()
print(status['history']['tushare']['available'])  # False

# 应自动降级到 akshare
df = dm.get_kline('600036', count=30)
print(f"降级后数据行数: {len(df) if df is not None else 0}")
```

---

## 九、性能优化建议

### 9.1 缓存策略

| 数据类型 | 缓存 TTL | 说明 |
|----------|----------|------|
| 实时行情 | 不缓存 | 实时数据，每次请求 |
| 日 K 线 | 24 小时 | 盘中数据不变 |
| 财务数据 | 7 天 | 季报/年报更新频率低 |
| 股票基本信息 | 30 天 | 上市/退市等变动少 |
| 股指期货 | 24 小时 | 与股票 K 线一致 |
| 宏观经济 | 7 天 | 月度/季度数据 |

### 9.2 批量请求优化

```python
# 避免循环调用
# 错误做法
for symbol in symbols:
    df = dm.get_kline(symbol)  # 每次都是独立请求

# 正确做法（如果数据源支持批量）
# Tushare 不支持批量 K 线，但可以减少 API 调用
# 预加载常用股票数据到本地缓存
```

### 9.3 异步加载

```python
# 在 Streamlit 中使用缓存
@st.cache_data(ttl=3600)
def get_stock_data(symbol):
    return dm.get_kline(symbol, count=250)

# 首次加载后 1 小时内直接从缓存读取
```

---

## 十、故障排查

### 10.1 Tushare 连接失败

```
错误: Tushare API 初始化失败
原因: Token 无效或网络问题
解决:
1. 检查 Token 是否正确: echo $TUSHARE_TOKEN
2. 检查网络: curl https://tushare.pro
3. 检查积分是否足够: 部分接口需要积分
```

### 10.2 akshare 请求失败

```
错误: ConnectionError / Timeout
原因: WSL 网络不稳定
解决:
1. 检查 WSL 网络: wsl hostname -I
2. 尝试切换 DNS: 在 Windows  hosts 文件中添加
3. 依赖数据路由层的自动降级到本地缓存
```

### 10.3 数据不完整

```
警告: tushare 数据不完整，尝试备用源
原因: API 返回数据行数不足
解决:
1. 检查 start_date/end_date 范围
2. 检查股票是否已退市
3. 查看 data/cache/router/ 中的缓存文件
```

---

## 十一、文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| **数据路由层** | `data/data_router.py` | 统一数据源路由，自动降级 |
| **Tushare 期货** | `data/tushare_futures.py` | Tushare 期货数据获取器 |
| **Token 配置** | `data/.env.tushare` | Tushare Token 配置文件 |
| **集成方案** | `docs/tushare_futures_integration.md` | 期货集成详细方案 |
| **本方案** | `docs/multi_source_data_architecture.md` | 多源数据架构完整方案 |

---

## 十二、下一步行动

1. **配置 Token**: 将 Tushare Token 填入 `data/.env.tushare`
2. **安装依赖**: `pip install tushare pyarrow python-dotenv`
3. **测试路由层**: `python3 data/data_router.py`
4. **验证降级**: 使用无效 Token 测试自动降级到 akshare
5. **集成到量化引擎**: 修改 `quant_engine.py` 使用 `dm.get_financials()`
6. **集成到前端**: 修改 `app.py` 使用数据路由层
7. **性能测试**: 验证缓存和降级逻辑
