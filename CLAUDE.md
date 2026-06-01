# AI智投量化平台 v4

## 项目描述
AI辅助的量化投资策略平台，后端 FastAPI (port 8000)，前端 Vue 3 + TypeScript。

## 架构
- 后端: FastAPI, port 8000, /api/v1 前缀
- 前端: Vue 3 + Vite + TypeScript + Pinia + Vue Router
- 前端开发服务器: port 5173, proxy /api → localhost:8000
- 当前前端代码在 frontend/ 目录下

## 任务
基于 Stitch 原型图重新生成 Vue 3 前端代码。
原型 URL: https://stitch.withgoogle.com/preview/5265188649520568824?node-id=e30f1bf50fb54716b64ffb98b0cbf2e5

## 要求
1. 先使用 stitch-design 的 extract-design-md 技能分析原型，提取设计系统
2. 然后根据设计系统重写 frontend/src/ 下的所有 Vue 组件
3. 页面: 单股分析(/analyze) | 全市场扫描(/scan) | AI策略(/ai-strategy) | 回测(/backtest) | 策略库(/strategies)
4. API 层保留现有的 api/index.ts 结构不变
5. 路由用 vue-router，状态管理用 Pinia
6. 保持深色主题，主色 #38bdf8
7. 确保 TypeScript 编译通过 (vue-tsc --noEmit)
