#!/usr/bin/env python3
"""
每日盯市脚本 (Mark-to-Market)
任务 2: 每日自动更新数据库中持仓股票的表现。
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from db import get_pending_stocks, update_mark_to_market
from a_stock_data import fetch_tencent_quotes
from config import TRADING_FEES

def run_mark_to_market():
    print("👀 开始每日盯市 (Mark-to-Market)...")
    
    # 1. 获取所有未平仓股票
    pending = get_pending_stocks()
    if not pending:
        print("   ✅ 无持仓股票需要更新。")
        return
    
    codes = [p['code'] for p in pending]
    print(f"   检查 {len(codes)} 只持仓股票: {codes}")
    
    # 2. 批量获取实时行情
    quotes = fetch_tencent_quotes(codes)
    
    updated_count = 0
    for stock in pending:
        code = stock['code']
        quote = quotes.get(code)
        
        if quote:
            current_price = quote['price']
            high = quote.get('high', current_price)
            low = quote.get('low', current_price)
            
            # 更新数据库
            changed = update_mark_to_market(code, current_price, high, low)
            if changed:
                updated_count += 1
                status = "触发止损" if quote['low'] <= stock['stop_loss'] else "正常"
                print(f"   🔄 {stock['name']} ({code}): {current_price} | 盈亏 {quote['chg_pct']}% | {status}")
        else:
            print(f"   ⚠️ {stock['name']} ({code}): 获取行情失败")

    print(f"\n✅ 盯市完成：成功更新 {updated_count} 条记录")

if __name__ == "__main__":
    run_mark_to_market()
