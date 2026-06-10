<template>
  <div class="ai-strategy-view">
    <h1 class="page-title">🤖 AI策略生成器</h1>
    <p class="page-subtitle">用自然语言描述策略，AI自动生成可执行的Python代码</p>

    <!-- 输入区 -->
    <div class="editor-layout">
      <!-- 左侧：输入 -->
      <div class="editor-panel card">
        <h2 class="card-title">💬 策略描述</h2>

        <div class="form-group">
          <textarea
            v-model="prompt"
            class="textarea prompt-input"
            placeholder="描述你的策略，例如：当5日均线上穿20日均线时买入，下穿时卖出，止损8%，止盈25%..."
            rows="6"
          ></textarea>
        </div>

        <div class="form-group">
          <label>策略风格</label>
          <select v-model="style" class="input">
            <option value="conservative">🛡️ 保守型（严格止损）</option>
            <option value="balanced">⚖️ 平衡型（风险收益均衡）</option>
            <option value="aggressive">🚀 激进型（追求高收益）</option>
          </select>
        </div>

        <div class="btn-group">
          <button class="btn btn-primary" @click="handleGenerate" :disabled="generating" style="flex: 1;">
            {{ generating ? '⏳ 生成中...' : '✨ 生成策略' }}
          </button>
          <button class="btn btn-secondary" @click="handleClear">🗑️ 清空</button>
        </div>

        <!-- 示例策略 -->
        <div class="examples" style="margin-top: var(--space-lg); padding-top: var(--space-lg); border-top: 1px solid var(--border);">
          <h3 style="font-size: 28px; margin-bottom: var(--space-sm); color: var(--text-secondary);">快速加载示例</h3>
          <div class="btn-group">
            <button class="btn btn-secondary btn-sm" @click="loadExample('ma')">📐 均线金叉</button>
            <button class="btn btn-secondary btn-sm" @click="loadExample('rsi')">📊 RSI动量</button>
          </div>
        </div>
      </div>

      <!-- 右侧：代码 -->
      <div class="editor-panel card">
        <h2 class="card-title">💻 策略代码</h2>

        <div v-if="generating" class="loading">
          <div class="spinner"></div>
          <p>AI正在思考策略...</p>
        </div>

        <div v-else-if="generatedCode" class="code-container">
          <div class="code-header">
            <span class="code-title">Python</span>
            <span :class="isValid ? 'badge badge-success' : 'badge badge-danger'">
              {{ isValid ? '✓ 代码有效' : '✗ 代码无效' }}
            </span>
          </div>

          <!-- 策略说明 -->
          <div v-if="explanation" class="explanation-box" style="margin: var(--space-md); padding: 12px 16px; background: rgba(56,189,248,0.03); border: 1px solid rgba(56,189,248,0.1); border-radius: 8px; font-size: 26px; color: var(--text-secondary); line-height: 1.6; white-space: pre-wrap;">
            {{ explanation }}
          </div>

          <pre class="code-editor"><code>{{ generatedCode }}</code></pre>

          <div class="code-actions" style="display: flex; gap: var(--space-sm); margin: var(--space-md);">
            <input v-model="strategyName" type="text" class="input" placeholder="策略名称" style="flex: 1;" />
            <button class="btn btn-primary" @click="handleSave">💾 保存</button>
          </div>
        </div>

        <div v-else class="empty-state" style="padding: 40px 20px;">
          <p>👈 在左侧输入策略描述，点击「生成策略」</p>
        </div>
      </div>
    </div>

    <!-- 回测区 -->
    <div v-if="generatedCode" class="backtest-section card">
      <h2 class="card-title">📊 策略回测</h2>

      <div class="backtest-form flex gap-md" style="align-items: center;">
        <input v-model="backtestSymbol" type="text" class="input" placeholder="回测标的（如 600036）" style="flex: 1;" />
        <button class="btn btn-primary" @click="handleBacktest" :disabled="backtesting">
          {{ backtesting ? '⏳ 回测中...' : '▶ 运行回测' }}
        </button>
      </div>

      <div v-if="backtestResult" class="backtest-result" style="margin-top: var(--space-lg);">
        <div class="metric-grid" style="margin-bottom: 0;">
          <div class="metric-card">
            <div class="metric-value" :class="((backtestResult.metrics.total_return ?? 0) >= 0) ? 'positive' : 'negative'">
              {{ backtestResult.metrics.total_return != null ? backtestResult.metrics.total_return + '%' : 'N/A' }}
            </div>
            <div class="metric-label">总收益率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value" :class="((backtestResult.metrics.annual_return ?? 0) >= 0) ? 'positive' : 'negative'">
              {{ backtestResult.metrics.annual_return != null ? backtestResult.metrics.annual_return + '%' : 'N/A' }}
            </div>
            <div class="metric-label">年化收益</div>
          </div>
          <div class="metric-card">
            <div class="metric-value" :class="((backtestResult.metrics.sharpe_ratio ?? 0) >= 1) ? 'positive' : 'negative'">
              {{ backtestResult.metrics.sharpe_ratio != null ? backtestResult.metrics.sharpe_ratio.toFixed(2) : 'N/A' }}
            </div>
            <div class="metric-label">夏普比率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value" :class="((backtestResult.metrics.max_drawdown ?? 0) >= -10) ? 'positive' : 'negative'">
              {{ backtestResult.metrics.max_drawdown != null ? backtestResult.metrics.max_drawdown + '%' : 'N/A' }}
            </div>
            <div class="metric-label">最大回撤</div>
          </div>
          <div class="metric-card">
            <div class="metric-value" :class="((backtestResult.metrics.win_rate ?? 0) >= 50) ? 'positive' : 'negative'">
              {{ backtestResult.metrics.win_rate != null ? backtestResult.metrics.win_rate + '%' : 'N/A' }}
            </div>
            <div class="metric-label">胜率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ backtestResult.metrics.total_trades ?? 0 }}</div>
            <div class="metric-label">交易次数</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { aiApi, strategyApi, backtestApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { BacktestResult } from '@/stores/app'

const store = useAppStore()

const prompt = ref('')
const style = ref('balanced')
const generatedCode = ref('')
const isValid = ref(false)
const explanation = ref('')
const generating = ref(false)
const strategyName = ref('')
const backtestSymbol = ref('')
const backtesting = ref(false)
const backtestResult = ref<BacktestResult | null>(null)

// 示例策略
const examples: Record<string, string> = {
  ma: `def init(context):
    context.symbol = "600036"
    context.ma_short = 5
    context.ma_long = 20
    context.stop_loss = -0.08
    context.take_profit = 0.25

def handle_data(context, data):
    symbol = context.symbol
    current_price = data[symbol]["close"]
    kline = get_kline(symbol, period="day", count=60)
    if kline is None or len(kline) < 20:
        return
    
    close = kline["close"].values
    ma_short = np.mean(close[-context.ma_short:])
    ma_long = np.mean(close[-context.ma_long:])
    position = context.portfolio.positions.get(symbol, None)
    
    if position is None:
        if len(close) >= context.ma_long + 1:
            prev_ma_short = np.mean(close[-context.ma_short-1:-1])
            prev_ma_long = np.mean(close[-context.ma_long-1:-1])
            if prev_ma_short <= prev_ma_long and ma_short > ma_long:
                buy(symbol, current_price, "金叉买入")
    
    if position is not None:
        cost = position["cost_price"]
        if current_price >= cost * (1 + context.take_profit):
            sell(symbol, current_price, "止盈")
        elif current_price <= cost * (1 + context.stop_loss):
            sell(symbol, current_price, "止损")`,

  rsi: `def init(context):
    context.symbol = "600036"
    context.rsi_period = 14
    context.rsi_overbought = 70
    context.rsi_oversold = 30
    context.stop_loss = -0.08
    context.take_profit = 0.25

def handle_data(context, data):
    symbol = context.symbol
    current_price = data[symbol]["close"]
    kline = get_kline(symbol, period="day", count=60)
    if kline is None or len(kline) < 20:
        return
    
    close = kline["close"].values
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-context.rsi_period:])
    avg_loss = np.mean(losses[-context.rsi_period:])
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - 100 / (1 + rs)
    
    position = context.portfolio.positions.get(symbol, None)
    
    if position is None and rsi < context.rsi_oversold:
        buy(symbol, current_price, f"RSI超卖 {rsi:.1f}")
    
    if position is not None:
        cost = position["cost_price"]
        if current_price >= cost * (1 + context.take_profit):
            sell(symbol, current_price, "止盈")
        elif current_price <= cost * (1 + context.stop_loss):
            sell(symbol, current_price, "止损")`
}

function loadExample(type: string) {
  prompt.value = type === 'ma'
    ? '当5日均线上穿20日均线时买入，下穿时卖出，止损8%，止盈25%'
    : '当RSI低于30时买入，高于70时卖出，止损8%，止盈25%'
  generatedCode.value = examples[type]
  isValid.value = true
}

async function handleGenerate() {
  if (!prompt.value.trim()) {
    store.setError('请输入策略描述')
    return
  }

  generating.value = true
  generatedCode.value = ''

  try {
    const response = await aiApi.generate({ prompt: prompt.value, style: style.value })
    generatedCode.value = response.data.code
    isValid.value = response.data.is_valid ?? true
    explanation.value = response.data.explanation || ''
    store.setGeneratedCode(response.data.code)
  } catch (err: any) {
    store.setError(err.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

function handleClear() {
  prompt.value = ''
  generatedCode.value = ''
  isValid.value = false
  strategyName.value = ''
  backtestResult.value = null
}

async function handleSave() {
  if (!generatedCode.value.trim()) {
    store.setError('没有可保存的代码')
    return
  }
  if (!strategyName.value.trim()) {
    store.setError('请输入策略名称')
    return
  }

  // 从提示词中提取筛选条件作为 config
  const config = extractConditionsFromPrompt(prompt.value)

  try {
    await strategyApi.create({
      name: strategyName.value,
      code: generatedCode.value,
      description: prompt.value,
      tags: [style.value],
      config: config.conditions.length > 0 ? config : undefined,
    })
    store.setError(null)
    alert('✅ 策略已保存')
  } catch (err: any) {
    store.setError(err.response?.data?.detail || '保存失败')
  }
}

// 从策略描述中提取选股条件
function extractConditionsFromPrompt(prompt: string): { pool: string; conditions: any[]; conditionLogic: string } {
  const result: { pool: string; conditions: any[]; conditionLogic: string } = {
    pool: 'all',
    conditions: [],
    conditionLogic: 'AND',
  }
  const p = prompt.replace(/\s/g, '')

  // PE条件
  const peMatch = p.match(/PE(低于|小于|<=|<|=)(\d+(\.\d+)?)/)
  if (peMatch) result.conditions.push({ indicator: 'pe_ttm', operator: '<', range: 'day', value: peMatch[2] })

  // PB条件
  const pbMatch = p.match(/PB(低于|小于|<=|<|=)(\d+(\.\d+)?)/)
  if (pbMatch) result.conditions.push({ indicator: 'pb', operator: '<', range: 'day', value: pbMatch[2] })

  // ROE条件
  const roeMatch = p.match(/ROE(高于|大于|>=|>|=)(\d+(\.\d+)?)/)
  if (roeMatch) result.conditions.push({ indicator: 'roe', operator: '>', range: 'day', value: roeMatch[2] })

  // 换手率条件
  const trMatch = p.match(/换手率(高于|大于|>=|>)(\d+(\.\d+)?)/)
  if (trMatch) result.conditions.push({ indicator: 'turnover_rate', operator: '>', range: 'day', value: trMatch[2] })

  // 市盈率条件
  const peCn = p.match(/市盈率(低于|小于|<=|<)(\d+(\.\d+)?)/)
  if (peCn) result.conditions.push({ indicator: 'pe_ttm', operator: '<', range: 'day', value: peCn[2] })

  // 市净率条件
  const pbCn = p.match(/市净率(低于|小于|<=|<)(\d+(\.\d+)?)/)
  if (pbCn) result.conditions.push({ indicator: 'pb', operator: '<', range: 'day', value: pbCn[2] })

  // 市值条件
  const capMatch = p.match(/市值(高于|大于|>=|>|=)(\d+(\.\d+)?)/)
  if (capMatch) result.conditions.push({ indicator: 'market_cap', operator: '>', range: 'day', value: capMatch[2] })

  return result
}

async function handleBacktest() {
  if (!backtestSymbol.value.trim()) {
    store.setError('请输入回测标的')
    return
  }

  backtesting.value = true
  backtestResult.value = null

  try {
    const response = await backtestApi.validateAndRun({
      code: generatedCode.value,
      symbol: backtestSymbol.value
    })
    backtestResult.value = response.data
    store.setBacktestResult(response.data)
  } catch (err: any) {
    store.setError(err.response?.data?.detail || '回测失败')
  } finally {
    backtesting.value = false
  }
}
</script>

<style scoped>
.ai-strategy-view {
  max-width: 1400px;
}

.editor-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-lg);
}

.editor-panel {
  display: flex;
  flex-direction: column;
}

.prompt-input {
  font-family: inherit;
}

.code-actions .input {
  flex: 1;
  min-width: 0;
}

.backtest-form .input {
  flex: 1;
  min-width: 0;
}

@media (max-width: 900px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
}
</style>