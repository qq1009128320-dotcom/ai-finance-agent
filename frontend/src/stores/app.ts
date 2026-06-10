import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Strategy {
  id: string
  name: string
  code: string
  description?: string
  tags: string[]
  config?: any
  created_at: string
  updated_at: string
  version: number
}

export interface AnalysisResult {
  symbol: string
  name: string
  price: number
  change_pct: number
  total_score: number
  rating: string
  dimensions: any[]
  factor_distribution: Record<string, number>
  risk_metrics: Record<string, any>
  recommendation: string
  signal_summary?: string
  triggers?: Record<string, string>
  tech_snapshot?: Record<string, any>
  relative_strength?: Record<string, any>
  financial_summary?: Record<string, any>
  news_sentiment?: Record<string, any>
}

export interface BacktestResult {
  symbol: string
  start_date: string
  end_date: string
  status: string
  message: string
  metrics: {
    total_return?: number
    annual_return?: number
    max_drawdown?: number
    sharpe_ratio?: number
    win_rate?: number
    profit_factor?: number
    total_trades?: number
    buy_count?: number
    sell_count?: number
    initial_capital: number
    final_capital?: number
    equity_curve?: { date: string; value: number; drawdown: number }[]
  }
  trades: any[]
}

export const useAppStore = defineStore('app', () => {
  // 状态
  const currentSymbol = ref('')
  const analysisResult = ref<AnalysisResult | null>(null)
  const strategies = ref<Strategy[]>([])
  const backtestResult = ref<BacktestResult | null>(null)
  const generatedCode = ref('')
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // 选股结果页数据
  const screenStrategyName = ref('')
  const screenConditions = ref<any[]>([])
  const screenPool = ref('all')
  const screenLogic = ref('AND')
  const screenResult = ref<{ total: number; stocks: any[] } | null>(null)

  // Actions
  function setSymbol(symbol: string) {
    currentSymbol.value = symbol
  }

  function setAnalysisResult(result: AnalysisResult) {
    analysisResult.value = result
  }

  function setStrategies(list: Strategy[]) {
    strategies.value = list
  }

  function addStrategy(strategy: Strategy) {
    strategies.value.unshift(strategy)
  }

  function removeStrategy(id: string) {
    strategies.value = strategies.value.filter(s => s.id !== id)
  }

  function setBacktestResult(result: BacktestResult) {
    backtestResult.value = result
  }

  function setGeneratedCode(code: string) {
    generatedCode.value = code
  }

  function setLoading(value: boolean) {
    isLoading.value = value
  }

  function setError(value: string | null) {
    error.value = value
  }

  function clearError() {
    error.value = null
  }

  function setScreenParams(name: string, conditions: any[], pool: string, logic: string) {
    screenStrategyName.value = name
    screenConditions.value = conditions
    screenPool.value = pool
    screenLogic.value = logic
    screenResult.value = null
  }

  function setScreenResult(result: { total: number; stocks: any[] }) {
    screenResult.value = result
  }

  return {
    currentSymbol, analysisResult, strategies, backtestResult,
    generatedCode, isLoading, error,
    screenStrategyName, screenConditions, screenPool, screenLogic, screenResult,
    setSymbol, setAnalysisResult, setStrategies, addStrategy, removeStrategy,
    setBacktestResult, setGeneratedCode, setLoading, setError, clearError,
    setScreenParams, setScreenResult,
  }
})
