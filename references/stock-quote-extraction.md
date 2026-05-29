# 个股实时行情抓取指南

## 🥇 腾讯行情 API（首选 — 最稳定）

```
http://qt.gtimg.cn/q=sh000001,sz399001,sh600519
```

返回格式：`v_sh000001="1~名称~代码~现价~昨收~开盘~..."`（~分隔，共约50个字段）

**关键字段（纯数字，无需中文编码处理）**：
| 字段 | 含义 | 示例 |
|------|------|------|
| 1 | 市场 | 1=沪市 |
| 2 | 代码 | 000001 |
| 3 | 最新价 | 4087.86 |
| 4 | 昨收 | 4093.73 |
| 5 | 开盘 | 4080.30 |
| 6 | 成交量(手) | 386602099 |
| 31 | 最高/最低价索引 | — |
| 32 | 涨跌幅(%) | -0.14 |
| 37 | 成交额(万元) | 82660790 → /10000 = 亿 |

**代码格式**：`sh`+6位（沪市），`sz`+6位（深市）
**验证日期**：2026-05-28，通过 HTTP 代理 100% 稳定
**解析方式**：`curl` + 正则提取 `"...(.*)"` 后按 `~` split

## 🥇 东财 datacenter-web API（北向资金）

```
https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_MUTUAL_DEAL_HISTORY&columns=ALL&pageNumber=1&pageSize=5&sortColumns=TRADE_DATE&sortTypes=-1
```

返回纯 JSON，无需浏览器：
- `MUTUAL_TYPE`: `001`=沪股通, `003`=深股通, `005`/`006`=港股通
- `NET_DEAL_AMT` = 净买额(万元), `DEAL_AMT` = 成交额(万元)
- `TRADE_DATE` = 交易日期
- 需要 Referer + User-Agent headers

## 东方财富 push2 API（次选）

```
https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f57,f58,f60,f169,f170&ut=fa5fd1943c7b386f172d6893dbfba10b&fltt=2
```

**secid 编码规则**：
- 沪市（sh）：`1.XXXXXX` 如 `1.600519`
- 深市（sz）：`0.XXXXXX` 如 `0.300223`

**返回字段**：
| 字段 | 含义 | 注意 |
|------|------|------|
| f43 | 最新价 | **数值×100**（129100 = 1291.00元） |
| f57 | 股票代码 | 字符串 |
| f58 | 股票名称 | 字符串 |
| f60 | 昨收 | **数值×100** |
| f169 | 涨跌额 | 实际值，不×100 |
| f170 | 涨跌幅% | 实际值（-92 = -0.92%） |

**注意**：此 API 偶尔返回 ERR_EMPTY_RESPONSE，遇到时回退到页面抓取。

## 东方财富 quote 页面（可靠备选）

### 概念版（数据加载快）
```
https://quote.eastmoney.com/concept/sh600519.html
https://quote.eastmoney.com/concept/sh603986.html
```

### 经典版
```
https://quote.eastmoney.com/sh600519.html
https://quote.eastmoney.com/sz300223.html
```

### Title 抓取（最简 fallback）
页面 `<title>` 格式固定：
```
贵州茅台 1291.00 -12.00(-0.92%)最新价格_行情_走势图—东方财富网
```
通过 `browser_console` 读取 `document.title` 即可解析出价格和涨跌幅。

## 港股通数据快速提取

在任意个股 quote 页面顶部导航栏中直接显示：
```
港股通(沪) 有额度 净买额19.20亿
港股通(深) 有额度 净买额14.87亿
```
可用 `browser_snapshot` 或 `browser_console` 提取，无需跳转专用页面。

## 新浪行情接口（不推荐）
```
https://hq.sinajs.cn/list=sh600519,sz300223
```
⚠️ 需要 Referer 头，从沙箱直接访问通常返回 "Forbidden"。
⚠️ 即使通过代理可访问，返回内容为 GBK 编码，在 Linux 沙箱中解码复杂且易出错。
**结论**：腾讯 API 已覆盖相同功能，无需使用新浪。

## ⚠️ 已验证不可靠的接口
| 接口 | 问题 | 验证日期 |
|------|------|---------|
| `push2his.eastmoney.com/api/qt/ulist.np/get` | 通过代理经常返回空/限速 | 2026-05-28 |
| `push2ex.eastmoney.com/getTopicZDTIndex` | 返回空，报表配置不存在 | 2026-05-28 |
| `datacenter-web...RPT_LIMITUP_DOWN` | 报表配置不存在 (code: 9501) | 2026-05-28 |
| `datacenter-web...RPT_INDUSTRY_DEAL` | 报表配置不存在 (code: 9501) | 2026-05-28 |

**教训**：东财 datacenter 的报表名（reportName）不是固定公开的，部分报表可能随时失效或被改名。验证可用后应记录在 SKILL.md 中。
