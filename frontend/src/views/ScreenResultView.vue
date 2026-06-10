<template>
  <div class="screen-view">
    <div class="screen-header">
      <button class="btn btn-secondary btn-sm" @click="goBack" style="margin-right: 12px;">← 返回策略库</button>
      <h1 class="page-title" style="display: inline;">📋 选股结果</h1>
      <span class="strategy-name-label">{{ store.screenStrategyName || '策略' }}</span>
    </div>

    <!-- 条件摘要 -->
    <div class="conditions-bar card">
      <span class="cond-label">筛选条件：</span>
      <span v-if="store.screenConditions.length === 0" class="cond-text">（无条件，显示默认股票池）</span>
      <span v-else class="cond-text">{{ conditionSummary }}</span>
      <span class="cond-logic">{{ store.screenLogic }}</span>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>正在选股...</p>
    </div>

    <!-- 结果 -->
    <div v-else-if="store.screenResult" class="result-wrapper">
      <div class="result-summary card">
        <span class="summary-count">共 <strong>{{ store.screenResult.total }}</strong> 只股票满足条件</span>
        <span class="summary-date">📅 {{ today }}</span>
      </div>

      <div class="stock-table card">
        <div class="table-header">
          <span class="col-rank">#</span>
          <span class="col-code">代码</span>
          <span class="col-name">名称</span>
          <span class="col-price">现价</span>
          <span class="col-change">涨跌幅</span>
          <span class="col-pe">PE</span>
          <span class="col-pb">PB</span>
          <span class="col-volume">成交量</span>
        </div>
        <div class="table-body">
          <div v-for="(s, idx) in store.screenResult.stocks" :key="s.symbol" class="table-row">
            <span class="col-rank">{{ idx + 1 }}</span>
            <span class="col-code">{{ s.symbol }}</span>
            <span class="col-name">{{ s.name }}</span>
            <span class="col-price">{{ s.price?.toFixed(2) }}</span>
            <span class="col-change" :class="s.change_pct >= 0 ? 'text-up' : 'text-down'">
              {{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct?.toFixed(2) }}%
            </span>
            <span class="col-pe">{{ s.pe != null ? s.pe.toFixed(1) : '-' }}</span>
            <span class="col-pb">{{ s.pb != null ? s.pb.toFixed(2) : '-' }}</span>
            <span class="col-volume">{{ formatVol(s.volume) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 无结果 -->
    <div v-else-if="!loading && store.screenResult === null" class="empty-state">
      <p>暂无数据，请从策略库中点击「📋 选股」</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const store = useAppStore()
const loading = ref(false)

const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })

const conditionSummary = computed(() => {
  return store.screenConditions.map((c: any) => {
    const names: Record<string, string> = {
      pe_ttm: 'PE(TTM)', pe_static: 'PE(静态)', pb: 'PB',
      volume_ratio: '量比', turnover_rate: '换手率',
      market_cap: '市值', roe: 'ROE',
    }
    const label = names[c.indicator] || c.indicator
    const op = c.operator === '>' ? '>' : '<'
    return `${label} ${op} ${c.value}`
  }).join('，') || '无条件'
})

function formatVol(v: number | undefined | null): string {
  if (!v) return '-'
  if (v > 1e8) return (v / 1e8).toFixed(1) + '亿'
  if (v > 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toFixed(0)
}

onMounted(async () => {
  if (!store.screenResult && store.screenConditions.length >= 0) {
    await fetchScreen()
  }
})

async function fetchScreen() {
  loading.value = true
  try {
    const r = await (await fetch('/api/v1/builder/screen', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pool: store.screenPool,
        conditions: store.screenConditions,
        condition_logic: store.screenLogic,
        limit: 50,
      }),
    })).json()
    store.setScreenResult(r)
  } catch {
    store.setError('选股失败')
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/strategies')
}
</script>

<style scoped>
.screen-view { max-width: 1200px; }
.screen-header { display: flex; align-items: center; margin-bottom: var(--space-lg); flex-wrap: wrap; gap: 8px; }
.strategy-name-label { font-size: 26px; color: var(--text-muted); margin-left: 12px; }

.conditions-bar { display: flex; align-items: center; gap: 8px; padding: 12px 20px; flex-wrap: wrap; }
.cond-label { font-size: 26px; font-weight: 500; white-space: nowrap; }
.cond-text { font-size: 24px; color: var(--text-secondary); }
.cond-logic { font-size: 22px; background: var(--primary); color: var(--bg-main); padding: 2px 10px; border-radius: 4px; }

.result-summary { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; }
.summary-count { font-size: 26px; }
.summary-count strong { font-size: 30px; color: var(--primary); }
.summary-date { font-size: 24px; color: var(--text-muted); }

.stock-table { padding: 0; overflow: hidden; }
.table-header { display: flex; padding: 14px 20px; background: var(--bg-main); border-bottom: 2px solid var(--border); font-size: 24px; color: var(--text-muted); font-weight: 600; }
.table-body { }
.table-row { display: flex; align-items: center; padding: 14px 20px; border-bottom: 1px solid var(--border); font-size: 26px; transition: background 0.15s; }
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: var(--bg-card-hover); }

.col-rank { flex: 0.5; color: var(--text-muted); }
.col-code { flex: 1.2; font-family: monospace; font-weight: 500; }
.col-name { flex: 1.8; }
.col-price { flex: 1; text-align: right; }
.col-change { flex: 1; text-align: right; font-weight: 600; }
.col-pe { flex: 0.8; text-align: right; color: var(--text-muted); }
.col-pb { flex: 0.8; text-align: right; color: var(--text-muted); }
.col-volume { flex: 1.2; text-align: right; color: var(--text-muted); }
.text-up { color: var(--up); }
.text-down { color: var(--down); }
</style>
