<template>
  <div class="app-layout">
    <!-- 全局错误提示 -->
    <transition name="fade">
      <div v-if="store.error" class="global-error" @click="store.clearError()">
        <span class="error-icon">⚠️</span>
        <span class="error-text">{{ store.error }}</span>
      </div>
    </transition>

    <!-- 机会雷达滚动条 -->
    <div v-if="radarItems.length > 0" class="radar-marquee" @mouseenter="pauseMarquee" @mouseleave="resumeMarquee">
      <div class="radar-label">🎯 机会雷达</div>
      <div class="marquee-track" :style="{ transform: `translateX(-${scrollOffset}px)` }">
        <div class="marquee-content">
          <div v-for="(item, idx) in radarItems" :key="idx" class="radar-item">
            <span class="radar-symbol">{{ item.symbol }}</span>
            <span class="radar-name">{{ item.name }}</span>
            <span class="radar-score" :class="item.score >= 80 ? 'score-high' : item.score >= 60 ? 'score-med' : 'score-low'">
              {{ item.score }}分
            </span>
            <span :class="item.change_pct >= 0 ? 'text-up' : 'text-down'">
              {{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct }}%
            </span>
          </div>
          <!-- 复制一份实现无缝滚动 -->
          <div v-for="(item, idx) in radarItems" :key="'dup-' + idx" class="radar-item">
            <span class="radar-symbol">{{ item.symbol }}</span>
            <span class="radar-name">{{ item.name }}</span>
            <span class="radar-score" :class="item.score >= 80 ? 'score-high' : item.score >= 60 ? 'score-med' : 'score-low'">
              {{ item.score }}分
            </span>
            <span :class="item.change_pct >= 0 ? 'text-up' : 'text-down'">
              {{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 侧边栏 + 主内容区容器 -->
    <div class="app-body">
      <!-- 左侧边栏 -->
      <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="logo-text">
          <span class="logo-icon">📊</span>
          <span>AI智投量化</span>
        </div>
        <div class="logo-subtitle">INSTITUTIONAL GRADE</div>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/analyze" class="sidebar-nav-item" active-class="router-link-active">
          <span class="nav-icon">📈</span>
          <span>单股分析</span>
        </router-link>
        <router-link to="/scan" class="sidebar-nav-item" active-class="router-link-active">
          <span class="nav-icon">🔭</span>
          <span>全市场扫描</span>
        </router-link>
        <router-link to="/builder" class="sidebar-nav-item" active-class="router-link-active">
          <span class="nav-icon">🛠️</span>
          <span>策略编辑器</span>
        </router-link>
        <router-link to="/ai-strategy" class="sidebar-nav-item" active-class="router-link-active">
          <span class="nav-icon">🤖</span>
          <span>AI策略</span>
        </router-link>
        <router-link to="/backtest" class="sidebar-nav-item" active-class="router-link-active">
          <span class="nav-icon">📊</span>
          <span>策略回测</span>
        </router-link>
        <router-link to="/strategies" class="sidebar-nav-item" active-class="router-link-active">
          <span class="nav-icon">📚</span>
          <span>策略库</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <!-- 顶部通栏 -->
      <header class="topbar">
        <div class="topbar-nav">
          <router-link to="/analyze" class="topbar-nav-link" active-class="router-link-active">单股分析</router-link>
          <router-link to="/scan" class="topbar-nav-link" active-class="router-link-active">全市场扫描</router-link>
          <router-link to="/builder" class="topbar-nav-link" active-class="router-link-active">策略编辑器</router-link>
          <router-link to="/ai-strategy" class="topbar-nav-link" active-class="router-link-active">AI策略</router-link>
          <router-link to="/backtest" class="topbar-nav-link" active-class="router-link-active">回测</router-link>
          <router-link to="/strategies" class="topbar-nav-link" active-class="router-link-active">策略库</router-link>
        </div>
        <div class="topbar-actions">
          <button class="topbar-icon-btn" title="通知">
            🔔
          </button>
          <button class="topbar-icon-btn" title="设置">
            ⚙️
          </button>
          <div class="user-avatar" title="用户">AD</div>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="content">
        <router-view />
        <!-- 重要提示（所有页面底部） -->
        <div class="disclaimer card">
          <p><strong>⚠️ 重要提示</strong></p>
          <p>AI智投量化平台仅供量化策略学习与研究交流之用。平台展示的所有策略信号、持仓建议及收益回测结果均基于历史数据的模拟计算，不构成任何投资建议或承诺。模拟计算可能因交易滑点、市场流动性等因素与实盘存在偏差，实际交易收益可能与模拟结果不一致。投资有风险，入市需谨慎。</p>
        </div>
      </main>
    </div>
    </div> <!-- app-body end -->
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { quantApi } from '@/api'

const store = useAppStore()

// 机会雷达数据
interface RadarItem {
  symbol: string
  name: string
  score: number
  change_pct: number
}

const radarItems = ref<RadarItem[]>([])
const scrollOffset = ref(0)
let marqueeInterval: ReturnType<typeof setInterval> | null = null
let isPaused = false

function startMarquee() {
  marqueeInterval = setInterval(() => {
    if (!isPaused) {
      scrollOffset.value += 1
      // 当滚动到一半时重置，实现无缝循环
      if (scrollOffset.value >= 50 * radarItems.value.length) {
        scrollOffset.value = 0
      }
    }
  }, 50)
}

function pauseMarquee() {
  isPaused = true
}

function resumeMarquee() {
  isPaused = false
}

async function fetchRadar() {
  try {
    const response = await quantApi.scan({
      scope: 'top200',
      min_score: 60,
      sort_by: 'score',
      limit: 10
    })
    const data = response.data
    if (data && data.top_stocks) {
      radarItems.value = data.top_stocks.slice(0, 8).map((s: any) => ({
        symbol: s.symbol,
        name: s.name,
        score: s.score,
        change_pct: s.change_pct
      }))
    }
  } catch (err) {
    console.error('雷达数据获取失败', err)
  }
}

onMounted(() => {
  fetchRadar()
  // 每30秒刷新一次雷达数据
  const refreshInterval = setInterval(fetchRadar, 30000)
  // 启动滚动
  setTimeout(startMarquee, 500)
  
  onUnmounted(() => {
    if (marqueeInterval) clearInterval(marqueeInterval)
    clearInterval(refreshInterval)
  })
})

onUnmounted(() => {
  if (marqueeInterval) clearInterval(marqueeInterval)
})
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-main);
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 机会雷达滚动条 */
.radar-marquee {
  display: flex;
  align-items: center;
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.12), rgba(56, 189, 248, 0.05));
  border-bottom: 1px solid var(--border);
  padding: 8px 0;
  overflow: hidden;
  position: relative;
}

.radar-label {
  font-size: 22px;
  font-weight: 600;
  color: var(--primary);
  padding: 0 20px;
  white-space: nowrap;
  z-index: 2;
}

.marquee-track {
  display: flex;
  transition: transform 0.05s linear;
  will-change: transform;
}

.marquee-content {
  display: flex;
  gap: 24px;
  padding-right: 24px;
}

.radar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 16px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 20px;
  white-space: nowrap;
  transition: background 0.2s;
}

.radar-item:hover {
  background: rgba(56, 189, 248, 0.15);
}

.radar-symbol {
  font-family: 'Fira Code', monospace;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.radar-name {
  font-size: 20px;
  color: var(--text-secondary);
}

.radar-score {
  font-size: 18px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}

.score-high {
  background: rgba(34, 197, 94, 0.2);
  color: var(--up);
}

.score-med {
  background: rgba(250, 204, 21, 0.2);
  color: #facc15;
}

.score-low {
  background: rgba(239, 68, 68, 0.2);
  color: var(--down);
}

.global-error {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: rgba(239, 68, 68, 0.95);
  color: white;
  border-radius: var(--radius-md);
  font-size: 14px;
  cursor: pointer;
  box-shadow: var(--shadow-lg);
  max-width: 90vw;
  backdrop-filter: blur(8px);
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}

.disclaimer { margin-top: 32px; padding: 20px 24px; font-size: 18px; line-height: 1.8; color: var(--text-muted); background: rgba(255,255,255,0.02); }
.disclaimer p { margin-bottom: 6px; }
.disclaimer strong { color: var(--warning); }
</style>
