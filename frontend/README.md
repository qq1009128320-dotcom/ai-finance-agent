# AI量化策略平台 - 前端

Vue 3 + Vite + TypeScript 前端项目

## 技术栈

- **Vue 3** - 响应式框架
- **Vite** - 构建工具
- **TypeScript** - 类型安全
- **Pinia** - 状态管理
- **Vue Router** - 路由
- **Axios** - HTTP 客户端
- **ECharts** - 图表（可选）

## 项目结构

```
frontend/
├── src/
│   ├── api/           # API 客户端
│   ├── assets/        # 静态资源
│   ├── components/    # 可复用组件
│   ├── router/        # 路由配置
│   ├── stores/        # Pinia 状态
│   ├── views/         # 页面组件
│   ├── App.vue        # 根组件
│   ├── main.ts        # 入口文件
│   └── style.css      # 全局样式
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 开发服务器

- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API代理: /api/* → http://localhost:8000/api/v1

## 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 重定向 | → `/analyze` |
| `/analyze` | 单股分析 | 28因子量化分析 |
| `/scan` | 全市场扫描 | 市场情绪概览 |
| `/ai-strategy` | AI策略生成 | 自然语言生成策略 |
| `/backtest` | 策略回测 | 模拟历史回测 |
| `/strategies` | 策略库 | 管理保存的策略 |

## API 对接

前端通过 `src/api/index.ts` 对接 FastAPI 后端：

```typescript
import { quantApi, aiApi, strategyApi, backtestApi } from '@/api'

// 单股分析
const result = await quantApi.analyze({ symbol: '600036' })

// AI生成策略
const strategy = await aiApi.generate({ prompt: '...' })

// 回测
const backtest = await backtestApi.run({ code: '...', symbol: '600036' })
```

## 样式系统

采用深色主题，CSS 变量定义在 `src/style.css`：

```css
:root {
  --primary-color: #38bdf8;
  --bg-dark: #0f172a;
  --bg-card: #1e293b;
  --text-primary: #f8fafc;
  ...
}
```
