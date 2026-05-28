"""
A股历史数据适配器 - 通过代理从腾讯/新浪API灌入真实数据
数据源: 
  - 腾讯: K线数据 (HTTP, 前复权/后复权/RAW)
  - 新浪: 股票列表、实时行情
代理: http://5.5name.cn:10831
"""
import urllib.request
import json
import time
import sys
import os

PROXY = "http://5.5name.cn:10831"

def _build_opener():
    proxy_handler = urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY})
    opener = urllib.request.build_opener(proxy_handler)
    opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
        ('Accept', 'application/json, text/javascript, */*'),
        ('Accept-Encoding', 'identity'),
        ('Connection', 'keep-alive'),
    ]
    return opener

def _fetch(url, opener=None):
    if opener is None:
        opener = _build_opener()
    try:
        req = urllib.request.Request(url)
        resp = opener.open(req, timeout=15)
        text = resp.read().decode('utf-8', errors='ignore')
        return text
    except Exception as e:
        print(f"  [WARN] fetch error: {e}", file=sys.stderr)
        return None

def get_stock_list(page=1, num=80):
    """获取A股股票列表 (新浪)"""
    opener = _build_opener()
    url = f'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page={page}&num={num}&sort=price&asc=0&node=hs_a&symbol=&_s_r_a=auto'
    text = _fetch(url, opener)
    if text:
        try:
            return json.loads(text)
        except:
            return []
    return []

def get_stock_list_count():
    """获取A股总数"""
    opener = _build_opener()
    url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeStockCount?node=hs_a'
    text = _fetch(url, opener)
    if text:
        try:
            return int(text.strip().strip('"'))
        except:
            return 0
    return 0

def get_kline(symbol, start_date, end_date, days=120, use_qfq=True):
    """
    获取个股K线数据 (腾讯)
    symbol: 如 'sh600519' 或 'sz000858'
    use_qfq: True=前复权(qfqday), False=RAW(day)
    返回: list of [date, open, high, low, close, volume]
    """
    opener = _build_opener()
    suffix = ',qfq' if use_qfq else ''
    url = f'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,{start_date},{end_date},{days}{suffix}'
    text = _fetch(url, opener)
    if not text:
        return []
    try:
        data = json.loads(text)
        stock_data = data.get('data', {}).get(symbol, {})
        key = 'qfqday' if use_qfq else 'day'
        klines = stock_data.get(key, [])
        return klines
    except:
        return []

def get_realtime_quotes(symbols):
    """
    获取实时行情 (腾讯)
    symbols: list of 'sh600519', 'sz000858'
    返回: dict of {symbol: {name, price, open, high, low, volume, ...}}
    """
    opener = _build_opener()
    q_symbols = ','.join(symbols)
    url = f'http://qt.gtimg.cn/q={q_symbols}'
    text = _fetch(url, opener)
    if not text:
        return {}
    
    results = {}
    for line in text.strip().split(';'):
        line = line.strip()
        if '=' not in line:
            continue
        key, val = line.split('=', 1)
        sym = key.replace('v_', '').strip()
        parts = val.strip('~').split('~')
        if len(parts) >= 45:
            results[sym] = {
                'name': parts[1],
                'code': parts[2],
                'price': float(parts[3]) if parts[3] else 0,
                'prev_close': float(parts[4]) if parts[4] else 0,
                'open': float(parts[5]) if parts[5] else 0,
                'volume': int(parts[6]) if parts[6] else 0,
                'high': float(parts[33]) if parts[33] else 0,
                'low': float(parts[34]) if parts[34] else 0,
                'turnover': float(parts[36]) if parts[36] else 0,
                'pe': float(parts[39]) if parts[39] else 0,
            }
    return results

def convert_symbol_to_sina(symbol):
    """转换代码格式: 600519 -> sh600519, 000858 -> sz000858"""
    code = symbol.replace('sh', '').replace('sz', '').replace('bj', '')
    if code.startswith('6'):
        return f'sh{code}'
    elif code.startswith('0') or code.startswith('3'):
        return f'sz{code}'
    elif code.startswith('8') or code.startswith('4'):
        return f'bj{code}'
    return f'sz{code}'

if __name__ == '__main__':
    print("=== A股数据适配器测试 ===")
    
    # 1. 测试获取股票总数
    count = get_stock_list_count()
    print(f"1. A股总数: {count}")
    
    # 2. 测试获取股票列表
    stocks = get_stock_list(page=1, num=10)
    print(f"2. 获取 {len(stocks)} 只股票:")
    for s in stocks[:5]:
        print(f"   {s.get('symbol','?')} {s.get('name','?')} 价格={s.get('trade','?')}")
    
    # 3. 测试K线数据
    print("3. K线测试:")
    klines = get_kline('sh600519', '2025-01-01', '2025-05-28', 120, use_qfq=True)
    print(f"   茅台: {len(klines)} 条K线")
    if klines:
        print(f"   最新: {klines[-1]}")
    
    klines_raw = get_kline('sh000001', '2025-01-01', '2025-05-28', 120, use_qfq=False)
    print(f"   上证指数RAW: {len(klines_raw)} 条")
    if klines_raw:
        print(f"   最新: {klines_raw[-1]}")
    
    # 4. 测试实时行情
    print("4. 实时行情:")
    quotes = get_realtime_quotes(['sh600519', 'sz000858', 'sh000001'])
    for sym, q in quotes.items():
        print(f"   {sym}: {q['name']} {q['price']}")
    
    print("\n=== 测试完成 ===")
