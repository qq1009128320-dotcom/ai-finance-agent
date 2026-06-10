<template>
  <div class="strategies-view">
    <h1 class="page-title">📚 策略库</h1>
    <p class="page-subtitle">管理您的私有量化策略模型，查看历史表现并进行深度回测</p>

    <!-- 搜索与筛选 -->
    <div class="strategies-header card">
      <div class="flex items-center gap-md" style="flex-wrap: wrap;">
        <input
          v-model="searchQuery"
          type="text"
          class="input"
          placeholder="🔍 搜索策略..."
          style="flex: 1; min-width: 200px; max-width: 300px;"
        />
        <select v-model="filterTag" class="input" style="max-width: 150px;">
          <option value="">所有标签</option>
          <option value="conservative">保守型</option>
          <option value="balanced">平衡型</option>
          <option value="aggressive">激进型</option>
        </select>
        <button class="btn btn-primary" @click="refreshStrategies">
          🔄 刷新
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="filteredStrategies.length === 0" class="empty-state">
      <div class="empty-state-icon">📚</div>
      <p>{{ searchQuery || filterTag ? '未找到匹配的策略' : '暂无策略，请在「AI策略」页面生成并保存' }}</p>
    </div>

    <!-- 策略列表 -->
    <div v-else class="strategies-list">
      <div v-for="strategy in filteredStrategies" :key="strategy.id" class="strategy-card card">
        <div class="strategy-header">
          <div class="flex items-center gap-md">
            <h3 style="font-size: 36px; font-weight: 600;">{{ strategy.name }}</h3>
            <span v-for="tag in strategy.tags" :key="tag" class="badge badge-primary">{{ tag }}</span>
          </div>
          <div class="strategy-version">
            <span class="text-muted" style="font-size: 24px;">v{{ strategy.version }}</span>
          </div>
        </div>

        <p class="strategy-desc" style="font-size: 26px; color: var(--text-secondary); margin: var(--space-sm) 0;">
          {{ strategy.description || '暂无描述' }}
        </p>

        <div class="strategy-meta flex items-center gap-md" style="font-size: 24px; color: var(--text-muted);">
          <span>📅 {{ formatDate(strategy.created_at) }}</span>
          <span>🕐 {{ formatTime(strategy.updated_at) }}</span>
        </div>

        <div class="strategy-actions flex gap-sm" style="margin-top: var(--space-md);">
          <button class="btn btn-secondary btn-sm" @click="viewStrategy(strategy)">
            👁️ 查看
          </button>
          <button class="btn btn-secondary btn-sm" @click="runBacktest(strategy)">
            📊 回测
          </button>
          <button class="btn btn-secondary btn-sm" @click="runScreen(strategy)">
            📋 选股
          </button>
          <button class="btn btn-secondary btn-sm" @click="editStrategy(strategy)">
            ✏️ 编辑
          </button>
          <button class="btn btn-danger btn-sm" @click="deleteStrategy(strategy.id)">
            🗑️ 删除
          </button>
        </div>

        <!-- 选股结果 -->
        <div v-if="screenResults[strategy.id]" class="screen-results" style="margin-top: var(--space-md);">
          <p style="font-size: 24px; color: var(--text-muted); margin-bottom: 8px;">
            ✅ 选股完成 — 共 <strong style="color: var(--text-primary);">{{ screenResults[strategy.id].total }}</strong> 只股票满足条件
          </p>
          <div class="screen-table">
            <div class="picks-header">
              <span class="picks-col-code">代码</span>
              <span class="picks-col-name">名称</span>
              <span class="picks-col-price">现价</span>
              <span class="picks-col-change">涨跌幅</span>
            </div>
            <div v-for="s in screenResults[strategy.id].stocks" :key="s.symbol" class="picks-row">
              <span class="picks-col-code">{{ s.symbol }}</span>
              <span class="picks-col-name">{{ s.name }}</span>
              <span class="picks-col-price">{{ s.price?.toFixed(2) }}</span>
              <span class="picks-col-change" :class="s.change_pct >= 0 ? 'text-up' : 'text-down'">{{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct?.toFixed(2) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { strategyApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { Strategy } from '@/stores/app'

const router = useRouter()
const store = useAppStore()

const loading = ref(false)
const searchQuery = ref('')
const filterTag = ref('')
const strategies = ref<Strategy[]>([])
const screenResults = ref<Record<string, { total: number; stocks: any[] }>>({})

onMounted(() => {
  refreshStrategies()
})

async function refreshStrategies() {
  loading.value = true
  try {
    const response = await strategyApi.list()
    const data = response.data
    strategies.value = data.strategies ?? data
    store.setStrategies(strategies.value)
  } catch (err) {
    console.error('加载策略失败', err)
  } finally {
    loading.value = false
  }
}

const filteredStrategies = computed(() => {
  let list = strategies.value

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(s =>
      s.name.toLowerCase().includes(q) ||
      s.code.toLowerCase().includes(q) ||
      (s.description?.toLowerCase().includes(q) ?? false)
    )
  }

  if (filterTag.value) {
    list = list.filter(s => s.tags.includes(filterTag.value))
  }

  return list
})

function formatDate(isoString: string): string {
  const d = new Date(isoString)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function formatTime(isoString: string): string {
  const d = new Date(isoString)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function viewStrategy(strategy: Strategy) {
  // 查看策略详情 — 可以打开一个模态框或跳转到详情页
  alert(`策略：${strategy.name}\n代码预览：\n${strategy.code.substring(0, 200)}...`)
}

function runBacktest(strategy: Strategy) {
  store.setGeneratedCode(strategy.code)
  router.push(`/backtest`)
}

async function runScreen(strategy: Strategy) {
  // 优先使用策略保存的 config
  let conditions: any[] = []
  let pool = 'all'
  let conditionLogic = 'AND'

  // 方式1: 使用策略的 config 字段
  if (strategy.config && strategy.config.conditions && strategy.config.conditions.length > 0) {
    conditions = strategy.config.conditions
    pool = strategy.config.pool || 'all'
    conditionLogic = strategy.config.conditionLogic || 'AND'
  } else {
    // 方式2: 尝试将 code 作为 JSON 解析（策略编辑器保存的格式）
    try {
      const config = JSON.parse(strategy.code)
      if (config && typeof config === 'object' && config.conditions) {
        conditions = config.conditions || []
        pool = config.pool || 'all'
        conditionLogic = config.conditionLogic || 'AND'
      }
    } catch {
      // Python 代码策略 — 无 config 时用默认股票池
      conditions = [{ indicator: 'volume_ratio', operator: '>', range: 'day', value: '0' }]
    }
  }

  if (conditions.length === 0) {
    // 没有选股条件时，直接显示默认股票池
    conditions = [{ indicator: 'volume_ratio', operator: '>', range: 'day', value: '0' }]
  }

  try {
    const r = await (await fetch('/api/v1/builder/screen', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool, conditions, condition_logic: conditionLogic, limit: 50 }),
    })).json()
    screenResults.value = { ...screenResults.value, [strategy.id]: r }
    if (r.total === 0) {
      store.setError('没有股票满足当前条件，请放宽筛选条件')
    }
  } catch {
    store.setError('选股失败，接口不可用')
  }
}

function editStrategy(strategy: Strategy) {
  store.setGeneratedCode(strategy.code)
  router.push(`/ai-strategy`)
}

async function deleteStrategy(id: string) {
  if (!confirm('确定要删除这个策略吗？此操作不可恢复。')) return

  try {
    await strategyApi.delete(id)
    strategies.value = strategies.value.filter(s => s.id !== id)
    store.removeStrategy(id)
  } catch (err: any) {
    store.setError(err.response?.data?.detail || '删除失败')
  }
}
</script>

<style scoped>
.strategies-view {
}
.strategies-header {
  margin-bottom: var(--space-lg);
}

.strategies-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: var(--space-lg);
}

.strategy-card {
  display: flex;
  flex-direction: column;
  padding: var(--space-lg);
}

.strategy-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.strategy-version {
  font-family: 'Fira Code', monospace;
}

.strategy-actions {
  flex-wrap: wrap;
}

@media (max-width: 600px) {
  .strategies-list {
    grid-template-columns: 1fr;
  }
}

/* 选股结果表格 */
.screen-table { width: 100%; border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; }
.picks-header { display: flex; padding: 10px 12px; border-bottom: 2px solid var(--border); font-size: 22px; color: var(--text-muted); font-weight: 500; background: var(--bg-main); }
.picks-row { display: flex; align-items: center; padding: 10px 12px; border-bottom: 1px solid rgba(0,0,0,0.04); font-size: 24px; }
.picks-row:last-child { border-bottom: none; }
.picks-row:hover { background: var(--bg-card-hover); }
.picks-col-code { flex: 1.2; font-family: monospace; }
.picks-col-name { flex: 2; }
.picks-col-price { flex: 1; text-align: right; }
.picks-col-change { flex: 1; text-align: right; font-weight: 600; }
.text-up { color: var(--up); }
.text-down { color: var(--down); }
</style>