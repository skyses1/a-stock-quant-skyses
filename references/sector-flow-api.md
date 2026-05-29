# 板块资金流 API 指南

## 行业板块资金流 (push2 API)
```
https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:90+t:2&fields=f12,f14,f3,f62,f184,f124
```

## 概念板块资金流 (push2 API)
```
https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:90+t:3&fields=f12,f14,f3,f62,f184,f124
```

**字段说明**:
- `f12`: 板块代码 (如 BK0475)
- `f14`: 板块名称
- `f3`: 涨跌幅(%)
- `f62`: 主力净流入(元) — 注意单位是元，除以 1e8 = 亿
- `f184`: 主力净占比(%)
- `f124`: 其他指标

**调用注意事项**:
1. 需要 Referer (`https://quote.eastmoney.com/`) 和 User-Agent 头
2. 通过 HTTP 代理调用经常被限速返回空
3. 重试策略：最多 3 次，每次间隔 2 秒
4. 如果连续失败，降级到 Web Search 搜索 "今日行业板块资金流 TOP10"

**返回格式示例**:
```json
{
  "data": {
    "diff": [
      {
        "f12": "BK0475",
        "f14": "半导体",
        "f3": 2.35,
        "f62": 1234567890,  // 元 → 12.35亿
        "f184": 15.6
      }
    ]
  }
}
```

**验证日期**: 2026-05-28
