import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/analyze'
    },
    {
      path: '/analyze',
      name: 'Analyze',
      component: () => import('@/views/AnalyzeView.vue')
    },
    {
      path: '/scan',
      name: 'Scan',
      component: () => import('@/views/ScanView.vue')
    },
    {
      path: '/ai-strategy',
      name: 'AIStrategy',
      component: () => import('@/views/AIStrategyView.vue')
    },
    {
      path: '/backtest',
      name: 'Backtest',
      component: () => import('@/views/BacktestView.vue')
    },
    {
      path: '/strategies',
      name: 'Strategies',
      component: () => import('@/views/StrategiesView.vue')
    }
  ]
})

export default router
