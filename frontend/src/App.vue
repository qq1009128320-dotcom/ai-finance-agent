<template>
  <div class="app-layout">
    <!-- 全局错误提示 -->
    <transition name="fade">
      <div v-if="store.error" class="global-error" @click="store.clearError()">
        <span class="error-icon">⚠️</span>
        <span class="error-text">{{ store.error }}</span>
      </div>
    </transition>

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
        <a href="#" class="sidebar-footer-link">
          <span class="nav-icon">⚙️</span>
          <span>Settings</span>
        </a>
        <a href="#" class="sidebar-footer-link">
          <span class="nav-icon">❓</span>
          <span>Support</span>
        </a>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <!-- 顶部通栏 -->
      <header class="topbar">
        <div class="topbar-nav">
          <router-link to="/analyze" class="topbar-nav-link" active-class="router-link-active">单股分析</router-link>
          <router-link to="/scan" class="topbar-nav-link" active-class="router-link-active">全市场扫描</router-link>
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
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'

const store = useAppStore()
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  background: var(--bg-main);
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
</style>
