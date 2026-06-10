<template>
  <div class="analyze-view">
    <h1 class="page-title">📈 单股量化分析</h1>
    <p class="page-subtitle">输入股票代码，获取28因子量化诊断报告</p>

    <!-- 搜索区 -->
    <div class="search-card card">
      <div class="search-form">
        <input
          v-model="symbolInput"
          type="text"
          class="input"
          placeholder="输入股票代码（如 600036）或名称..."
          @keyup.enter="handleAnalyze"
        />
        <button class="btn btn-primary" @click="handleAnalyze" :disabled="loading">
          {{ loading ? '⏳ 分析中...' : '🔍 开始分析' }}
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>正在分析 {{ symbolInput }} ...</p>
    </div>

    <!-- K线图区 -->
    <div v-if="klineData && klineData.klines && klineData.klines.length > 0" class="card" style="margin-bottom: var(--space-lg);">
      <h2 class="card-title">📊 K线走势 ({{ klineData.name }})</h2>
      <div ref="klineChartRef" style="width: 100%; height: 480px;"></div>
    </div>

    <!-- 结果区 -->
    <template v-else-if="result">
      <!-- 指标卡 -->
      <div class="metric-grid">
        <div class="metric-card card-wide">
          <div class="metric-value stock-name">{{ result.name }}</div>
          <div class="metric-label">{{ result.symbol }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" :class="result.change_pct >= 0 ? 'positive' : 'negative'">
            {{ result.change_pct >= 0 ? '+' : '' }}{{ result.change_pct }}%
          </div>
          <div class="metric-label">涨跌幅</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{{ result.total_score }}</div>
          <div class="metric-label">综合评分</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">
            <span class="badge" :class="getScoreBadge(result.total_score)">{{ result.rating }}</span>
          </div>
          <div class="metric-label">评级</div>
        </div>
      </div>

      <!-- 操作建议 -->
      <div class="card">
        <h2 class="card-title">📊 量化分析报告</h2>

        <div class="recommendation-box card" style="margin-bottom: 0; background: rgba(56,189,248,0.05); border-color: rgba(56,189,248,0.2);">
          <div class="flex items-center gap-md">
            <span class="badge badge-primary">操作建议</span>
            <span style="font-size: 30px;">{{ result.recommendation }}</span>
          </div>
        </div>

        <!-- 信号摘要 -->
        <div v-if="result.signal_summary" class="section">
          <div class="signal-summary">{{ result.signal_summary }}</div>
        </div>

        <!-- 买卖触发条件 -->
        <div v-if="result.triggers" class="section">
          <h3 class="section-title">🎯 量化操作条件</h3>
          <div class="triggers-grid">
            <div v-if="result.triggers.buy_condition" class="trigger-item trigger-buy">
              <span class="trigger-label">🟢 买入触发</span>
              <span class="trigger-text">{{ result.triggers.buy_condition }}</span>
            </div>
            <div v-if="result.triggers.stop_condition" class="trigger-item trigger-stop">
              <span class="trigger-label">🔴 止损条件</span>
              <span class="trigger-text">{{ result.triggers.stop_condition }}</span>
            </div>
            <div v-if="result.triggers.invalidate_condition" class="trigger-item trigger-invalid">
              <span class="trigger-label">🚫 剔除条件</span>
              <span class="trigger-text">{{ result.triggers.invalidate_condition }}</span>
            </div>
            <div v-if="result.triggers.target1" class="trigger-item trigger-target">
              <span class="trigger-label">🎯 第一目标</span>
              <span class="trigger-text">{{ result.triggers.target1 }}</span>
            </div>
            <div v-if="result.triggers.target2" class="trigger-item trigger-target">
              <span class="trigger-label">🎯 第二目标</span>
              <span class="trigger-text">{{ result.triggers.target2 }}</span>
            </div>
          </div>
        </div>

        <!-- 因子分布 -->
        <div class="section">
          <h3 class="section-title">📊 因子信号分布</h3>
          <div class="factor-bars">
            <div v-for="(count, signal) in result.factor_distribution" :key="signal" class="factor-bar">
              <span class="factor-label">{{ factorSignalLabel(signal) }}</span>
              <div class="progress-track" style="flex: 1; margin: 0 12px;">
                <div class="progress-fill" :class="signalClass(signal)" :style="{ width: (count / 28 * 100) + '%' }"></div>
              </div>
              <span class="factor-count">{{ count }}/28</span>
            </div>
          </div>
        </div>

        <!-- 各维度因子展开 -->
        <div v-if="result.dimensions && result.dimensions.length" class="section">
          <h3 class="section-title">📊 五维度因子深度分析</h3>
          <div class="dimension-tabs">
            <button
              v-for="(dim, idx) in result.dimensions"
              :key="idx"
              class="dimension-tab"
              :class="{ active: activeDim === idx }"
              @click="activeDim = idx"
            >
              {{ dim.name }}
              <span class="dim-score-badge" :class="getScoreBadge(dim.total_score)">
                {{ dim.total_score }}
              </span>
            </button>
          </div>

          <!-- 当前维度详情 -->
          <div v-if="result.dimensions[activeDim]" class="dimension-panel">
            <div class="dim-summary">{{ result.dimensions[activeDim].summary }}</div>

            <!-- 所有因子列表 -->
            <div class="factors-list">
              <div v-for="(factor, fidx) in result.dimensions[activeDim].factors" :key="fidx" class="factor-item">
                <div class="factor-header">
                  <span class="factor-name">{{ factor.name }}</span>
                  <span class="factor-score" :class="factorScoreClass(factor.signal)">
                    {{ factor.score }}
                  </span>
                  <span class="factor-signal" :class="factorSignalBadge(factor.signal)">
                    {{ signalLabel(factor.signal) }}
                  </span>
                </div>
                <div class="factor-detail">{{ factor.detail }}</div>
              </div>
            </div>

            <!-- 优势/劣势因子 -->
            <div v-if="result.dimensions[activeDim].strengths?.length || result.dimensions[activeDim].weaknesses?.length" class="strength-weakness">
              <div v-if="result.dimensions[activeDim].strengths?.length" class="strength-section">
                <span class="sw-label sw-strength">✅ 优势因子</span>
                <span v-for="(s, si) in result.dimensions[activeDim].strengths" :key="si" class="sw-item sw-item-strength">{{ s }}</span>
              </div>
              <div v-if="result.dimensions[activeDim].weaknesses?.length" class="weakness-section">
                <span class="sw-label sw-weakness">⚠️ 劣势因子</span>
                <span v-for="(w, wi) in result.dimensions[activeDim].weaknesses" :key="wi" class="sw-item sw-item-weakness">{{ w }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 风险指标 -->
        <div class="section">
          <h3 class="section-title">风险指标</h3>
          <div class="metric-grid" style="margin-bottom: 0;">
            <div v-for="item in riskMetricsList" :key="item.key" class="metric-card" style="padding: var(--space-md);">
              <div class="metric-label" style="font-size: 24px;">{{ item.label }}</div>
              <div class="metric-value" style="font-size: 40px; margin-top: 4px;">{{ item.value }}</div>
            </div>
          </div>
        </div>

        <!-- 技术指标快照 -->
        <div v-if="result.tech_snapshot && Object.keys(result.tech_snapshot).length" class="section">
          <h3 class="section-title">📡 技术指标快照</h3>
          <div class="tech-grid">
            <div v-for="(val, key) in result.tech_snapshot" :key="key" class="tech-item">
              <span class="tech-key">{{ key }}</span>
              <span class="tech-val">{{ formatTechValue(val) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <div class="empty-state-icon">📊</div>
      <p>👆 输入股票代码，点击「开始分析」获取28因子量化报告</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { quantApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { AnalysisResult } from '@/stores/app'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const route = useRoute()
const store = useAppStore()

const symbolInput = ref('')
const loading = ref(false)
const result = ref<AnalysisResult | null>(null)
const activeDim = ref(0)
const klineData = ref<any>(null)
const klineChartRef = ref<HTMLElement | null>(null)
let klineChart: echarts.ECharts | null = null

const riskMetricsList = computed(() => {
  if (!result.value?.risk_metrics) return []
  const map: Record<string, string> = {
    max_drawdown: '最大回撤',
    sharpe_ratio: '夏普比率',
    volatility: '波动率',
    beta: 'Beta系数',
    var_95: 'VaR(95%)'
  }
  return Object.entries(result.value.risk_metrics).map(([key, value]) => ({
    key,
    label: map[key] || key.replace(/_/g, ' '),
    value: formatMetricValue(value)
  }))
})

async function handleAnalyze() {
  const input = symbolInput.value.trim()
  if (!input) {
    store.setError('请输入股票代码')
    return
  }

  loading.value = true
  result.value = null
  klineData.value = null

  // 并行获取量化分析和K线数据
  try {
    const [analyzeRes, klineRes] = await Promise.all([
      quantApi.analyze({ symbol: input }),
      fetch(`/api/v1/quant/kline?symbol=${input}&period=day&count=120`).then(r => r.json()),
    ])
    result.value = analyzeRes.data
    klineData.value = klineRes
    activeDim.value = 0
    store.setAnalysisResult(analyzeRes.data)

    await nextTick()
    renderKlineChart()
  } catch (err: any) {
    console.error('[AnalyzeView] analyze error:', err.response?.status, err.response?.data)
    store.setError(err.response?.data?.detail || '分析失败，请检查股票代码')
  } finally {
    loading.value = false
  }
}

function renderKlineChart() {
  if (!klineChartRef.value || !klineData.value?.klines?.length) return

  if (klineChart) klineChart.dispose()
  klineChart = echarts.init(klineChartRef.value)

  const d = klineData.value
  const dates = d.klines.map((k: any) => k[0])
  const ohlc = d.klines.map((k: any) => [k[1], k[2], k[3], k[4]])
  const vols = d.klines.map((k: any) => k[5])

  // 计算vol颜色
  const volColors = d.klines.map((k: any) => (k[2] >= k[1] ? '#ef4444' : '#22c55e'))

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: ['K线', 'MA5', 'MA10', 'MA20', 'MA60', '成交量'],
      textStyle: { fontSize: 18, color: 'var(--text-secondary)' },
      top: 0,
    },
    grid: [
      { left: '6%', right: '6%', top: '10%', height: '55%' },
      { left: '6%', right: '6%', top: '73%', height: '20%' },
    ],
    xAxis: [
      {
        type: 'category', data: dates, gridIndex: 0,
        axisLabel: { fontSize: 14, color: 'var(--text-secondary)', interval: Math.floor(dates.length / 10) },
        axisLine: { lineStyle: { color: 'var(--border)' } },
      },
      {
        type: 'category', data: dates, gridIndex: 1,
        axisLabel: { show: false },
        axisLine: { lineStyle: { color: 'var(--border)' } },
      },
    ],
    yAxis: [
      {
        type: 'value', gridIndex: 0, scale: true,
        splitLine: { lineStyle: { color: 'var(--border)', opacity: 0.3 } },
        axisLabel: { fontSize: 14, color: 'var(--text-secondary)' },
      },
      {
        type: 'value', gridIndex: 1,
        splitLine: { show: false },
        axisLabel: { fontSize: 12, color: 'var(--text-secondary)', formatter: (v: number) => v >= 10000 ? (v / 10000).toFixed(0) + '万' : String(v) },
      },
    ],
    series: [
      {
        name: 'K线', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: { color: '#ef4444', color0: '#22c55e', borderColor: '#ef4444', borderColor0: '#22c55e' },
        data: ohlc,
      },
      {
        name: 'MA5', type: 'line', xAxisIndex: 0, yAxisIndex: 0,
        symbol: 'none', lineStyle: { width: 1.5, color: '#f59e0b' },
        data: d.ma5,
      },
      {
        name: 'MA10', type: 'line', xAxisIndex: 0, yAxisIndex: 0,
        symbol: 'none', lineStyle: { width: 1.5, color: '#3b82f6' },
        data: d.ma10,
      },
      {
        name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0,
        symbol: 'none', lineStyle: { width: 1.5, color: '#8b5cf6' },
        data: d.ma20,
      },
      {
        name: 'MA60', type: 'line', xAxisIndex: 0, yAxisIndex: 0,
        symbol: 'none', lineStyle: { width: 1.5, color: '#ec4899' },
        data: d.ma60,
      },
      {
        name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1,
        itemStyle: { color: (p: any) => volColors[p.dataIndex] },
        data: vols,
      },
    ],
  }

  klineChart.setOption(option)
  klineChart.resize()
}

// 响应式调整
function handleResize() {
  if (klineChart) klineChart.resize()
}
onMounted(() => {
  window.addEventListener('resize', handleResize)
  if (route.query.symbol) {
    symbolInput.value = String(route.query.symbol)
  }
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (klineChart) { klineChart.dispose(); klineChart = null }
})

function getScoreBadge(score: number): string {
  if (score >= 80) return 'badge-success'
  if (score >= 60) return 'badge-warning'
  return 'badge-danger'
}

function signalClass(signal: string): string {
  const s = signal.toLowerCase()
  if (s.includes('多头') || s.includes('买入') || s.includes('看涨')) return 'success'
  if (s.includes('空头') || s.includes('卖出') || s.includes('看跌')) return 'danger'
  if (s.includes('中性')) return 'neutral'
  return 'primary'
}

function factorScoreClass(signal: string): string {
  const s = signal.toLowerCase()
  if (s === 'bullish') return 'score-bullish'
  if (s === 'bearish') return 'score-bearish'
  return 'score-neutral'
}

function factorSignalBadge(signal: string): string {
  const s = signal.toLowerCase()
  if (s === 'bullish') return 'sig-bullish'
  if (s === 'bearish') return 'sig-bearish'
  return 'sig-neutral'
}

function signalLabel(signal: string): string {
  const s = signal.toLowerCase()
  if (s === 'bullish') return '🔴 看涨'
  if (s === 'bearish') return '🟢 看跌'
  return '➖ 中性'
}

function factorSignalLabel(signal: string): string {
  const s = signal.toLowerCase()
  if (s.includes('bullish') || s.includes('看涨') || s.includes('买入') || s.includes('多头')) return '🟢 看涨信号'
  if (s.includes('bearish') || s.includes('看跌') || s.includes('卖出') || s.includes('空头')) return '🔴 看跌信号'
  return '⚪ 中性信号'
}

function formatMetricValue(value: any): string {
  if (typeof value === 'number') {
    if (Math.abs(value) < 1 && value !== 0) return value.toFixed(4)
    return value.toFixed(2)
  }
  return String(value)
}

function formatTechValue(val: any): string {
  if (typeof val === 'number') return val.toFixed(2)
  if (typeof val === 'string') return val
  return JSON.stringify(val)
}
</script>

<style scoped>
.analyze-view {
}

.search-card .search-form {
  display: flex;
  gap: var(--space-md);
  align-items: center;
}

.search-form .input {
  flex: 1;
  min-width: 0;
}

/* 信号摘要 */
.signal-summary {
  background: rgba(56,189,248,0.03);
  border: 1px solid rgba(56,189,248,0.1);
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 28px;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* 触发条件 */
.triggers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 8px;
}

.trigger-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.05);
}

.trigger-buy { background: rgba(5,150,105,0.08); border-color: rgba(5,150,105,0.2); }
.trigger-stop { background: rgba(220,38,38,0.08); border-color: rgba(220,38,38,0.2); }
.trigger-invalid { background: rgba(245,158,11,0.08); border-color: rgba(245,158,11,0.2); }
.trigger-target { background: rgba(37,99,235,0.08); border-color: rgba(37,99,235,0.2); }

.trigger-label {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-muted);
}

.trigger-text {
  font-size: 26px;
  color: var(--text-secondary);
  line-height: 1.4;
}

/* 通用 section */
.section {
  margin-top: var(--space-xl);
}

.section-title {
  font-size: 32px;
  margin-bottom: var(--space-md);
  color: var(--text-secondary);
}

/* 维度选项卡 */
.dimension-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.dimension-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
  color: var(--text-secondary);
  font-size: 26px;
  cursor: pointer;
  transition: all 0.2s;
}

.dimension-tab:hover { border-color: rgba(56,189,248,0.3); }
.dimension-tab.active {
  border-color: var(--primary);
  background: rgba(56,189,248,0.08);
  color: var(--text);
}

.dim-score-badge {
  font-size: 22px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.dimension-panel {
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  padding: 16px;
}

.dim-summary {
  font-size: 28px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  padding: 8px 12px;
  background: rgba(255,255,255,0.02);
  border-radius: 6px;
}

/* 因子列表 */
.factors-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.factor-item {
  padding: 10px 14px;
  border-radius: 6px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
}

.factor-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.factor-name {
  font-size: 26px;
  font-weight: 500;
  color: var(--text);
  flex: 1;
  min-width: 100px;
}

.factor-score {
  font-size: 28px;
  font-weight: 700;
  min-width: 40px;
  text-align: right;
}

.score-bullish { color: var(--up); }
.score-bearish { color: var(--down); }
.score-neutral { color: #f59e0b; }

.factor-signal {
  font-size: 22px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.sig-bullish { background: rgba(239,68,68,0.1); color: #ef4444; }
.sig-bearish { background: rgba(34,197,94,0.1); color: #22c55e; }
.sig-neutral { background: rgba(245,158,11,0.1); color: #f59e0b; }

.factor-detail {
  margin-top: 6px;
  font-size: 24px;
  color: var(--text-muted);
  line-height: 1.5;
}

/* 优势/劣势因子 */
.strength-weakness {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.strength-section, .weakness-section {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.sw-label { font-size: 24px; font-weight: 600; margin-right: 4px; }
.sw-strength { color: #10b981; }
.sw-weakness { color: #ef4444; }

.sw-item {
  font-size: 24px;
  padding: 3px 10px;
  border-radius: 4px;
}

.sw-item-strength { background: rgba(16,185,129,0.08); color: #34d399; }
.sw-item-weakness { background: rgba(239,68,68,0.08); color: #f87171; }

/* 技术指标 */
.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}

.tech-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  border-radius: 6px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
}

.tech-key {
  font-size: 22px;
  color: var(--text-muted);
}

.tech-val {
  font-size: 28px;
  font-weight: 600;
  color: var(--text);
}

/* 因子信号条 */
.factor-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.factor-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.factor-label {
  font-size: 26px;
  color: var(--text-secondary);
  min-width: 80px;
}

.factor-count {
  font-size: 24px;
  color: var(--text-muted);
  min-width: 40px;
  text-align: right;
}

.recommendation-box p {
  font-size: 30px;
}

/* 股票名称跨列显示 */
.card-wide {
  grid-column: span 2;
}

.stock-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 48px;
}
</style>