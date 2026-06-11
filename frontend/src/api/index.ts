import axios from 'axios'

const API_BASE = '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 量化分析 API
export const quantApi = {
  analyze: (data: { symbol: string; period?: string; count?: number }) =>
    api.post('/quant/analyze', data),
  
  scan: (data: { scope?: string; min_score?: number; sort_by?: string; limit?: number }) =>
    api.post('/quant/scan', data),
  
  getSymbols: () => api.get('/quant/symbols')
}

// AI 策略 API
export const aiApi = {
  generate: (data: { prompt: string; style?: string }) =>
    api.post('/ai/generate', data),
  
  validate: (code: string) => api.post('/ai/validate', { code })
}

// 策略管理 API
export const strategyApi = {
  create: (data: { name: string; code: string; description?: string; tags?: string[]; config?: any }) =>
    api.post('/strategy/create', data),
  
  list: () => api.get('/strategy/list'),
  
  get: (id: string) => api.get(`/strategy/get/${id}`),
  
  delete: (id: string) => api.delete(`/strategy/delete/${id}`),
  
  validate: (code: string) => api.post('/strategy/validate', { code })
}

// 回测 API
export const backtestApi = {
  run: (data: { code: string; symbol: string; start_date?: string; end_date?: string; initial_capital?: number; confirmed?: boolean }) =>
    api.post('/backtest/run', data),

  validateAndRun: (data: { code: string; symbol: string; confirmed?: boolean }) =>
    api.post('/backtest/validate-and-run', data)
}

// 系统 API
export const systemApi = {
  health: () => api.get('/system/health'),
  ready: () => api.get('/system/ready')
}

export default api
