#!/usr/bin/env python3
"""
A股数据采集脚本 — 通过公开API获取实时行情数据
数据源：腾讯行情 + 东方财富北向资金 + 东方财富行业资金流
代理：http://5.5name.cn:10831
"""

import json
import re
import subprocess
import time
from datetime import datetime, timedelta

PROXY = "http://5.5name.cn:10831"
TIMEOUT = 15

def curl(url, headers="", timeout=TIMEOUT, encoding="utf-8", retries=3):
    """通过代理执行 curl 请求，失败自动重试"""
    cmd = f'curl -x {PROXY} -s --connect-timeout 8 -m {timeout} "{url}" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" {headers} 2>&1'
    for attempt in range(retries):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout + 5)
            if result.returncode == 0 and len(result.stdout) > 50:
                try:
                    return result.stdout.decode(encoding).strip()
                except:
                    return result.stdout.decode('latin-1').strip()
        except:
            pass
        if attempt < retries - 1:
            time.sleep(2)  # 等待后重试
    return ""

def parse_jsonp(text):
    """剥离 JSONP 回调并解析 JSON"""
    if not text:
        return None
    if '(' in text and text.rstrip().endswith(')'):
        text = text[text.index('(')+1:text.rindex(')')]
    try:
        return json.loads(text)
    except:
        return None

def safe_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default


# ============================================================
# 数据源 1：腾讯行情 API（最稳定）
# ============================================================
def fetch_tencent_quotes(stock_codes):
    """
    获取腾讯行情数据
    stock_codes: 如 ["sh000001", "sz399001", "sh600519"]
    返回: dict {code: {price, prev_close, open, high, low, volume, amount, chg_pct, time}}
    """
    codes_str = ",".join(stock_codes)
    url = f"http://qt.gtimg.cn/q={codes_str}"
    # 腾讯行情返回 GBK 编码
    out = curl(url, encoding="gbk")
    
    results = {}
    for line in out.strip().split('\n'):
        m = re.search(r'v_([a-z]+\d+)="([^"]*)"', line)
        if not m:
            continue
        code_raw = m.group(1)  # 如 sh000001
        parts = m.group(2).split('~')
        if len(parts) < 38:
            continue
        
        # 腾讯字段索引（不需要中文名称）
        price = parts[3]
        prev_close = parts[4]
        open_price = parts[5]
        high = parts[33] if len(parts) > 33 else parts[4]
        low = parts[34] if len(parts) > 34 else parts[4]
        volume = parts[6]  # 手
        amount_wan = safe_float(parts[37], 0)  # 万元
        chg_val = safe_float(parts[31], 0)
        chg_pct = safe_float(parts[32], 0)
        trade_time = parts[30] if len(parts) > 30 else ""  # YYYYMMDDHHMMSS
        
        results[code_raw] = {
            "price": safe_float(price),
            "prev_close": safe_float(prev_close),
            "open": safe_float(open_price),
            "high": safe_float(high),
            "low": safe_float(low),
            "volume": int(safe_float(volume)),
            "amount_yi": amount_wan / 10000,  # 转为亿
            "chg_val": chg_val,
            "chg_pct": chg_pct,
            "trade_time": trade_time
        }
    
    return results


# ============================================================
# 数据源 2：东方财富 北向资金
# ============================================================
def fetch_northbound_flow():
    """
    获取北向资金（沪股通+深股通）最近几天的数据
    返回: list of {date, total_net_yi, total_deal_yi, sh_net_yi, sz_net_yi}
    """
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_MUTUAL_DEAL_HISTORY&columns=ALL&pageNumber=1&pageSize=10&sortColumns=TRADE_DATE&sortTypes=-1"
    headers = '-H "Referer: https://data.eastmoney.com/hsgt/"'
    out = curl(url, headers=headers, timeout=20)
    
    d = parse_jsonp(out)
    if not d or not d.get("result", {}).get("data"):
        return []
    
    items = d["result"]["data"]
    
    # 按日期和类型分组
    dates = {}
    for item in items:
        td = item.get("TRADE_DATE", "")[:10]
        mt = item.get("MUTUAL_TYPE", "")
        net = safe_float(item.get("NET_DEAL_AMT"), 0)  # 单位：万
        deal = safe_float(item.get("DEAL_AMT"), 0)
        
        if td not in dates:
            dates[td] = {"sh_net": 0, "sz_net": 0, "hk_sh_net": 0, "hk_sz_net": 0, "sh_deal": 0, "sz_deal": 0}
        
        # 001=沪股通, 003=深股通, 002=港股通(沪), 004=港股通(深), 005/006=其他变体
        if mt in ("001", "005"):
            dates[td]["sh_net"] += net
            dates[td]["sh_deal"] += deal
        elif mt in ("003", "006"):
            dates[td]["sz_net"] += net
            dates[td]["sz_deal"] += deal
    
    results = []
    for td in sorted(dates.keys(), reverse=True)[:5]:
        d = dates[td]
        total_net = d["sh_net"] + d["sz_net"]  # 万
        total_deal = d["sh_deal"] + d["sz_deal"]
        results.append({
            "date": td,
            "total_net_yi": round(total_net / 10000, 2),
            "total_deal_yi": round(total_deal / 10000, 2),
            "sh_net_yi": round(d["sh_net"] / 10000, 2),
            "sz_net_yi": round(d["sz_net"] / 10000, 2)
        })
    
    return results


# ============================================================
# 数据源 3：东方财富 K线历史（日线）
# ============================================================
def fetch_kline(secid, lmt=5):
    """
    获取日线K线数据
    secid: 如 "1.000001"(上证指数), "0.399001"(深证成指)
    lmt: 返回最近N根K线
    返回: list of {date, open, close, high, low, volume, amount, chg_pct}
    """
    ts = int(time.time())
    url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&beg=0&end=20500101&lmt={lmt}&_={ts}"
    headers = '-H "Referer: https://quote.eastmoney.com/"'
    out = curl(url, headers=headers, timeout=15)
    
    d = parse_jsonp(out)
    if not d or not d.get("data", {}).get("klines"):
        return []
    
    results = []
    for line in d["data"]["klines"]:
        parts = line.split(",")
        if len(parts) >= 8:
            results.append({
                "date": parts[0],
                "open": safe_float(parts[2]),
                "close": safe_float(parts[1]),
                "high": safe_float(parts[3]),
                "low": safe_float(parts[4]),
                "volume": int(safe_float(parts[5])),
                "amount_yi": round(safe_float(parts[6]) / 10000, 2),
                "chg_pct": safe_float(parts[7])
            })
    
    return results


# ============================================================
# 数据源 4：东方财富 行业板块资金流
# ============================================================
def fetch_sector_flow():
    """
    获取行业板块主力资金净流入 TOP10
    返回: list of {name, net_inflow_yi, chg_pct}
    """
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:90+t:2&fields=f12,f14,f3,f62,f184,f124"
    headers = '-H "Referer: https://quote.eastmoney.com/"'
    out = curl(url, headers=headers, timeout=15)
    
    d = parse_jsonp(out)
    if not d or not d.get("data", {}).get("diff"):
        return []
    
    results = []
    for item in d["data"]["diff"]:
        name = item.get("f14", "?")
        net = safe_float(item.get("f62"), 0)  # 元
        chg = safe_float(item.get("f3"), 0)
        results.append({
            "name": name,
            "net_inflow_yi": round(net / 1e8, 2),
            "chg_pct": chg
        })
    
    return results


# ============================================================
# 数据源 5：东方财富 概念板块资金流
# ============================================================
def fetch_concept_flow():
    """
    获取概念板块主力资金净流入 TOP10
    返回: list of {name, net_inflow_yi, chg_pct}
    """
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:90+t:3&fields=f12,f14,f3,f62,f184,f124"
    headers = '-H "Referer: https://quote.eastmoney.com/"'
    out = curl(url, headers=headers, timeout=15)
    
    d = parse_jsonp(out)
    if not d or not d.get("data", {}).get("diff"):
        return []
    
    results = []
    for item in d["data"]["diff"]:
        name = item.get("f14", "?")
        net = safe_float(item.get("f62"), 0)
        chg = safe_float(item.get("f3"), 0)
        results.append({
            "name": name,
            "net_inflow_yi": round(net / 1e8, 2),
            "chg_pct": chg
        })
    
    return results


# ============================================================
# 主函数
# ============================================================
def main():
    report = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "data_sources": {}}
    
    print("=" * 60)
    print(f"  A股数据采集报告 — {report['timestamp']}")
    print("=" * 60)
    print()
    
    # ---- 1. 腾讯行情 ----
    print("📊 [1/5] 腾讯行情 API...")
    index_codes = ["sh000001", "sz399001", "sz399006", "sh000300", "sh000688"]
    quotes = fetch_tencent_quotes(index_codes)
    report["data_sources"]["tencent_quotes"] = quotes
    
    print(f"  成功获取 {len(quotes)} 个指数行情")
    
    # 计算沪深总成交额
    sh_amt = quotes.get("sh000001", {}).get("amount_yi", 0)
    sz_amt = quotes.get("sz399001", {}).get("amount_yi", 0)
    total_amount = sh_amt + sz_amt
    print(f"  上证: {sh_amt:.1f}亿 | 深证: {sz_amt:.1f}亿 | 合计: {total_amount:.1f}亿")
    report["total_amount_yi"] = round(total_amount, 1)
    
    print()
    
    # ---- 2. 北向资金 ----
    print("🌐 [2/5] 东财北向资金...")
    northbound = fetch_northbound_flow()
    report["data_sources"]["northbound_flow"] = northbound
    
    if northbound:
        latest = northbound[0]
        print(f"  最新({latest['date']}): 净买额 {latest['total_net_yi']:+.2f}亿 | 成交额 {latest['total_deal_yi']:.2f}亿")
        print(f"    沪股通: {latest['sh_net_yi']:+.2f}亿 | 深股通: {latest['sz_net_yi']:+.2f}亿")
    else:
        print("  ⚠️ 数据获取失败（可能限速）")
    
    print()
    
    # ---- 3. K线历史 ----
    print("📈 [3/5] 东财K线(上证近5日)...")
    kline = fetch_kline("1.000001", lmt=5)
    report["data_sources"]["kline_sh"] = kline
    
    if kline:
        for k in kline:
            flag = "📈" if k["chg_pct"] >= 0 else "📉"
            print(f"  {flag} {k['date']}: {k['close']} ({k['chg_pct']:+.2f}%) | 成交 {k['amount_yi']:.1f}亿")
    else:
        print("  ⚠️ 数据获取失败（可能限速，可重试）")
    
    print()
    
    # ---- 4. 行业板块资金流 ----
    print("💰 [4/5] 东财行业资金流 TOP5...")
    sector_flow = fetch_sector_flow()
    report["data_sources"]["sector_flow"] = sector_flow
    
    if sector_flow:
        for s in sector_flow[:5]:
            flag = "🟢" if s["net_inflow_yi"] > 0 else "🔴"
            print(f"  {flag} {s['name']}: {s['net_inflow_yi']:+.2f}亿 ({s['chg_pct']:+.2f}%)")
    else:
        print("  ⚠️ 数据获取失败")
    
    print()
    
    # ---- 5. 概念板块资金流 ----
    print("💡 [5/5] 东财概念资金流 TOP5...")
    concept_flow = fetch_concept_flow()
    report["data_sources"]["concept_flow"] = concept_flow
    
    if concept_flow:
        for s in concept_flow[:5]:
            flag = "🟢" if s["net_inflow_yi"] > 0 else "🔴"
            print(f"  {flag} {s['name']}: {s['net_inflow_yi']:+.2f}亿 ({s['chg_pct']:+.2f}%)")
    else:
        print("  ⚠️ 数据获取失败")
    
    print()
    print("=" * 60)
    
    # ---- 输出 JSON 供后续分析使用 ----
    print()
    print("📋 JSON 输出:")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    
    return report


if __name__ == "__main__":
    main()
