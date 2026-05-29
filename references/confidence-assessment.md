# 置信度评估与数据质量指南

## 报告置信度等级

| 等级 | 数据覆盖率 | 决策可用性 |
|------|-----------|-----------|
| 🔴 **40-50%** | 仅 Polymarket 信号，无 A 股实盘硬数据 | 仅适合"策略观察框架"，不可跟单 |
| 🟡 **70%** | Polymarket 实数据 + A 股成交额/主力流向/涨跌比 + 跨市场映射 + 评分观察池 | 有参考价值，可辅助决策 |
| 🟢 **90%+** | 以上全部 + 北向资金精确值 + 涨停/连板统计 + AKShare 直连 | 可高度信赖 |

## 各数据源可靠性评估

### ✅ 高可靠（可直接使用）
| 数据 | 来源 | 方法 | 延迟 |
|------|------|------|------|
| 指数行情 | `quote.eastmoney.com/center/` | `browser_snapshot` 直接获取 | ~15min |
| 成交额/主力流向 | 搜索+东方财富页面 | `browser_console` 提取 | ~15min |
| Polymarket 概率 | gamma-api.polymarket.com | CORS 代理 + API | 实时 |
| 隔夜外盘 | 搜索 | Web Search | ~1h |

### ⚠️ 中等可靠（需验证）
| 数据 | 来源 | 问题 | 解决方案 |
|------|------|------|---------|
| 北向资金 | `data.eastmoney.com/hsgt/` | 异步 AJAX 加载，snapshot 常为空 | 用 `browser_console` 等待 JS 渲染后提取，或调 push2 API |
| 涨停/连板统计 | 搜索/页面抓取 | 格式不统一 | 交叉验证 2 个来源 |

### 🔴 不可靠（当前环境）
| 数据 | 原因 | 替代方案 |
|------|------|---------|
| AKShare 全量数据 | 沙箱无法安装包 | 等 VPS 环境 |
| 东方财富实时 K 线 | 页面复杂，JS 渲染 | 用 title 抓取 fallback |

## 突破路径

### 方案 A：VPS + AKShare（推荐）
在大陆网络的 VPS 上：
```bash
pip install akshare
python -c "import akshare as ak; print(ak.stock_zh_a_spot_em())"
```
数据质量直接拉到 90%+

### 方案 B：东方财富 push2 API 直连
```
https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f57,f58,f60,f169,f170
```
可获取实时行情，但北向资金等宏观数据仍需页面抓取

### 方案 C：搜索兜底
当所有 API 都失败时，用 Web Search 搜索关键词获取最新数据，准确率约 60%
