# A股数据源 API 详解 (双端口代理)

## 代理配置
- **10831** (US 192.155.87.186): 腾讯 + 新浪
- **10841** (US 38.64.57.71): 东方财富
- ⚠️ Python `requests` HTTPS 通过代理偶发超时，改用 `urllib.request` 或 HTTP 协议

## Python 环境
- venv: `~/.hermes/quant_venv` (Python 3.11.15)
- 激活: `source ~/.hermes/quant_venv/bin/activate`
- 执行: `/home/admin/.hermes/quant_venv/bin/python script.py`

## urllib.request 代理配置模板
```python
import urllib.request
import json

PROXY = "http://5.5name.cn:10831"  # 或 10841

def _fetch(url, timeout=15):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY})
    )
    opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'),
        ('Accept', 'application/json'),
    ]
    if 'eastmoney' in url:
        opener.addheaders.append(('Referer', 'https://quote.eastmoney.com/'))
    resp = opener.open(url, timeout=timeout)
    return resp.read().decode('utf-8', errors='ignore')
```

## 1. 新浪指数K线 (⭐⭐⭐⭐⭐)
```
http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=240&ma=no&datalen=200
```
- **symbol**: sh000001(上证), sz399001(深成), sz399006(创业板), sh000300(沪深300)
- **scale**: 240=日线, 60=60分钟, 30=30分钟, 15=15分钟, 5=5分钟, 1=1分钟
- **datalen**: 最大 1023
- **返回**: `[{day, open, high, low, close, volume}, ...]` JSON 数组
- **示例响应**:
```json
[{"day":"2026-05-28","open":"4080.304","high":"4110.782","low":"4055.828","close":"4098.636","volume":"47489644700"}]
```

## 2. 腾讯个股K线前复权 (⭐⭐⭐⭐⭐)
```
http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600519,day,2025-01-01,2025-06-01,120,qfq
```
- **param格式**: `{symbol},day,{start},{end},{count},qfq`
- **symbol**: sh600519(茅台), sz000858(五粮液) 等
- **返回**: `data.{symbol}.qfqday` → `[[date, open, close, high, low, volume], ...]`
- **字段顺序**: `[日期, 开盘, 收盘, 最高, 最低, 成交量]`
- 指数用 `day` 字段（不支持 qfqday）

## 3. 腾讯实时行情 (⭐⭐⭐⭐⭐)
```
http://qt.gtimg.cn/q=sh600519,sz000858,sh000001
```
- **返回格式**: `v_sh600519="1~贵州茅台~600519~1275.98~1303.00~..."`
- **~分隔字段**: 1=市场, 2=名称, 3=代码, 4=现价, 5=昨收, 6=开盘, 7=成交量(手), 33=最高, 34=最低, 37=成交额(万元), 40=PE

## 4. 东财股票列表 (⭐⭐⭐⭐)
```
http://94.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=80&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3
```
- **pn**: 页码, **pz**: 每页数量(最大80)
- **fs**: `m:0+t:6`(深证主板), `m:0+t:80`(深证其他), `m:1+t:2`(上证主板), `m:1+t:23`(上证其他)
- **fields**: f12=代码, f14=名称, f2=价格(分), f3=涨跌幅
- ⚠️ **data.diff 是 dict 不是 list!** 解析: `list(data['data']['diff'].values())`
- **total**: 总股票数(~5530)

## 5. 东财指数K线 (⭐⭐⭐⭐)
```
http://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000001&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56&klt=101&fqt=0&beg=20250101&end=20250601&lmt=250
```
- **secid**: 1.xxxxxx=上交所, 0.xxxxxx=深交所
- **klt**: 101=日线, 102=周线, 103=月线
- **fqt**: 0=不复权, 1=前复权, 2=后复权
- **返回**: `data.klines` → `["2025-01-02,开,收,高,低,量,额", ...]`

## 6. 东财北向资金
```
https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_MUTUAL_DEAL_HISTORY&columns=ALL&pageNumber=1&pageSize=5&sortColumns=TRADE_DATE&sortTypes=-1
```
- **MUTUAL_TYPE**: 001=沪股通, 003=深股通
- **NET_DEAL_AMT**: 净买额(万元), DEAL_AMT: 成交额(万元)

## 数据库 Schema (灌入后)
```sql
price_history (symbol, date, open, high, low, close, volume, amount, data_type, source_timestamp)
  - data_type: 'index' or 'stock'
  - PRIMARY KEY (symbol, date, data_type)

stock_info (symbol, name, exchange, last_update)
  - symbol: 'sh600519', 'sz000858'
```
