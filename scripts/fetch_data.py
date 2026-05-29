#!/usr/bin/env python3
"""
A-Stock Data Fetcher (Native urllib, Zero Dependencies)
Calls EastMoney底层 JSON interfaces directly.
"""
import urllib.request
import json
import re
import sys

def fetch_market_data():
    print(">>> 开始获取 A 股数据...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # 1. 北向资金
    try:
        url = "https://push2.eastmoney.com/api/qt/kamt.rtmin/get?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54,f55&ut=b955bf0971c9ee216a4b221b29f9202d"
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=5).read().decode()
        data = re.search(r'\{.*\}', resp).group()
        print(f"北向资金数据: OK")
    except Exception as e:
        print(f"北向资金 API 失败: {e}", file=sys.stderr)

    # 2. 上证指数
    try:
        url_sh = "https://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f43,f44,f45,f46,f47,f170,f48&ut=fa5fd1943c7b386f172d6893dbbd4179"
        req = urllib.request.Request(url_sh, headers=headers)
        resp = urllib.request.urlopen(req, timeout=5).read().decode()
        print(f"上证指数数据: OK")
    except Exception as e:
        print(f"上证指数 API 失败: {e}", file=sys.stderr)

if __name__ == "__main__":
    fetch_market_data()