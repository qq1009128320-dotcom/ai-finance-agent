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
            <option value="all">全部</option>
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
    </div>

    <!-- 加载状态 -->
    <div v-if="scanning" class="loading">
      <div class="spinner"></div>
      <p>正在扫描市场...</p>
    </div>

    <!-- 结果区 -->
    <template v-else-if="scanResult">
      <!-- 市场概览 -->
      <div class="market-overview card">
        <h2 class="card-title">📊 市场情绪概览</h2>
        <div class="overview-content">
          <div class="overview-bars">
            <div class="bar-item">
              <span class="bar-label">🟢 看涨</span>
              <div class="progress-track" style="flex: 1; margin: 0 12px;">
                <div class="progress-fill success" :style="{ width: (scanResult.bullish_count / scanResult.total_stocks * 100) + '%' }"></div>
              </div>
              <span class="bar-value text-success">{{ scanResult.bullish_count }}</span>
            </div>
            <div class="bar-item">
              <span class="bar-label">⚪ 中性</span>
              <div class="progress-track" style="flex: 1; margin: 0 12px;">
                <div class="progress-fill neutral" :style="{ width: (scanResult.neutral_count / scanResult.total_stocks * 100) + '%' }"></div>
              </div>
              <span class="bar-value">{{ scanResult.neutral_count }}</span>
            </div>
            <div class="bar-item">
              <span class="bar-label">🔴 看跌</span>
              <div class="progress-track" style="flex: 1; margin: 0 12px;">
                <div class="progress-fill danger" :style="{ width: (scanResult.bearish_count / scanResult.total_stocks * 100) + '%' }"></div>
              </div>
              <span class="bar-value text-danger">{{ scanResult.bearish_count }}</span>
            </div>
          </div>
          <div class="overview-stats flex gap-lg" style="margin-top: var(--space-md); padding-top: var(--space-md); border-top: 1px solid var(--border);">
            <div class="stat">
              <span class="stat-value" style="font-size: 24px; font-weight: 700;">{{ scanResult.avg_score }}</span>
              <span class="stat-label">平均评分</span>
            </div>
            <div class="stat">
              <span class="stat-value" style="font-size: 24px; font-weight: 700;">{{ scanResult.total_stocks }}</span>
              <span class="stat-label">扫描数量</span>
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
              <span :class="stock.change_pct >= 0 ? 'text-success' : 'text-danger'" style="font-weight: 600;">
                {{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct }}%
              </span>
            </div>
            <div class="stock-score">
              评分：<strong style="font-size: 18px; color: var(--primary);">{{ stock.score }}</strong>
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
              <span :class="stock.change_pct >= 0 ? 'text-success' : 'text-danger'" style="font-weight: 600;">
                {{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct }}%
              </span>
            </div>
            <div class="stock-score">
              评分：<strong style="font-size: 18px; color: var(--danger);">{{ stock.score }}</strong>
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { quantApi } from '@/api'

const router = useRouter()

const scope = ref('top200')
const minScore = ref(60)
const sortBy = ref('score')
const scanning = ref(false)
const scanResult = ref<MarketScanResponse | null>(null)

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

async function handleScan() {
  scanning.value = true
  scanResult.value = null

  try {
    const response = await quantApi.scan({
      scope: scope.value,
      min_score: minScore.value,
      sort_by: sortBy.value,
      limit: 50
    })
    scanResult.value = response.data
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
  max-width: 1400px;
}

.scan-controls .control-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  align-items: end;
}

.control-group label {
  margin-bottom: var(--space-xs);
}

.section-title {
  font-size: 18px;
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
  font-size: 16px;
  font-weight: 700;
  font-family: 'Fira Code', monospace;
}

.stock-name {
  font-size: 14px;
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
  font-size: 18px;
  font-weight: 600;
}

.stock-score {
  font-size: 13px;
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
  font-size: 13px;
  min-width: 60px;
}

.bar-value {
  font-size: 14px;
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
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
</style>
