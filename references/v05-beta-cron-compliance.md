# v0.5-beta Cron 报告合规体系 (2026-05-29)

## 背景
用户发现 08:00/10:00/14:30 三个 Cron Job 生成的报告存在严重问题：
1. 标题和正文使用 "v2.0" 版本号，与实际系统状态不符
2. 使用 "建议仓位""操作建议""买入""卖出" 等实盘导向表达
3. 娱乐/名人 Polymarket 市场出现在 A 股报告中
4. 统计口径不严谨 ("月度跑输9/15" 实为 "跑赢6/15")
5. 无硬拦截机制，违规报告直接推送企业微信

## 解决方案
### 1. system_status.json (单一事实源)
路径: `/home/admin/.hermes/scripts/quant_v2/system_status.json`
所有 Cron Job 的 Step 0 必须读取此文件，禁止在 Prompt 中硬编码版本号或状态。

### 2. cron_report_lint.py (硬拦截)
路径: `/home/admin/.hermes/scripts/cron_report_lint.py`
每次报告生成后运行 Lint，最多重试 3 次，失败则取消推送。

### 3. Prompt 同步升级
三个 Cron Job 的 Prompt 统一包含：
- Step 0: 读取 system_status.json
- Step 4: 合规性自检 (运行 Lint)
- 强制禁止列表 (v2.0 / 建议仓位 / 操作建议 / 买入 / 卖出 / 等)

## 合规表达映射表
| 旧表达 | 新表达 |
|--------|--------|
| A 股量化系统 v2.0 | A 股量化系统 v0.5-beta |
| 高级金融投资分析师 | 数据链路监控员 |
| 建议仓位 X% | 虚拟盘观察仓位：X%（仅用于 Paper Trading 记录） |
| 操作建议 | 今日系统观察结论 |
| 动态止损纪律 | 虚拟盘风控观察止损 |
| ATR Proxy | 日内振幅代理 Intraday Range Proxy |
| 量化打分 | 市场观察评分 |
| 娱乐 OPPORTUNITY | EXCLUDED |

## Dry-Run 结果
2026-05-29 对三个 Job 执行 dry-run，全部通过 LINT_PASS。
