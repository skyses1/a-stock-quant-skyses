# A 股量化实战系统 (A-Stock Quant System)

基于 **Polymarket 预测市场数据** 与 **A 股微观资金流向** 的跨市场量化交易系统。
**版本**: v2.0 (2026-05-28 Update)

## 📦 核心架构

本项目不仅是一个脚本集合，而是一个具备**“数据-分析-验证”闭环**的自动化量化 Agent 系统。

### 🧩 核心模块

| 模块 | 文件 | 说明 | 状态 |
|------|------|------|------|
| **数据采集引擎** | `a_stock_data.py` | 整合腾讯行情 (实时) + 东财北向资金 + 行业资金流 | ✅ 生产就绪 |
| **量化打分卡** | `quant_v2/scoring_risk.py` | 四维模型 (资金/情绪/宏观/技术) 自动计算系统评分 | ✅ v2.0 新增 |
| **风控系统** | `quant_v2/scoring_risk.py` | **ATR 动态止损** (替代固定止损) + 智能仓位管理 | ✅ v2.0 新增 |
| **持久化数据库** | `quant_v2/db.py` | SQLite 存储历史快照、推荐记录、映射历史 | ✅ v2.0 新增 |
| **虚拟盘核对** | `quant_v2/main.py` | Paper Trading Loop，自动追踪推荐标的盈亏 | ✅ v2.0 新增 |
| **动态学习引擎** | `quant_v2/learning_engine.py` | 根据历史胜率自动调整 Polymarket->A 股 映射权重 | 🟡 待积累数据 |

## 🚀 快速开始

### 1. 运行量化系统 v2.0
系统主入口，包含数据抓取、打分、风控和存储：
```bash
python3 quant_v2/main.py
```
*   **输出**：结构化 JSON 报告（供 Agent 或下游系统使用）。
*   **功能**：自动计算综合评分、建议仓位、动态止损位。

### 2. 独立运行数据采集
如果只需要获取行情数据：
```bash
python3 a_stock_data.py
```

## 📊 系统工作流 (Agent Workflow)

系统被设计为 Cron Job 自动化运行，分为三个阶段：

1.  **08:00 早盘战略 (Daily Report)**
    *   运行 `main.py` 获取昨日战绩回顾 (Paper Trading Check)。
    *   结合 Polymarket 宏观概率，生成今日策略与观察池。
    *   输出风控矩阵（建议仓位、动态止损价）。

2.  **10:00 / 14:30 盘中雷达 (Intraday Radar)**
    *   调用 `a_stock_data.py` 获取盘中实时数据。
    *   监控观察池个股是否触发关键支撑/阻力位。
    *   推送盘中异动提醒。

## 🛠️ 技术栈

*   **Language**: Python 3.11
*   **Data Sources**: Tencent Finance API, Eastmoney Datacenter (No heavy dependencies like AKShare).
*   **Storage**: SQLite (`quant_system.db`).
*   **Delivery**: WeCom (XiaoMing) via Hermes Agent.

## ⚠️ 风险提示

本系统主要用于**策略验证与辅助决策**，所有交易建议均包含“虚拟盘”追踪。
**市场有风险，投资需谨慎。**

## 📄 License

Private Project - Skyses
