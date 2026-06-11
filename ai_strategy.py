#!/usr/bin/env python3
"""
AI Strategy Generation Module - AI智投量化平台 v4
Core functions:
1. AI Strategy Generation: User describes strategy in natural language, AI generates executable Python code
2. Strategy Editor: Support manual editing of generated strategies
3. Strategy Backtest: Integrate with quant_engine backtest framework
4. Strategy Management: Save/Load/Delete strategies
"""

import os
import json
import sys
import time
import hashlib
import openai
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import numpy as np

# -- Path --
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "data"))

# -- Config --
STRATEGY_DIR = PROJECT_DIR / "strategies"
STRATEGY_DIR.mkdir(exist_ok=True)

# Load API Key from .env
from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / ".env")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


def get_deepseek_client():
    """Get DeepSeek API client"""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not configured, please check .env file")
    
    return openai.OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )


# -- Strategy Generation --
STRATEGY_SYSTEM_PROMPT = """You are a professional quantitative trading strategy development engineer. Users will describe their desired trading strategy in natural language, and you need to convert it into executable Python strategy code.

IMPORTANT: All user-facing text (buy/sell reasons, strategy descriptions, comments) MUST be in Chinese (中文). Example: use "金叉买入信号" not "Golden cross buy signal", use "止盈卖出" not "Take profit sell", use "止损卖出" not "Stop loss sell".

## Strategy Code Standards

### Required Functions
```python
def init(context):
    \"\"\"Strategy initialization, set parameters, subscribe symbols, etc.\"\"\"
    context.symbol = "600036"  # Default symbol
    context.ma_short = 5
    context.ma_long = 20
    context.stop_loss = -0.08  # -8% stop loss
    context.take_profit = 0.25  # +25% take profit

def handle_data(context, data):
    \"\"\"Processing logic for each trading day\"\"\"
    symbol = context.symbol
    current_price = data[symbol]["close"]
    
    # Get K-line data (last 60 days)
    kline = get_kline(symbol, period="day", count=60)
    if kline is None or len(kline) < 20:
        return
    
    # Calculate indicators
    close = kline["close"].values
    ma_short = np.mean(close[-context.ma_short:])
    ma_long = np.mean(close[-context.ma_long:])
    
    # Position status
    position = context.portfolio.positions.get(symbol, None)
    
    # -- Buy Signal --
    if position is None:
        # Golden cross buy: short MA crosses above long MA
        if len(close) >= context.ma_long + 1:
            prev_ma_short = np.mean(close[-context.ma_short-1:-1])
            prev_ma_long = np.mean(close[-context.ma_long-1:-1])
            if prev_ma_short <= prev_ma_long and ma_short > ma_long:
                buy(symbol, current_price, "Golden cross buy signal")
                return
    
    # -- Sell Signal --
    if position is not None:
        cost_price = position["cost_price"]
        
        # Take profit
        if current_price >= cost_price * (1 + context.take_profit):
            sell(symbol, current_price, "Take profit sell")
            return
        
        # Stop loss
        if current_price <= cost_price * (1 + context.stop_loss):
            sell(symbol, current_price, "Stop loss sell")
            return
        
        # Death cross sell: short MA crosses below long MA
        if len(close) >= context.ma_long + 1:
            prev_ma_short = np.mean(close[-context.ma_short-1:-1])
            prev_ma_long = np.mean(close[-context.ma_long-1:-1])
            if prev_ma_short >= prev_ma_long and ma_short < ma_long:
                sell(symbol, current_price, "Death cross sell signal")
                return
```

### Available APIs
- `get_kline(symbol, period, count)` - Get K-line data
- `buy(symbol, price, reason)` - Buy
- `sell(symbol, price, reason)` - Sell
- `context.portfolio` - Get position and capital info
- `context.portfolio.positions[symbol]` - Get position for a symbol
- `context.portfolio.cash` - Available cash

### Code Requirements
1. Output only Python code, no explanation
2. Code must be complete and runnable, including init and handle_data functions
3. Use numpy for technical indicator calculations
4. Include stop loss and take profit logic
5. Clear code comments

## Common Strategy Templates Reference

### Moving Average Strategy
- Golden cross buy (short MA crosses above long MA)
- Death cross sell (short MA crosses below long MA)
- Multi-period MA alignment

### Momentum Strategy
- RSI overbought/oversold
- MACD golden/death cross
- Bollinger Band breakout

### Trend Strategy
- ADX trend strength
- Ichimoku Cloud
- Donchian Channel breakout

### Value Strategy
- Piotroski F-Score stock selection
- Low PE/PB screening
- ROE screening

Please generate corresponding strategy code based on user's specific description.
"""

def generate_strategy(user_prompt: str, style: str = "balanced") -> Tuple[str, str]:
    """
    Generate strategy code based on user description
    
    Args:
        user_prompt: User's natural language description of strategy requirements
        style: Strategy style - conservative/balanced/aggressive
    
    Returns:
        (strategy_code, explanation) - Strategy code and explanation
    """
    client = get_deepseek_client()
    
    # Build style prompt
    style_map = {
        "conservative": "Conservative strategy, focuses on risk control, strict stop loss (-5%), moderate take profit (+15%), suitable for steady investors",
        "balanced": "Balanced strategy, balanced risk-reward, moderate stop loss (-8%), reasonable take profit (+25%), suitable for most investors",
        "aggressive": "Aggressive strategy, pursues high returns, loose stop loss (-12%), higher take profit (+40%), suitable for investors with high risk tolerance"
    }
    
    full_prompt = f"""User strategy requirement: {user_prompt}
Strategy style: {style_map.get(style, style_map["balanced"])}

Please generate complete Python strategy code, including init() and handle_data() functions."""
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        
        code = response.choices[0].message.content.strip()
        
        # Extract code block (if AI returned markdown code block)
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
        
        # Generate explanation
        explanation = generate_strategy_explanation(code, user_prompt)
        
        return code, explanation
        
    except Exception as e:
        return f"# Strategy generation failed: {str(e)}", f"Generation failed: {str(e)}"


def generate_strategy_explanation(code: str, user_prompt: str) -> str:
    """Generate strategy explanation"""
    # Extract key info from code
    lines = code.split("\n")
    
    # Find key parameters
    ma_short = "5"
    ma_long = "20"
    stop_loss = "-8%"
    take_profit = "+25%"
    
    for line in lines:
        if "ma_short" in line and "=" in line:
            try:
                ma_short = line.split("=")[1].strip().split("#")[0].strip()
            except:
                pass
        if "ma_long" in line and "=" in line:
            try:
                ma_long = line.split("=")[1].strip().split("#")[0].strip()
            except:
                pass
        if "stop_loss" in line and "=" in line:
            try:
                val = line.split("=")[1].strip().split("#")[0].strip()
                stop_loss = f"{float(val)*100:.0f}%"
            except:
                pass
        if "take_profit" in line and "=" in line:
            try:
                val = line.split("=")[1].strip().split("#")[0].strip()
                take_profit = f"{float(val)*100:.0f}%"
            except:
                pass
    
    explanation = f"""## Strategy Explanation

**User Description**: {user_prompt}

### Core Logic
This strategy is automatically generated based on user description, mainly including:

1. **Buy Signal**: Main buy conditions detected in code
2. **Sell Signal**: Main sell conditions detected in code
3. **Risk Control**: Stop loss {stop_loss}, Take profit {take_profit}

### Key Parameters
- Short-term MA: {ma_short} days
- Long-term MA: {ma_long} days
- Stop loss ratio: {stop_loss}
- Take profit ratio: {take_profit}

### Important Note
- This strategy is AI-generated, **please carefully read the code logic before using**
- Recommended to test with paper trading or small capital first
- Market has risks, invest cautiously"""
    
    return explanation


# -- Strategy Code Validation --
def validate_strategy_code(code: str) -> Tuple[bool, str]:
    """
    Validate basic structure of strategy code
    
    Returns:
        (is_valid, message)
    """
    if not code or code.startswith("# Strategy generation failed"):
        return False, "Strategy code is empty or generation failed"
    
    # Check required functions
    if "def init(" not in code:
        return False, "Missing init() function"
    if "def handle_data(" not in code:
        return False, "Missing handle_data() function"
    
    # Check basic syntax (simple check)
    try:
        compile(code, "<strategy>", "exec")
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    
    return True, "Strategy code structure is correct"


# -- Strategy Backtest --
def run_backtest(strategy_code: str, symbol: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    """
    Run strategy backtest
    
    Args:
        strategy_code: Strategy code
        symbol: Backtest symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        Backtest result dictionary
    """
    from quotes import TencentQuotes
    
    # Fetch historical data
    quotes_engine = TencentQuotes()
    kline_data = quotes_engine.get_kline([symbol], period="day", count=500)
    
    if not kline_data or symbol not in kline_data:
        return {
            "symbol": symbol,
            "status": "error",
            "message": f"Failed to fetch K-line data for {symbol}",
            "metrics": {}
        }
    
    bars = kline_data[symbol]
    if len(bars) < 60:
        return {
            "symbol": symbol,
            "status": "error",
            "message": f"Insufficient data: only {len(bars)} bars available",
            "metrics": {}
        }
    
    # Parse K-line data
    cols = ["date", "open", "close", "high", "low", "volume"]
    df = pd.DataFrame(bars, columns=cols[:len(bars[0])])
    for c in ["open", "close", "high", "low", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    
    # Create execution context for strategy
    class BacktestContext:
        def __init__(self):
            self.symbol = symbol
            self.portfolio = {
                "cash": 100000.0,  # Initial capital
                "positions": {},
                "trades": []
            }
            # Copy strategy parameters from code
            self.ma_short = 5
            self.ma_long = 20
            self.stop_loss = -0.08
            self.take_profit = 0.25
    
    context = BacktestContext()
    
    # 安全沙箱：限制 __builtins__ 为安全子集
    _safe_builtins = {
        'abs': abs, 'all': all, 'any': any, 'bool': bool, 'dict': dict,
        'enumerate': enumerate, 'float': float, 'int': int, 'len': len,
        'list': list, 'max': max, 'min': min, 'print': print,
        'range': range, 'round': round, 'set': set, 'sorted': sorted,
        'str': str, 'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
        'True': True, 'False': False, 'None': None,
        'isinstance': isinstance, 'hasattr': hasattr, 'getattr': getattr,
        'setattr': setattr, 'abs': abs, 'map': map, 'filter': filter,
    }
    # 安全的 __import__
    _SAFE_IMPORT_MODULES = {'numpy', 'pandas', 'json', 'math', 'random',
                            'collections', 'datetime', 'decimal', 'itertools',
                            'functools', 'operator', 're', 'typing'}
    def _safe_import(name, *args, **kwargs):
        if name.split('.')[0] not in _SAFE_IMPORT_MODULES:
            raise ImportError(f"模块 '{name}' 不在安全导入列表中，禁止导入")
        return __import__(name, *args, **kwargs)
    _safe_builtins['__import__'] = _safe_import
    
    # Execute init
    try:
        exec(strategy_code, {
            "__builtins__": _safe_builtins,
            "np": np,
            "pd": pd,
            "get_kline": lambda s, p, c: df.reset_index().values.tolist() if s == symbol else None,
            "context": context,
        })
        
        # Call init
        local_vars = {}
        exec(strategy_code, {
            "__builtins__": _safe_builtins,
            "np": np,
            "pd": pd,
            "get_kline": lambda s, p, c: df.reset_index().values.tolist() if s == symbol else None,
            "context": context,
            "buy": lambda s, p, r: context.portfolio["trades"].append({"type": "buy", "symbol": s, "price": p, "reason": r}),
            "sell": lambda s, p, r: context.portfolio["trades"].append({"type": "sell", "symbol": s, "price": p, "reason": r}),
        }, local_vars)
        
        if "init" in local_vars:
            local_vars["init"](context)
        
        # Run backtest simulation
        close_prices = df["close"].values
        trades = []
        position = None
        cost_price = 0
        
        for i in range(20, len(close_prices)):  # Start after enough data for indicators
            current_price = close_prices[i]
            
            # Calculate indicators
            ma_short = np.mean(close_prices[i-context.ma_short:i])
            ma_long = np.mean(close_prices[i-context.ma_long:i])
            
            # Simulate handle_data
            data = {symbol: {"close": current_price}}
            
            try:
                if "handle_data" in local_vars:
                    local_vars["handle_data"](context, data)
            except Exception as e:
                print(f"[ai_strategy] handle_data error: {e}")
        
        # Calculate metrics
        total_trades = len(trades)
        buy_trades = [t for t in trades if t["type"] == "buy"]
        sell_trades = [t for t in trades if t["type"] == "sell"]
        
        # Simplified return calculation
        if len(buy_trades) > 0 and len(sell_trades) > 0:
            total_return = (sell_trades[-1]["price"] - buy_trades[0]["price"]) / buy_trades[0]["price"] * 100
        else:
            total_return = 0
        
        backtest_result = {
            "symbol": symbol,
            "start_date": df.index[0].strftime("%Y-%m-%d"),
            "end_date": df.index[-1].strftime("%Y-%m-%d"),
            "status": "success",
            "message": f"Backtest completed: {total_trades} trades executed",
            "metrics": {
                "total_return": round(total_return, 2),
                "total_trades": total_trades,
                "buy_count": len(buy_trades),
                "sell_count": len(sell_trades),
                "initial_capital": 100000,
                "final_capital": round(100000 * (1 + total_return/100), 2),
            },
            "trades": trades[-10:] if trades else [],  # Last 10 trades
        }
        
        return backtest_result
        
    except Exception as e:
        return {
            "symbol": symbol,
            "status": "error",
            "message": f"Backtest execution error: {str(e)}",
            "metrics": {}
        }


# -- Strategy Management --
def save_strategy(name: str, code: str, description: str = "", tags: List[str] = None) -> str:
    """
    Save strategy to local storage
    
    Args:
        name: Strategy name
        code: Strategy code
        description: Strategy description
        tags: Tag list
    
    Returns:
        Strategy file path
    """
    if tags is None:
        tags = []
    
    # Generate unique ID
    strategy_id = hashlib.md5(f"{name}{time.time()}".encode("utf-8")).hexdigest()[:8]
    
    # Strategy file
    strategy_file = STRATEGY_DIR / f"{strategy_id}_{name.replace(' ', '_')}.json"
    
    strategy_data = {
        "id": strategy_id,
        "name": name,
        "code": code,
        "description": description,
        "tags": tags,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "version": 1,
    }
    
    with open(strategy_file, "w", encoding="utf-8") as f:
        json.dump(strategy_data, f, ensure_ascii=False, indent=2)
    
    return str(strategy_file)


def load_strategy(strategy_id: str = None, strategy_name: str = None) -> Optional[Dict[str, Any]]:
    """
    Load strategy
    
    Args:
        strategy_id: Strategy ID
        strategy_name: Strategy name
    
    Returns:
        Strategy data dict, None if not found
    """
    if strategy_id:
        pattern = f"*{strategy_id}*"
    elif strategy_name:
        pattern = f"*{strategy_name.replace(' ', '_')}*"
    else:
        return None
    
    files = list(STRATEGY_DIR.glob(pattern))
    if not files:
        return None
    
    # Take latest
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    
    with open(latest_file, "r", encoding="utf-8") as f:
        return json.load(f)


def list_strategies() -> List[Dict[str, Any]]:
    """List all saved strategies"""
    strategies = []
    for f in STRATEGY_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                data["file"] = str(f)
                strategies.append(data)
        except:
            continue
    
    # Sort by creation time
    strategies.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return strategies


def delete_strategy(strategy_id: str) -> bool:
    """Delete strategy"""
    files = list(STRATEGY_DIR.glob(f"*{strategy_id}*"))
    for f in files:
        f.unlink()
    return True


# -- Streamlit UI Components --
def render_ai_strategy_tab():
    """Render AI Strategy Generation Tab complete UI"""
    import streamlit as st
    
    st.markdown('<p class="section-title">🤖 AI Strategy Generator</p>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:12px;padding:1rem;margin:1rem 0;">
        <strong>💡 Usage Guide</strong><br/>
        Describe your trading strategy in natural language, AI will automatically generate executable Python strategy code.<br/>
        Example: "<i>Buy when 5-day MA crosses above 20-day MA, sell when crosses below, stop loss 8%, take profit 25%</i>"
    </div>
    """, unsafe_allow_html=True)
    
    # -- Left: Strategy Generation Area --
    col_gen, col_edit = st.columns([1, 1])
    
    with col_gen:
        st.subheader("📝 Strategy Description")
        
        # Strategy description input
        strategy_prompt = st.text_area(
            "Describe your strategy in natural language",
            placeholder="Example: Buy when 5-day MA crosses above 20-day MA, sell when crosses below, stop loss 8%, take profit 25%",
            height=150,
            key="strategy_prompt"
        )
        
        # Strategy style selection
        strategy_style = st.selectbox(
            "Strategy Style",
            ["conservative", "balanced", "aggressive"],
            format_func=lambda x: {"conservative": "🛡️ Conservative (Strict Stop Loss)", "balanced": "⚖️ Balanced (Risk-Reward Balanced)", "aggressive": "🚀 Aggressive (High Return Pursuit)"}.get(x, x),
            key="strategy_style"
        )
        
        # Backtest symbol
        backtest_symbol = st.text_input("Backtest Symbol (Optional)", placeholder="600036", key="backtest_symbol")
        
        # Generate button
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            generate_btn = st.button("✨ Generate Strategy", type="primary", use_container_width=True, key="gen_strategy_btn")
        with col_btn2:
            clear_btn = st.button("🗑️ Clear", use_container_width=True, key="clear_strategy_btn")
        
        if clear_btn:
            st.session_state.generated_strategy = ""
            st.session_state.strategy_explanation = ""
            st.rerun()
        
        # Generate strategy
        if generate_btn and strategy_prompt.strip():
            with st.spinner("🤖 AI is thinking about strategy..."):
                code, explanation = generate_strategy(strategy_prompt.strip(), strategy_style)
                st.session_state.generated_strategy = code
                st.session_state.strategy_explanation = explanation
                st.session_state.strategy_valid = validate_strategy_code(code)[0]
                st.rerun()
        elif generate_btn and not strategy_prompt.strip():
            st.error("Please enter strategy description")
    
    with col_edit:
        st.subheader("💻 Strategy Code")
        
        # Show generated strategy
        if "generated_strategy" in st.session_state and st.session_state.generated_strategy:
            code = st.session_state.generated_strategy
            
            # Code editor
            edited_code = st.text_area(
                "Edit strategy code (can manually modify)",
                value=code,
                height=400,
                key="edited_strategy_code"
            )
            
            # Validation status
            is_valid, msg = validate_strategy_code(edited_code)
            if is_valid:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")
            
            # Strategy operations
            col_op1, col_op2, col_op3 = st.columns(3)
            
            with col_op1:
                save_name = st.text_input("Strategy Name", placeholder="My MA Strategy", key="strategy_save_name")
            
            with col_op2:
                save_btn = st.button("💾 Save Strategy", use_container_width=True, key="save_strategy_btn")
            
            with col_op3:
                backtest_btn = st.button("📊 Backtest", use_container_width=True, key="backtest_strategy_btn")
            
            if save_btn and save_name.strip():
                strategy_file = save_strategy(
                    save_name.strip(),
                    edited_code,
                    description=st.session_state.get("strategy_explanation", "")[:100],
                    tags=[strategy_style]
                )
                st.success(f"✅ Strategy saved to: {strategy_file}")
            
            if backtest_btn and backtest_symbol.strip():
                with st.spinner("🔄 Running backtest..."):
                    result = run_backtest(edited_code, backtest_symbol.strip())
                    st.json(result)
        else:
            st.info("👈 Enter strategy description on left, click 'Generate Strategy'")
    
    # -- Bottom: Strategy Library --
    st.divider()
    st.subheader("📚 My Strategy Library")
    
    strategies = list_strategies()
    if strategies:
        cols = st.columns(min(len(strategies), 4))
        for i, s in enumerate(strategies):
            with cols[i % 4]:
                st.markdown(f"""
                <div style="background:#1E293B;border:1px solid #334155;border-radius:8px;padding:0.8rem;margin:0.5rem 0;">
                    <strong>{s['name']}</strong><br/>
                    <span style="color:#64748B;font-size:0.8rem;">{s.get('tags', [])}</span><br/>
                    <span style="color:#94A3B8;font-size:0.75rem;">{s.get('created_at', '')[:10]}</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No saved strategies yet, generate and click 'Save Strategy'")


# -- Example Strategies --
EXAMPLE_STRATEGIES = {
    "MA Golden Cross": """def init(context):
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
    
    # Buy: Golden Cross
    if position is None:
        if len(close) >= context.ma_long + 1:
            prev_ma_short = np.mean(close[-context.ma_short-1:-1])
            prev_ma_long = np.mean(close[-context.ma_long-1:-1])
            if prev_ma_short <= prev_ma_long and ma_short > ma_long:
                buy(symbol, current_price, "Golden Cross Buy")
    
    # Sell: Death Cross / Take Profit / Stop Loss
    if position is not None:
        cost = position["cost_price"]
        if current_price >= cost * (1 + context.take_profit):
            sell(symbol, current_price, "Take Profit")
        elif current_price <= cost * (1 + context.stop_loss):
            sell(symbol, current_price, "Stop Loss")
        elif len(close) >= context.ma_long + 1:
            prev_ma_short = np.mean(close[-context.ma_short-1:-1])
            prev_ma_long = np.mean(close[-context.ma_long-1:-1])
            if prev_ma_short >= prev_ma_long and ma_short < ma_long:
                sell(symbol, current_price, "Death Cross Sell")""",
    
    "RSI Momentum": """def init(context):
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
    
    # Calculate RSI
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-context.rsi_period:])
    avg_loss = np.mean(losses[-context.rsi_period:])
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - 100 / (1 + rs)
    
    position = context.portfolio.positions.get(symbol, None)
    
    # Buy: RSI Oversold
    if position is None and rsi < context.rsi_oversold:
        buy(symbol, current_price, f"RSI Oversold {rsi:.1f}")
    
    # Sell: RSI Overbought / Take Profit / Stop Loss
    if position is not None:
        cost = position["cost_price"]
        if current_price >= cost * (1 + context.take_profit):
            sell(symbol, current_price, "Take Profit")
        elif current_price <= cost * (1 + context.stop_loss):
            sell(symbol, current_price, "Stop Loss")
        elif rsi > context.rsi_overbought:
            sell(symbol, current_price, f"RSI Overbought {rsi:.1f}")""",
}


def quick_load_example(name: str):
    """Quickly load example strategy"""
    if name in EXAMPLE_STRATEGIES:
        st.session_state.generated_strategy = EXAMPLE_STRATEGIES[name]
        st.session_state.strategy_valid = True
        return True
    return False
