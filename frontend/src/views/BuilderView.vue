<template>
  <div class="builder-view">
    <!-- 顶部操作栏 -->
    <div class="builder-toolbar card">
      <div class="toolbar-left">
        <span class="glyphicon glyphicon-edit" style="cursor:pointer;">✏️</span>
        <input v-model="strategyName" class="input name-input" placeholder="策略名称" />
        <span class="toolbar-action">💾 <a @click="saveStrategy">保存</a></span>
        <span class="toolbar-action">📂 <a @click="loadStrategy">另存</a></span>
        <span class="toolbar-action">🗑️ <a>删除</a></span>
        <span class="toolbar-action">🆕 <a>新建</a></span>
      </div>
    </div>

    <!-- 步骤导航 -->
    <div class="step-nav card">
      <a class="step-item" :class="{ active: step === 1 }" @click="step = 1"><s></s>择股设置<b></b></a>
      <a class="step-item" :class="{ active: step === 2 }" @click="step = 2"><s></s>交易模型<b></b></a>
      <a class="step-item" :class="{ active: step === 3 }" @click="step = 3"><s></s>大盘择时<b></b></a>
    </div>

    <!-- ========== 步骤1: 择股设置 ========== -->
    <div v-show="step === 1">
      <!-- 股票池 -->
      <div class="pool-section card">
        <span class="pool-label">我的股票池：</span>
        <div class="pool-controls">
          <span>股票上限(只)：</span><input v-model.number="config.poolLimit" type="number" class="input" style="width:100px;" />
          <span>调仓周期(日)：</span><input v-model.number="config.rebalanceDays" type="number" class="input" style="width:100px;" />
          <select v-model="config.pool" class="input" style="width:200px;">
            <option value="all">全A股</option>
            <option value="hs300">沪深300</option>
            <option value="zz500">中证500</option>
          </select>
        </div>
      </div>

      <!-- 左右两栏：指标列表 + 条件表格 -->
      <div class="screen-layout">
        <!-- 左栏：选股指标 -->
        <div class="factor-panel card">
          <div class="panel-header">
            <span class="panel-title">选股指标</span>
            <input v-model="searchQuery" class="input" placeholder="搜索财务选项与指标" style="flex:1;margin-left:12px;padding:6px 10px;font-size: 26px;" />
          </div>
          <div class="factor-list">
            <div v-for="cat in factorCategories" :key="cat.name" class="factor-category">
              <div class="cat-title" @click="cat.open = !cat.open">{{ cat.open ? '▼' : '▶' }} {{ cat.name }}</div>
              <div v-if="cat.open" class="cat-items">
                <div v-for="ind in filteredIndicators(cat)" :key="ind.key" class="factor-item" @click="addCondition(ind)">
                  {{ ind.label }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右栏：选股条件 -->
        <div class="filter-panel card">
          <div class="panel-header">
            <div class="filter-tabs">
              <span class="filter-tab" :class="{ active: filterTab === 'condition' }" @click="filterTab = 'condition'">筛选条件<span v-if="config.conditions.length" class="badge">{{ config.conditions.length }}</span></span>
              <span class="filter-tab" :class="{ active: filterTab === 'rank' }" @click="filterTab = 'rank'">排名条件<span v-if="config.rankBy" class="badge">1</span></span>
            </div>
            <div class="logic-toggle" v-if="filterTab === 'condition' && config.conditions.length > 1">
              <span class="logic-btn" :class="{ active: config.conditionLogic === 'AND' }" @click="config.conditionLogic = 'AND'">全部满足</span>
              <span class="logic-btn" :class="{ active: config.conditionLogic === 'OR' }" @click="config.conditionLogic = 'OR'">满足任一</span>
            </div>
          </div>

          <!-- 筛选条件 -->
          <div v-if="filterTab === 'condition'" class="condition-table">
            <div class="condition-header">
              <span class="col-name">指标</span>
              <span class="col-operator">比较符</span>
              <span class="col-range">范围</span>
              <span class="col-value">值</span>
              <span class="col-action">操作</span>
            </div>
            <div v-if="config.conditions.length === 0" class="condition-empty">点击左侧选股指标，生成筛选条件</div>
            <div v-for="(cond, idx) in config.conditions" :key="idx" class="condition-row">
              <span class="col-name">{{ getIndicatorLabel(cond.indicator) }}</span>
              <span class="col-operator">
                <select v-model="cond.operator" class="input" style="width:70px;padding:4px 6px;">
                  <option value=">">&gt;</option><option value="<">&lt;</option>
                  <option value=">=">&ge;</option><option value="<=">&le;</option>
                  <option value="between">区间</option>
                </select>
              </span>
              <span class="col-range">
                <select v-model="cond.range" class="input" style="width:80px;padding:4px 6px;">
                  <option value="day">日频</option><option value="week">周频</option>
                  <option value="month">月频</option><option value="quarter">季频</option>
                  <option value="year">年频</option>
                </select>
              </span>
              <span class="col-value"><input v-model="cond.value" type="text" class="input" style="width:100px;padding:4px 6px;" /></span>
              <span class="col-action"><button class="btn-del" @click="config.conditions.splice(idx,1)">✕</button></span>
            </div>
          </div>

          <!-- 排名条件 -->
          <div v-if="filterTab === 'rank'" class="condition-table">
            <div class="condition-header">
              <span class="col-name">指标</span>
              <span class="col-operator">次序</span>
              <span class="col-range">范围</span>
              <span class="col-value">权重</span>
              <span class="col-action">操作</span>
            </div>
            <div v-if="!config.rankBy" class="condition-empty">点击左侧选股指标，生成排名条件</div>
            <div v-if="config.rankBy" class="condition-row">
              <span class="col-name">{{ getIndicatorLabel(config.rankBy) }}</span>
              <span class="col-operator">
                <select v-model="config.rankOrder" class="input" style="width:70px;padding:4px 6px;">
                  <option value="desc">降序</option><option value="asc">升序</option>
                </select>
              </span>
              <span class="col-range"><input v-model.number="config.rankTop" type="number" class="input" style="width:70px;padding:4px 6px;" /></span>
              <span class="col-value">100%</span>
              <span class="col-action"><button class="btn-del" @click="config.rankBy = ''">✕</button></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 步骤2: 交易模型 ========== -->
    <div v-show="step === 2" class="step-content card">
      <h2 class="card-title">📊 交易模型</h2>
      <p class="text-muted" style="font-size: 26px;">买入规则 / 卖出规则 / 仓位管理</p>
      <div class="trading-grid">
        <div class="trading-section">
          <h3>🟢 买入规则</h3>
          <select v-model="config.buyCondition" class="input">
            <option value="golden_cross">金叉买入（5日线上穿20日线）</option>
            <option value="rsi_oversold">RSI超卖（RSI < 30）</option>
            <option value="breakout">突破买入（突破20日高点）</option>
          </select>
          <label style="margin-top:12px;">买入仓位：<input v-model.number="config.buyPosition" type="range" min="10" max="100" step="5" /> {{ config.buyPosition }}%</label>
        </div>
        <div class="trading-section">
          <h3>🔴 卖出规则</h3>
          <label>止盈：<input v-model.number="config.takeProfit" type="range" min="5" max="100" step="5" /> +{{ config.takeProfit }}%</label>
          <label>止损：<input v-model.number="config.stopLoss" type="range" min="2" max="30" step="1" /> -{{ config.stopLoss }}%</label>
          <label>跟踪止损：<input v-model.number="config.trailingStop" type="range" min="2" max="20" step="1" /> {{ config.trailingStop }}%</label>
        </div>
        <div class="trading-section">
          <h3>📦 仓位管理</h3>
          <label>最大持仓：<input v-model.number="config.maxPositions" type="number" style="width:80px;" /></label>
          <label>单只上限：<input v-model.number="config.maxSinglePct" type="range" min="5" max="50" step="5" /> {{ config.maxSinglePct }}%</label>
          <label>调仓周期：
            <select v-model="config.rebalanceFreq">
              <option value="daily">每日</option><option value="weekly">每周</option>
              <option value="monthly">每月</option>
            </select>
          </label>
        </div>
      </div>
    </div>

    <!-- ========== 步骤3: 大盘择时 ========== -->
    <div v-show="step === 3" class="step-content card">
      <h2 class="card-title">🌐 大盘择时</h2>
      <label><input type="checkbox" v-model="config.enableTiming" /> 启用大盘择时</label>
      <div v-if="config.enableTiming" style="margin-top:12px;">
        <div v-for="(cond, idx) in config.timingConditions" :key="idx" class="condition-row" style="margin-bottom:8px;max-width:600px;">
          <select v-model="cond.indicator" class="input" style="flex:2;"><option value="sh_index">上证指数</option><option value="sh_pe">上证PE</option></select>
          <select v-model="cond.operator" class="input" style="flex:1;"><option value=">">&gt;</option><option value="<">&lt;</option></select>
          <input v-model="cond.value" type="text" class="input" placeholder="值" style="flex:1.5;" />
          <button class="btn-del" @click="config.timingConditions.splice(idx,1)">✕</button>
        </div>
        <button class="btn btn-secondary btn-sm" @click="config.timingConditions.push({indicator:'sh_index',operator:'>',value:''})">+ 添加条件</button>
      </div>
    </div>

    <!-- 底部操作 -->
    <div class="bottom-bar">
      <button class="btn btn-primary" @click="runBacktest">📊 运行回测</button>
      <button class="btn btn-secondary" @click="runHistoricalScreen">📋 按此模型选股</button>
      <button class="btn btn-secondary" @click="saveStrategy">💾 保存策略</button>
    </div>

    <!-- 回测结果展示 -->
    <div v-if="backtestResult" class="result-section card">
      <h2 class="card-title">📊 回测结果</h2>
      <div class="result-metrics">
        <div class="result-metric"><span class="metric-label">总收益</span><span class="metric-value" :class="backtestResult.metrics?.total_return >= 0 ? 'text-up' : 'text-down'">{{ backtestResult.metrics?.total_return?.toFixed(2) }}%</span></div>
        <div class="result-metric"><span class="metric-label">年化收益</span><span class="metric-value" :class="backtestResult.metrics?.annual_return >= 0 ? 'text-up' : 'text-down'">{{ (backtestResult.metrics?.annual_return || 0).toFixed(2) }}%</span></div>
        <div class="result-metric"><span class="metric-label">夏普比率</span><span class="metric-value">{{ (backtestResult.metrics?.sharpe_ratio || 0).toFixed(2) }}</span></div>
        <div class="result-metric"><span class="metric-label">最大回撤</span><span class="metric-value text-down">{{ (backtestResult.metrics?.max_drawdown || 0).toFixed(2) }}%</span></div>
        <div class="result-metric"><span class="metric-label">交易次数</span><span class="metric-value">{{ backtestResult.metrics?.total_trades || 0 }}</span></div>
        <div class="result-metric"><span class="metric-label">胜率</span><span class="metric-value">{{ (backtestResult.metrics?.win_rate || 0).toFixed(1) }}%</span></div>
        <div class="result-metric"><span class="metric-label">盈亏比</span><span class="metric-value">{{ (backtestResult.metrics?.profit_factor || 0).toFixed(2) }}</span></div>
      </div>
    </div>

    <!-- 选股结果展示 -->
    <div v-if="picks.length > 0" class="result-section card">
      <h2 class="card-title">📋 选股结果 <span class="result-subtitle">共 {{ picks.length }} 只股票</span></h2>
      <div class="picks-table">
        <div class="picks-header">
          <span class="picks-col-code">代码</span>
          <span class="picks-col-name">名称</span>
          <span class="picks-col-price">现价</span>
          <span class="picks-col-change">涨跌幅</span>
        </div>
        <div v-for="s in picks" :key="s.symbol" class="picks-row">
          <span class="picks-col-code">{{ s.symbol }}</span>
          <span class="picks-col-name">{{ s.name }}</span>
          <span class="picks-col-price">{{ s.price?.toFixed(2) }}</span>
          <span class="picks-col-change" :class="s.change_pct >= 0 ? 'text-up' : 'text-down'">{{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct?.toFixed(2) }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { backtestApi, strategyApi } from '@/api'

const store = useAppStore()
const step = ref(1)
const strategyName = ref('新策略')
const searchQuery = ref('')
const filterTab = ref('condition')
const backtestResult = ref<any>(null)
const picks = ref<any[]>([])

const config = reactive({
  pool: 'all', poolLimit: 100, rebalanceDays: 5,
  conditionLogic: 'AND' as 'AND' | 'OR',
  conditions: [] as any[],
  rankBy: '', rankOrder: 'desc', rankTop: 50,
  buyCondition: 'golden_cross', buyPosition: 50,
  takeProfit: 25, stopLoss: 8, trailingStop: 6,
  maxPositions: 5, maxSinglePct: 20, rebalanceFreq: 'monthly',
  enableTiming: false, timingConditions: [] as any[],
})

const indicators = [
  { key: 'pe_ttm', label: '市盈率(TTM)', cat: '估值' },
  { key: 'pe_static', label: '市盈率(静态)', cat: '估值' },
  { key: 'pb', label: '市净率', cat: '估值' },
  { key: 'ps_ttm', label: '市销率(TTM)', cat: '估值' },
  { key: 'pcf', label: '市现率', cat: '估值' },
  { key: 'dividend_yield', label: '股息率', cat: '估值' },
  { key: 'market_cap', label: '总市值', cat: '规模' },
  { key: 'circulate_cap', label: '流通市值', cat: '规模' },
  { key: 'roe', label: 'ROE', cat: '成长能力' },
  { key: 'profit_growth_yoy', label: '净利润同比增长', cat: '成长能力' },
  { key: 'revenue_growth_yoy', label: '营收同比增长', cat: '成长能力' },
  { key: 'profit_growth_3y', label: '净利润3年复合增长', cat: '成长能力' },
  { key: 'gross_margin', label: '毛利率', cat: '盈利能力' },
  { key: 'net_margin', label: '净利率', cat: '盈利能力' },
  { key: 'asset_liability', label: '资产负债率', cat: '偿债能力' },
  { key: 'current_ratio', label: '流动比率', cat: '偿债能力' },
  { key: 'volume_ratio', label: '量比', cat: '技术指标' },
  { key: 'turnover_rate', label: '换手率', cat: '技术指标' },
  { key: 'rsi_14', label: 'RSI(14)', cat: '技术指标' },
  { key: 'ma_status', label: '均线状态', cat: '技术指标' },
  { key: 'volatility_20d', label: '20日波动率', cat: '技术指标' },
  { key: 'beta', label: 'Beta系数', cat: '技术指标' },
  { key: 'north_flow', label: '北向资金持股', cat: '资金流向' },
  { key: 'margin_balance', label: '融资余额', cat: '资金流向' },
]

const factorCategories = computed(() => {
  const cats: { name: string; open: boolean; items: typeof indicators }[] = []
  const names = [...new Set(indicators.map(i => i.cat))]
  names.forEach(n => {
    cats.push({ name: n, open: true, items: indicators.filter(i => i.cat === n) })
  })
  return cats
})

function filteredIndicators(cat: { name: string; open: boolean; items: typeof indicators }) {
  if (!searchQuery.value) return cat.items
  const q = searchQuery.value.toLowerCase()
  return cat.items.filter(i => i.label.toLowerCase().includes(q) || i.key.toLowerCase().includes(q))
}

function getIndicatorLabel(key: string) {
  return indicators.find(i => i.key === key)?.label || key
}

function addCondition(ind: typeof indicators[0]) {
  if (filterTab.value === 'condition') {
    config.conditions.push({ indicator: ind.key, operator: '<', range: 'day', value: '' })
  } else {
    config.rankBy = ind.key
  }
}

function runBacktest() {
  const code = `import numpy as np
def init(context):
    context.symbol = "600036"
    context.ma_short = 5; context.ma_long = 20
    context.stop_loss = -${Number(config.stopLoss) / 100}
    context.take_profit = ${Number(config.takeProfit) / 100}
    context.trailing_stop = ${Number(config.trailingStop) / 100}
    context.max_positions = ${Number(config.maxPositions)}
    context.highest_price = 0
def handle_data(context, data):
    symbol = context.symbol
    current_price = data[symbol]["close"]
    kline = get_kline(symbol, period="day", count=60)
    if kline is None or len(kline) < 20: return
    close = kline["close"].values
    ma_short = np.mean(close[-5:]); ma_long = np.mean(close[-20:])
    position = context.portfolio.positions.get(symbol, None)
    if position is None:
        p5 = np.mean(close[-6:-1]); p20 = np.mean(close[-21:-1])
        if p5 <= p20 and ma_short > ma_long:
            buy(symbol, current_price, "金叉买入")
            return
    if position is not None:
        cost = position.get("cost_price", current_price); pnl = (current_price - cost) / max(cost, 0.01)
        if context.highest_price is None or current_price > context.highest_price:
            context.highest_price = current_price
        highest = context.highest_price if context.highest_price and context.highest_price > 0 else current_price
        dd = (highest - current_price) / highest
        if pnl >= context.take_profit: sell(symbol, current_price, "止盈"); return
        if pnl <= context.stop_loss: sell(symbol, current_price, "止损"); return
        if pnl > 0 and dd >= context.trailing_stop: sell(symbol, current_price, "跟踪止损"); return`

  backtestApi.run({ code, symbol: '600036', initial_capital: 100000 }).then(r => {
    backtestResult.value = r.data
    store.setError(null)
  }).catch(() => store.setError('回测失败'))
}

async function runHistoricalScreen() {
  try {
    const r = await (await fetch('/api/v1/builder/screen', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool: config.pool, conditions: config.conditions, condition_logic: config.conditionLogic, limit: 50 }),
    })).json()
    picks.value = r.stocks || []
    store.setError(null)
  } catch { store.setError('选股失败，接口不可用') }
}

async function saveStrategy() {
  if (!strategyName.value.trim()) { store.setError('请输入策略名称'); return }
  try {
    // 把完整配置序列化保存
    const strategyConfig = {
      pool: config.pool,
      poolLimit: config.poolLimit,
      rebalanceDays: config.rebalanceDays,
      conditions: config.conditions,
      conditionLogic: config.conditionLogic,
      rankBy: config.rankBy,
      rankOrder: config.rankOrder,
      rankTop: config.rankTop,
      buyCondition: config.buyCondition,
      buyPosition: config.buyPosition,
      takeProfit: config.takeProfit,
      stopLoss: config.stopLoss,
      trailingStop: config.trailingStop,
      maxPositions: config.maxPositions,
      maxSinglePct: config.maxSinglePct,
      rebalanceFreq: config.rebalanceFreq,
      enableTiming: config.enableTiming,
      timingConditions: config.timingConditions,
    }
    const r = await strategyApi.create({
      name: strategyName.value,
      code: JSON.stringify(strategyConfig),
      description: `策略编辑器手动配置 | 条件逻辑:${config.conditionLogic} 买入:${config.buyCondition} 止盈:${config.takeProfit}% 止损:${config.stopLoss}%`,
      tags: ['策略编辑器'],
    })
    if (r.data.id) { alert('✅ 策略已保存'); store.setError(null) }
  } catch (e: any) {
    store.setError(e?.response?.data?.detail || '保存失败')
  }
}

function loadStrategy() { window.location.href = '/strategies' }
</script>

<style scoped>
.builder-view { max-width: 100%; }

/* 顶部工具栏 */
.builder-toolbar { display: flex; align-items: center; padding: 10px 20px; }
.toolbar-left { display: flex; align-items: center; gap: 12px; }
.name-input { max-width: 160px; padding: 6px 10px; font-size: 28px; border: none; background: transparent; color: var(--text); border-bottom: 1px solid var(--border); }
.name-input:focus { outline: none; border-color: var(--primary); }
.toolbar-action { font-size: 26px; color: var(--text-muted); cursor: pointer; }
.toolbar-action a { color: inherit; text-decoration: none; }
.toolbar-action:hover { color: var(--text-secondary); }

/* 步骤导航 */
.step-nav { display: flex; margin-bottom: 16px; padding: 0; }
.step-item { flex: 1; text-align: center; padding: 12px; cursor: pointer; color: var(--text-muted); border-bottom: 2px solid transparent; font-size: 28px; transition: all .2s; text-decoration: none; }
.step-item:hover { color: var(--text-secondary); }
.step-item.active { color: var(--primary); border-bottom-color: var(--primary); }

/* 股票池 */
.pool-section { display: flex; flex-direction: column; gap: 8px; padding: 16px 20px; margin-bottom: 16px; }
.pool-label { font-size: 28px; font-weight: 500; }
.pool-controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 26px; color: var(--text-secondary); }
.pool-controls .input { width: auto; padding: 8px 12px; font-size: 24px; min-height: 40px; }

/* 左右两栏布局 */
.screen-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }

/* 指标面板 */
.factor-panel { display: flex; flex-direction: column; min-height: 400px; }
.panel-header { display: flex; align-items: center; padding-bottom: 12px; border-bottom: 1px solid var(--border); margin-bottom: 12px; }
.panel-title { font-size: 28px; font-weight: 600; white-space: nowrap; }
.factor-list { flex: 1; overflow-y: auto; max-height: 500px; }
.factor-category { margin-bottom: 4px; }
.cat-title { font-size: 26px; font-weight: 500; color: var(--text-muted); cursor: pointer; padding: 6px 8px; border-radius: 4px; }
.cat-title:hover { background: rgba(255,255,255,0.03); }
.cat-items { display: flex; flex-direction: column; gap: 2px; padding-left: 16px; }
.factor-item { font-size: 26px; color: var(--text-secondary); padding: 6px 10px; border-radius: 4px; cursor: pointer; transition: all .15s; }
.factor-item:hover { background: rgba(56,189,248,0.08); color: var(--primary); }

/* 条件面板 */
.filter-panel { display: flex; flex-direction: column; min-height: 400px; }
.filter-tabs { display: flex; gap: 0; }
.filter-tab { padding: 8px 16px; cursor: pointer; font-size: 26px; color: var(--text-muted); border-bottom: 2px solid transparent; }
.filter-tab.active { color: var(--primary); border-bottom-color: var(--primary); }
.filter-tab .badge { margin-left: 4px; background: var(--primary); color: var(--bg-main); padding: 1px 6px; border-radius: 8px; font-size: 22px; }

.logic-toggle { display: flex; margin-left: auto; border: 1px solid var(--border); border-radius: 4px; overflow: hidden; }
.logic-btn { padding: 4px 12px; font-size: 24px; cursor: pointer; color: var(--text-muted); }
.logic-btn.active { background: var(--primary); color: var(--bg-main); }

/* 条件表格 */
.condition-table { flex: 1; }
.condition-header { display: flex; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 24px; color: var(--text-muted); font-weight: 500; }
.condition-row { display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.03); font-size: 26px; }
.condition-empty { padding: 40px 20px; text-align: center; color: var(--text-muted); font-size: 26px; }
.col-name { flex: 2.5; }
.col-operator { flex: 1.5; }
.col-range { flex: 1.5; }
.col-value { flex: 2; }
.col-action { flex: 0.8; text-align: center; }
.btn-del { background: none; border: none; color: var(--danger); cursor: pointer; font-size: 28px; padding: 2px 6px; }

/* 交易模型 */
.trading-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.trading-section h3 { font-size: 30px; margin-bottom: 12px; color: var(--text-secondary); }
.trading-section label { display: block; margin-bottom: 8px; font-size: 26px; color: var(--text-secondary); }

/* 底部 */
.bottom-bar { display: flex; gap: 12px; justify-content: center; margin-top: 24px; padding: 16px; }

/* 结果展示区 */
.result-section { margin-top: 16px; }
.result-subtitle { font-size: 22px; color: var(--text-muted); font-weight: 400; margin-left: 8px; }
.result-metrics { display: flex; flex-wrap: wrap; gap: 12px; }
.result-metric { flex: 1; min-width: 120px; padding: 12px 16px; background: var(--bg-main); border-radius: var(--radius-md); text-align: center; }
.metric-label { display: block; font-size: 22px; color: var(--text-muted); margin-bottom: 4px; }
.metric-value { font-size: 28px; font-weight: 700; color: var(--text-primary); }
.text-up { color: var(--up); }
.text-down { color: var(--down); }

/* 选股结果表格 */
.picks-table { width: 100%; }
.picks-header { display: flex; padding: 10px 0; border-bottom: 2px solid var(--border); font-size: 24px; color: var(--text-muted); font-weight: 500; }
.picks-row { display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(0,0,0,0.04); font-size: 26px; transition: background 0.15s; }
.picks-row:hover { background: var(--bg-card-hover); }
.picks-col-code { flex: 1.2; font-family: monospace; }
.picks-col-name { flex: 2; }
.picks-col-price { flex: 1; text-align: right; }
.picks-col-change { flex: 1; text-align: right; font-weight: 600; }

.disclaimer { margin-top: 24px; padding: 16px 20px; font-size: 24px; line-height: 1.8; color: var(--text-muted); background: rgba(255,255,255,0.02); }
.disclaimer p { margin-bottom: 4px; }
.disclaimer strong { color: var(--warning); }
</style>