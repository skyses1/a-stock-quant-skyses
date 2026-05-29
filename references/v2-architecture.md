# A 股量化系统 v2.0 架构详解

## 模块概览

```
quant_v2/
├── main.py              # 主入口：串联所有模块
├── scoring_risk.py      # 四维打分卡 + 动态 ATR 止损
├── db.py                # SQLite 持久化引擎
└── learning_engine.py   # 动态映射学习引擎
```

## 1. 主程序 (main.py)

**执行流程**：
1. 初始化 SQLite 数据库
2. 调用 `a_stock_data.py` 获取实时数据（腾讯行情 + 东财北向）
3. 运行四维打分卡计算系统评分
4. 根据评分计算建议仓位
5. 计算市场波动率（ATR Proxy）用于动态止损
6. 保存每日快照到数据库
7. 输出结构化 JSON 供 Agent 读取

**输出 JSON 结构**：
```json
{
  "date": "20260528",
  "scores": {"total": 70, "financial": 30, "sentiment": 20, "macro": 10, "tech": 10},
  "position": {"pct": 10, "style": "稳健持有"},
  "market": {
    "sh": {"price": 4098.64, "chg_pct": 0.12, "amount_yi": 13613.26, ...},
    "sz": {...},
    "cyb": {...},
    "total_amount": 29681.5,
    "northbound_net": 0.76
  }
}
```

## 2. 四维打分卡 (scoring_risk.py)

### 打分公式
```
总分 = 资金面(40) + 情绪面(30) + 宏观面(20) + 技术面(10)
```

### 资金面 (0-40 分)
| 指标 | 条件 | 分数 |
|------|------|------|
| 成交额 | >10000 亿 | 15 |
| | 8000-10000 亿 | 10 |
| | 6000-8000 亿 | 5 |
| | <6000 亿 | 0 |
| 北向资金 | >50 亿 | 25 |
| | 0-50 亿 | 15 |
| | -50 亿到 0 | 10 |
| | <-50 亿 | 0 |

### 情绪面 (0-30 分)
- 基准分 15
- 上证涨 >0.5%: +10
- 上证跌 >1%: -10
- 创业板涨 >1%: +5

### 宏观面 (0-20 分)
- 基于 Polymarket 系统性风险评分 (0-100, 0 最安全)
- 公式: `max(0, 20 - (risk_score / 5))`
- 例: 风险分 50 → 宏观面 10 分; 风险分 20 → 宏观面 16 分

### 技术面 (0-10 分)
- 上证/创业板同涨: 10 分
- 上证跌 >1%: 2 分
- 其他: 5 分 (基准)

### 仓位建议映射
| 总分 | 建议仓位 | 风格 |
|------|---------|------|
| ≥80 | 80-100% | 重仓进攻 |
| 60-79 | 40-80% | 稳健持有 |
| 40-59 | 40% | 防守反击 |
| <40 | 10% | 空仓观望 |

## 3. 动态 ATR 止损 (scoring_risk.py)

### 公式
```
止损价 = 买入价 - (2 × 当日振幅)
当日振幅 = 最高价 - 最低价
```

### 原理
- 使用当日振幅作为 ATR (Average True Range) 的代理
- 2 倍振幅意味着价格需要超出正常波动范围 2 倍才触发止损
- 这能有效过滤市场噪音，避免被正常洗盘震出

### 示例
| 股票 | 现价 | 最高 | 最低 | 振幅 | 止损距离 | 止损价 | 止损% |
|------|------|------|------|------|---------|--------|-------|
| 贵州茅台 | 1276 | 1304 | 1271 | 33 | 66 | 1210 | 5.2% |
| 寒武纪 (高波动) | 1340 | 1380 | 1280 | 100 | 200 | 1140 | 14.9% |
| 长江电力 (低波动) | 25 | 25.3 | 24.8 | 0.5 | 1.0 | 24.0 | 4.0% |

## 4. 持久化数据库 (db.py)

### 表结构

**daily_snapshots** (每日宏观数据快照)
```sql
date, total_amount, northbound_net, sh_close, sz_close, cyb_close, 
polymarket_risk_score, system_score
```

**recommendations** (推荐标的 Paper Trading)
```sql
id, date, code, name, price, current_price, pnl_pct, 
stop_loss, target_position, score, logic, status
```
- status: `PENDING` → `HIT_TP` (止盈) / `HIT_SL` (止损) / `HOLDING` / `CLOSED`

**mapping_history** (映射关系历史)
```sql
id, date, event_category, target_sector, success_score
```
- success_score: -1.0 到 1.0，基于次日实际表现

## 5. 动态学习引擎 (learning_engine.py)

### 工作原理
1. 每天记录 Polymarket 事件类别 → A 股板块的映射
2. 次日检查该板块的实际涨跌幅
3. 计算 success_score (-1 到 1)
4. 累积多次后，计算平均成功率
5. 根据历史表现调整该映射的权重

### 权重计算公式
```
基础权重 = 1.0
调整值 = 平均成功率 × 0.5 (最多调整 50%)
最终权重 = 基础权重 + 调整值
```

**前提条件**：至少需要 3 次样本才开始调整权重。

## 6. Paper Trading Loop

### 每日自动核对流程
1. 查询 SQLite 中 `status='PENDING'` 的昨日推荐
2. 用腾讯 API 批量获取这些标的的现价
3. 计算盈亏百分比: `pnl_pct = (current - entry) / entry`
4. 判定状态:
   - `pnl_pct >= 0.05` → `HIT_TP` (止盈)
   - `current_price <= stop_loss` → `HIT_SL` (止损)
   - 其他 → `HOLDING`
5. 更新数据库
6. 在报告中输出"昨日战绩"摘要

### 报告输出示例
```
📉 昨日战绩：推荐 3 只 | 2 止盈 (+4.2%, +2.1%) | 1 止损 (-3.1%)
   → 贵州茅台 1275.98 (-0.31%) 继续持有
   → 中际旭创 185.50 (+5.2%) 触发止盈 ✅
   → 寒武纪 1250.00 (-5.1%) 触发止损 🛑
```

## 7. Cron Job 集成

### 08:00 早盘报告
```bash
# Step 1: 运行 v2.0 系统
python3 /home/admin/.hermes/scripts/quant_v2/main.py

# Step 2: 从 JSON 输出中提取数据，结合 Polymarket 分析生成报告
```

### 10:00 / 14:30 盘中雷达
```bash
# Step 1: 运行数据采集
python3 /home/admin/.hermes/scripts/a_stock_data.py

# Step 2: 检查观察池个股实时表现
```
