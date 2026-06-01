<template>
  <div class="app">
    <header class="header">
      <div class="container">
        <div class="header-content">
          <div class="logo">
            <span class="logo-icon">📊</span>
            <span class="logo-text">AI量化策略平台</span>
          </div>
          <nav class="nav">
            <router-link to="/analyze" class="nav-link" active-class="active">单股分析</router-link>
            <router-link to="/scan" class="nav-link" active-class="active">全市场扫描</router-link>
            <router-link to="/ai-strategy" class="nav-link" active-class="active">AI策略</router-link>
            <router-link to="/backtest" class="nav-link" active-class="active">回测</router-link>
            <router-link to="/strategies" class="nav-link" active-class="active">策略库</router-link>
          </nav>
        </div>
      </div>
    </header>
    <main class="main">
      <div class="container">
        <router-view />
      </div>
    </main>
    <footer class="footer">
      <div class="container">
        <p>AI Quantitative Strategy Platform v4.0 | Powered by FastAPI + Vue 3</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
// App 根组件
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  padding: 16px 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.nav {
  display: flex;
  gap: 8px;
}

.nav-link {
  padding: 8px 16px;
  border-radius: var(--radius);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-card-hover);
}

.nav-link.active {
  color: var(--primary-color);
  background: var(--bg-card-hover);
}

.main {
  flex: 1;
  padding: 32px 0;
}

.footer {
  background: var(--bg-card);
  border-top: 1px solid var(--border-color);
  padding: 16px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
