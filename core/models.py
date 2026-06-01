"""
AI Quantitative Strategy Platform v4 - Pydantic Data Models
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ==================== 量化分析模型 ====================

class FactorScore(BaseModel):
    """因子评分"""
    name: str
    value: float
    score: float = Field(..., ge=0, le=100)
    signal: str  # bullish | bearish | neutral
    weight: float
    contribution: float
    detail: str


class DimensionReport(BaseModel):
    """维度报告"""
    name: str
    total_score: float
    max_score: float
    factors: List[FactorScore]
    summary: str
    strengths: List[str]
    weaknesses: List[str]


class QuantAnalysisRequest(BaseModel):
    """量化分析请求"""
    symbol: str = Field(..., description="股票代码，如 600036")
    name: Optional[str] = Field(None, description="股票名称")
    period: str = Field("day", description="K线周期: day | week | month")
    count: int = Field(60, ge=30, le=500, description="K线数量")


class QuantAnalysisResponse(BaseModel):
    """量化分析响应"""
    symbol: str
    name: str
    price: float
    change_pct: float
    timestamp: str
    
    # 综合评分
    total_score: float
    rating: str  # AAA | AA | A | BBB | BB | B | CCC
    confidence: str
    
    # 维度报告
    dimensions: List[DimensionReport]
    
    # 因子分布
    factor_distribution: Dict[str, int]
    
    # 风险指标
    risk_metrics: Dict[str, Any]
    
    # 操作建议
    entry_zone: Optional[Dict[str, float]] = None
    exit_zone: Optional[Dict[str, float]] = None
    recommendation: str
    position_advice: str


# ==================== 市场扫描模型 ====================

class MarketScanRequest(BaseModel):
    """市场扫描请求"""
    scope: str = Field("top200", description="扫描范围: top200 | top500 | all")
    min_score: float = Field(60, ge=0, le=100, description="最低评分")
    sort_by: str = Field("score", description="排序字段: score | volume | change")
    limit: int = Field(50, ge=1, le=200, description="返回数量")


class StockSnapshot(BaseModel):
    """个股快照"""
    symbol: str
    name: str
    price: float
    change_pct: float
    volume: float
    score: float
    rating: str
    signal: str  # buy | sell | hold


class MarketScanResponse(BaseModel):
    """市场扫描响应"""
    timestamp: str
    total_stocks: int
    avg_score: float
    bullish_count: int
    bearish_count: int
    neutral_count: int
    top_stocks: List[StockSnapshot]
    weak_stocks: List[StockSnapshot]


# ==================== 策略模型 ====================

class StrategyCreateRequest(BaseModel):
    """创建策略请求"""
    name: str
    code: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class StrategyResponse(BaseModel):
    """策略响应"""
    id: str
    name: str
    code: str
    description: Optional[str]
    tags: List[str]
    created_at: str
    updated_at: str
    version: int


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    total: int
    strategies: List[StrategyResponse]


class StrategyValidateRequest(BaseModel):
    """策略验证请求"""
    code: str


class StrategyValidateResponse(BaseModel):
    """策略验证响应"""
    is_valid: bool
    message: str


# ==================== AI策略生成模型 ====================

class AIStrategyGenerateRequest(BaseModel):
    """AI策略生成请求"""
    prompt: str = Field(..., description="策略描述")
    style: str = Field("balanced", description="策略风格: conservative | balanced | aggressive")


class AIStrategyGenerateResponse(BaseModel):
    """AI策略生成响应"""
    code: str
    explanation: str
    is_valid: bool
    validation_message: str


# ==================== 回测模型 ====================

class BacktestRequest(BaseModel):
    """回测请求"""
    code: str = Field(..., description="策略代码")
    symbol: str = Field(..., description="回测标的")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = Field(100000.0, description="初始资金")


class BacktestMetrics(BaseModel):
    """回测指标"""
    total_return: Optional[float] = None
    annual_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    total_trades: Optional[int] = None
    buy_count: Optional[int] = None
    sell_count: Optional[int] = None
    initial_capital: float
    final_capital: Optional[float] = None


class TradeRecord(BaseModel):
    """交易记录"""
    day: Optional[int] = None
    type: str  # buy | sell
    symbol: str
    price: float
    reason: str


class BacktestResponse(BaseModel):
    """回测响应"""
    symbol: str
    start_date: str
    end_date: str
    status: str  # success | error
    message: str
    metrics: BacktestMetrics
    trades: List[TradeRecord]


# ==================== 健康检查模型 ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]
