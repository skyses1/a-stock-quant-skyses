#!/usr/bin/env python3
"""
A 股量化系统 v2.0 主入口
整合：数据抓取 -> 四维打分 -> 风控计算 -> 持久化 -> 报告输出
"""

import sys
import os
import json
import subprocess

# 添加路径 (父目录 + 当前目录)
BASE_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(BASE_DIR)
sys.path.append(PARENT_DIR)
sys.path.append(BASE_DIR)

from db import init_db, save_daily_snapshot, save_recommendations
from scoring_risk import calculate_market_score, get_position_advice
from a_stock_data import fetch_tencent_quotes, fetch_northbound_flow, safe_float

def run():
    print("=" * 60)
    print("  A 股量化系统 v2.0")
    print("=" * 60)
    
    # 1. 初始化数据库 (P2)
    init_db()
    
    # 2. 抓取数据 (P0 - 已修复)
    print("\n[1/4] 抓取数据...")
    quotes = fetch_tencent_quotes(["sh000001", "sz399001", "sz399006", "sh000688"])
    northbound = fetch_northbound_flow()
    
    if not quotes:
        print("❌ 数据抓取失败")
        return

    # 解析关键指标
    sh = quotes.get("sh000001", {})
    sz = quotes.get("sz399001", {})
    cyb = quotes.get("sz399006", {})
    kcb = quotes.get("sh000688", {})
    
    total_amount = sh.get("amount_yi", 0) + sz.get("amount_yi", 0)
    nb_net = northbound[0]['total_net_yi'] if northbound else 0
    
    print(f"  上证：{sh.get('price')} ({sh.get('chg_pct')}%)")
    print(f"  成交：{total_amount:.1f}亿 | 北向：{nb_net:+.2f}亿")

    # 3. 计算打分 (P1) & 风控 (P0)
    print("\n[2/4] 计算模型评分...")
    
    # 构造输入数据 (模拟 Polymarket 风险分)
    input_data = {
        "total_amount": total_amount,
        "northbound_net": nb_net,
        "sh_chg": sh.get("chg_pct"),
        "cyb_chg": cyb.get("chg_pct"),
        "polymarket_risk_score": 50
    }
    
    scores = calculate_market_score(input_data)
    print(f"  综合得分：{scores['total']}/100")
    
    advice, style = get_position_advice(scores['total'])
    print(f"  仓位建议：{advice}% ({style})")

    # 计算动态止损参考 (Market Volatility)
    from scoring_risk import calculate_dynamic_stop_loss
    # 使用指数的波动率作为市场基准参考
    # ATR Proxy for SH Index
    sh_high = sh.get('high', sh.get('price'))
    sh_low = sh.get('low', sh.get('price'))
    sh_price = sh.get('price')
    
    # 如果数据异常，使用 price
    stop_dist = sh_high - sh_low
    if stop_dist > 0:
        stop_loss_pct = (stop_dist * 2) / sh_price * 100
        print(f"  📊 市场波动率 (ATR Proxy): {stop_loss_pct:.2f}% (建议止损宽度)")
    else:
        print("  📊 市场波动率: 数据不足")


    # 4. 持久化 (P2)
    print("\n[3/5] 写入数据库...")
    today = quotes["sh000001"].get("trade_time", "")[:8]
    if not today:
        from datetime import datetime
        today = datetime.now().strftime("%Y%m%d")

    snapshot_data = {
        "date": today,
        "total_amount": total_amount,
        "northbound_net": nb_net,
        "sh_close": sh.get("price"),
        "sz_close": sz.get("price"),
        "cyb_close": cyb.get("price"),
        "polymarket_risk": 50,
        "system_score": scores['total']
    }
    
    save_daily_snapshot(today, snapshot_data)
    print(f"  已保存今日快照: {today}")

    # P2: 失效报警 (Kill Switch)
    # 检查最近 5 次推荐表现
    from db import get_pending_stocks
    pending = get_pending_stocks()
    recent_losses = 0
    for stock in pending:
        if stock.get('pnl_pct', 0) < -0.05: # 亏损超过 5%
            recent_losses += 1
    
    kill_switch_active = recent_losses >= 3
    if kill_switch_active:
        print(f"\n  🚨 触发失效报警 (Kill Switch): 近期 {recent_losses} 只持仓严重亏损！")
        print(f"  系统已自动降级：建议仓位强制调整为 10% (防守模式)")
        advice = 10
        style = "🚨 风控降级"

    # 5. 输出结果供 Agent 读取
    print("\n[4/4] 输出 JSON 结果...")
    
    result = {
        "date": today,
        "scores": scores,
        "position": {"pct": advice, "style": style},
        "market": {
            "sh": sh, "sz": sz, "cyb": cyb, "kcb": kcb,
            "total_amount": round(total_amount, 1),
            "northbound_net": round(nb_net, 2)
        }
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"❌ 系统错误：{e}")
        import traceback
        traceback.print_exc()
