<template>
  <div class="strategies-view">
    <h1 class="page-title">📚 策略库</h1>

    <div class="strategies-header">
      <p>已保存的策略列表，可编辑、回测、删除</p>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="strategies.length === 0" class="empty-state">
      <p>暂无策略，请在「AI策略」页面生成并保存</p>
    </div>

    <div v-else class="strategies-list">
      <div v-for="strategy in strategies" :key="strategy.id" class="strategy-card card">
        <div class="strategy-header">
          <h3>{{ strategy.name }}</h3>
          <div class="strategy-tags">
            <span v-for="tag in strategy.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>
        
        <div class="strategy-meta">
          <span>📅 {{ formatDate(strategy.created_at) }}</span>
          <span>📝 v{{ strategy.version }}</span>
        </div>

        <div class="strategy-actions">
          <button class="btn btn-secondary btn-sm" @click="viewStrategy(strategy)">查看</button>
          <button class="btn btn-secondary btn-sm" @click="runBacktest(strategy)">回测</button>
          <button class="btn btn-danger btn-sm" @click="deleteStrategy(strategy.id)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { strategyApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { Strategy } from '@/stores/app'

const store = useAppStore()
const strategies = ref<Strategy[]>([])
const loading = ref(true)

onMounted(async () => {
  await loadStrategies()
})

async function loadStrategies() {
  try {
    const response = await strategyApi.list()
    strategies.value = response.data.strategies
    store.setStrategies(response.data.strategies)
  } catch (err) {
    console.error('加载策略失败', err)
  } finally {
    loading.value = false
  }
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('zh-CN')
}

function viewStrategy(strategy: Strategy) {
  // 跳转到AI策略页面并加载代码
  store.setGeneratedCode(strategy.code)
  store.setSymbol(strategy.id) // 临时用id标识
  window.location.href = '/ai-strategy'
}

async function deleteStrategy(id: string) {
  if (!confirm('确定删除此策略？')) return
  
  try {
    await strategyApi.delete(id)
    store.removeStrategy(id)
  } catch (err) {
    alert('删除失败')
  }
}

function runBacktest(strategy: Strategy) {
  store.setGeneratedCode(strategy.code)
  window.location.href = '/backtest'
}
</script>

<style scoped>
.strategies-view {
  max-width: 1000px;
}

.page-title {
  font-size: 28px;
  margin-bottom: 24px;
}

.strategies-header {
  margin-bottom: 24px;
  color: var(--text-secondary);
}

.strategies-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.strategy-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.strategy-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.strategy-header h3 {
  font-size: 18px;
}

.strategy-tags {
  display: flex;
  gap: 8px;
}

.tag {
  display: inline-block;
  padding: 4px 12px;
  background: var(--bg-card-hover);
  border-radius: 999px;
  font-size: 12px;
  color: var(--text-secondary);
}

.strategy-meta {
  display: flex;
  gap: 24px;
  color: var(--text-muted);
  font-size: 13px;
}

.strategy-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}
</style>
