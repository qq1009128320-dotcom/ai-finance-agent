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

    <!-- 结果区 -->
    <template v-else-if="result">
      <!-- 指标卡 -->
      <div class="metric-grid">
        <div class="metric-card">
          <div class="metric-value">{{ result.name }}</div>
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

      <!-- 分析报告 -->
      <div class="card">
        <h2 class="card-title">📊 量化分析报告</h2>

        <div class="recommendation-box card" style="margin-bottom: 0; background: rgba(56,189,248,0.05); border-color: rgba(56,189,248,0.2);">
          <div class="flex items-center gap-md">
            <span class="badge badge-primary">操作建议</span>
            <span style="font-size: 15px;">{{ result.recommendation }}</span>
          </div>
        </div>

        <!-- 因子分布 -->
        <div class="factor-distribution" style="margin-top: var(--space-xl);">
          <h3 style="font-size: 16px; margin-bottom: var(--space-md); color: var(--text-secondary);">因子信号分布</h3>
          <div class="factor-bars">
            <div v-for="(count, signal) in result.factor_distribution" :key="signal" class="factor-bar">
              <span class="factor-label">{{ signal }}</span>
              <div class="progress-track" style="flex: 1; margin: 0 12px;">
                <div class="progress-fill" :class="signalClass(signal)" :style="{ width: (count / 28 * 100) + '%' }"></div>
              </div>
              <span class="factor-count">{{ count }}/28</span>
            </div>
          </div>
        </div>

        <!-- 风险指标 -->
        <div class="risk-metrics" style="margin-top: var(--space-xl);">
          <h3 style="font-size: 16px; margin-bottom: var(--space-md); color: var(--text-secondary);">风险指标</h3>
          <div class="metric-grid" style="margin-bottom: 0;">
            <div v-for="item in riskMetricsList" :key="item.key" class="metric-card" style="padding: var(--space-md);">
              <div class="metric-label" style="font-size: 12px;">{{ item.label }}</div>
              <div class="metric-value" style="font-size: 20px; margin-top: 4px;">{{ item.value }}</div>
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
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { quantApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { AnalysisResult } from '@/stores/app'

const route = useRoute()
const store = useAppStore()

const symbolInput = ref('')
const loading = ref(false)
const result = ref<AnalysisResult | null>(null)

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

onMounted(() => {
  if (route.query.symbol) {
    symbolInput.value = String(route.query.symbol)
  }
})

async function handleAnalyze() {
  if (!symbolInput.value.trim()) {
    store.setError('请输入股票代码')
    return
  }

  loading.value = true
  result.value = null

  try {
    const response = await quantApi.analyze({ symbol: symbolInput.value })
    result.value = response.data
    store.setAnalysisResult(response.data)
  } catch (err: any) {
    store.setError(err.response?.data?.detail || '分析失败，请检查股票代码')
  } finally {
    loading.value = false
  }
}

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

function formatMetricValue(value: any): string {
  if (typeof value === 'number') {
    if (Math.abs(value) < 1 && value !== 0) return value.toFixed(4)
    return value.toFixed(2)
  }
  return String(value)
}
</script>

<style scoped>
.analyze-view {
  max-width: 1400px;
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
  font-size: 13px;
  color: var(--text-secondary);
  min-width: 80px;
}

.factor-count {
  font-size: 12px;
  color: var(--text-muted);
  min-width: 40px;
  text-align: right;
}

.recommendation-box p {
  font-size: 15px;
}
</style>
