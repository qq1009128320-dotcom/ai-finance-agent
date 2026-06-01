<template>
  <div class="analyze-view">
    <h1 class="page-title">📊 单股量化分析</h1>
    
    <!-- 搜索区 -->
    <div class="search-card card">
      <div class="search-form">
        <input
          v-model="symbolInput"
          type="text"
          class="input"
          placeholder="输入股票代码（如 600036）或名称"
          @keyup.enter="handleAnalyze"
        />
        <button class="btn btn-primary" @click="handleAnalyze" :disabled="loading">
          {{ loading ? '分析中...' : '开始分析' }}
        </button>
      </div>
    </div>

    <!-- 结果区 -->
    <template v-if="result">
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
            <span :class="getScoreClass(result.total_score)">{{ result.rating }}</span>
          </div>
          <div class="metric-label">评级</div>
        </div>
      </div>

      <!-- 分析报告 -->
      <div class="card">
        <h2 class="section-title">📈 量化分析报告</h2>
        
        <div class="recommendation-box">
          <strong>操作建议：</strong> {{ result.recommendation }}
        </div>

        <!-- 因子分布 -->
        <div class="factor-distribution">
          <h3>因子信号分布</h3>
          <div class="factor-bars">
            <div v-for="(count, signal) in result.factor_distribution" :key="signal" class="factor-bar">
              <span class="factor-label">{{ signal }}</span>
              <div class="factor-track">
                <div class="factor-fill" :class="signal" :style="{ width: (count / 28 * 100) + '%' }"></div>
              </div>
              <span class="factor-count">{{ count }}</span>
            </div>
          </div>
        </div>

        <!-- 风险指标 -->
        <div class="risk-metrics">
          <h3>风险指标</h3>
          <div class="metrics-grid">
            <div v-for="(value, key) in result.risk_metrics" :key="key" class="metric-item">
              <span class="metric-name">{{ formatMetricName(key) }}</span>
              <span class="metric-val">{{ formatMetricValue(value) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 空状态 -->
    <div v-else-if="!loading" class="empty-state">
      <p>👆 输入股票代码，点击「开始分析」获取28因子量化报告</p>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>正在分析 {{ symbolInput }} ...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { quantApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { AnalysisResult } from '@/stores/app'

const store = useAppStore()
const symbolInput = ref('')
const loading = ref(false)
const result = ref<AnalysisResult | null>(null)

async function handleAnalyze() {
  if (!symbolInput.value.trim()) return
  
  loading.value = true
  store.clearError()
  
  try {
    const response = await quantApi.analyze({
      symbol: symbolInput.value.trim(),
      count: 60
    })
    
    result.value = response.data
    store.setAnalysisResult(response.data)
    store.setSymbol(symbolInput.value.trim())
  } catch (err: any) {
    store.setError(err.response?.data?.detail || '分析失败')
  } finally {
    loading.value = false
  }
}

function getScoreClass(score: number): string {
  if (score >= 80) return 'score-excellent'
  if (score >= 60) return 'score-good'
  if (score >= 40) return 'score-fair'
  return 'score-poor'
}

function formatMetricName(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function formatMetricValue(value: any): string {
  if (typeof value === 'number') {
    return value.toFixed(2)
  }
  return String(value)
}
</script>

<style scoped>
.analyze-view {
  max-width: 1200px;
}

.page-title {
  font-size: 28px;
  margin-bottom: 24px;
  color: var(--text-primary);
}

.search-card {
  margin-bottom: 24px;
}

.search-form {
  display: flex;
  gap: 12px;
}

.search-form .input {
  flex: 1;
  max-width: 400px;
}

.section-title {
  font-size: 18px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--primary-color);
}

.recommendation-box {
  background: rgba(56, 189, 248, 0.1);
  border-left: 4px solid var(--primary-color);
  padding: 16px;
  margin-bottom: 24px;
  border-radius: 0 var(--radius) var(--radius) 0;
}

.factor-distribution,
.risk-metrics {
  margin-top: 24px;
}

.factor-distribution h3,
.risk-metrics h3 {
  font-size: 16px;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.factor-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.factor-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.factor-label {
  width: 80px;
  font-size: 13px;
  color: var(--text-secondary);
}

.factor-track {
  flex: 1;
  height: 24px;
  background: var(--bg-dark);
  border-radius: 4px;
  overflow: hidden;
}

.factor-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.factor-fill.bullish { background: var(--success); }
.factor-fill.bearish { background: var(--danger); }
.factor-fill.neutral { background: var(--text-muted); }

.factor-count {
  width: 30px;
  text-align: right;
  font-size: 13px;
  color: var(--text-secondary);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  background: var(--bg-dark);
  border-radius: var(--radius);
}

.metric-name {
  color: var(--text-secondary);
  font-size: 13px;
}

.metric-val {
  color: var(--text-primary);
  font-weight: 600;
  font-size: 14px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.positive { color: var(--success) !important; }
.negative { color: var(--danger) !important; }
</style>
