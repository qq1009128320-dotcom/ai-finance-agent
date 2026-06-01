"""
AI智投量化平台 v4 - Backend Configuration
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用
    APP_NAME: str = "AI智投量化平台"
    APP_VERSION: str = "4.0.0"
    DEBUG: bool = True
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["*"]
    
    # 行情数据
    QUOTE_PROVIDER: str = "tencent"  # tencent | tushare
    TUSHARE_TOKEN: Optional[str] = None
    
    # AI API
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    
    # 回测
    BACKTEST_DEFAULT_CAPITAL: float = 100000.0
    
    # 策略存储
    STRATEGY_DIR: str = "./strategies"
    
    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 策略存储目录
STRATEGY_DIR = PROJECT_ROOT / settings.STRATEGY_DIR
STRATEGY_DIR.mkdir(exist_ok=True)
