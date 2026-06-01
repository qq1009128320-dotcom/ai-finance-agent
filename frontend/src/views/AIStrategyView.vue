<template>
  <div class="ai-strategy-view">
    <h1 class="page-title">🤖 AI策略生成器</h1>
    
    <div class="intro-card card">
      <p>用自然语言描述你想要的交易策略，AI会自动生成可执行的Python策略代码。</p>
      <p class="example">示例：当5日均线上穿20日均线时买入，下穿时卖出，止损8%，止盈25%</p>
    </div>

    <div class="strategy-editor">
      <!-- 左侧：输入区 -->
      <div class="editor-panel">
        <h2>策略描述</h2>
        
        <textarea
          v-model="prompt"
          class="input prompt-input"
          placeholder="描述你的策略..."
          rows="6"
        ></textarea>

        <div class="style-selector">
          <label>策略风格：</label>
          <select v-model="style" class="input">
            <option value="conservative">🛡️ 保守型（严格止损）</option>
            <option value="balanced">⚖️ 平衡型（风险收益均衡）</option>
            <option value="aggressive">🚀 激进型（追求高收益）</option>
          </select>
        </div>

        <div class="btn-group">
          <button class="btn btn-primary" @click="handleGenerate" :disabled="generating">
            {{ generating ? '生成中...' : '✨ 生成策略' }}
          </button>
          <button class="btn btn-secondary" @click="handleClear">清空</button>
        </div>

        <!-- 示例策略 -->
        <div class="examples">
          <h3>快速加载示例</h3>
          <div class="example-buttons">
            <button class="btn btn-secondary btn-sm" @click="loadExample('ma')">均线金叉</button>
            <button class="btn btn-secondary btn-sm" @click="loadExample('rsi')">RSI动量</button>
          </div>
        </div>
      </div>

      <!-- 右侧：代码区 -->
      <div class="editor-panel">
        <h2>策略代码</h2>
        
        <div v-if="generating" class="loading">
          <div class="spinner"></div>
          <p>AI正在思考策略...</p>
        </div>

        <div v-else-if="generatedCode" class="code-container">
          <div class="code-header">
            <span class="code-title">Python</span>
            <span :class="isValid ? 'status-valid' : 'status-invalid'">
              {{ isValid ? '✓ 代码有效' : '✗ 代码无效' }}
            </span>
          </div>
          <pre class="code-editor"><code>{{ generatedCode }}</code></pre>
          
          <div class="code-actions">
            <input v-model="strategyName" type="text" class="input" placeholder="策略名称" />
            <button class="btn btn-primary" @click="handleSave">💾 保存</button>
          </div>
        </div>

        <div v-else class="empty-code">
          <p>👈 在左侧输入策略描述，点击「生成策略」</p>
        </div>
      </div>
    </div>

    <!-- 回测区 -->
    <div v-if="generatedCode" class="backtest-section card">
      <h2>📊 策略回测</h2>
      
      <div class="backtest-form">
        <input v-model="backtestSymbol" type="text" class="input" placeholder="回测标的（如 600036）" />
        <button class="btn btn-primary" @click="handleBacktest" :disabled="backtesting">
          {{ backtesting ? '回测中...' : '运行回测' }}
        </button>
      </div>

      <div v-if="backtestResult" class="backtest-result">
        <div class="metric-grid">
          <div class="metric-card">
            <div class="metric-value">{{ backtestResult.metrics.total_return }}%</div>
            <div class="metric-label">总收益率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ backtestResult.metrics.total_trades }}</div>
            <div class="metric-label">交易次数</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ backtestResult.metrics.buy_count }}</div>
            <div class="metric-label">买入次数</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ backtestResult.metrics.sell_count }}</div>
            <div class="metric-label">卖出次数</div>
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
import type { BacktestResult, Strategy } from '@/stores/app'

const store = useAppStore()

const prompt = ref('')
const style = ref('balanced')
const generatedCode = ref('')
const isValid = ref(false)
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
            sell(symbol, current_price, "止损")
        elif rsi > context.rsi_overbought:
            sell(symbol, current_price, f"RSI超买 {rsi:.1f}")`
}

async function handleGenerate() {
  if (!prompt.value.trim()) return
  
  generating.value = true
  
  try {
    const response = await aiApi.generate({
      prompt: prompt.value,
      style: style.value
    })
    
    generatedCode.value = response.data.code
    isValid.value = response.data.is_valid
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

function loadExample(name: string) {
  if (examples[name]) {
    generatedCode.value = examples[name]
    isValid.value = true
  }
}

async function handleSave() {
  if (!strategyName.value.trim() || !generatedCode.value) return
  
  try {
    const response = await strategyApi.create({
      name: strategyName.value,
      code: generatedCode.value,
      tags: [style.value]
    })
    
    store.addStrategy(response.data)
    alert('策略已保存！')
  } catch (err: any) {
    alert('保存失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function handleBacktest() {
  if (!backtestSymbol.value.trim()) {
    alert('请输入回测标的')
    return
  }
  
  backtesting.value = true
  
  try {
    const response = await backtestApi.run({
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

.page-title {
  font-size: 28px;
  margin-bottom: 24px;
}

.intro-card {
  margin-bottom: 24px;
}

.intro-card p {
  margin-bottom: 8px;
}

.example {
  color: var(--text-secondary);
  font-style: italic;
}

.strategy-editor {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.editor-panel {
  display: flex;
  flex-direction: column;
}

.editor-panel h2 {
  font-size: 18px;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.prompt-input {
  resize: vertical;
  margin-bottom: 16px;
}

.style-selector {
  margin-bottom: 16px;
}

.style-selector label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 14px;
}

.btn-group {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.examples {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.examples h3 {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.example-buttons {
  display: flex;
  gap: 8px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.code-container {
  display: flex;
  flex-direction: column;
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-dark);
  border: 1px solid var(--border-color);
  border-bottom: none;
  border-radius: var(--radius) var(--radius) 0 0;
}

.code-title {
  color: var(--text-secondary);
  font-size: 13px;
}

.status-valid {
  color: var(--success);
  font-size: 13px;
}

.status-invalid {
  color: var(--danger);
  font-size: 13px;
}

.code-editor {
  border-radius: 0 0 var(--radius) var(--radius);
  min-height: 300px;
  margin-bottom: 16px;
}

.code-editor code {
  white-space: pre;
}

.code-actions {
  display: flex;
  gap: 12px;
}

.code-actions .input {
  flex: 1;
}

.empty-code {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.backtest-section {
  margin-top: 24px;
}

.backtest-section h2 {
  font-size: 18px;
  margin-bottom: 16px;
}

.backtest-form {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.backtest-form .input {
  flex: 1;
  max-width: 300px;
}

.backtest-result {
  margin-top: 16px;
}
</style>
