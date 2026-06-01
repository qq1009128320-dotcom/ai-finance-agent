"""
AI Quantitative Strategy Platform v4 - Strategy Management Service
"""

import sys
import json
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import STRATEGY_DIR
from core.models import (
    StrategyCreateRequest, StrategyResponse, StrategyListResponse,
    StrategyValidateRequest, StrategyValidateResponse
)


class StrategyService:
    """策略管理服务"""
    
    def validate_code(self, code: str) -> tuple[bool, str]:
        """
        验证策略代码
        
        Returns:
            (is_valid, message)
        """
        if not code:
            return False, "策略代码为空"
        
        # 检查必需函数
        if "def init(" not in code:
            return False, "缺少 init() 函数"
        if "def handle_data(" not in code:
            return False, "缺少 handle_data() 函数"
        
        # 检查语法
        try:
            compile(code, "<strategy>", "exec")
        except SyntaxError as e:
            return False, f"语法错误: {e}"
        
        return True, "策略代码结构正确"
    
    def create_strategy(self, request: StrategyCreateRequest) -> StrategyResponse:
        """
        创建/保存策略
        
        Args:
            request: 创建请求
        
        Returns:
            策略响应
        """
        # 验证代码
        is_valid, msg = self.validate_code(request.code)
        if not is_valid:
            raise ValueError(msg)
        
        # 生成ID
        strategy_id = hashlib.md5(
            f"{request.name}{time.time()}".encode()
        ).hexdigest()[:8]
        
        # 保存文件
        safe_name = request.name.replace(" ", "_").replace("/", "_")
        strategy_file = STRATEGY_DIR / f"{strategy_id}_{safe_name}.json"
        
        strategy_data = {
            "id": strategy_id,
            "name": request.name,
            "code": request.code,
            "description": request.description or "",
            "tags": request.tags,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 1,
        }
        
        with open(strategy_file, "w", encoding="utf-8") as f:
            json.dump(strategy_data, f, ensure_ascii=False, indent=2)
        
        return StrategyResponse(
            id=strategy_id,
            name=request.name,
            code=request.code,
            description=request.description,
            tags=request.tags,
            created_at=strategy_data["created_at"],
            updated_at=strategy_data["updated_at"],
            version=1,
        )
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyResponse]:
        """
        获取策略
        
        Args:
            strategy_id: 策略ID
        
        Returns:
            策略响应，不存在返回None
        """
        files = list(STRATEGY_DIR.glob(f"*{strategy_id}*"))
        if not files:
            return None
        
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return StrategyResponse(
            id=data["id"],
            name=data["name"],
            code=data["code"],
            description=data.get("description"),
            tags=data.get("tags", []),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            version=data.get("version", 1),
        )
    
    def list_strategies(self) -> StrategyListResponse:
        """
        列出所有策略
        
        Returns:
            策略列表响应
        """
        strategies = []
        
        for f in STRATEGY_DIR.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    strategies.append(StrategyResponse(
                        id=data["id"],
                        name=data["name"],
                        code=data["code"],
                        description=data.get("description"),
                        tags=data.get("tags", []),
                        created_at=data["created_at"],
                        updated_at=data["updated_at"],
                        version=data.get("version", 1),
                    ))
            except Exception:
                continue
        
        # 按创建时间排序
        strategies.sort(key=lambda x: x.created_at, reverse=True)
        
        return StrategyListResponse(
            total=len(strategies),
            strategies=strategies,
        )
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """
        删除策略
        
        Args:
            strategy_id: 策略ID
        
        Returns:
            是否成功
        """
        files = list(STRATEGY_DIR.glob(f"*{strategy_id}*"))
        for f in files:
            f.unlink()
        return True
    
    def update_strategy(self, strategy_id: str, code: str, 
                        name: Optional[str] = None,
                        description: Optional[str] = None) -> StrategyResponse:
        """
        更新策略
        
        Args:
            strategy_id: 策略ID
            code: 新代码
            name: 新名称（可选）
            description: 新描述（可选）
        
        Returns:
            更新后的策略响应
        """
        # 验证代码
        is_valid, msg = self.validate_code(code)
        if not is_valid:
            raise ValueError(msg)
        
        # 找到策略文件
        files = list(STRATEGY_DIR.glob(f"*{strategy_id}*"))
        if not files:
            raise ValueError(f"策略 {strategy_id} 不存在")
        
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 更新
        if name:
            data["name"] = name
        data["code"] = code
        if description is not None:
            data["description"] = description
        data["updated_at"] = datetime.now().isoformat()
        data["version"] = data.get("version", 1) + 1
        
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return StrategyResponse(
            id=data["id"],
            name=data["name"],
            code=data["code"],
            description=data.get("description"),
            tags=data.get("tags", []),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            version=data["version"],
        )


# 全局策略服务实例
strategy_service = StrategyService()
