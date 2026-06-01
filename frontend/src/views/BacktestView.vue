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

        <!-- 交易记录 -->
        <div v-if="result.trades.length > 0" class="trades-table">
          <h3 style="font-size: 16px; margin-bottom: var(--space-md); color: var(--text-secondary);">交易记录（最近{{ result.trades.length }}笔）</h3>
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
                <tr v-for=" trade in result.trades" :key="trade.id || trade.symbol + trade.price">
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

onMounted(() => {
  if (store.generatedCode) {
    code.value = store.generatedCode
  }
})

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
  font-size: 13px;
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
  font-size: 14px;
}
</style>
