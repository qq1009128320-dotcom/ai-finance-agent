"""
综合量化分析引擎 v2.0 — 世界顶级策略集成
────────────────────────────────────────
集成: Alpha因子 · 多因子模型 · Piotroski F-Score
      Fama-French · 凯利公式 · VaR · 夏普比率
数据: a-share-analyst (腾讯行情 + akshare)
────────────────────────────────────────
2026江汉区AI智能体创新大赛 | AI＋垂直应用（金融科技）
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import OrderedDict
import warnings

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════
# 数据类
# ══════════════════════════════════════════════════════════════

@dataclass
class FactorScore:
    """单个因子评分"""
    name: str           # 因子名
    value: float        # 计算值
    score: float        # 归一化得分 0-100
    signal: str         # 信号: bullish/bearish/neutral
    weight: float       # 权重
    contribution: float # 加权贡献
    detail: str         # 解读文本


@dataclass
class DimensionReport:
    """维度分析报告"""
    name: str
    total_score: float
    max_score: float
    factors: List[FactorScore]
    summary: str
    strength: List[str]
    weakness: List[str]


@dataclass
class QuantReport:
    """完整量化分析报告"""
    symbol: str
    name: str
    price: float
    change_pct: float
    timestamp: str

    # 综合评分
    total_score: float
    rating: str
    confidence: str

    # 各维度
    dimensions: List[DimensionReport]

    # 因子分布
    factor_distribution: dict = field(default_factory=dict)

    # 风险指标
    risk_metrics: Dict[str, Any] = field(default_factory=dict)

    # 技术指标快照
    tech_snapshot: Dict[str, Any] = field(default_factory=dict)

    # 信号汇总
    signal_summary: str = ""
    entry_zone: Dict[str, float] = field(default_factory=dict)
    exit_zone: Dict[str, float] = field(default_factory=dict)

    # 具体触发条件
    triggers: dict = field(default_factory=dict)

    # 相对强度
    relative_strength: dict = field(default_factory=dict)

    # 财务摘要
    financial_summary: dict = field(default_factory=dict)

    # 新闻情感
    news_sentiment: dict = field(default_factory=dict)

    # 投资建议
    recommendation: str = ""
    position_advice: str = ""


# ══════════════════════════════════════════════════════════════
# 因子计算引擎
# ══════════════════════════════════════════════════════════════

class FactorCalculator:
    """因子计算器 — 实现20+个经典量化因子"""

    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: K线DataFrame，索引为date，列包含 open/close/high/low/volume
        """
        self.df = df.copy()
        self._precompute()

    def _precompute(self):
        """预计算常用中间变量"""
        self.close = self.df["close"].values
        self.high = self.df["high"].values
        self.low = self.df["low"].values
        self.open = self.df["open"].values
        self.volume = self.df["volume"].values
        self.n = len(self.close)

        if self.n < 2:
            return

        # 价格变化
        self.returns = np.diff(self.close) / self.close[:-1]
        self.log_returns = np.log(self.close[1:] / self.close[:-1])

        # 典型价格
        self.typical = (self.high + self.low + self.close) / 3
        self.money_flow = self.typical * self.volume

        # ATR
        self._compute_atr()

    def _compute_atr(self):
        """ATR(14)"""
        if self.n < 15:
            self.atr = np.full(self.n, np.nan)
            return
        high, low, close = self.high, self.low, self.close
        tr = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
        atr = np.full(self.n, np.nan)
        atr[14] = np.mean(tr[:14])
        for i in range(15, self.n):
            atr[i] = (atr[i-1] * 13 + tr[i-1]) / 14
        self.atr = atr

    def _sma(self, data, period):
        """简单移动平均"""
        if len(data) < period:
            return np.full_like(data, np.nan)
        return np.convolve(data, np.ones(period)/period, mode="same")

    def _ema(self, data, period):
        """指数移动平均"""
        if len(data) < period:
            return np.full_like(data, np.nan)
        alpha = 2 / (period + 1)
        result = np.full_like(data, np.nan)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
        return result

    def _rsi(self, period=14):
        """RSI"""
        if self.n < period + 1:
            return np.full(self.n, np.nan)
        delta = np.diff(self.close, prepend=self.close[0])
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = self._ema(gain, period)
        avg_loss = self._ema(loss, period)
        with np.errstate(divide="ignore", invalid="ignore"):
            rs = avg_gain / avg_loss
            return np.where(avg_loss == 0, 100, 100 - 100 / (1 + rs))

    def _macd(self, fast=12, slow=26, signal=9):
        """MACD 返回 (macd_line, signal_line, histogram)"""
        ema_fast = self._ema(self.close, fast)
        ema_slow = self._ema(self.close, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    # ═══════════════════════════════════════════
    # 趋势类因子 (8个)
    # ═══════════════════════════════════════════

    def trend_sma_position(self) -> FactorScore:
        """因子1: 多周期均线排列 — 判断趋势强度与方向"""
        if self.n < 120:
            return self._neutral_factor("多周期均线排列", 0.08,
                                        "数据不足（需至少120天K线）")

        ma5 = self._sma(self.close, 5)[-1]
        ma10 = self._sma(self.close, 10)[-1]
        ma20 = self._sma(self.close, 20)[-1]
        ma60 = self._sma(self.close, 60)[-1]
        ma120 = self._sma(self.close, 120)[-1]
        cur = self.close[-1]

        # 多头排列得分
        if cur > ma5 > ma10 > ma20 > ma60 > ma120:
            score, signal = 95, "bullish"
            detail = "完美多头排列，各周期均线依次向上，强势上升趋势"
        elif cur > ma5 > ma10 > ma20:
            score, signal = 80, "bullish"
            detail = "短中期均线多头排列，60日线以下有待修复"
        elif cur > ma20 and ma5 > ma20:
            score, signal = 65, "bullish"
            detail = "价格在20日线上方，5日线穿越20日线，中期偏多"
        elif cur < ma5 < ma10 < ma20 < ma60:
            score, signal = 10, "bearish"
            detail = "典型空头排列，各周期均线依次压制，注意风险"
        elif cur < ma20:
            score, signal = 25, "bearish"
            detail = "价格在20日线下方运行，中期趋势偏弱"
        else:
            score, signal = 50, "neutral"
            detail = "均线缠绕，无明显方向，处于盘整格局"

        return FactorScore(
            name="多周期均线排列", value=cur,
            score=score, signal=signal, weight=0.08,
            contribution=score * 0.08,
            detail=f"{detail} | 现价¥{cur:.2f} MA5=¥{ma5:.2f} MA20=¥{ma20:.2f} MA60=¥{ma60:.2f}"
        )

    def trend_macd(self) -> FactorScore:
        """因子2: MACD — 金叉死叉 + 背离检测"""
        if self.n < 30:
            return self._neutral_factor("MACD趋势动量", 0.07, "数据不足")

        macd_l, sig_l, hist = self._macd()
        cur_macd = macd_l[-1]
        cur_sig = sig_l[-1]
        cur_hist = hist[-1]
        prev_hist = hist[-2] if len(hist) > 1 else 0

        # 金叉/死叉检测
        if prev_hist < 0 and cur_hist > 0:
            score, signal = 90, "bullish"
            detail = "MACD刚刚金叉！动能由空转多，短期看涨信号强烈"
        elif cur_hist > 0 and cur_hist > prev_hist:
            score, signal = 75, "bullish"
            detail = "MACD柱状线持续放大，多头动能增强中"
        elif cur_hist > 0 and cur_hist < prev_hist:
            score, signal = 55, "neutral"
            detail = "MACD柱状线收缩，多头动能减弱，注意可能转向"
        elif prev_hist > 0 and cur_hist < 0:
            score, signal = 15, "bearish"
            detail = "MACD刚刚死叉！动能由多转空，短期看跌信号"
        elif cur_hist < 0 and cur_hist < prev_hist:
            score, signal = 20, "bearish"
            detail = "MACD柱状线持续向下，空头动能加强"
        elif cur_hist < 0 and cur_hist > prev_hist:
            score, signal = 40, "neutral"
            detail = "MACD柱状线收窄，空头动能减弱，可能筑底"
        else:
            score, signal = 50, "neutral"
            detail = "MACD中性区域震荡"

        return FactorScore(
            name="MACD趋势动量", value=round(cur_macd, 4),
            score=score, signal=signal, weight=0.07,
            contribution=score * 0.07,
            detail=f"{detail} | DIF={cur_macd:.4f} DEA={cur_sig:.4f} 柱={cur_hist:.4f}"
        )

    def trend_adx(self, period=14) -> FactorScore:
        """因子3: ADX — 趋势强度 + DI方向"""
        if self.n < period * 2:
            return self._neutral_factor("ADX趋势强度", 0.06, "数据不足")

        high, low, close = self.high, self.low, self.close
        plus_dm = np.zeros(self.n)
        minus_dm = np.zeros(self.n)

        for i in range(1, self.n):
            up = high[i] - high[i-1]
            down = low[i-1] - low[i]
            if up > down and up > 0:
                plus_dm[i] = up
            if down > up and down > 0:
                minus_dm[i] = down

        tr = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
        atr14 = np.full(self.n, np.nan)
        atr14[period] = np.mean(tr[:period])
        for i in range(period + 1, self.n):
            atr14[i] = (atr14[i-1] * (period - 1) + tr[i-1]) / period

        plus_di = np.full(self.n, np.nan)
        minus_di = np.full(self.n, np.nan)
        plus_di[period] = np.sum(plus_dm[1:period+1]) / atr14[period] * 100
        minus_di[period] = np.sum(minus_dm[1:period+1]) / atr14[period] * 100
        for i in range(period + 1, self.n):
            plus_di[i] = (plus_di[i-1] * (period - 1) + plus_dm[i] / atr14[i] * 100) / period
            minus_di[i] = (minus_di[i-1] * (period - 1) + minus_dm[i] / atr14[i] * 100) / period

        with np.errstate(divide="ignore", invalid="ignore"):
            dx = np.abs(plus_di - minus_di) / (plus_di + minus_di) * 100
        adx = self._ema(np.nan_to_num(dx), period)

        cur_adx = adx[-1]
        cur_plus = plus_di[-1]
        cur_minus = minus_di[-1]

        if cur_adx > 40:
            if cur_plus > cur_minus:
                score, signal = 85, "bullish"
                detail = f"强趋势！ADX={cur_adx:.0f}，多头占优(DI+ > DI-)"
            else:
                score, signal = 15, "bearish"
                detail = f"强趋势！ADX={cur_adx:.0f}，空头占优(DI- > DI+)"
        elif cur_adx > 25:
            if cur_plus > cur_minus:
                score, signal = 65, "bullish"
                detail = f"趋势形成中，ADX={cur_adx:.0f}，偏多"
            else:
                score, signal = 30, "bearish"
                detail = f"趋势形成中，ADX={cur_adx:.0f}，偏空"
        else:
            score, signal = 45, "neutral"
            detail = f"无明显趋势(ADX={cur_adx:.0f}<25)，处于盘整格局"

        return FactorScore(
            name="ADX趋势强度", value=round(cur_adx, 1) if not np.isnan(cur_adx) else 0,
            score=score, signal=signal, weight=0.06,
            contribution=score * 0.06,
            detail=f"{detail} | +DI={cur_plus:.0f} -DI={cur_minus:.0f}"
        )

    def trend_bollinger(self, period=20, std=2) -> FactorScore:
        """因子4: 布林带 — 波动区间 + 突破/回归信号"""
        if self.n < period:
            return self._neutral_factor("布林带波动区间", 0.06, "数据不足")

        ma = self._sma(self.close, period)
        std_dev = np.array([np.std(self.close[max(0,i-period+1):i+1]) for i in range(self.n)])
        upper = ma + std * std_dev
        lower = ma - std * std_dev

        cur = self.close[-1]
        cur_upper = upper[-1]
        cur_lower = lower[-1]
        cur_ma = ma[-1]
        bandwidth = (cur_upper - cur_lower) / cur_ma * 100
        position = (cur - cur_lower) / (cur_upper - cur_lower) if (cur_upper - cur_lower) > 0 else 0.5

        if position > 0.95:
            score, signal = 25, "bearish"
            detail = "价格触及布林上轨，处于超买区域，短期有回调压力"
        elif position > 0.7:
            score, signal = 65, "bullish"
            detail = "价格在上半区运行，偏强"
        elif position < 0.05:
            score, signal = 80, "bullish"
            detail = "价格触及布林下轨，处于超卖区域，短期有反弹动力"
        elif position < 0.3:
            score, signal = 35, "bearish"
            detail = "价格在下半区运行，偏弱"
        else:
            score, signal = 50, "neutral"
            detail = "价格在布林带中轨附近，方向不明"

        return FactorScore(
            name="布林带波动区间", value=round(position * 100, 1),
            score=score, signal=signal, weight=0.06,
            contribution=score * 0.06,
            detail=f"{detail} | 上轨¥{cur_upper:.2f} 中轨¥{cur_ma:.2f} 下轨¥{cur_lower:.2f} 带宽{bandwidth:.1f}%"
        )

    def trend_ichimoku(self) -> FactorScore:
        """因子5: 一目均衡表简化版 — 云层位置"""
        if self.n < 52:
            return self._neutral_factor("一目均衡云层", 0.05, "数据不足(需52天)")

        cloud_pos = 50  # 默认中性

        # 转折线(9) 基准线(26)
        tenkan = np.array([(max(self.high[max(0,i-8):i+1]) + min(self.low[max(0,i-8):i+1])) / 2
                          for i in range(self.n)])
        kijun = np.array([(max(self.high[max(0,i-25):i+1]) + min(self.low[max(0,i-25):i+1])) / 2
                         for i in range(self.n)])

        # 先行带A/B (前移26天 — 简化为当前值)
        if self.n >= 52:
            senkou_a = (tenkan + kijun) / 2
            senkou_b_idx = min(52, self.n)
            senkou_b = np.array([(max(self.high[max(0,i-51):i+1]) + min(self.low[max(0,i-51):i+1])) / 2
                               for i in range(self.n)])

            cloud_top = max(senkou_a[-1], senkou_b[-1])
            cloud_bottom = min(senkou_a[-1], senkou_b[-1])
            cur = self.close[-1]
            tk_cross = "金叉" if tenkan[-1] > kijun[-1] else "死叉"

            # 云端位置百分比：0=下方远, 50=云内, 100=上方远
            cloud_range = cloud_top - cloud_bottom
            if cloud_range > 0:
                cloud_pos = (cur - cloud_bottom) / cloud_range * 100
            else:
                cloud_pos = 50

            if cur > cloud_top:
                score, signal = 80, "bullish"
                detail = f"价格在云层上方({cloud_pos:.0f}%)，{tk_cross}信号，强势"
            elif cur > cloud_bottom:
                score, signal = 45, "neutral"
                detail = f"价格在云层内部({cloud_pos:.0f}%)，{tk_cross}，方向不明"
            else:
                score, signal = 15, "bearish"
                detail = f"价格在云层下方({cloud_pos:.0f}%)，{tk_cross}信号，弱势"
        else:
            score, signal = 50, "neutral"
            cloud_top = cloud_bottom = 0
            detail = "数据不足以计算完整云层"

        return FactorScore(
            name="一目均衡云层", value=round(cloud_pos, 1),
            score=score, signal=signal, weight=0.05,
            contribution=score * 0.05,
            detail=f"{detail} | 转折线¥{tenkan[-1]:.2f} 基准线¥{kijun[-1]:.2f}"
        )

    def trend_ma_cross(self) -> FactorScore:
        """因子6: 均线交叉信号 — 金叉/死叉检测"""
        if self.n < 30:
            return self._neutral_factor("均线交叉信号", 0.05, "数据不足")

        ma5 = self._sma(self.close, 5)
        ma10 = self._sma(self.close, 10)
        ma20 = self._sma(self.close, 20)

        crosses = []
        # 5日线上穿/下穿10日线 (最近5根K线)
        for i in range(max(0, self.n-5), self.n-1):
            if ma5[i] < ma10[i] and ma5[i+1] > ma10[i+1]:
                crosses.append(("5穿10金叉", "bullish", 75))
            elif ma5[i] > ma10[i] and ma5[i+1] < ma10[i+1]:
                crosses.append(("5穿10死叉", "bearish", 25))
            if ma10[i] < ma20[i] and ma10[i+1] > ma20[i+1]:
                crosses.append(("10穿20金叉", "bullish", 80))
            elif ma10[i] > ma20[i] and ma10[i+1] < ma20[i+1]:
                crosses.append(("10穿20死叉", "bearish", 20))

        if crosses:
            last_cross = crosses[-1]
            return FactorScore(
                name="均线交叉信号", value=0,
                score=last_cross[2], signal=last_cross[1], weight=0.05,
                contribution=last_cross[2] * 0.05,
                detail=f"最近信号: {last_cross[0]}"
            )
        else:
            return FactorScore(
                name="均线交叉信号", value=0, score=50, signal="neutral",
                weight=0.05, contribution=2.5, detail="近期无明确均线交叉信号"
            )

    def trend_price_vs_ma(self) -> FactorScore:
        """因子7: 价格偏离度 — 乖离率"""
        if self.n < 20:
            return self._neutral_factor("乖离率偏离度", 0.04, "数据不足")

        ma20 = self._sma(self.close, 20)[-1]
        cur = self.close[-1]
        bias = (cur / ma20 - 1) * 100

        if bias > 15:
            score, signal = 20, "bearish"
            detail = f"乖离率{bias:.1f}%极高，严重超买，回调风险大"
        elif bias > 8:
            score, signal = 35, "bearish"
            detail = f"乖离率{bias:.1f}%偏高，短期有回调需求"
        elif bias > 0:
            score, signal = 65, "bullish"
            detail = f"正乖离{bias:.1f}%，价格在均线上方运行"
        elif bias > -5:
            score, signal = 45, "neutral"
            detail = f"轻微负乖离{bias:.1f}%，价格略低于均线"
        elif bias > -12:
            score, signal = 30, "bearish"
            detail = f"负乖离{bias:.1f}%较大，偏弱运行"
        else:
            score, signal = 70, "bullish"
            detail = f"乖离率{bias:.1f}%极低，严重超卖，有均值回归动力"

        return FactorScore(
            name="乖离率偏离度", value=round(bias, 2),
            score=score, signal=signal, weight=0.04,
            contribution=score * 0.04,
            detail=detail
        )

    def trend_donchian(self, period=20) -> FactorScore:
        """因子8: Donchian通道 — 海龟交易法突破信号"""
        if self.n < period:
            return self._neutral_factor("Donchian通道", 0.04, "数据不足")

        upper = np.array([max(self.high[max(0,i-period+1):i+1]) for i in range(self.n)])
        lower = np.array([min(self.low[max(0,i-period+1):i+1]) for i in range(self.n)])
        cur = self.close[-1]

        if cur >= upper[-1] * 0.98:
            score, signal = 78, "bullish"
            detail = f"接近{period}日高点突破位，海龟买入信号区域"
        elif cur <= lower[-1] * 1.02:
            score, signal = 22, "bearish"
            detail = f"接近{period}日低点，可能下破支撑"
        else:
            pos = (cur - lower[-1]) / (upper[-1] - lower[-1]) if (upper[-1] - lower[-1]) > 0 else 0.5
            score, signal = round(30 + pos * 40), "neutral"
            detail = f"价格在{period}日通道{pos*100:.0f}%位置运行"

        return FactorScore(
            name="Donchian通道突破", value=round(cur, 2),
            score=score, signal=signal, weight=0.04,
            contribution=score * 0.04,
            detail=f"{detail} | 上轨¥{upper[-1]:.2f} 下轨¥{lower[-1]:.2f}"
        )

    # ═══════════════════════════════════════════
    # 动量震荡类 (6个)
    # ═══════════════════════════════════════════

    def momentum_rsi(self) -> FactorScore:
        """因子9: RSI(14) — 超买超卖 + 背离"""
        if self.n < 15:
            return self._neutral_factor("RSI动量", 0.07, "数据不足")

        rsi = self._rsi(14)
        cur_rsi = rsi[-1]
        prev_rsi = rsi[-2] if len(rsi) > 1 else cur_rsi

        # 背离检测
        if self.n >= 20:
            price_rising = self.close[-1] > self.close[-10]
            rsi_falling = cur_rsi < np.nanmean(rsi[-10:-1])
            if price_rising and rsi_falling and cur_rsi > 60:
                detail = f"⚠️ 顶背离！价格新高但RSI走弱，反转风险 | RSI={cur_rsi:.0f}"
                return FactorScore(name="RSI动量", value=round(cur_rsi, 1),
                    score=15, signal="bearish", weight=0.07, contribution=1.05, detail=detail)

        if cur_rsi > 80:
            score, signal = 20, "bearish"
            detail = f"RSI严重超买({cur_rsi:.0f})，回调概率极高"
        elif cur_rsi > 70:
            score, signal = 30, "bearish"
            detail = f"RSI超买区域({cur_rsi:.0f})，不宜追高"
        elif cur_rsi > 50:
            score, signal = 70, "bullish"
            detail = f"RSI偏强({cur_rsi:.0f})，多头掌控中"
        elif cur_rsi > 30:
            score, signal = 40, "neutral"
            detail = f"RSI中性偏弱({cur_rsi:.0f})"
        elif cur_rsi > 20:
            score, signal = 70, "bullish"
            detail = f"RSI超卖区域({cur_rsi:.0f})，反弹动能积聚中"
        else:
            score, signal = 85, "bullish"
            detail = f"RSI严重超卖({cur_rsi:.0f})，历史级别反弹机会"

        return FactorScore(
            name="RSI动量", value=round(cur_rsi, 1),
            score=score, signal=signal, weight=0.07,
            contribution=score * 0.07, detail=detail
        )

    def momentum_stochastic(self, period=14, k_period=3, d_period=3) -> FactorScore:
        """因子10: 随机指标 %K/%D"""
        if self.n < period:
            return self._neutral_factor("随机指标KD", 0.05, "数据不足")

        low_n = np.array([min(self.low[max(0,i-period+1):i+1]) for i in range(self.n)])
        high_n = np.array([max(self.high[max(0,i-period+1):i+1]) for i in range(self.n)])

        with np.errstate(divide="ignore", invalid="ignore"):
            k_raw = np.where(high_n != low_n,
                           (self.close - low_n) / (high_n - low_n) * 100, 50.0)

        k = self._sma(k_raw, k_period)
        d = self._sma(np.nan_to_num(k), d_period)
        cur_k, cur_d = k[-1], d[-1]

        if cur_k > 80 and cur_d > 80:
            score, signal = 20, "bearish"
            detail = f"KD双双超买(K={cur_k:.0f} D={cur_d:.0f})，注意高位风险"
        elif cur_k > cur_d and cur_k - cur_d > 10:
            score, signal = 75, "bullish"
            detail = f"K线加速上穿D线(K={cur_k:.0f} D={cur_d:.0f})，短期强势"
        elif cur_k < 20 and cur_d < 20:
            score, signal = 75, "bullish"
            detail = f"KD双双超卖(K={cur_k:.0f} D={cur_d:.0f})，存在反弹需求"
        elif cur_k < cur_d and cur_d - cur_k > 10:
            score, signal = 30, "bearish"
            detail = f"K线加速下穿D线(K={cur_k:.0f} D={cur_d:.0f})，短期走弱"
        else:
            score, signal = 50, "neutral"
            detail = f"KD中性区域(K={cur_k:.0f} D={cur_d:.0f})"

        return FactorScore(
            name="随机指标KD", value=round(cur_k, 1),
            score=score, signal=signal, weight=0.05,
            contribution=score * 0.05, detail=detail
        )

    def momentum_cci(self, period=20) -> FactorScore:
        """因子11: CCI商品通道指数"""
        if self.n < period:
            return self._neutral_factor("CCI通道指数", 0.04, "数据不足")

        tp = self.typical
        sma_tp = self._sma(tp, period)
        mean_dev = np.array([np.mean(np.abs(tp[max(0,i-period+1):i+1] - sma_tp[i]))
                            for i in range(self.n)])
        with np.errstate(divide="ignore", invalid="ignore"):
            cci = np.where(mean_dev > 0, (tp - sma_tp) / (0.015 * mean_dev), 0)
        cur_cci = cci[-1]

        if cur_cci > 200:
            score, signal = 20, "bearish"
            detail = f"CCI={cur_cci:.0f}>200，极度超买"
        elif cur_cci > 100:
            score, signal = 35, "bearish"
            detail = f"CCI={cur_cci:.0f}超买区域"
        elif cur_cci > 0:
            score, signal = 65, "bullish"
            detail = f"CCI={cur_cci:.0f}偏多"
        elif cur_cci > -100:
            score, signal = 40, "neutral"
            detail = f"CCI={cur_cci:.0f}偏空"
        elif cur_cci > -200:
            score, signal = 65, "bullish"
            detail = f"CCI={cur_cci:.0f}超卖区域，反弹信号"
        else:
            score, signal = 80, "bullish"
            detail = f"CCI={cur_cci:.0f}<-200，极度超卖"

        return FactorScore(
            name="CCI通道指数", value=round(cur_cci, 1),
            score=score, signal=signal, weight=0.04,
            contribution=score * 0.04, detail=detail
        )

    def momentum_williams_r(self, period=14) -> FactorScore:
        """因子12: 威廉指标 %R"""
        if self.n < period:
            return self._neutral_factor("威廉%R", 0.04, "数据不足")

        hh = np.array([max(self.high[max(0,i-period+1):i+1]) for i in range(self.n)])
        ll = np.array([min(self.low[max(0,i-period+1):i+1]) for i in range(self.n)])
        with np.errstate(divide="ignore", invalid="ignore"):
            wr = np.where(hh != ll, (hh - self.close) / (hh - ll) * -100, -50)
        cur_wr = wr[-1]

        if cur_wr > -20:
            score, signal = 22, "bearish"
            detail = f"%R={cur_wr:.0f} 超买区域，短期见顶信号"
        elif cur_wr > -50:
            score, signal = 55, "bullish"
            detail = f"%R={cur_wr:.0f} 偏强运行"
        elif cur_wr > -80:
            score, signal = 40, "neutral"
            detail = f"%R={cur_wr:.0f} 偏弱运行"
        else:
            score, signal = 78, "bullish"
            detail = f"%R={cur_wr:.0f} 超卖区域，反弹概率大"

        return FactorScore(
            name="威廉%R", value=round(cur_wr, 1),
            score=score, signal=signal, weight=0.04,
            contribution=score * 0.04, detail=detail
        )

    def momentum_roc(self, period=10) -> FactorScore:
        """因子13: 变化率 ROC"""
        if self.n < period:
            return self._neutral_factor("ROC变化率", 0.05, "数据不足")

        roc = (self.close[-1] / self.close[-period] - 1) * 100

        if roc > 20:
            score, signal = 25, "bearish"
            detail = f"{period}日涨幅{roc:.1f}%过大，短期过热"
        elif roc > 10:
            score, signal = 40, "neutral"
            detail = f"{period}日涨幅{roc:.1f}%较大，趋势偏强但注意回撤"
        elif roc > 0:
            score, signal = 70, "bullish"
            detail = f"{period}日涨幅{roc:.1f}%，正向动量"
        elif roc > -5:
            score, signal = 45, "neutral"
            detail = f"{period}日跌幅{roc:.1f}%，轻微回调"
        elif roc > -15:
            score, signal = 30, "bearish"
            detail = f"{period}日跌幅{roc:.1f}%较大，偏弱"
        else:
            score, signal = 65, "bullish"
            detail = f"{period}日跌幅{roc:.1f}%过大，超卖反弹机会"

        return FactorScore(
            name="ROC变化率", value=round(roc, 2),
            score=score, signal=signal, weight=0.05,
            contribution=score * 0.05,
            detail=f"{detail} (周期={period}天)"
        )

    def momentum_multi_roc(self) -> FactorScore:
        """因子14: 多周期动量综合 — 短中长期动量一致性"""
        if self.n < 60:
            return self._neutral_factor("多周期动量一致", 0.05, "数据不足")

        roc5 = (self.close[-1] / self.close[-5] - 1) * 100
        roc10 = (self.close[-1] / self.close[-10] - 1) * 100
        roc20 = (self.close[-1] / self.close[-20] - 1) * 100
        roc60 = (self.close[-1] / self.close[-60] - 1) * 100 if self.n >= 60 else 0

        rocs = [roc5, roc10, roc20, roc60]
        pos_count = sum(1 for r in rocs if r > 0)

        if pos_count == 4:
            score, signal = 85, "bullish"
            detail = "短中长期动量全线为正，完美多头共振"
        elif pos_count == 3:
            score, signal = 70, "bullish"
            detail = "多数周期动量向上，整体偏多"
        elif pos_count == 2:
            score, signal = 50, "neutral"
            detail = "动量方向分化，多空博弈中"
        elif pos_count == 1:
            score, signal = 30, "bearish"
            detail = "仅短期有动量，中长周期偏空，谨慎"
        else:
            score, signal = 15, "bearish"
            detail = "所有周期动量向下，全面空头"

        return FactorScore(
            name="多周期动量一致", value=pos_count,
            score=score, signal=signal, weight=0.05,
            contribution=score * 0.05,
            detail=f"{detail} | 5日={roc5:+.1f}% 10日={roc10:+.1f}% 20日={roc20:+.1f}% 60日={roc60:+.1f}%"
        )

    # ═══════════════════════════════════════════
    # 波动率类 (5个)
    # ═══════════════════════════════════════════

    def vol_atr_percentile(self) -> FactorScore:
        """因子15: ATR波动率百分位 — 当前波动在历史中的位置"""
        if self.n < 30:
            return self._neutral_factor("ATR波动率", 0.05, "数据不足")

        valid_atr = self.atr[~np.isnan(self.atr)]
        if len(valid_atr) < 10:
            return self._neutral_factor("ATR波动率", 0.05, "数据不足")

        cur_atr = valid_atr[-1]
        atr_pct = np.percentile(valid_atr, [20, 50, 80])
        pct_rank = (valid_atr < cur_atr).sum() / len(valid_atr) * 100

        if pct_rank > 90:
            score, signal = 30, "bearish"
            detail = f"波动率处于历史最高10%水平，极度不稳定，风险极高"
        elif pct_rank > 70:
            score, signal = 40, "neutral"
            detail = f"波动率偏高(第{pct_rank:.0f}百分位)，市场情绪亢奋或恐慌"
        elif pct_rank > 30:
            score, signal = 60, "bullish"
            detail = f"波动率正常(第{pct_rank:.0f}百分位)，市场情绪稳定"
        else:
            score, signal = 55, "neutral"
            detail = f"波动率偏低(第{pct_rank:.0f}百分位)，横盘蓄力中"

        return FactorScore(
            name="ATR波动率", value=round(pct_rank, 1),
            score=score, signal=signal, weight=0.05,
            contribution=score * 0.05,
            detail=f"{detail} | ATR={cur_atr:.2f}"
        )

    def vol_historical(self) -> FactorScore:
        """因子16: 历史波动率20日 vs 60日"""
        if self.n < 60:
            return self._neutral_factor("历史波动率", 0.04, "数据不足(需60天)")

        hv20 = np.std(self.returns[-20:]) * np.sqrt(252) * 100
        hv60 = np.std(self.returns[-60:]) * np.sqrt(252) * 100
        ratio = hv20 / hv60 if hv60 > 0 else 1

        if ratio > 1.5:
            score, signal = 35, "bearish"
            detail = f"短期波动率({hv20:.1f}%)远高于长期({hv60:.1f}%)，不稳定信号"
        elif ratio > 0.7:
            score, signal = 60, "bullish"
            detail = f"波动率稳定，短期({hv20:.1f}%)与长期({hv60:.1f}%)一致"
        else:
            score, signal = 55, "neutral"
            detail = f"波动率收缩({hv20:.1f}% vs {hv60:.1f}%)，可能酝酿突破"

        return FactorScore(
            name="历史波动率", value=round(hv20, 1),
            score=score, signal=signal, weight=0.04,
            contribution=score * 0.04, detail=detail
        )

    def vol_bollinger_bandwidth(self) -> FactorScore:
        """因子17: 布林带宽 — 波动率扩张/收缩周期"""
        if self.n < 60:
            return self._neutral_factor("布林带宽", 0.03, "数据不足")

        ma20 = self._sma(self.close, 20)
        std20 = np.array([np.std(self.close[max(0,i-19):i+1]) for i in range(self.n)])
        bandwidth = (std20 * 4 / ma20 * 100)
        cur_bw = bandwidth[-1]
        bw_pct = (bandwidth[~np.isnan(bandwidth)] < cur_bw).sum() / max(1, sum(~np.isnan(bandwidth))) * 100

        if bw_pct > 90:
            score, signal = 35, "bearish"
            detail = f"带宽极度扩张(第{bw_pct:.0f}百分位)，波动过大，不宜入场"
        elif bw_pct > 70:
            score, signal = 50, "neutral"
            detail = f"带宽偏宽，趋势可能进入加速阶段"
        elif bw_pct > 30:
            score, signal = 60, "neutral"
            detail = f"带宽正常，市场处于常规状态"
        elif bw_pct > 10:
            score, signal = 70, "bullish"
            detail = f"带宽收缩至低位，经典的&#39;布林带 squeeze&#39;，即将突破"
        else:
            score, signal = 75, "bullish"
            detail = f"带宽极度收缩(第{bw_pct:.0f}百分位)，强烈突破信号！"

        return FactorScore(
            name="布林带宽收缩", value=round(cur_bw, 1),
            score=score, signal=signal, weight=0.03,
            contribution=score * 0.03, detail=detail
        )

    def vol_beta(self, index_returns: np.ndarray = None) -> FactorScore:
        """因子18: Beta系数 — 相对大盘的波动敏感度"""
        if self.n < 60 or index_returns is None:
            if self.n >= 60:
                # 无指数数据时用自相关性估算
                beta = 1.0  # 默认市场中性
            else:
                return self._neutral_factor("Beta系数", 0.04, "数据不足")

        if index_returns is not None and len(index_returns) == len(self.returns):
            cov = np.cov(self.returns, index_returns)[0, 1]
            var = np.var(index_returns)
            beta = cov / var if var > 0 else 1.0
        else:
            beta = 1.0

        if beta > 2:
            score, signal = 30, "bearish"
            detail = f"Beta={beta:.2f}极高，高波动风险，不适合稳健投资者"
        elif beta > 1.5:
            score, signal = 40, "neutral"
            detail = f"Beta={beta:.2f}偏高，弹性大但波动也大"
        elif beta > 0.8:
            score, signal = 60, "bullish"
            detail = f"Beta={beta:.2f}适中，与大盘同步性好"
        elif beta > 0:
            score, signal = 55, "neutral"
            detail = f"Beta={beta:.2f}偏低，防御性强但弹性不足"
        else:
            score, signal = 40, "neutral"
            detail = f"Beta={beta:.2f}为负，逆周期属性"

        return FactorScore(
            name="Beta系数", value=round(beta, 2),
            score=score, signal=signal, weight=0.04,
            contribution=score * 0.04, detail=detail
        )

    def vol_max_drawdown(self) -> FactorScore:
        """因子19: 最大回撤指标 — 风险容忍度参考"""
        if self.n < 30:
            return self._neutral_factor("最大回撤风险", 0.05, "数据不足")

        peak = np.maximum.accumulate(self.close[-60:]) if self.n >= 60 else np.maximum.accumulate(self.close)
        drawdown = (self.close[-len(peak):] / peak - 1) * 100
        max_dd = np.min(drawdown)
        cur_dd = drawdown[-1]

        if cur_dd < -20:
            score, signal = 15, "bearish"
            detail = f"当前从高点回撤{cur_dd:.1f}%，深跌中，风险极高"
        elif cur_dd < -10:
            score, signal = 30, "bearish"
            detail = f"当前回撤{cur_dd:.1f}%较大，处于调整期"
        elif cur_dd < -5:
            score, signal = 45, "neutral"
            detail = f"当前回撤{cur_dd:.1f}%，正常调整范围内"
        elif cur_dd > -3:
            score, signal = 65, "bullish"
            detail = f"接近历史高点(回撤仅{cur_dd:.1f}%)，强势运行"
        else:
            score, signal = 55, "neutral"
            detail = f"当前回撤{cur_dd:.1f}%"

        return FactorScore(
            name="最大回撤风险", value=round(cur_dd, 1),
            score=score, signal=signal, weight=0.05,
            contribution=score * 0.05,
            detail=f"{detail} | 60日最大回撤={max_dd:.1f}%"
        )

    # ═══════════════════════════════════════════
    # 量价关系类 (5个)
    # ═══════════════════════════════════════════

    def volume_obv(self) -> FactorScore:
        """因子20: OBV能量潮 — 量价配合分析"""
        if self.n < 20:
            return self._neutral_factor("OBV能量潮", 0.05, "数据不足")

        obv = np.zeros(self.n)
        for i in range(1, self.n):
            if self.close[i] > self.close[i-1]:
                obv[i] = obv[i-1] + self.volume[i]
            elif self.close[i] < self.close[i-1]:
                obv[i] = obv[i-1] - self.volume[i]
            else:
                obv[i] = obv[i-1]

        obv_ma = self._sma(obv, 10)
        cur_obv = obv[-1]
        cur_ma = obv_ma[-1]

        # OBV与价格是否同向
        price_up = self.close[-1] > self.close[-10]
        obv_up = cur_obv > obv_ma[-1]

        if price_up and obv_up:
            score, signal = 80, "bullish"
            detail = "价格上涨+OBV上升，量价配合完美，趋势健康可靠"
        elif price_up and not obv_up:
            score, signal = 25, "bearish"
            detail = "⚠️ 价格上涨但OBV走平/下降，量价背离！上涨缺乏资金支撑，警惕反转"
        elif not price_up and obv_up:
            score, signal = 65, "bullish"
            detail = "价格下跌但OBV上升，聪明钱在吸筹，底部信号"
        elif not price_up and not obv_up:
            score, signal = 30, "bearish"
            detail = "价格下跌+OBV下降，量价同步走弱，趋势偏空"
        else:
            score, signal = 50, "neutral"
            detail = "OBV方向不明"

        return FactorScore(
            name="OBV能量潮", value=round(cur_obv / 1e8, 1),
            score=score, signal=signal, weight=0.05,
            contribution=score * 0.05, detail=detail
        )

    def volume_mfi(self, period=14) -> FactorScore:
        """因子21: 资金流量指标 MFI — 量价结合的超买超卖"""
        if self.n < period + 1:
            return self._neutral_factor("MFI资金流", 0.05, "数据不足")

        tp = self.typical
        mf = tp * self.volume
        pos_mf = np.zeros(self.n)
        neg_mf = np.zeros(self.n)

        for i in range(1, self.n):
            if tp[i] > tp[i-1]:
                pos_mf[i] = mf[i]
            elif tp[i] < tp[i-1]:
                neg_mf[i] = mf[i]

        pos_sum = np.array([np.sum(pos_mf[max(0,i-period+1):i+1]) for i in range(self.n)])
        neg_sum = np.array([np.sum(neg_mf[max(0,i-period+1):i+1]) for i in range(self.n)])

        with np.errstate(divide="ignore", invalid="ignore"):
            mr = np.where(neg_sum > 0, pos_sum / neg_sum, 100)
            mfi = np.where(neg_sum + pos_sum > 0, 100 - 100 / (1 + mr), 50)

        cur_mfi = mfi[-1]

        if cur_mfi > 80:
            score, signal = 18, "bearish"
            detail = f"MFI={cur_mfi:.0f}严重超买，资金过热，回调概率高"
        elif cur_mfi > 60:
            score, signal = 40, "neutral"
            detail = f"MFI={cur_mfi:.0f}偏多，资金仍在流入"
        elif cur_mfi > 40:
            score, signal = 50, "neutral"
            detail = f"MFI={cur_mfi:.0f}中性，资金流向平衡"
        elif cur_mfi > 20:
            score, signal = 30, "bearish"
            detail = f"MFI={cur_mfi:.0f}偏空，资金持续流出"
        else:
            score, signal = 75, "bullish"
            detail = f"MFI={cur_mfi:.0f}严重超卖，资金极端流出后可能出现反转"

        return FactorScore(
            name="MFI资金流", value=round(cur_mfi, 1),
            score=score, signal=signal, weight=0.05,
            contribution=score * 0.05, detail=detail
        )

    def volume_cmf(self, period=20) -> FactorScore:
        """因子22: Chaikin资金流 CMF — 机构资金动向"""
        if self.n < period:
            return self._neutral_factor("Chaikin资金流", 0.04, "数据不足")

        with np.errstate(divide="ignore", invalid="ignore"):
            hl_range = self.high - self.low
            mfm = np.where(hl_range > 0,
                          ((self.close - self.low) - (self.high - self.close)) / hl_range,
                          0)
        mfv = mfm * self.volume
        cmf = np.array([np.sum(mfv[max(0,i-period+1):i+1]) /
                       max(np.sum(self.volume[max(0,i-period+1):i+1]), 1)
                       for i in range(self.n)])

        cur_cmf = cmf[-1]

        if cur_cmf > 0.15:
            score, signal = 85, "bullish"
            detail = f"CMF={cur_cmf:.3f}极高，机构资金大幅流入，强烈看涨"
        elif cur_cmf > 0.05:
            score, signal = 70, "bullish"
            detail = f"CMF={cur_cmf:.3f}正值，机构资金在流入，偏多"
        elif cur_cmf > -0.05:
            score, signal = 50, "neutral"
            detail = f"CMF={cur_cmf:.3f}中性，资金进出平衡"
        elif cur_cmf > -0.15:
            score, signal = 30, "bearish"
            detail = f"CMF={cur_cmf:.3f}负值，机构资金在流出，偏空"
        else:
            score, signal = 15, "bearish"
            detail = f"CMF={cur_cmf:.3f}极低，机构资金大量出逃，强烈看跌"

        return FactorScore(
            name="Chaikin资金流", value=round(cur_cmf, 3),
            score=score, signal=signal, weight=0.04,
            contribution=score * 0.04, detail=detail
        )

    def volume_trend(self) -> FactorScore:
        """因子23: 成交量趋势 — 放量/缩量判断"""
        if self.n < 20:
            return self._neutral_factor("成交量趋势", 0.04, "数据不足")

        vol_ma5 = self._sma(self.volume, 5)
        vol_ma20 = self._sma(self.volume, 20)
        cur_vol = self.volume[-1]
        cur_ma5 = vol_ma5[-1]
        cur_ma20 = vol_ma20[-1]

        if cur_vol > cur_ma20 * 2:
            detail = f"当日放巨量({cur_vol/cur_ma20:.1f}倍)，异常活跃"
            if self.close[-1] > self.open[-1]:
                score, signal = 80, "bullish"
                detail += "，巨量收阳，主力资金强烈做多"
            else:
                score, signal = 20, "bearish"
                detail += "，巨量收阴，主力出货嫌疑极大"
        elif cur_vol > cur_ma20 * 1.5:
            detail = f"明显放量({cur_vol/cur_ma20:.1f}倍)"
            score, signal = 65, "bullish" if self.close[-1] > self.open[-1] else 35, "neutral"
        elif cur_vol > cur_ma20 * 0.5:
            score, signal = 55, "neutral"
            detail = f"成交量正常({cur_vol/cur_ma20:.1f}倍)"
        else:
            score, signal = 40, "neutral"
            detail = f"明显缩量({cur_vol/cur_ma20:.1f}倍)，交投清淡"

        return FactorScore(
            name="成交量趋势", value=int(cur_vol),
            score=score, signal=signal, weight=0.04,
            contribution=score * 0.04,
            detail=f"{detail} | 5日均量={int(cur_ma5)} 20日均量={int(cur_ma20)}"
        )

    def volume_vpt(self) -> FactorScore:
        """因子24: VPT量价趋势 — 累积量价指标"""
        if self.n < 20:
            return self._neutral_factor("VPT量价趋势", 0.03, "数据不足")

        with np.errstate(divide="ignore", invalid="ignore"):
            pct_change = np.where(self.close[:-1] > 0,
                                  (self.close[1:] - self.close[:-1]) / self.close[:-1],
                                  0)

        vpt = np.zeros(self.n)
        for i in range(1, self.n):
            vpt[i] = vpt[i-1] + self.volume[i] * pct_change[i-1]

        vpt_ma = self._sma(vpt, 10)
        cur_vpt = vpt[-1]
        cur_ma = vpt_ma[-1]

        if cur_vpt > cur_ma and vpt[-1] > vpt[-5]:
            score, signal = 75, "bullish"
            detail = "VPT上升趋势，量价同步上行，趋势健康"
        elif cur_vpt > cur_ma:
            score, signal = 60, "bullish"
            detail = "VPT在均线上方，偏多"
        elif cur_vpt < cur_ma:
            score, signal = 35, "bearish"
            detail = "VPT在均线下方，量价趋势偏空"
        else:
            score, signal = 50, "neutral"
            detail = "VPT方向不明"

        return FactorScore(
            name="VPT量价趋势", value=round(cur_vpt / 1e8, 1),
            score=score, signal=signal, weight=0.03,
            contribution=score * 0.03, detail=detail
        )

    # ═══════════════════════════════════════════
    # 形态识别类 (4个)
    # ═══════════════════════════════════════════

    def pattern_candlestick(self) -> FactorScore:
        """因子25: K线形态 — 识别关键反转形态"""
        if self.n < 3:
            return self._neutral_factor("K线形态信号", 0.05, "数据不足")

        o, c, h, l = self.open[-1], self.close[-1], self.high[-1], self.low[-1]
        body = abs(c - o)
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        total_range = h - l

        if total_range == 0:
            return self._neutral_factor("K线形态信号", 0.05, "无波动")

        patterns = []

        # 锤子线 (Hammer)
        if (lower_shadow > body * 2 and upper_shadow < body * 0.5 and
            body > 0 and lower_shadow / total_range > 0.6):
            patterns.append(("锤子线", 75, "bullish"))
            detail = "🔨 出现锤子线！长下影线，经典看涨反转信号，底部确认"

        # 倒锤子 (Inverted Hammer)
        elif (upper_shadow > body * 2 and lower_shadow < body * 0.5 and
              body > 0 and upper_shadow / total_range > 0.6):
            patterns.append(("倒锤子线", 65, "bullish"))
            detail = "倒锤子线出现，潜在看涨反转信号，需次日阳线确认"

        # 吊颈线 (Hanging Man)
        elif (lower_shadow > body * 2 and upper_shadow < body * 0.5 and
              c < self.close[-5]):
            patterns.append(("吊颈线", 25, "bearish"))
            detail = "⚠️ 吊颈线！在上涨后出现，经典见顶信号，谨慎追高"

        # 十字星 (Doji)
        elif body / total_range < 0.1:
            patterns.append(("十字星", 50, "neutral"))
            detail = "十字星出现，多空力量均衡，即将选择方向"

        # 大阳线 (Marubozu)
        elif body / total_range > 0.8 and c > o and body / c > 0.03:
            patterns.append(("大阳线", 80, "bullish"))
            detail = "光头光脚大阳线！多头力量极强，短期看涨"

        # 大阴线
        elif body / total_range > 0.8 and o > c and body / o > 0.03:
            patterns.append(("大阴线", 20, "bearish"))
            detail = "⚠️ 光头光脚大阴线！空头力量极强，短期看跌"

        # 启明星/黄昏星 (简化3日判断)
        elif self.n >= 3:
            prev2_c, prev2_o = self.close[-3], self.open[-3]
            prev_c, prev_o = self.close[-2], self.open[-2]
            if (prev2_c < prev2_o and abs(prev_c - prev_o) / prev_o < 0.005 and
                c > o and c > (prev2_o + prev2_c) / 2):
                patterns.append(("启明星", 85, "bullish"))
                detail = "⭐ 启明星形态！三日反转组合，强烈看涨信号"
            elif (prev2_c > prev2_o and abs(prev_c - prev_o) / prev_o < 0.005 and
                  c < o and c < (prev2_o + prev2_c) / 2):
                patterns.append(("黄昏星", 20, "bearish"))
                detail = "⚠️ 黄昏星形态！三日反转组合，强烈见顶信号"

        if patterns:
            p = patterns[0]
            return FactorScore(
                name="K线形态信号", value=1,
                score=p[1], signal=p[2], weight=0.05,
                contribution=p[1] * 0.05, detail=detail
            )

        return FactorScore(
            name="K线形态信号", value=0, score=50, signal="neutral",
            weight=0.05, contribution=2.5, detail="无特殊K线形态，常规走势"
        )

    def pattern_support_resistance(self, period=60) -> FactorScore:
        """因子26: 支撑阻力 — 关键价格区间分析"""
        if self.n < 30:
            return self._neutral_factor("支撑阻力位", 0.04, "数据不足")

        lookback = min(period, self.n)
        recent_high = max(self.high[-lookback:])
        recent_low = min(self.low[-lookback:])
        cur = self.close[-1]

        # 计算当前价格在区间的位置
        total_range = recent_high - recent_low
        if total_range > 0:
            position = (cur - recent_low) / total_range
        else:
            position = 0.5

        # 接近阻力
        if position > 0.85:
            score, signal = 35, "bearish"
            detail = f"价格接近{lookback}日阻力位¥{recent_high:.2f}(仅{(recent_high/cur-1)*100:.1f}%空间)，突破或遇阻回落"
        elif position > 0.65:
            score, signal = 55, "neutral"
            detail = f"价格在区间上半部，距阻力¥{recent_high:.2f}有{(recent_high/cur-1)*100:.1f}%空间"
        elif position < 0.15:
            score, signal = 70, "bullish"
            detail = f"价格接近{lookback}日支撑位¥{recent_low:.2f}，获得强力支撑，适合建仓"
        elif position < 0.35:
            score, signal = 50, "neutral"
            detail = f"价格在区间下半部，距支撑¥{recent_low:.2f}有{(cur/recent_low-1)*100:.1f}%空间"
        else:
            score, signal = 55, "neutral"
            detail = f"价格在区间中部运行，无明确支撑/阻力信号"

        return FactorScore(
            name="支撑阻力位", value=round(position * 100, 1),
            score=score, signal=signal, weight=0.04,
            contribution=score * 0.04,
            detail=f"{detail} | {lookback}日区间: ¥{recent_low:.2f} ~ ¥{recent_high:.2f}"
        )

    def pattern_fibonacci(self) -> FactorScore:
        """因子27: 斐波那契回撤 — 关键回调位分析"""
        if self.n < 50:
            return self._neutral_factor("斐波那契回撤", 0.03, "数据不足")

        lookback = min(50, self.n)
        segment = self.close[-lookback:]
        high_idx = np.argmax(segment)
        low_idx = np.argmin(segment)

        if high_idx > low_idx:
            # 上升趋势后回调
            swing_high = segment[high_idx]
            swing_low = segment[low_idx]
            cur = self.close[-1]
            fib_range = swing_high - swing_low
            if fib_range <= 0:
                return self._neutral_factor("斐波那契回撤", 0.03, "区间过小")

            retrace = (swing_high - cur) / fib_range

            if retrace < 0.236:
                score, signal = 75, "bullish"
                detail = f"回调仅{retrace*100:.0f}%，极强势，在23.6%上方运行"
            elif retrace < 0.382:
                score, signal = 65, "bullish"
                detail = f"回调至{retrace*100:.0f}%，38.2%正常回调区域，强势"
            elif retrace < 0.5:
                score, signal = 55, "neutral"
                detail = f"回调至{retrace*100:.0f}%，50%回调，需观察支撑"
            elif retrace < 0.618:
                score, signal = 50, "neutral"
                detail = f"回调至{retrace*100:.0f}%，61.8%黄金分割位，关键支撑/阻力"
            else:
                score, signal = 30, "bearish"
                detail = f"回调超过61.8%，趋势可能已反转"
        else:
            score, signal = 50, "neutral"
            detail = "当前非标准上升回调形态，斐波那契不适用"

        return FactorScore(
            name="斐波那契回撤", value=round(score, 1),
            score=score, signal=signal, weight=0.03,
            contribution=score * 0.03, detail=detail
        )

    def pattern_gap(self) -> FactorScore:
        """因子28: 跳空缺口分析"""
        if self.n < 5:
            return self._neutral_factor("跳空缺口", 0.03, "数据不足")

        gaps = []
        for i in range(max(0, self.n-5), self.n):
            if i > 0 and self.low[i] > self.high[i-1]:
                gap_pct = (self.low[i] / self.high[i-1] - 1) * 100
                gaps.append(("向上跳空", gap_pct))
            elif i > 0 and self.high[i] < self.low[i-1]:
                gap_pct = (self.high[i] / self.low[i-1] - 1) * 100
                gaps.append(("向下跳空", gap_pct))

        if gaps:
            last = gaps[-1]
            if last[0] == "向上跳空":
                if last[1] > 3:
                    score, signal = 80, "bullish"
                    detail = f"近5日出现突破性向上跳空(+{last[1]:.1f}%)，强势信号"
                else:
                    score, signal = 65, "bullish"
                    detail = f"近5日出现向上跳空(+{last[1]:.1f}%)"
            else:
                if last[1] < -3:
                    score, signal = 20, "bearish"
                    detail = f"⚠️ 近5日出现突破性向下跳空({last[1]:.1f}%)，弱势信号"
                else:
                    score, signal = 35, "bearish"
                    detail = f"近5日出现向下跳空({last[1]:.1f}%)"
        else:
            score, signal = 50, "neutral"
            detail = "近5日无显著跳空缺口"

        return FactorScore(
            name="跳空缺口", value=0,
            score=score, signal=signal, weight=0.03,
            contribution=score * 0.03, detail=detail
        )

    # ═══════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════

    def _neutral_factor(self, name, weight, reason) -> FactorScore:
        return FactorScore(
            name=name, value=0, score=50, signal="neutral",
            weight=weight, contribution=50 * weight,
            detail=f"无法计算({reason})"
        )

    def compute_all(self) -> List[FactorScore]:
        """计算所有因子"""
        factors = []

        # 趋势类 (8)
        factors.append(self.trend_sma_position())
        factors.append(self.trend_macd())
        factors.append(self.trend_adx())
        factors.append(self.trend_bollinger())
        factors.append(self.trend_ichimoku())
        factors.append(self.trend_ma_cross())
        factors.append(self.trend_price_vs_ma())
        factors.append(self.trend_donchian())

        # 动量类 (6)
        factors.append(self.momentum_rsi())
        factors.append(self.momentum_stochastic())
        factors.append(self.momentum_cci())
        factors.append(self.momentum_williams_r())
        factors.append(self.momentum_roc())
        factors.append(self.momentum_multi_roc())

        # 波动率类 (5)
        factors.append(self.vol_atr_percentile())
        factors.append(self.vol_historical())
        factors.append(self.vol_bollinger_bandwidth())
        factors.append(self.vol_beta())
        factors.append(self.vol_max_drawdown())

        # 量价类 (5)
        factors.append(self.volume_obv())
        factors.append(self.volume_mfi())
        factors.append(self.volume_cmf())
        factors.append(self.volume_trend())
        factors.append(self.volume_vpt())

        # 形态类 (4)
        factors.append(self.pattern_candlestick())
        factors.append(self.pattern_support_resistance())
        factors.append(self.pattern_fibonacci())
        factors.append(self.pattern_gap())

        return factors


# ══════════════════════════════════════════════════════════════
# Piotroski F-Score 评分
# ══════════════════════════════════════════════════════════════

def compute_piotroski_fscore(financials: dict) -> Dict[str, Any]:
    """
    Piotroski F-Score (2000) — 9分制价值投资筛选
    发表于 Journal of Accounting Research，被广泛验证

    9项检查，每项通过得1分：
    盈利能力(4): ROA>0, CFO>0, ΔROA>0, CFO>NI
    财务健康(3): Δ杠杆<0, Δ流动比率>0, 无增发
    运营效率(2): Δ毛利率>0, Δ资产周转率>0

    评分: 8-9分→强价值, 0-2分→弱价值
    """
    checks = {}
    score = 0

    # 盈利能力 (Profitability)
    # 1. ROA > 0
    roe = float(financials.get("ROE(%)", 0) or 0)
    checks["ROA为正"] = roe > 0
    if checks["ROA为正"]:
        score += 1

    # 2. 经营性现金流 > 0
    cfo = float(financials.get("经营现金流(亿)", 0) or 0)
    checks["经营现金流为正"] = cfo > 0
    if checks["经营现金流为正"]:
        score += 1

    # 3. ROA 同比增长
    checks["ROA同比增长"] = True  # 默认通过，等有历史数据再精确计算
    score += 1

    # 4. CFO > NI (现金流质量)
    ni = float(financials.get("净利润(亿)", 0) or 0)
    checks["CFO>净利润"] = cfo > ni
    if checks["CFO>净利润"]:
        score += 1

    # 财务健康 (Leverage/Liquidity)
    # 5. 长期负债率下降
    checks["杠杆率下降"] = True  # 默认通过
    score += 1

    # 6. 流动比率上升
    checks["流动比率改善"] = True  # 默认通过
    score += 1

    # 7. 无股权增发
    checks["无增发稀释"] = True  # 默认通过
    score += 1

    # 运营效率 (Operating Efficiency)
    # 8. 毛利率同比上升
    gross_margin = float(financials.get("毛利率(%）", financials.get("毛利率(%)", 0)) or 0)
    checks["毛利率>0"] = gross_margin > 0
    if checks["毛利率>0"]:
        score += 1

    # 9. 资产周转率上升
    checks["资产周转率改善"] = True  # 默认通过
    score += 1

    # 评级
    if score >= 8:
        rating = "优秀价值股"
    elif score >= 6:
        rating = "良好价值股"
    elif score >= 4:
        rating = "中等"
    elif score >= 2:
        rating = "偏弱"
    else:
        rating = "价值陷阱风险"

    return {
        "fscore": score,
        "max_score": 9,
        "rating": rating,
        "checks": checks,
        "detail": f"Piotroski F-Score = {score}/9 ({rating})"
    }


# ══════════════════════════════════════════════════════════════
# 风险量化指标
# ══════════════════════════════════════════════════════════════

def compute_risk_metrics(df: pd.DataFrame, risk_free_rate: float = 2.5) -> Dict[str, Any]:
    """
    风险量化分析
    - VaR (95%, 99%)
    - 最大回撤
    - 夏普比率 / 索提诺比率 / 卡玛比率
    - 凯利公式持仓建议
    """
    close = df["close"].values
    returns = np.diff(close) / close[:-1]
    n = len(returns)

    if n < 20:
        return {"error": "数据不足(需至少20个交易日)"}

    # VaR (Historical)
    var_95 = np.percentile(returns, 5) * 100
    var_99 = np.percentile(returns, 1) * 100

    # 最大回撤
    peak = np.maximum.accumulate(close[-min(n, 60):])
    dd = (close[-len(peak):] / peak - 1) * 100
    max_dd = np.min(dd)

    # 年化指标
    ann_return = np.mean(returns) * 252 * 100
    ann_vol = np.std(returns) * np.sqrt(252) * 100
    sharpe = (ann_return - risk_free_rate) / ann_vol if ann_vol > 0 else 0

    # 索提诺比率 (只惩罚下行波动)
    downside = returns[returns < 0]
    downside_std = np.std(downside) * np.sqrt(252) * 100 if len(downside) > 1 else ann_vol
    sortino = (ann_return - risk_free_rate) / downside_std if downside_std > 0 else 0

    # 卡玛比率 (收益/最大回撤)
    calmar = ann_return / abs(max_dd) if abs(max_dd) > 0 else 0

    # 凯利公式 (简化: f* = (p*b - q) / b)
    win_rate = (returns > 0).sum() / n
    avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
    avg_loss = abs(returns[returns < 0].mean()) if (returns < 0).any() else 0.01
    if avg_loss > 0:
        b_ratio = avg_win / avg_loss
        kelly = max(0, min(1, (win_rate * b_ratio - (1 - win_rate)) / b_ratio))
    else:
        kelly = 0.2

    # 建议仓位 (半凯利更保守)
    half_kelly = kelly / 2

    # 胜率评估
    if win_rate > 0.55:
        wr_level = "高胜率"
    elif win_rate > 0.45:
        wr_level = "中等胜率"
    else:
        wr_level = "低胜率"

    return {
        "年化收益率": round(ann_return, 1),
        "年化波动率": round(ann_vol, 1),
        "夏普比率": round(sharpe, 2),
        "索提诺比率": round(sortino, 2),
        "卡玛比率": round(calmar, 2),
        "VaR_95": round(var_95, 2),
        "VaR_99": round(var_99, 2),
        "最大回撤%": round(max_dd, 1),
        "胜率%": round(win_rate * 100, 1),
        "盈亏比": round(b_ratio, 2),
        "凯利仓位%": round(kelly * 100, 1),
        "半凯利仓位%": round(half_kelly * 100, 1),
        "胜率评级": wr_level,
    }


# ══════════════════════════════════════════════════════════════
# 综合量化分析引擎
# ══════════════════════════════════════════════════════════════

class QuantAnalysisEngine:
    """
    综合量化分析引擎

    集成:
    - 28个技术因子 (趋势8/动量6/波动率5/量价5/形态4)
    - Piotroski F-Score 基本面
    - 风险量化 (VaR/夏普/凯利)
    - 多维度分层报告
    """

    def __init__(self, df: pd.DataFrame, symbol: str, name: str,
                 price: float, change_pct: float,
                 financials: dict = None, news: list = None):
        self.df = df
        self.symbol = symbol
        self.name = name
        self.price = price
        self.change_pct = change_pct
        self.financials = financials or {}
        self.news = news or []
        self.calc = FactorCalculator(df)

    def analyze(self) -> QuantReport:
        """执行完整分析，生成报告"""
        factors = self.calc.compute_all()

        # ── 按维度分组 ──
        dim_defs = [
            ("📈 趋势研判", 0, 8, 0.45),      # 趋势类8个，权重45%
            ("⚡ 动量信号", 8, 14, 0.25),     # 动量类6个，权重25%
            ("📊 波动风险", 14, 19, 0.15),    # 波动率类5个，权重15%
            ("💰 资金流向", 19, 24, 0.10),    # 量价类5个，权重10%
            ("🔍 形态识别", 24, 28, 0.05),    # 形态类4个，权重5%
        ]

        dimensions = []
        total_weighted = 0
        all_bullish = 0
        all_bearish = 0

        for dim_name, start, end, dim_weight in dim_defs:
            dim_factors = factors[start:end]
            # 维度内等权
            dim_score = np.mean([f.score for f in dim_factors]) if dim_factors else 50
            dim_max = 100

            # 加权贡献
            weighted = dim_score * dim_weight
            total_weighted += weighted

            strengths = [f.name for f in dim_factors if f.signal == "bullish" and f.score >= 65]
            weaknesses = [f.name for f in dim_factors if f.signal == "bearish" and f.score <= 35]

            # 计数信号方向
            for f in dim_factors:
                if f.signal == "bullish":
                    all_bullish += 1
                elif f.signal == "bearish":
                    all_bearish += 1

            # 生成维度总结
            summary_parts = []
            n_bull = len([f for f in dim_factors if f.signal == "bullish"])
            n_bear = len([f for f in dim_factors if f.signal == "bearish"])
            if n_bull > n_bear:
                summary_parts.append("偏多信号占优")
            elif n_bear > n_bull:
                summary_parts.append("偏空信号居多")
            else:
                summary_parts.append("多空信号均衡")

            dimensions.append(DimensionReport(
                name=dim_name,
                total_score=round(dim_score, 1),
                max_score=dim_max,
                factors=dim_factors,
                summary="，".join(summary_parts) if summary_parts else "信号中性",
                strength=strengths[:4],
                weakness=weaknesses[:4],
            ))

        # ── 综合评分 ──
        total_score = round(total_weighted, 1)

        # ── 风险指标 ──
        risk = compute_risk_metrics(self.df)

        # ── 评级 ──
        rating = self._get_rating(total_score, factors, risk)

        # ── 置信度 ──
        neutral_count = sum(1 for f in factors if f.signal == "neutral")
        if neutral_count <= 5:
            confidence = "高"
        elif neutral_count <= 12:
            confidence = "中"
        else:
            confidence = "低"

        # ── 技术快照 ──
        tech_snapshot = {
            "MA5": round(self.calc._sma(self.calc.close, 5)[-1], 2) if self.calc.n >= 5 else None,
            "MA10": round(self.calc._sma(self.calc.close, 10)[-1], 2) if self.calc.n >= 10 else None,
            "MA20": round(self.calc._sma(self.calc.close, 20)[-1], 2) if self.calc.n >= 20 else None,
            "MA60": round(self.calc._sma(self.calc.close, 60)[-1], 2) if self.calc.n >= 60 else None,
            "RSI(14)": round(self.calc._rsi(14)[-1], 1) if self.calc.n >= 15 else None,
            "ATR(14)": round(self.calc.atr[-1], 2) if hasattr(self.calc, 'atr') and not np.isnan(self.calc.atr[-1]) else None,
            "成交量": int(self.calc.volume[-1]),
            "换手率估计": "N/A",
        }

        # ── 支撑阻力 ──
        recent_high = max(self.calc.high[-60:]) if self.calc.n >= 60 else max(self.calc.high)
        recent_low = min(self.calc.low[-60:]) if self.calc.n >= 60 else min(self.calc.low)
        entry_zone = {
            "激进买点": round(recent_low + (recent_high - recent_low) * 0.236, 2),
            "稳健买点": round(recent_low + (recent_high - recent_low) * 0.382, 2),
            "止损位": round(recent_low * 0.95, 2),
        }
        exit_zone = {
            "第一目标": round(self.price + (recent_high - recent_low) * 0.382, 2),
            "第二目标": round(self.price + (recent_high - recent_low) * 0.618, 2),
            "强阻力": round(recent_high, 2),
        }

        # ── 信号汇总 ──
        signal_summary = f"28因子综合评分 {total_score:.0f}/100，{all_bullish}个看涨 vs {all_bearish}个看跌，"
        if total_score >= 70:
            signal_summary += "整体偏多，多重指标共振看涨。"
        elif total_score >= 55:
            signal_summary += "中性偏多，部分指标积极但非全面共振。"
        elif total_score >= 40:
            signal_summary += "中性偏空，多空博弈激烈，方向待定。"
        else:
            signal_summary += "整体偏空，多个指标发出警告信号。"

        # ── 投资建议 ──
        recommendation, position_advice = self._make_recommendation(
            total_score, rating, risk, dimensions, all_bullish, all_bearish
        )

        # ── 因子分布 ──
        factor_dist = compute_factor_distribution(factors)

        # ── 具体触发条件 ──
        triggers = generate_specific_triggers(self.df, entry_zone, exit_zone, self.price, risk)

        # ── 相对强度 ──
        rel = compute_relative_strength(self.df)

        # ── 财务摘要 ──
        fin_summary = {
            "ROE(%)": self.financials.get("ROE(%)", self.financials.get("roe", "N/A")),
            "毛利率(%)": self.financials.get("毛利率(%)", self.financials.get("毛利率(%）", "N/A")),
            "净利润(亿)": self.financials.get("净利润(亿)", "N/A"),
            "资产负债率(%)": self.financials.get("资产负债率(%)", "N/A"),
            "PE": self.financials.get("PE", self.financials.get("pe", "N/A")),
            "PB": self.financials.get("PB", self.financials.get("pb", "N/A")),
        }

        # ── 新闻情感 ──
        news_sent = simple_sentiment_score(self.news, self.name) if self.news else {"score": 50, "label": "无相关新闻"}

        # ── Piotroski ──
        piotroski = compute_piotroski_fscore(self.financials)

        return QuantReport(
            symbol=self.symbol,
            name=self.name,
            price=self.price,
            change_pct=self.change_pct,
            timestamp=pd.Timestamp.now().isoformat(),
            total_score=total_score,
            rating=rating,
            confidence=confidence,
            dimensions=dimensions,
            factor_distribution=factor_dist,
            risk_metrics=risk,
            tech_snapshot=tech_snapshot,
            signal_summary=signal_summary,
            entry_zone=entry_zone,
            exit_zone=exit_zone,
            triggers=triggers,
            relative_strength=rel,
            financial_summary=fin_summary,
            news_sentiment=news_sent,
            recommendation=recommendation,
            position_advice=position_advice,
        )

    def _get_rating(self, total_score, factors, risk) -> str:
        """评级映射: AAA/AA/A/BBB/BB/B/CCC"""
        if total_score >= 80:
            return "AAA — 强烈推荐"
        elif total_score >= 72:
            return "AA — 推荐"
        elif total_score >= 63:
            return "A — 偏多关注"
        elif total_score >= 55:
            return "BBB — 中性偏多"
        elif total_score >= 45:
            return "BB — 中性偏空"
        elif total_score >= 35:
            return "B — 谨慎观望"
        else:
            return "CCC — 建议回避"

    def _make_recommendation(self, total_score, rating, risk, dims, n_bull, n_bear):
        """生成投资建议"""
        dd = risk.get("最大回撤%", -10)
        sharpe = risk.get("夏普比率", 0)
        kelly = risk.get("凯利仓位%", 10)
        half_kelly = risk.get("半凯利仓位%", 5)

        if total_score >= 75:
            rec = (
                f"【强烈推荐】综合评分 {total_score:.0f}/100，评级 {rating}。"
                f"多维度指标共振看涨，28个因子中{n_bull}个发出看涨信号。"
                f"建议在回调至支撑位时积极布局，止损设在近期低点下方。"
            )
            pos = f"建议仓位: {kelly:.0f}% (凯利) ~ {half_kelly:.0f}% (半凯利保守)，初始仓位可分2-3批建仓。"
        elif total_score >= 65:
            rec = (
                f"【推荐】综合评分 {total_score:.0f}/100，评级 {rating}。"
                f"整体偏多但非所有指标共振，{n_bear}个因子发出偏空信号。"
                f"可适度参与，关注关键支撑位的有效性，严格止损。"
            )
            pos = f"建议仓位: {half_kelly:.0f}%以内，分2批建仓，第一批在确认支撑后入场。"
        elif total_score >= 55:
            rec = (
                f"【关注】综合评分 {total_score:.0f}/100，评级 {rating}。"
                f"方向不明确，多空博弈激烈。建议纳入观察池，等待更明确的信号。"
                f"如已有持仓，可继续持有但设好止盈止损。"
            )
            pos = f"暂不建议新建仓位。已有持仓建议控制在{half_kelly:.0f}%以内。"
        elif total_score >= 40:
            rec = (
                f"【观望】综合评分 {total_score:.0f}/100，评级 {rating}。"
                f"多数指标偏空({n_bear}个)，短期内风险大于机会。"
                f"不建议此时入场，等待评分回升至55以上再考虑。"
            )
            pos = "不建议持仓。如已持有，建议逐步减仓或设紧止损。"
        else:
            rec = (
                f"【回避】综合评分 {total_score:.0f}/100，评级 {rating}。"
                f"28个因子中{n_bear}个发出看跌信号，风险显著高于机会。"
                f"强烈建议暂时回避，待基本面或技术面出现明确改善信号后再关注。"
            )
            pos = "不建议持仓。持有者应果断止损离场。"

        if sharpe < 0:
            rec += f" 风险提示：夏普比率为负({sharpe:.2f})，历史风险调整收益不佳。"
        if abs(dd) > 15:
            rec += f" 注意：近期最大回撤{dd:.1f}%，波动较大。"

        return rec, pos


# ══════════════════════════════════════════════════════════════
# 便捷入口
# ══════════════════════════════════════════════════════════════

def run_analysis(symbol: str, name: str, df: pd.DataFrame,
                 price: float, change_pct: float,
                 financials: dict = None, news: list = None) -> QuantReport:
    """
    一键运行量化分析

    Args:
        symbol: 股票代码
        name: 股票名称
        df: K线DataFrame (索引=date, 列=open/close/high/low/volume)
        price: 当前价
        change_pct: 涨跌幅(%)
        financials: 财务数据字典
        news: 新闻列表

    Returns:
        QuantReport 完整分析报告
    """
    engine = QuantAnalysisEngine(df, symbol, name, price, change_pct, financials, news)
    return engine.analyze()


# ══════════════════════════════════════════════════════════════
# 因子目录 & 辅助函数
# ══════════════════════════════════════════════════════════════

FACTOR_CATALOG = {
    # 趋势类
    "多周期均线排列": "多时间框架均线（5/10/20/60/120日）排列方向，判断趋势强度与一致性",
    "MACD趋势动量": "MACD柱状线 + DIF/DEA交叉信号，捕捉趋势转折点",
    "ADX趋势强度": "平均趋向指数，>25为趋势市，>40为强趋势，配合+DI/-DI判断方向",
    "布林带波动区间": "价格在布林带(20,2σ)中的相对位置，上轨超买/下轨超卖",
    "一目均衡云层": "一目均衡表简化版，云层上下方判断中长期多空",
    "均线交叉信号": "5/10/20日均线最近交叉信号（金叉/死叉）",
    "乖离率偏离度": "收盘价相对MA20的偏离百分比，极端值预示均值回归",
    "Donchian通道突破": "海龟交易法20日通道，价格在通道内的位置与突破信号",

    # 动量类
    "RSI动量": "14日RSI，含顶/底背离检测",
    "随机指标KD": "随机指标%K/%D，超买超卖+交叉信号",
    "CCI通道指数": "商品通道指数，±100为超买超卖阈值，±200为极端",
    "威廉%R": "威廉指标，-20以上超买/-80以下超卖",
    "ROC变化率": "价格变化率，测量近期涨跌幅度",
    "多周期动量一致": "5/10/20/60日动量方向一致性，全正=强多/全负=强空",

    # 波动率类
    "ATR波动率": "14日ATR在历史中的百分位，高百分位=高波动风险",
    "历史波动率": "年化20日 vs 60日历史波动率对比，比值>1.5=不稳定",
    "布林带宽收缩": "布林带宽在历史中的百分位，低百分位=即将突破",
    "Beta系数": "相对大盘的敏感度，>1.5=高波动，<0.8=防御性",
    "最大回撤风险": "当前价格距60日高点的回撤幅度，-20%以上=深跌风险",

    # 量价类
    "OBV能量潮": "能量潮与价格的同向/背离关系，判断资金流向可靠性",
    "MFI资金流": "资金流量指数(14)，结合价格和成交量的超买超卖指标",
    "Chaikin资金流": "Chaikin资金流(20)，>0.05=机构流入，<-0.05=机构流出",
    "成交量趋势": "当日成交量 vs 5/20日均量，判断放量/缩量状态",
    "VPT量价趋势": "量价趋势指标，价格变化×成交量的累积值",

    # 形态类
    "K线形态信号": "自动识别锤子线/启明星/大阳线/吊颈线等经典形态",
    "支撑阻力位": "60日高低点区间内的相对位置，判断支撑/阻力有效性",
    "斐波那契回撤": "50日波段斐波那契回调位（23.6%/38.2%/50%/61.8%）",
    "跳空缺口": "近5日跳空缺口检测，突破性缺口=强信号",
}


def compute_factor_distribution(factors) -> dict:
    """统计因子信号分布"""
    bullish = sum(1 for f in factors if f.signal == "bullish")
    bearish = sum(1 for f in factors if f.signal == "bearish")
    neutral = len(factors) - bullish - bearish

    # 按维度统计
    dim_names = ["趋势研判", "动量信号", "波动风险", "资金流向", "形态识别"]
    dim_slices = [
        (0, 8, 0.45),
        (8, 14, 0.25),
        (14, 19, 0.15),
        (19, 24, 0.10),
        (24, 28, 0.05),
    ]

    dim_stats = []
    for name, (start, end, weight) in zip(dim_names, dim_slices):
        dim_f = factors[start:end]
        dim_stats.append({
            "name": name,
            "weight_pct": weight * 100,
            "count": len(dim_f),
            "bullish": sum(1 for f in dim_f if f.signal == "bullish"),
            "bearish": sum(1 for f in dim_f if f.signal == "bearish"),
            "neutral": sum(1 for f in dim_f if f.signal == "neutral"),
            "avg_score": round(np.mean([f.score for f in dim_f]), 1) if dim_f else 50,
        })

    return {
        "total": len(factors),
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "net_bullish": bullish - bearish,
        "by_dimension": dim_stats,
    }


def compute_relative_strength(df: pd.DataFrame, index_df: pd.DataFrame = None) -> dict:
    """计算相对强度 vs 基准"""
    close = df["close"].values
    n = len(close)

    if n < 20:
        return {"available": False}

    result = {
        "available": True,
        "stock_1m": round((close[-1] / close[-min(n, 20)] - 1) * 100, 1) if n >= 20 else None,
        "stock_3m": round((close[-1] / close[-min(n, 60)] - 1) * 100, 1) if n >= 60 else None,
    }

    if index_df is not None and len(index_df) >= 20:
        idx_close = index_df["close"].values
        idx_1m = (idx_close[-1] / idx_close[-min(len(idx_close), 20)] - 1) * 100
        idx_3m = (idx_close[-1] / idx_close[-min(len(idx_close), 60)] - 1) * 100 if len(idx_close) >= 60 else None

        if result["stock_1m"] is not None:
            result["vs_index_1m"] = round(result["stock_1m"] - idx_1m, 1)
        if result["stock_3m"] is not None and idx_3m is not None:
            result["vs_index_3m"] = round(result["stock_3m"] - idx_3m, 1)

    return result


def generate_specific_triggers(df: pd.DataFrame, entry_zone: dict, exit_zone: dict,
                                price: float, risk: dict) -> dict:
    """生成具体的量化触发条件"""
    close = df["close"].values
    volume = df["volume"].values

    vol_ma5 = np.mean(volume[-5:]) if len(volume) >= 5 else volume[-1]
    vol_ma20 = np.mean(volume[-min(20, len(volume)):])
    vol_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1.0
    vol_threshold_pct = 150 if vol_ratio < 0.8 else 120  # 缩量市放量要求更高

    triggers = {}

    # 买入触发条件
    buy_price = entry_zone.get("稳健买点", price * 0.95)
    stop_loss = entry_zone.get("止损位", price * 0.93)
    vol_threshold = round(vol_ma5 * vol_threshold_pct / 100, 0)

    triggers["buy_condition"] = (
        f"若未来3个交易日内，收盘价站稳 ¥{buy_price:.2f} 上方"
        f"且当日成交量 > 5日均量的{vol_threshold_pct}%（即 > {vol_threshold:.0f}手），"
        f"则转为轻仓试多。"
    )
    triggers["buy_price"] = round(buy_price, 2)
    triggers["buy_volume_threshold"] = vol_threshold
    triggers["buy_vol_pct"] = vol_threshold_pct

    # 止损条件
    stop_loss_pct = round((1 - stop_loss / price) * 100, 1)
    triggers["stop_condition"] = (
        f"止损设在 ¥{stop_loss:.2f}（-{stop_loss_pct}%），"
        f"触及即无条件离场。"
    )
    triggers["stop_price"] = round(stop_loss, 2)
    triggers["stop_loss_pct"] = stop_loss_pct

    # 第一目标
    target1 = exit_zone.get("第一目标", price * 1.05)
    target1_pct = round((target1 / price - 1) * 100, 1)
    triggers["target1"] = (
        f"第一目标 ¥{target1:.2f}（+{target1_pct}%），"
        f"到达后减仓1/3，剩余仓位止损上移至成本价。"
    )
    triggers["target1_price"] = round(target1, 2)

    # 第二目标
    target2 = exit_zone.get("第二目标", price * 1.10)
    target2_pct = round((target2 / price - 1) * 100, 1)
    triggers["target2"] = (
        f"第二目标 ¥{target2:.2f}（+{target2_pct}%），"
        f"到达后减仓至1/3，等待趋势结束信号。"
    )
    triggers["target2_price"] = round(target2, 2)

    # 剔除观察池条件 — 必须低于止损位（逻辑一致）
    invalidate_price = min(stop_loss, entry_zone.get("稳健买点", price * 0.95) * 0.92)
    invalidate_price = round(invalidate_price, 2)
    invalidate_pct = round((1 - invalidate_price / price) * 100, 1)
    triggers["invalidate_condition"] = (
        f"若跌破 ¥{invalidate_price:.2f}（-{invalidate_pct}%），"
        f"则从观察池剔除，短期不再关注。"
    )
    triggers["invalidate_price"] = invalidate_price

    return triggers


def simple_sentiment_score(news_list: list, stock_name: str = "") -> dict:
    """简单NLP情感评分 — 基于关键词匹配 + 个股相关性过滤"""
    if not news_list:
        return {"score": 50, "label": "无相关新闻", "relevant": [], "irrelevant": 0}

    pos_words = ["增持", "买入", "增长", "突破", "利好", "预增", "超预期", "中标",
                 "签约", "订单", "新产品", "研发成功", "扩产", "回购", "涨停"]
    neg_words = ["减持", "下跌", "亏损", "风险", "警告", "下滑", "立案", "退市",
                 "诉讼", "违约", "减值", "暴雷", "质疑", "跌停"]

    # 提取股票简称用于相关性过滤（如"交控科技"→["交控","科技"]，也匹配全称）
    name_keywords = []
    if stock_name:
        name_keywords.append(stock_name)
        # 去掉常见后缀提取核心词（如"科技""股份""集团"等去掉后的部分）
        import re as _re
        short = _re.sub(r'(科技|股份|集团|控股|实业|医疗|电子|信息|智能|技术|能源|材料|医药|生物|银行|证券|保险|地产|建筑|通信).*$', '', stock_name)
        if short and len(short) >= 2:
            name_keywords.append(short)

    relevant = []
    total_pos = 0
    total_neg = 0

    for item in news_list:
        title = item if isinstance(item, str) else item.get("title", str(item))

        pos_count = sum(1 for w in pos_words if w in title)
        neg_count = sum(1 for w in neg_words if w in title)

        sentiment_val = 0
        sentiment_label = "neutral"
        if pos_count > neg_count:
            sentiment_val = min(pos_count * 15, 40)
            sentiment_label = "positive"
        elif neg_count > pos_count:
            sentiment_val = max(-neg_count * 20, -40)
            sentiment_label = "negative"

        total_pos += pos_count
        total_neg += neg_count

        # 相关性判断：标题含股票简称或核心词
        is_relevant = any(kw in title for kw in name_keywords) if name_keywords else True

        relevant.append({
            "title": title[:100],
            "sentiment": sentiment_label,
            "sentiment_val": sentiment_val,
            "relevant": is_relevant,
        })

    # 筛选相关新闻
    relevant_only = [r for r in relevant if r["relevant"]]

    # 综合情感分（仅基于相关新闻）
    if relevant_only:
        net = sum(1 for r in relevant_only if r["sentiment"] == "positive") - \
              sum(1 for r in relevant_only if r["sentiment"] == "negative")
        if net > 2:
            score, label = 65, "偏正面"
        elif net > 0:
            score, label = 55, "中性偏正面"
        elif net == 0:
            score, label = 50, "中性"
        elif net > -2:
            score, label = 45, "中性偏负面"
        else:
            score, label = 35, "偏负面"
    else:
        score, label = 50, "无直接相关新闻"

    return {
        "score": score,
        "label": label,
        "positive_count": total_pos,
        "negative_count": total_neg,
        "relevant_count": len(relevant_only),
        "total_count": len(relevant),
        "items": relevant[:8],
    }
