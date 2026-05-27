# 技术实现原理 (Implementation)

## 架构设计
本系统采用 **Agent + Cron Job + Context Chain** 架构，不依赖重型第三方库（如 AKShare），确保在云端沙箱环境中稳定运行。

## 1. 数据层 (Data Layer)
- **A 股微观数据**: 
  - 使用 `scripts/fetch_data.py` (原生 `urllib` 库) 直连**东方财富底层 JSON 接口**。
  - 获取数据：上证指数量价、北向资金流向、涨跌停统计。
  - 优势：零依赖、极速、稳定。
  - **兜底机制**: 若接口失败，Agent 自动切换 Web Search 抓取替代数据。
- **宏观概率数据**: 
  - 优先通过代理访问 Polymarket Gamma API。
  - 失败则通过 Web Search 获取市场快照。

## 2. 逻辑层 (Logic Layer)
- **跨市场映射 (Cross-Market Mapping)**: 
  - 预定义映射表：降息->医药/黄金；AI 突破->光模块/算力；地缘冲突->军工/能源。
- **四维评分模型**: 
  - 根据量价、北向、情绪、技术面综合打分。
- **自适应策略 (Self-Correction)**: 
  - 读取昨日报告评分，自动调整今日推荐权重。
  - 连续低分板块自动降级为"回避"；连续高分板块升级为"核心主线"。

## 3. 控制层 (Control Layer)
- **Cron Job 调度**: 
  - 3 个独立任务 (08:00, 10:00, 14:30)。
  - 使用 `context_from` 参数实现任务间上下文传递（昨日评分 -> 今日自适应）。
- **消息推送**: 
  - 硬编码推送到 WeCom/Telegram 等指定频道。