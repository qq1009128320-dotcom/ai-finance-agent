# AI智投量化平台

> AI辅助的量化投资策略平台 — 用户通过自然语言驱动量化策略，支持自定义编辑、回测验证与策略管理

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Vue 3](https://img.shields.io/badge/Vue%203-4FC08D?style=flat&logo=vue.js)](https://vuejs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 功能总览

| 页面 | 路由 | 说明 |
|------|------|------|
| **策略编辑器** | `/builder` | 三步导航式构建量化策略（择股→交易模型→大盘择时），左右两栏布局 |
| **单股量化分析** | `/analyze` | 28因子5维度全方位诊断，覆盖5525只A股，中文名称自动识别 |
| **全市场扫描** | `/scan` | 批量扫描股票池，市场情绪概览，强势/弱势股排名 |
| **AI策略生成** | `/ai-strategy` | 自然语言描述投资想法，AI自动生成完整量化策略 |
| **策略回测** | `/backtest` | 完整回测指标（收益/夏普/回撤/胜率），收益曲线可视化 |
| **策略库** | `/strategies` | 策略CRUD管理，搜索/标签筛选，一键跳转回测 |

---

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│               Vue 3 前端 (Port 5173 / 3000)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 单股分析  │ │全市场扫描 │ │AI策略生成 │ │策略回测  │   │
│  │ 策略编辑器 │ │ 策略库   │ │          │ │          │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/JSON (Axios)
┌──────────────────────▼──────────────────────────────────┐
│               FastAPI 后端 (Port 8000)                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │              API v1 Endpoints                     │   │
│  │  /quant/*  /strategy/*  /backtest/*  /ai/*       │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Services 层                             │   │
│  │  quant.py  strategy.py  backtest.py  ai.py       │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   核心引擎层                              │
│  ┌──────────────────┐  ┌────────────────────────────┐   │
│  │ 28因子量化引擎    │  │ 回测引擎                   │   │
│  │ (趋势/动量/波动/  │  │ (收益/夏普/回撤/胜率       │   │
│  │  资金/形态)      │  │  未来穿越防护/Mock TA-Lib) │   │
│  └──────────────────┘  └────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ AI策略引擎 (DeepSeek API) — 自然语言→结构化策略   │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                    数据层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ 腾讯行情    │  │ Akshare     │  │ DeepSeek AI │     │
│  │ (零依赖)    │  │ (全A股映射) │  │ (策略生成)  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## 核心创新亮点

### 1. 自然语言驱动的策略生成
创新性地将大语言模型（DeepSeek）与量化因子体系结合，用户用日常语言描述投资想法，AI自动解析为包含因子条件、排名逻辑、交易模型的结构化策略，无需编程基础。

### 2. 自主研发28因子量化引擎
覆盖趋势、动量、波动、资金、形态5大维度的28个量化因子，构建完整的A股量化评分体系。引擎完全自主研发，不依赖第三方量化库（如TA-Lib），核心技术自主可控。

### 3. 零依赖行情数据架构
采用腾讯行情API作为主要数据源，零成本、零注册、零依赖。配合Akshare作为全A股名称映射的降级方案，确保数据层的稳定性和可维护性。

### 4. 回测引擎完整性保障
自主研发的回测引擎内置多重防护机制：未来穿越检测（防止使用未来数据）、Mock TA-Lib兼容（支持社区策略迁移）、仓位管理模型、标准化回测指标计算，确保回测结果真实可靠。

---

## 快速开始

### 环境要求
- Python 3.9+
- Node.js 16.x+
- npm 8+

### 方式一：本地开发

```bash
# 1. 后端启动
cd ai-finance-agent
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 2. 前端启动（新终端）
cd frontend
npm install
npm run dev
```

访问：
- 前端页面：http://localhost:5173
- API文档（Swagger）：http://localhost:8000/docs
- API文档（ReDoc）：http://localhost:8000/redoc

### 方式二：Docker 部署

```bash
cp .env.example .env
# 编辑 .env 填入 API Key
docker-compose up -d
# 访问前端: http://localhost:3000
```

---

## API 文档

| 方法 | 端点 | 功能 |
|------|------|------|
| `POST` | `/api/v1/quant/analyze` | 单股量化分析（28因子诊断） |
| `POST` | `/api/v1/quant/scan` | 全市场扫描 |
| `POST` | `/api/v1/ai/generate` | AI生成策略（自然语言→策略） |
| `POST` | `/api/v1/backtest/run` | 运行策略回测 |
| `POST` | `/api/v1/strategy/create` | 保存策略 |
| `GET` | `/api/v1/strategy/list` | 策略列表 |
| `GET` | `/api/v1/strategy/{id}` | 策略详情 |
| `PUT` | `/api/v1/strategy/{id}` | 更新策略 |
| `DELETE` | `/api/v1/strategy/{id}` | 删除策略 |

---

## 28因子量化体系

| 维度 | 因子数 | 核心指标 |
|------|--------|---------|
| 趋势研判 | 8 | SMA多周期/MACD/ADX/布林带/一目均衡/Donchian |
| 动量信号 | 6 | RSI(背离)/KD/CCI/威廉%R/ROC/多周期动量共振 |
| 波动风险 | 5 | ATR百分位/历史波动率/布林带Squeeze/Beta/回撤 |
| 资金流向 | 5 | OBV/MFI/Chaikin/量比/VPT |
| 形态识别 | 4 | K线形态/支撑阻力/斐波那契/缺口 |

---

## 项目结构

```
ai-finance-agent/
├── main.py                    # FastAPI 入口
├── core/                      # 核心模块
│   ├── config.py              # 配置管理（Pydantic Settings）
│   └── models.py              # Pydantic 数据模型
├── services/                  # 业务服务层
│   ├── data.py                # 数据服务
│   ├── quant.py               # 量化分析服务
│   ├── strategy.py            # 策略管理服务
│   ├── ai.py                  # AI策略生成服务
│   └── backtest.py            # 回测服务
├── api/v1/endpoints/          # API 路由
├── quant_engine.py            # 28因子量化引擎
├── ai_strategy.py             # AI策略生成引擎
├── data/                      # 数据采集模块
│   ├── quotes.py              # 腾讯行情
│   └── data_router.py         # 统一数据路由
├── frontend/                  # Vue 3 前端
│   ├── src/
│   │   ├── api/               # API 客户端（Axios）
│   │   ├── views/             # 6个功能页面组件
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── router/            # Vue Router 配置
│   │   └── style.css          # 全局样式
│   └── ...
├── strategies/                # 策略存储（JSON）
├── docker-compose.yml         # Docker 编排
├── Dockerfile.backend         # 后端镜像
├── Dockerfile.frontend        # 前端镜像
├── nginx.conf                 # Nginx 配置
└── requirements.txt           # Python 依赖
```

---

## License

MIT
