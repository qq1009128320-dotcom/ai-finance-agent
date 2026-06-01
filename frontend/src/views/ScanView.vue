<template>
  <div class="scan-view">
    <h1 class="page-title">🔭 全市场扫描</h1>

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
        <button class="btn btn-primary" @click="handleScan" :disabled="scanning">
          {{ scanning ? '扫描中...' : '开始扫描' }}
        </button>
      </div>
    </div>

    <div v-if="scanning" class="loading">
      <div class="spinner"></div>
      <p>正在扫描市场...</p>
    </div>

    <template v-else-if="scanResult">
      <!-- 市场概览 -->
      <div class="market-overview">
        <div class="overview-card">
          <div class="overview-title">市场情绪</div>
          <div class="overview-bars">
            <div class="bar-item">
              <span class="bar-label">看涨</span>
              <div class="bar-track">
                <div class="bar-fill bullish" :style="{ width: (scanResult.bullish_count / scanResult.total_stocks * 100) + '%' }"></div>
              </div>
              <span class="bar-value">{{ scanResult.bullish_count }}</span>
            </div>
            <div class="bar-item">
              <span class="bar-label">中性</span>
              <div class="bar-track">
                <div class="bar-fill neutral" :style="{ width: (scanResult.neutral_count / scanResult.total_stocks * 100) + '%' }"></div>
              </div>
              <span class="bar-value">{{ scanResult.neutral_count }}</span>
            </div>
            <div class="bar-item">
              <span class="bar-label">看跌</span>
              <div class="bar-track">
                <div class="bar-fill bearish" :style="{ width: (scanResult.bearish_count / scanResult.total_stocks * 100) + '%' }"></div>
              </div>
              <span class="bar-value">{{ scanResult.bearish_count }}</span>
            </div>
          </div>
          <div class="overview-stats">
            <div class="stat">
              <span class="stat-value">{{ scanResult.avg_score }}</span>
              <span class="stat-label">平均评分</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ scanResult.total_stocks }}</span>
              <span class="stat-label">扫描数量</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 强势股 -->
      <div class="stocks-section">
        <h2>🔥 强势股 TOP {{ scanResult.top_stocks.length }}</h2>
        <div class="stocks-grid">
          <div v-for="stock in scanResult.top_stocks" :key="stock.symbol" class="stock-card card">
            <div class="stock-header">
              <span class="stock-symbol">{{ stock.symbol }}</span>
              <span class="stock-rating" :class="getRatingClass(stock.rating)">{{ stock.rating }}</span>
            </div>
            <div class="stock-name">{{ stock.name }}</div>
            <div class="stock-price">
              <span>¥{{ stock.price }}</span>
              <span :class="stock.change_pct >= 0 ? 'positive' : 'negative'">
                {{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct }}%
              </span>
            </div>
            <div class="stock-score">
              评分：<strong>{{ stock.score }}</strong>
            </div>
            <button class="btn btn-secondary btn-sm" @click="goToAnalyze(stock.symbol)">分析</button>
          </div>
        </div>
      </div>

      <!-- 弱势股 -->
      <div class="stocks-section">
        <h2>📉 弱势股</h2>
        <div class="stocks-grid">
          <div v-for="stock in scanResult.weak_stocks" :key="stock.symbol" class="stock-card card">
            <div class="stock-header">
              <span class="stock-symbol">{{ stock.symbol }}</span>
              <span class="stock-rating" :class="getRatingClass(stock.rating)">{{ stock.rating }}</span>
            </div>
            <div class="stock-name">{{ stock.name }}</div>
            <div class="stock-price">
              <span>¥{{ stock.price }}</span>
              <span :class="stock.change_pct >= 0 ? 'positive' : 'negative'">
                {{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct }}%
              </span>
            </div>
            <div class="stock-score">
              评分：<strong>{{ stock.score }}</strong>
            </div>
            <button class="btn btn-secondary btn-sm" @click="goToAnalyze(stock.symbol)">分析</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { quantApi } from '@/api'
import type { MarketScanResponse } from '@/api'

const scope = ref('top200')
const minScore = ref(60)
const sortBy = ref('score')
const scanning = ref(false)
const scanResult = ref<MarketScanResponse | null>(null)

async function handleScan() {
  scanning.value = true
  
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

function getRatingClass(rating: string): string {
  if (rating.startsWith('A')) return 'rating-high'
  if (rating.startsWith('B')) return 'rating-medium'
  return 'rating-low'
}

function goToAnalyze(symbol: string) {
  window.location.href = `/analyze?symbol=${symbol}`
}
</script>

<style scoped>
.scan-view {
  max-width: 1400px;
}

.page-title {
  font-size: 28px;
  margin-bottom: 24px;
}

.scan-controls {
  margin-bottom: 24px;
}

.control-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.control-group {
  flex: 1;
  max-width: 150px;
}

.control-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}

.market-overview {
  margin-bottom: 32px;
}

.overview-card {
  background: linear-gradient(135deg, var(--bg-card), var(--bg-card-hover));
  padding: 24px;
  border-radius: var(--radius);
}

.overview-title {
  font-size: 18px;
  margin-bottom: 16px;
}

.overview-bars {
  display: flex;
  gap: 32px;
  margin-bottom: 16px;
}

.bar-item {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.bar-label {
  width: 40px;
  font-size: 13px;
  color: var(--text-secondary);
}

.bar-track {
  flex: 1;
  height: 24px;
  background: var(--bg-dark);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
}

.bar-fill.bullish { background: var(--success); }
.bar-fill.neutral { background: var(--text-muted); }
.bar-fill.bearish { background: var(--danger); }

.bar-value {
  width: 30px;
  text-align: right;
  font-size: 13px;
  color: var(--text-secondary);
}

.overview-stats {
  display: flex;
  gap: 32px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--primary-color);
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.stocks-section {
  margin-bottom: 32px;
}

.stocks-section h2 {
  font-size: 20px;
  margin-bottom: 16px;
}

.stocks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.stock-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stock-symbol {
  font-size: 16px;
  font-weight: 600;
}

.stock-rating {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.rating-high {
  background: rgba(16, 185, 129, 0.2);
  color: var(--success);
}

.rating-medium {
  background: rgba(56, 189, 248, 0.2);
  color: var(--primary-color);
}

.rating-low {
  background: rgba(239, 68, 68, 0.2);
  color: var(--danger);
}

.stock-name {
  color: var(--text-secondary);
  font-size: 14px;
}

.stock-price {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.stock-price .positive { color: var(--success); }
.stock-price .negative { color: var(--danger); }

.stock-score {
  color: var(--text-muted);
  font-size: 13px;
}

.stock-score strong {
  color: var(--primary-color);
  font-size: 16px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
  margin-top: 8px;
}
</style>
