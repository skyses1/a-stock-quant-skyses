---
name: a-stock-quant
description: A-Stock Quantitative Trading System with Adaptive Strategy & Intraday Radars.
version: 1.0.0
author: Hermes Agent + XiaoMing
tags: [a-stock, quant, trading, adaptive, radar, cron]
---

# A 股量化实战系统 (A-Stock Quant)

## 概述
一套全天候自动化交易参谋系统。融合 Polymarket 宏观概率与 A 股微观资金数据，具备**自我验证、策略自适应、盘中实时监控**能力。

## 🧩 核心模块
1. **📅 08:00 深度实战报告**：宏观映射 + 资金情绪 + 观察池推荐 + 昨日验证评分 + 策略自适应。
2. **🔔 10:00 盘中雷达**：早盘量能确认，买卖点提示（进攻 vs 防守）。
3. **🔔 14:30 尾盘雷达**：尾盘风险诊断，持股过夜建议。

## 🧠 核心算法逻辑
### 1. 四维模型
- **宏观 (Macro)**: Polymarket 概率异动（如降息、地缘冲突）映射 A 股板块。
- **资金 (Capital)**: 北向资金流向、成交额阈值（>1.15T 为多头，<0.9T 为空头）。
- **情绪 (Sentiment)**: 涨跌停家数、连板高度。
- **技术 (Tech)**: RPS 相对强度、均线排列。

### 2. 自适应策略 (Adaptive Strategy)
- **评分公式**: `Score = 涨跌幅 (%) * 10` (涨停 100 分)。
- **动态权重**: 
  - `Score > 70`: 列为核心主线，加仓。
  - `Score < 30`: 列为回避/风险，减仓。
  - **虚拟盘追踪**: 记录历史累计理论收益，验证系统有效性。

## 🛠️ 部署指南
1. **安装技能**: 加载本技能 (`/skill a-stock-quant`)。
2. **创建定时任务**: 参考 `references/cron-prompts.md` 创建 3 个 Cron Job。
3. **配置代理**: 若沙箱网络受限，需配置 HTTP 代理 (如 `http://proxy:port`)。
4. **配置推送**: 设置 WeCom 或 Telegram 等消息通道。

## 📂 目录结构
- `SKILL.md`: 核心说明
- `references/implementation.md`: 技术架构详解
- `references/cron-prompts.md`: 3 个定时任务的完整 Prompt
- `scripts/fetch_data.py`: 原生 A 股数据抓取脚本