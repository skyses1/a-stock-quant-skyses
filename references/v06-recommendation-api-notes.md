# v0.6-beta 推荐与复盘引擎 — API 与数据验证笔记

## 东财板块资金流 API

**端点**: `http://push2.eastmoney.com/api/qt/clist/get`

**参数**:
```
pn=1&pz=3&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:90+t:2&fields=f12,f14,f3,f62
```

**返回字段**:
- `f12`: 板块代码 (如 BK1592)
- `f14`: 板块名称 (如 "通信线缆及配套")
- `f3`: 涨跌幅 (%)
- `f62`: 主力净流入 (单位: **元**, 需除以 1e8 转为亿)

**数据口径**: 08:00 调用返回的是 **T-1 收盘后** 的资金流数据（因为 T 日尚未开盘）。必须在记录中标注 `source_timestamp="T-1 Close"`。

## 东财板块成分股 API

**端点**: 同上 `clist/get`，`fs` 改为 `b:{sector_code}`（如 `fs=b:BK0494`）

**⚠️ 重要**: `push2.eastmoney.com` `clist` 端点从沙箱 IP 不可达（RemoteDisconnected），生产环境必须配置 `EASTMONEY_PROXY`。

**正确过滤器格式**: `fs=b:BKxxxx`（东财板块成分股专用语法）
- 示例: `fs=b:BK0494` → 返回半导体板块全部成分股，按 `fid=f62` 排序
- **之前错误的格式**: `m:90+t:2+i:2.{sector_code}` 或 `f:!2.{sector_code}` — 这些不能正确过滤板块成分股，会返回全市场资金流 Top 股票

**返回字段**:
- `f12`: 股票代码
- `f14`: 股票名称
- `f2`: 最新价
- `f3`: 涨跌幅 (%)
- `f62`: 主力净流入 (元)

**验证步骤**: 每次调用后必须检查返回股票是否真实属于该板块。如果非银行/白酒板块返回了茅台(600519)/平安银行(000001)/中国平安(601318)/招商银行(600036)等全市场龙头，判定过滤器失效，拒绝该板块并记录 `reject_reason = sector_membership_mismatch`。

## 腾讯实时行情 API

**端点**: `http://qt.gtimg.cn/q={codes}`

**代码格式**: `6`/`9` 开头 → `sh{code}`, `8`/`4` 开头 → `bj{code}`, 其他 → `sz{code}`

**返回格式**: `v_sh600519="1~名称~代码~现价~昨收~开盘~..."` (~分隔)

**关键字段索引**:
- idx 3: 最新价 (Close)
- idx 4: 昨收
- idx 5: 开盘 (Open)
- idx 33: 最高
- idx 34: 最低 (Low)

**示例解析**:
```python
parts = data.split('~')
open_p = float(parts[5])
close_p = float(parts[3])
low_p = float(parts[34])
```

**⚠️ 注意**: 如果 `open_p == 0`，表示一字涨停或停牌，无法模拟买入。

## 代理配置

**不要硬编码代理地址**。使用环境变量：
```python
EASTMONEY_PROXY = os.getenv('EASTMONEY_PROXY', '')
if EASTMONEY_PROXY:
    proxies = {'http': EASTMONEY_PROXY, 'https': EASTMONEY_PROXY}
else:
    proxies = None  # 直连
```

**不要写 `http://10841`** — 这是不完整的格式。如果需要写死，使用完整地址如 `http://192.155.87.186:10841`。

## 模拟买入规则

```python
entry_price = open_p * 1.002  # Open + 0.2% 滑点
day_return = close_p / entry_price - 1
max_dd = low_p / entry_price - 1
excess_vs_benchmark = day_return - benchmark_return
```

**特殊处理**:
- `open_p == 0`: → `REJECTED`, `reject_reason = "Zero open price (Limit up/suspension)"`
- 无价格数据: → `ERROR`, `failure_reason = "No price data"`
- 正常: → `REVIEWED`
