"""
A股真实历史数据灌入脚本 v3.0
"""
import urllib.request
import json
import sqlite3
import time
import sys
import os
from datetime import datetime

PROXY_STOCK = "http://5.5name.cn:10831"
PROXY_EAST = "http://5.5name.cn:10841"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quant_system.db")

def _fetch(url, proxy, timeout=15, retries=2):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy, 'https': proxy}))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0'), ('Accept', 'application/json')]
    if 'eastmoney' in url:
        opener.addheaders.append(('Referer', 'https://quote.eastmoney.com/'))
    for attempt in range(retries + 1):
        try:
            resp = opener.open(url, timeout=timeout)
            return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
                continue
            return None

def _parse_diff(data):
    diff = data.get('data', {}).get('diff', {})
    if isinstance(diff, dict):
        return list(diff.values())
    return diff

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS price_history (
        symbol TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL,
        volume REAL, amount REAL DEFAULT 0, data_type TEXT DEFAULT 'qfq',
        source_timestamp TEXT, PRIMARY KEY (symbol, date, data_type))''')
    c.execute('''CREATE TABLE IF NOT EXISTS stock_info (
        symbol TEXT PRIMARY KEY, name TEXT, exchange TEXT, last_update TEXT)''')
    conn.commit()
    return conn

def get_stock_list_east(proxy=PROXY_EAST, limit=200):
    print(f"📊 获取A股列表 (东方财富)...")
    all_stocks = []
    page = 1
    while len(all_stocks) < limit:
        url = f'http://94.push2.eastmoney.com/api/qt/clist/get?pn={page}&pz=80&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3'
        text = _fetch(url, proxy)
        if not text:
            break
        data = json.loads(text)
        items = _parse_diff(data)
        for item in items:
            code = str(item.get('f12', ''))
            name = str(item.get('f14', ''))
            if code and name and 'ST' not in name and 'PT' not in name:
                market = 'sh' if code.startswith('6') else 'sz'
                all_stocks.append({'symbol': f'{market}{code}', 'name': name, 'price': item.get('f2', 0)})
        print(f"  第{page}页: {len(items)} (累计 {len(all_stocks)})")
        if len(items) < 80:
            break
        page += 1
        time.sleep(0.3)
    print(f"✅ {len(all_stocks)} 只")
    return all_stocks

def get_index_kline_east(symbol, proxy=PROXY_EAST, days=250):
    secid_map = {'sh000001': '1.000001', 'sz399001': '0.399001', 'sz399006': '0.399006', 'sh000300': '1.000300'}
    secid = secid_map.get(symbol, symbol)
    url = f'http://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56&klt=101&fqt=0&beg=20250101&end=20250601&lmt={days}'
    text = _fetch(url, proxy, retries=3)
    if not text:
        return []
    data = json.loads(text)
    klines = data.get('data', {}).get('klines', [])
    result = []
    for k in klines:
        p = k.split(',')
        if len(p) >= 6:
            result.append({'date': p[0], 'open': float(p[1]), 'close': float(p[2]), 'high': float(p[3]), 'low': float(p[4]), 'volume': float(p[5]), 'amount': float(p[6]) if len(p) > 6 else 0})
    return result

def get_stock_kline_tencent(symbol, proxy=PROXY_STOCK, days=120):
    url = f'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,2025-01-01,2025-06-01,{days},qfq'
    text = _fetch(url, proxy)
    if not text:
        return []
    data = json.loads(text)
    klines = data.get('data', {}).get(symbol, {}).get('qfqday', [])
    result = []
    for k in klines:
        if len(k) >= 6:
            result.append({'date': k[0], 'open': float(k[1]), 'close': float(k[4]), 'high': float(k[3]), 'low': float(k[2]), 'volume': float(k[5]), 'amount': 0})
    return result

def save_klines(conn, symbol, klines, dtype='stock'):
    c = conn.cursor()
    for k in klines:
        c.execute('INSERT OR REPLACE INTO price_history VALUES (?,?,?,?,?,?,?,?,?,?)',
            (symbol, k['date'], k['open'], k['high'], k['low'], k['close'], k['volume'], k.get('amount', 0), dtype, datetime.now().isoformat()))
    conn.commit()
    return len(klines)

def main():
    print("=" * 55)
    print("A股真实历史数据灌入 v3.0")
    print("=" * 55)
    
    conn = init_db(DB_PATH)
    
    # Phase 1: 指数 (东方财富)
    print("\n📈 Phase 1: 指数K线")
    for sym, name in [('sh000001','上证指数'),('sz399001','深证成指'),('sz399006','创业板指'),('sh000300','沪深300')]:
        time.sleep(1)  # 限速
        klines = get_index_kline_east(sym)
        if klines:
            n = save_klines(conn, sym, klines, 'index')
            print(f"  ✅ {name}: {n}条 (最新:{klines[-1]['date']} 收:{klines[-1]['close']})")
        else:
            print(f"  ❌ {name}: 失败")
    
    # Phase 2: 核心个股 (腾讯)
    print("\n📊 Phase 2: 核心个股K线")
    stocks = get_stock_list_east(limit=150)
    core = stocks[:80]
    
    saved = 0
    for i, s in enumerate(core):
        klines = get_stock_kline_tencent(s['symbol'])
        if klines:
            n = save_klines(conn, s['symbol'], klines, 'stock')
            conn.execute('INSERT OR REPLACE INTO stock_info VALUES (?,?,?,?)',
                (s['symbol'], s['name'], s['symbol'][:2], datetime.now().isoformat()))
            conn.commit()
            saved += n
            print(f"  [{i+1:3d}] {s['symbol']} {s['name']}: {n}条 收:{klines[-1]['close']}")
        else:
            print(f"  [{i+1:3d}] {s['symbol']} {s['name']}: 失败")
        time.sleep(0.3)
    
    # 统计
    print("\n" + "=" * 55)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM price_history"); print(f"  总K线: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(DISTINCT symbol) FROM price_history WHERE data_type='index'"); print(f"  指数: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(DISTINCT symbol) FROM price_history WHERE data_type='stock'"); print(f"  个股: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM stock_info"); print(f"  股票信息: {c.fetchone()[0]}")
    c.execute("SELECT date,close FROM price_history WHERE symbol='sh000001' AND data_type='index' ORDER BY date DESC LIMIT 1")
    r = c.fetchone()
    if r: print(f"  上证指数: {r[0]} {r[1]}")
    conn.close()
    print("\n✅ 完成!")

if __name__ == '__main__':
    main()
