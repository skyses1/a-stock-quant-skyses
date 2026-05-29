# Cron 报告合规框架 (2026-05-29)

## system_status.json — 单一事实源

**路径**: `/home/admin/.hermes/scripts/quant_v2/system_status.json`

```json
{
  "version": "v0.5-beta",
  "purpose": "数据链路监控 / 虚拟盘观察 / Paper Trading",
  "strategy_validated": false,
  "universe_validated": false,
  "allow_live_advice": false,
  "allow_gatekeeper": false,
  "allow_parameter_evolution": false,
  "allow_full_market_expansion": false
}
```

所有 Cron Job 必须在 Step 0 读取此文件，报告中的版本号/有效性声明/权限限制必须与 JSON 严格对齐。
升级版本或开放实盘权限时，**只需修改此 JSON，无需重写 Prompt**。

## cron_report_lint.py — 硬拦截

**路径**: `/home/admin/.hermes/scripts/cron_report_lint.py`

**功能**: 逐行扫描报告正文，匹配 16 项违规正则。
**用法**: `python3 cron_report_lint.py <report_file> --job-id <job_id>`
**输出**: `LINT_PASS` (exit 0) 或 `LINT_FAIL` (exit 1) + 逐行打印违规详情。

**违规词清单**:
- `v2\.0` → 版本号错误
- `建议仓位` → 应改为 虚拟盘观察仓位
- `操作建议` → 应改为 今日系统观察结论
- `加仓` / `减仓` / `买入` / `卖出` → 实盘导向
- `实盘` → 实盘导向
- `娱乐.*OPPORTUNITY` → 包含排除类别
- `ATR Proxy` → 应改为 日内振幅代理
- `尾盘买入` / `尾盘加仓` / `明日重点买入` → 实盘导向
- `实盘执行` / `突破可追` / `跌破止损` → 实盘导向
- `高级金融投资分析师` → 角色越权

**Lint 脚本会自动跳过包含"禁止"/"应改为"/"违规"的元指令行，只检测实际报告正文。**

## Cron Job 统一 Prompt 模式

所有 3 个 Job（08:00 日报 / 10:00 雷达 / 14:30 雷达）必须包含以下 4 个 Step：

| Step | 内容 |
|------|------|
| **Step 0** | 读取 `system_status.json`，对齐版本/有效性/权限声明 |
| **Step 1** | 运行数据采集脚本，提取市场数据 |
| **Step 2** | 获取 Polymarket 数据（仅宏观映射，排除娱乐/体育/名人） |
| **Step 3** | 生成报告（9 个合规模块） |
| **Step 4** | 合规性自检：保存报告 → 运行 Lint → 若 FAIL 则修正并重试（Max 3 次）→ 3 次失败则取消推送并记录 `[BLOCKED]` |

## 报告标题规范

| Job | 标题 |
|-----|------|
| 08:00 | `📊 A 股量化系统 v0.5-beta — 数据链路监控与虚拟盘观察报告` |
| 10:00 | `📊 A 股量化系统 v0.5-beta — 盘中数据链路监控与虚拟盘观察雷达` |
| 14:30 | `📊 A 股量化系统 v0.5-beta — 尾盘数据链路监控与虚拟盘观察雷达` |

## Dry-Run 验证流程

修改任何 Cron Job prompt 后：
1. 设 `deliver: local`
2. 运行 job → 等待输出到 `~/.hermes/cron/output/<job_id>/`
3. 用 `cron_report_lint.py` 扫描生成的报告
4. 确认 `LINT_PASS` 后，恢复 `deliver: wecom:XiaoMing`

## Polymarket 缓存状态标注规范

若使用 DB 缓存（非实时），报告必须输出：
- `latest_snapshot_time`
- `data_age_hours`
- `cache_status`
- 若 > 24h，宏观因子权重降为 0

## 9 个合规模块

1. **系统状态声明** — v0.5-beta + 策略/数据宇宙未通过
2. **数据质量状态** — 逐项标注，涨跌停缺失写"情绪面降权"
3. **A 股市场观察指标** — 评分注明"不代表策略有效性"
4. **虚拟盘观察仓位** — 注明"仅用于 Paper Trading"
5. **风险观察** — 波动/回撤/Kill Switch
6. **Polymarket 宏观观察** — 仅宏观映射，标注缓存状态
7. **虚拟盘战绩回顾** — 跑输基准直写"未证明策略有效性"
8. **今日系统观察结论** — 禁止"操作建议"
9. **免责声明** — 原文包含指定文本
