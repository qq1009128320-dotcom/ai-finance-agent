"""
AI Quantitative Strategy Platform v4 - Backend Core
FastAPI 后端服务架构

目录结构:
    core/
        __init__.py
        config.py          # 配置管理
        database.py        # 数据库连接
        models.py          # Pydantic 数据模型
        dependencies.py    # 依赖注入
        
    services/
        __init__.py
        quant.py           # 量化分析服务
        strategy.py        # 策略管理服务
        ai.py              # AI策略生成服务
        backtest.py        # 回测服务
        data.py            # 数据服务（行情/K线）
        
    api/
        __init__.py
        v1/
            __init__.py
            endpoints/
                __init__.py
                quant.py       # /api/v1/quant/*
                strategy.py    # /api/v1/strategy/*
                backtest.py    # /api/v1/backtest/*
                health.py      # /api/v1/health
                
    main.py              # FastAPI 应用入口
"""
