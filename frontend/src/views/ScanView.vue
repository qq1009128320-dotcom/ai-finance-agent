<template>
  <div class="scan-view">
    <h1 class="page-title">🔭 全市场扫描</h1>
    <p class="page-subtitle">多维度因子扫描，快速发现强势股与弱势股</p>

    <!-- 控制区 -->
    <div class="scan-controls card">
      <div class="control-row">
        <div class="control-group">
          <label>扫描范围</label>
          <select v-model="scope" class="input">
            <option value="top200">前200只</option>
            <option value="top500">前500只</option>
            <option value="all">全部（约5500只）</option>
          </select>
        </div>
        <div class="control-group">
          <label>最低评分</label>
          <input v-model.number="minScore" type="number" class="input" min="0" max="100" />
        </div>
        <div class="control-group">
          <label>排序</label>
          <select v-model="sortBy" class="input">
            <option value="score">评分</option>
            <option value="volume">成交量</option>
            <option value="change">涨跌幅</option>
          </select>
        </div>
        <div style="display: flex; align-items: flex-end;">
          <button class="btn btn-primary" @click="handleScan" :disabled="scanning" style="width: 100%;">
            {{ scanning ? '⏳ 扫描中...' : '🔍 开始扫描' }}
          </button>
        </div>
      </div>
      <div v-if="scanResult" class="scan-info">
        <span class="text-muted">已扫描 {{ scanResult.total_stocks }} 只股票，耗时约 {{ scanTime }} 秒</span>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="scanning" class="loading">
      <div class="spinner"></div>
      <p>正在扫描市场{{ scope === 'all' ? '（全部约5500只股票，请稍候）' : '' }}...</p>
    </div>

    <!-- 结果区 -->
    <template v-else-if="scanResult">
      <!-- 市场概览 -->
      <div class="market-overview card">
        <h2 class="card-title">📊 市场情绪概览</h2>
        <div class="overview-content">
          <div class="overview-bars">
            <div class="bar-item" v-for="bar in overviewBars" :key="bar.label">
              <span class="bar-label">{{ bar.label }}</span>
              <div class="progress-track" style="flex: 1; margin: 0 12px;">
                <div class="progress-fill" :style="{ width: bar.width + '%', background: bar.color }"></div>
              </div>
              <span class="bar-value" :style="{ color: bar.color }">{{ bar.value }}</span>
            </div>
          </div>
          <div class="overview-stats flex gap-lg" style="margin-top: var(--space-md); padding-top: var(--space-md); border-top: 1px solid var(--border);">
            <div class="stat">
              <span class="stat-value" style="font-size: 48px; font-weight: 700;">{{ scanResult.avg_score }}</span>
              <span class="stat-label">平均评分</span>
            </div>
            <div class="stat">
              <span class="stat-value" style="font-size: 48px; font-weight: 700;">{{ scanResult.total_stocks }}</span>
              <span class="stat-label">扫描数量</span>
            </div>
            <div class="stat">
              <span class="stat-value" style="font-size: 48px; font-weight: 700; color: var(--up);">{{ bullish_pct }}%</span>
              <span class="stat-label">看涨占比</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 强势股 -->
      <div class="stocks-section">
        <h2 class="section-title">🔥 强势股 TOP {{ scanResult.top_stocks.length }}</h2>
        <div class="stocks-grid">
          <div v-for="stock in scanResult.top_stocks" :key="stock.symbol" class="stock-card card">
            <div class="stock-header">
              <span class="stock-symbol">{{ stock.symbol }}</span>
              <span class="badge" :class="getRatingBadge(stock.rating)">{{ stock.rating }}</span>
            </div>
            <div class="stock-name">{{ stock.name }}</div>
            <div class="stock-price">
              <span>¥{{ stock.price }}</span>
              <span :class="stock.change_pct >= 0 ? 'text-up' : 'text-down'" style="font-weight: 600;">
                {{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct }}%
              </span>
            </div>
            <div class="stock-score">
              评分：<strong style="font-size: 36px; color: var(--primary);">{{ stock.score }}</strong>
            </div>
            <button class="btn btn-secondary btn-sm" @click="goToAnalyze(stock.symbol)" style="margin-top: var(--space-sm); width: 100%;">
              🔍 分析
            </button>
          </div>
        </div>
      </div>

      <!-- 弱势股 -->
      <div class="stocks-section">
        <h2 class="section-title">📉 弱势股</h2>
        <div class="stocks-grid">
          <div v-for="stock in scanResult.weak_stocks" :key="stock.symbol" class="stock-card card">
            <div class="stock-header">
              <span class="stock-symbol">{{ stock.symbol }}</span>
              <span class="badge" :class="getRatingBadge(stock.rating)">{{ stock.rating }}</span>
            </div>
            <div class="stock-name">{{ stock.name }}</div>
            <div class="stock-price">
              <span>¥{{ stock.price }}</span>
              <span :class="stock.change_pct >= 0 ? 'text-up' : 'text-down'" style="font-weight: 600;">
                {{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct }}%
              </span>
            </div>
            <div class="stock-score">
              评分：<strong style="font-size: 36px; color: var(--danger);">{{ stock.score }}</strong>
            </div>
            <button class="btn btn-secondary btn-sm" @click="goToAnalyze(stock.symbol)" style="margin-top: var(--space-sm); width: 100%;">
              🔍 分析
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <div class="empty-state-icon">🔭</div>
      <p>👆 设置扫描条件，点击「开始扫描」</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { quantApi } from '@/api'

const router = useRouter()

const scope = ref('top200')
const minScore = ref(60)
const sortBy = ref('score')
const scanning = ref(false)
const scanResult = ref<MarketScanResponse | null>(null)
const scanTime = ref(0)

interface MarketScanResponse {
  total_stocks: number
  avg_score: number
  bullish_count: number
  neutral_count: number
  bearish_count: number
  top_stocks: StockItem[]
  weak_stocks: StockItem[]
}

interface StockItem {
  symbol: string
  name: string
  price: number
  change_pct: number
  score: number
  rating: string
}

const bullish_pct = computed(() => {
  if (!scanResult.value || scanResult.value.total_stocks === 0) return 0
  return ((scanResult.value.bullish_count / scanResult.value.total_stocks) * 100).toFixed(1)
})

const overviewBars = computed(() => {
  if (!scanResult.value || scanResult.value.total_stocks === 0) return []
  const total = scanResult.value.total_stocks
  return [
    { label: '🟢 看涨', value: scanResult.value.bullish_count, width: (scanResult.value.bullish_count / total * 100), color: 'var(--up)' },
    { label: '⚪ 中性', value: scanResult.value.neutral_count, width: (scanResult.value.neutral_count / total * 100), color: 'var(--warning)' },
    { label: '🔴 看跌', value: scanResult.value.bearish_count, width: (scanResult.value.bearish_count / total * 100), color: 'var(--down)' },
  ]
})

async function handleScan() {
  scanning.value = true
  scanResult.value = null
  scanTime.value = 0
  const startTime = Date.now()

  try {
    const response = await quantApi.scan({
      scope: scope.value,
      min_score: minScore.value,
      sort_by: sortBy.value,
      limit: 200
    })
    scanResult.value = response.data
    scanTime.value = Number(((Date.now() - startTime) / 1000).toFixed(1))
  } catch (err) {
    console.error('扫描失败', err)
  } finally {
    scanning.value = false
  }
}

function getRatingBadge(rating: string): string {
  if (rating.startsWith('A')) return 'badge-success'
  if (rating.startsWith('B')) return 'badge-warning'
  return 'badge-danger'
}

function goToAnalyze(symbol: string) {
  router.push(`/analyze?symbol=${symbol}`)
}
</script>

<style scoped>
.scan-view {
}

.scan-controls .control-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  align-items: end;
}

.scan-info {
  margin-top: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  font-size: 22px;
}

.control-group label {
  margin-bottom: var(--space-xs);
}

.section-title {
  font-size: 36px;
  font-weight: 600;
  margin-bottom: var(--space-md);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.stocks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-md);
}

.stock-card {
  padding: var(--space-md);
}

.stock-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-xs);
}

.stock-symbol {
  font-size: 32px;
  font-weight: 700;
  font-family: 'Fira Code', monospace;
}

.stock-name {
  font-size: 28px;
  color: var(--text-secondary);
  margin-bottom: var(--space-sm);
}

.stock-price {
  display: flex;
  align-items: baseline;
  gap: var(--space-sm);
  margin-bottom: var(--space-xs);
}

.stock-price span:first-child {
  font-size: 36px;
  font-weight: 600;
}

.stock-score {
  font-size: 26px;
  color: var(--text-secondary);
  margin-bottom: var(--space-sm);
}

.overview-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.bar-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bar-label {
  font-size: 26px;
  min-width: 60px;
}

.bar-value {
  font-size: 28px;
  font-weight: 600;
  min-width: 40px;
  text-align: right;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  font-size: 24px;
  color: var(--text-muted);
  margin-top: 2px;
}
</style>
