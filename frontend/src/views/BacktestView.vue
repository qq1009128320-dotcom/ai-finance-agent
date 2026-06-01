<template>
  <div class="backtest-view">
    <h1 class="page-title">📊 策略回测</h1>

    <div class="backtest-card card">
      <h2>回测配置</h2>
      
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

      <button class="btn btn-primary" @click="handleRun" :disabled="running">
        {{ running ? '回测中...' : '运行回测' }}
      </button>
    </div>

    <div v-if="result" class="result-section">
      <div class="card">
        <h2>回测结果</h2>
        
        <div class="status-badge" :class="result.status">
          {{ result.status === 'success' ? '✅ 回测成功' : '❌ 回测失败' }}
        </div>

        <p class="message">{{ result.message }}</p>

        <div class="metric-grid">
          <div class="metric-card">
            <div class="metric-value" :class="result.metrics.total_return >= 0 ? 'positive' : 'negative'">
              {{ result.metrics.total_return }}%
            </div>
            <div class="metric-label">总收益率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ result.metrics.total_trades }}</div>
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

        <div class="period-info">
          <span>📅 {{ result.start_date }}</span>
          <span>→</span>
          <span>📅 {{ result.end_date }}</span>
        </div>

        <!-- 交易记录 -->
        <div v-if="result.trades.length > 0" class="trades-table">
          <h3>交易记录（最近{{ result.trades.length }}笔）</h3>
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
              <tr v-for="(trade, i) in result.trades" :key="i">
                <td>
                  <span :class="trade.type === 'buy' ? 'trade-buy' : 'trade-sell'">
                    {{ trade.type === 'buy' ? '买入' : '卖出' }}
                  </span>
                </td>
                <td>{{ trade.symbol }}</td>
                <td>¥{{ trade.price }}</td>
                <td>{{ trade.reason }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { backtestApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { BacktestResult } from '@/stores/app'

const store = useAppStore()

const code = ref('')
const symbol = ref('')
const initialCapital = ref(100000)
const running = ref(false)
const result = ref<BacktestResult | null>(null)

// 从store加载已生成的代码
onMounted(() => {
  if (store.generatedCode) {
    code.value = store.generatedCode
  }
})

async function handleRun() {
  if (!code.value.trim()) {
    alert('请输入策略代码')
    return
  }
  if (!symbol.value.trim()) {
    alert('请输入回测标的')
    return
  }

  running.value = true
  result.value = null

  try {
    const response = await backtestApi.run({
      code: code.value,
      symbol: symbol.value,
      initial_capital: initialCapital.value
    })

    result.value = response.data
    store.setBacktestResult(response.data)
  } catch (err: any) {
    store.setError(err.response?.data?.detail || '回测失败')
  } finally {
    running.value = false
  }
}

function formatMoney(value: number): string {
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}
</script>

<style scoped>
.backtest-view {
  max-width: 1200px;
}

.page-title {
  font-size: 28px;
  margin-bottom: 24px;
}

.backtest-card {
  margin-bottom: 24px;
}

.backtest-card h2 {
  font-size: 18px;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 14px;
}

.code-input {
  width: 100%;
  padding: 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  background: var(--bg-dark);
  color: var(--text-primary);
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.8;
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.result-section {
  margin-top: 24px;
}

.result-section h2 {
  font-size: 18px;
  margin-bottom: 16px;
}

.status-badge {
  display: inline-block;
  padding: 8px 16px;
  border-radius: var(--radius);
  font-weight: 600;
  margin-bottom: 12px;
}

.status-badge.success {
  background: rgba(16, 185, 129, 0.2);
  color: var(--success);
}

.status-badge.error {
  background: rgba(239, 68, 68, 0.2);
  color: var(--danger);
}

.message {
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.period-info {
  color: var(--text-muted);
  font-size: 13px;
  margin-top: 16px;
}

.trades-table {
  margin-top: 24px;
}

.trades-table h3 {
  font-size: 16px;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.trade-buy {
  color: var(--success);
  font-weight: 600;
}

.trade-sell {
  color: var(--danger);
  font-weight: 600;
}

.positive { color: var(--success) !important; }
.negative { color: var(--danger) !important; }
</style>
