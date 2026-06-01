"""
AI智投量化平台 v4 - AI Strategy Generation Service
"""

import sys
import os
from pathlib import Path
from typing import Tuple, Dict, Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings
from core.models import AIStrategyGenerateRequest, AIStrategyGenerateResponse


# 从ai_strategy模块复用核心逻辑
from ai_strategy import (
    generate_strategy as _generate_strategy,
    validate_strategy_code as _validate_strategy_code,
    STRATEGY_SYSTEM_PROMPT,
)


class AIService:
    """AI策略生成服务"""
    
    def generate(self, request: AIStrategyGenerateRequest) -> AIStrategyGenerateResponse:
        """
        生成AI策略
        
        Args:
            request: 生成请求
        
        Returns:
            生成响应
        """
        # 调用策略生成
        code, explanation = _generate_strategy(
            request.prompt, 
            request.style
        )
        
        # 验证
        is_valid, msg = _validate_strategy_code(code)
        
        return AIStrategyGenerateResponse(
            code=code,
            explanation=explanation,
            is_valid=is_valid,
            validation_message=msg,
        )
    
    def validate(self, code: str) -> Tuple[bool, str]:
        """
        验证策略代码
        
        Args:
            code: 策略代码
        
        Returns:
            (is_valid, message)
        """
        return _validate_strategy_code(code)


# 全局AI服务实例
ai_service = AIService()
