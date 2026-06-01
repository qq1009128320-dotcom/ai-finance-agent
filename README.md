# AI量化策略平台 v4

AI辅助的量化策略平台 — 用户通过自然语言让AI生成量化策略，支持自定义编辑、回测验证、策略管理。

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    Vue 3 前端 (端口 3000)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 单股分析  │ │全市场扫描 │ │AI策略生成 │ │策略回测  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP/JSON
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 FastAPI 后端 (端口 8000)                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │              API v1 Endpoints                     │   │
│  │  /quant/*  /strategy/*  /backtest/*  /ai/*       │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Services 层                          │   │
│  │  quant.py  strategy.py  backtest.py  ai.py       │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Core 层                              │   │
│  │  config.py  models.py (Pydantic)                 │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    数据层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ 腾讯行情    │  │ Tushare     │  │ DeepSeek AI │     │
│  │ (零依赖)    │  │ (期货数据)  │  │ (策略生成)  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│  ┌─────────────┐                                        │
│  │ quant_engine│  28因子量化分析引擎                     │
│  └─────────────┘                                        │
└─────────────────────────────────────────────────────────┘
```

## 快速开始

### 方式一：本地开发

```bash
# 1. 后端启动
cd /home/administrator/tools/ai-finance-agent
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 2. 前端启动（新终端）
cd frontend
npm install
npm run dev
```

### 方式二：Docker 部署

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 启动
docker-compose up -d

# 访问
# 前端: http://localhost:3000
# 后端API: http://localhost:8000/docs
```

## API 文档

启动后端后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 核心 API

| 方法 | 端点 | 功能 |
|------|------|------|
| `POST` | `/api/v1/quant/analyze` | 单股量化分析 |
| `POST` | `/api/v1/quant/scan` | 全市场扫描 |
| `POST` | `/api/v1/ai/generate` | AI生成策略 |
| `POST` | `/api/v1/backtest/run` | 运行回测 |
| `POST` | `/api/v1/strategy/create` | 保存策略 |
| `GET` | `/api/v1/strategy/list` | 策略列表 |

## 项目结构

```
ai-finance-agent/
├── main.py                    # FastAPI 入口
├── core/                      # 核心模块
│   ├── config.py              # 配置管理
│   └── models.py              # Pydantic 模型
├── services/                  # 业务服务
│   ├── data.py                # 数据服务
│   ├── quant.py               # 量化分析
│   ├── strategy.py            # 策略管理
│   ├── ai.py                  # AI策略生成
│   └── backtest.py            # 回测服务
├── api/
│   └── v1/
│       └── endpoints/         # API路由
├── ai_strategy.py             # AI策略生成（复用）
├── quant_engine.py            # 28因子量化引擎
├── frontend/                  # Vue 3 前端
│   ├── src/
│   │   ├── api/               # API客户端
│   │   ├── views/             # 页面组件
│   │   └── stores/            # Pinia状态
│   └── ...
├── strategies/                # 策略存储
├── docker-compose.yml         # Docker编排
├── Dockerfile.backend         # 后端镜像
├── Dockerfile.frontend        # 前端镜像
└── requirements.txt           # Python依赖
```

## 28因子量化体系

| 维度 | 因子数 | 核心策略 |
|------|--------|---------|
| 趋势研判 | 8 | SMA多周期/MACD/ADX/布林带/一目均衡/Donchian |
| 动量信号 | 6 | RSI(背离)/KD/CCI/威廉%R/ROC/多周期动量共振 |
| 波动风险 | 5 | ATR百分位/历史波动率/布林带Squeeze/Beta/回撤 |
| 资金流向 | 5 | OBV/MFI/Chaikin/量比/VPT |
| 形态识别 | 4 | K线形态/支撑阻力/斐波那契/缺口 |

## 开发里程碑

| 阶段 | 时间 | 内容 | 状态 |
|------|------|------|------|
| Phase 1 | 6月15日 | Streamlit AI策略Tab | ✅ |
| Phase 2 | 6月20日 | FastAPI后端拆分 | ✅ |
| Phase 3 | 6月30日 | Vue 3 + FastAPI完整架构 | 🔄 |

## License

MIT
