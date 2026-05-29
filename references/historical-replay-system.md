# 历史时间切片回放训练系统 (v5.0)

## 核心定义
将历史上每一个交易日 T 都当成一次真实的"今天"进行回放。回放 T 日时，只能读取 T 日早上 08:00:00 之前已经存在的数据。

## 关键时间规则：08:00 信息集
| 数据类型 | T 日预测时是否允许 | 说明 |
|----------|-------------------|------|
| T-1 日 A 股收盘价 | ✅ 允许 | 昨日收盘后已经可知 |
| T 日 08:00 前公告 | ✅ 允许 | 必须有可靠发布时间 |
| 隔夜美股/外盘收盘 | ✅ 允许 | 通常在北京时间早上可知 |
| T 日 09:30 后盘中行情 | ❌ 禁止 | 属于预测之后的未来数据 |
| T 日 15:00 收盘价 | ❌ 禁用于预测 | 只能在 prediction_snapshot 保存后用于 reality 回填 |
| T+1 新闻 | ❌ 禁止 | 不能用未来新闻解释 T 日预测 |

## 核心模块
1. `point_in_time_dataset_builder.py` — 严格按 `as_of_time <= cutoff` 过滤，生成 feature_snapshots（带 Hash 防篡改）
2. `premarket_predictor.py` — 读取 feature_snapshot，生成 prediction_snapshot（status='locked'）
3. `postmarket_evaluator.py` — 读取 T 日 reality，计算收益/回撤/方向准确率
4. `historical_replay_engine.py` — 批量回放调度器
5. `leakage_auditor.py` — 扫描所有 timestamp，阻断 Look-ahead Bias

## 数据库表（17 张）
- `trading_calendar` — 交易日历
- `raw_market_daily` — 原始日线行情（带 source_timestamp）
- `raw_news_events` — 新闻与事件（带 published_at）
- `raw_macro_snapshots` — 宏观快照（带 snapshot_time）
- `raw_polymarket_snapshots` — Polymarket 快照（带 snapshot_time）
- `feature_snapshots` — T 日 08:00 特征快照（不可变，带 feature_set_hash）
- `prediction_snapshots` — 盘前预测快照（status='locked' 不可修改）
- `prediction_items` — 推荐板块/个股明细
- `reality_snapshots` — 盘后现实回填
- `evaluation_results` — 预测评估结果（方向准确率/收益/回撤）
- `factor_attribution` — 因子归因（哪个因子有效/失效/错误来源）
- `evolution_runs` — 进化运行记录
- `gatekeeper_decisions` — 门禁审核决策
- `leakage_audit_logs` — 未来函数审计日志
- `replay_configs` — **回放配置** (Cutoff 时间, 默认 T日 08:00:00 CST)
- `trading_cost_configs` — **交易成本配置** (印花税 0.05%, 佣金 0.03%, 滑点 0.2%)
- `gatekeeper_configs` — **门禁阈值配置** (最小样本60天, 收益提升≥3%, 回撤不恶化)
- `strategy_version_history` — **策略版本历史** (记录每次参数晋升 Old→New, 支持回滚)

## 未来函数防护清单
1. 所有 raw 表必须有 source_timestamp / published_at / snapshot_time
2. 所有 feature 构建 SQL 必须带 `timestamp <= cutoff_time` 条件
3. 所有 prediction_snapshot 必须在读取 reality 之前写入并锁定
4. reality_snapshots 只能在评估阶段读取，不允许被 predictor 引用
5. 禁止使用全量归一化统计
6. 训练窗口和测试窗口必须按时间顺序切分（Walk-forward）
7. 每轮训练必须输出 leakage_audit_logs
