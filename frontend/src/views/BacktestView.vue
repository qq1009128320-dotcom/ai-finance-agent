<template>
  <div class="backtest-view">
    <h1 class="page-title">📊 策略回测</h1>
    <p class="page-subtitle">配置回测参数，验证策略历史表现</p>

    <!-- 回测配置 -->
    <div class="backtest-card card">
      <h2 class="card-title">⚙️ 回测配置</h2>

      <div class="form-group">
        <label>策略代码</label>
        <textarea v-model="code" class="code-input" rows="10" placeholder="粘贴策略代码..."></textarea>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>回测标的</label>
          <input v-model="symbol" type="text" class="input" placeholder="如 600036" />
        </div>
        <div class="form-group">
          <label>初始资金</label>
          <input v-model.number="initialCapital" type="number" class="input" value="100000" />
        </div>
      </div>

      <div class="btn-group" style="margin-top: var(--space-md);">
        <button class="btn btn-primary" @click="handleRun" :disabled="running" style="flex: 1;">
          {{ running ? '⏳ 回测中...' : '▶ 运行回测' }}
        </button>
        <button class="btn btn-secondary" @click="code = ''">🗑️ 清空</button>
      </div>
    </div>

    <!-- 回测结果 -->
    <div v-if="result" class="result-section">
      <div class="card">
        <h2 class="card-title">📈 回测结果</h2>

        <div style="margin-bottom: var(--space-md);">
          <span class="badge" :class="result.status === 'success' ? 'badge-success' : 'badge-danger'">
            {{ result.status === 'success' ? '✅ 回测成功' : '❌ 回测失败' }}
          </span>
          <p class="text-muted" style="margin-top: var(--space-sm);">{{ result.message }}</p>
        </div>

        <div class="metric-grid">
          <div class="metric-card">
            <div class="metric-value" :class="((result.metrics.total_return ?? 0) >= 0) ? 'positive' : 'negative'">
              {{ result.metrics.total_return != null ? result.metrics.total_return + '%' : 'N/A' }}
            </div>
            <div class="metric-label">总收益率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value" :class="((result.metrics.annual_return ?? 0) >= 0) ? 'positive' : 'negative'">
              {{ result.metrics.annual_return != null ? result.metrics.annual_return + '%' : 'N/A' }}
            </div>
            <div class="metric-label">年化收益</div>
          </div>
          <div class="metric-card">
            <div class="metric-value" :class="((result.metrics.sharpe_ratio ?? 0) >= 1) ? 'positive' : 'negative'">
              {{ result.metrics.sharpe_ratio != null ? result.metrics.sharpe_ratio.toFixed(2) : 'N/A' }}
            </div>
            <div class="metric-label">夏普比率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value" :class="((result.metrics.max_drawdown ?? 0) >= -10) ? 'positive' : 'negative'">
              {{ result.metrics.max_drawdown != null ? result.metrics.max_drawdown + '%' : 'N/A' }}
            </div>
            <div class="metric-label">最大回撤</div>
          </div>
          <div class="metric-card">
            <div class="metric-value" :class="((result.metrics.win_rate ?? 0) >= 50) ? 'positive' : 'negative'">
              {{ result.metrics.win_rate != null ? result.metrics.win_rate + '%' : 'N/A' }}
            </div>
            <div class="metric-label">胜率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ result.metrics.profit_factor != null ? result.metrics.profit_factor.toFixed(2) : 'N/A' }}</div>
            <div class="metric-label">盈亏比</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ result.metrics.total_trades ?? 0 }}</div>
            <div class="metric-label">交易次数</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">¥{{ formatMoney(result.metrics.initial_capital) }}</div>
            <div class="metric-label">初始资金</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">¥{{ formatMoney(result.metrics.final_capital || 0) }}</div>
            <div class="metric-label">最终资金</div>
          </div>
        </div>

        <div class="period-info flex items-center gap-sm" style="margin: var(--space-md) 0; padding: var(--space-sm) 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);">
          <span>📅 {{ result.start_date }}</span>
          <span class="text-muted">→</span>
          <span>📅 {{ result.end_date }}</span>
        </div>

        <!-- 资金曲线图 -->
        <div v-if="result.metrics.equity_curve && result.metrics.equity_curve.length > 10" class="chart-container" style="margin-top: var(--space-lg);">
          <h3 style="font-size: 32px; margin-bottom: var(--space-md); color: var(--text-secondary);">📊 资金曲线 & 回撤</h3>
          <div ref="equityChartRef" style="width: 100%; height: 360px;"></div>
        </div>

        <!-- 交易记录 -->
        <div v-if="result.trades.length > 0" class="trades-table" style="margin-top: var(--space-lg);">
          <h3 style="font-size: 32px; margin-bottom: var(--space-md); color: var(--text-secondary);">交易记录（最近{{ result.trades.length }}笔）</h3>
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>类型</th>
                  <th>标的</th>
                  <th>价格</th>
                  <th>原因</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="trade in result.trades" :key="trade.id || trade.symbol + trade.price">
                  <td>
                    <span class="badge" :class="trade.type === 'buy' ? 'badge-success' : 'badge-danger'">
                      {{ trade.type === 'buy' ? '买入' : '卖出' }}
                    </span>
                  </td>
                  <td style="font-family: 'Fira Code', monospace;">{{ trade.symbol }}</td>
                  <td>¥{{ trade.price }}</td>
                  <td>{{ trade.reason }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { backtestApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { BacktestResult } from '@/stores/app'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const store = useAppStore()

const code = ref('')
const symbol = ref('')
const initialCapital = ref(100000)
const running = ref(false)
const result = ref<BacktestResult | null>(null)
const equityChartRef = ref<HTMLElement | null>(null)
let equityChart: echarts.ECharts | null = null

onMounted(() => {
  if (store.generatedCode) {
    code.value = store.generatedCode
  }
})

onUnmounted(() => {
  if (equityChart) {
    equityChart.dispose()
    equityChart = null
  }
})

function renderEquityChart() {
  if (!result.value?.metrics?.equity_curve || !equityChartRef.value) return
  
  const curve = result.value.metrics.equity_curve
  
  // 过滤掉无效数据点
  const validPoints = curve.filter(p => p.value != null && p.date)
  if (validPoints.length < 2) return

  if (!equityChart) {
    equityChart = echarts.init(equityChartRef.value)
  }

  const dates = validPoints.map(p => p.date)
  const values = validPoints.map(p => p.value)
  const drawdowns = validPoints.map(p => p.drawdown)

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        const p = params[0]
        const dd = params[1]
        return `
          <div style="font-size: 20px; margin-bottom: 8px;">${p.axisValue}</div>
          <div style="color: var(--primary); font-size: 22px; font-weight: 600;">
            ${p.seriesName}: ¥${p.value.toLocaleString()}
          </div>
          <div style="color: var(--danger); font-size: 18px;">
            回撤: ${dd.value}%
          </div>
        `
      }
    },
    legend: {
      data: ['资金曲线', '回撤'],
      textStyle: { fontSize: 20, color: 'var(--text-secondary)' },
      top: 10
    },
    grid: {
      left: '8%',
      right: '8%',
      bottom: '18%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: {
        fontSize: 18,
        color: 'var(--text-secondary)',
        interval: Math.floor(dates.length / 15),
        rotate: dates.length > 50 ? 30 : 0,
        margin: 12
      },
      axisLine: {
        lineStyle: { color: 'var(--border)' }
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '资金',
        nameTextStyle: { fontSize: 20, color: 'var(--text-secondary)' },
        axisLabel: {
          fontSize: 18,
          color: 'var(--text-secondary)',
          formatter: (val: number) => '¥' + (val / 10000).toFixed(0) + '万'
        },
        splitLine: {
          lineStyle: { color: 'var(--border)', opacity: 0.3 }
        }
      },
      {
        type: 'value',
        name: '回撤%',
        nameTextStyle: { fontSize: 20, color: 'var(--danger)' },
        axisLabel: {
          fontSize: 18,
          color: 'var(--danger)',
          formatter: (val: number) => val + '%'
        },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '资金曲线',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 3, color: 'var(--primary)' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(56, 189, 248, 0.3)' },
            { offset: 1, color: 'rgba(56, 189, 248, 0.05)' }
          ])
        },
        data: values
      } as any,
      {
        name: '回撤',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: 'var(--danger)' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(239, 68, 68, 0.15)' },
            { offset: 1, color: 'rgba(239, 68, 68, 0.02)' }
          ])
        },
        data: drawdowns
      } as any
    ]
  }

  equityChart.setOption(option)
}

async function handleRun() {
  if (!code.value.trim()) {
    store.setError('请输入策略代码')
    return
  }
  if (!symbol.value.trim()) {
    store.setError('请输入回测标的')
    return
  }

  running.value = true
  result.value = null
  
  // 清除旧图表
  if (equityChart) {
    equityChart.dispose()
    equityChart = null
  }

  try {
    const response = await backtestApi.run({
      code: code.value,
      symbol: symbol.value,
      initial_capital: initialCapital.value
    })
    result.value = response.data
    store.setBacktestResult(response.data)
    
    // 渲染资金曲线图
    setTimeout(() => {
      renderEquityChart()
    }, 100)
  } catch (err: any) {
    store.setError(err.response?.data?.detail || '回测失败')
  } finally {
    running.value = false
  }
}

function formatMoney(value: number): string {
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}

// 响应式处理
window.addEventListener('resize', () => {
  if (equityChart) {
    equityChart.resize()
  }
})
</script>

<style scoped>
.backtest-view {
  max-width: 1600px;
}

.backtest-card {
  margin-bottom: var(--space-lg);
}

.code-input {
  width: 100%;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 26px;
  line-height: 1.8;
  resize: vertical;
}

.code-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
}

.result-section {
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.period-info span {
  font-size: 28px;
}

.chart-container {
  padding: var(--space-md);
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
}

:deep(.echarts-tooltip-doms) {
  font-size: 18px !important;
}
</style>
