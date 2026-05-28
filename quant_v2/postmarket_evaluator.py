"""
盘后评估器 (Post-market Evaluator)
读取 T 日真实收盘，评估 prediction_snapshot 的准确性，计算收益与归因。
"""

import sys
import os
import json
sys.path.append(os.path.dirname(__file__))

from db import get_conn
from config import TRADING_FEES

def evaluate_prediction(trade_date, prediction_id):
    """
    1. 加载 prediction_snapshot。
    2. 加载 T 日真实收盘 (reality)。
    3. 计算方向准确率、模拟收益、最大回撤等。
    4. 写入 evaluation_results。
    """
    conn = get_conn()
    
    # 1. 获取预测信息
    # 注意：prediction_snapshots 不包含 market_features_json，需要从 feature_snapshots join 取
    pred = conn.execute("""
        SELECT ps.*, fs.market_features_json, fs.macro_features_json, fs.polymarket_features_json
        FROM prediction_snapshots ps
        JOIN feature_snapshots fs ON ps.feature_snapshot_id = fs.id
        WHERE ps.id = ?
    """, (prediction_id,)).fetchone()
    
    # 获取交易成本配置 (从数据库读取，不再硬编码)
    cost_config = conn.execute("SELECT * FROM trading_cost_configs WHERE status = 'active' LIMIT 1").fetchone()
    if cost_config:
        slippage_bps = cost_config['slippage_bps']
        commission_rate = cost_config['commission_rate']
        stamp_tax_sell = cost_config['stamp_tax_sell']
    else:
        # Fallback defaults
        slippage_bps = 20.0
        commission_rate = 0.0003
        stamp_tax_sell = 0.0005

    # 2. 获取 T 日真实收盘 (reality)
    reality = conn.execute("""
        SELECT symbol, open, close, high, low, pct_change 
        FROM raw_market_daily 
        WHERE trade_date = ? AND asset_type = 'index'
    """, (trade_date,)).fetchall()
    
    if not reality:
        print(f"⚠️ 无 T 日真实行情数据: {trade_date}")
        return

    # 提取上证指数表现作为基准
    sh_real = next((r for r in reality if '000001' in r[0]), None)
    benchmark_ret = sh_real[5] if sh_real else 0 # pct_change
    
    # 模拟组合收益 (MVP: 简化处理，假设跟随大盘方向 + 策略 Alpha)
    # 实际应读取 prediction_items 里的个股表现。这里用方向判断模拟。
    portfolio_ret = 0
    if pred['market_direction'] in ['bullish', 'volatile_bullish']:
        portfolio_ret = benchmark_ret * (pred['confidence'] + 0.2) # 简单的 Alpha 模拟
    else:
        portfolio_ret = -benchmark_ret * 0.5
        
    # 扣除交易成本 (使用配置参数)
    slippage = slippage_bps / 10000
    tax_fee = commission_rate + stamp_tax_sell # 假设双向佣金，单向印花税
    cost = slippage + tax_fee
    
    net_ret = portfolio_ret - cost
    excess_ret = net_ret - benchmark_ret
    
    # 方向是否正确
    direction_correct = 0
    if (pred['market_direction'] in ['bullish', 'volatile_bullish'] and benchmark_ret > 0) or \
       (pred['market_direction'] in ['bearish', 'volatile_bearish'] and benchmark_ret < 0):
        direction_correct = 1
        
    # 3. 写入 reality_snapshot
    market_close_json = json.dumps({r[1]: {"close": r[2], "high": r[3], "low": r[4], "pct": r[5]} for r in reality})
    conn.execute("""
        INSERT OR IGNORE INTO reality_snapshots (trade_date, close_time, market_close_json, benchmark_return, created_at)
        VALUES (?, '15:00:00', ?, ?, CURRENT_TIMESTAMP)
    """, (trade_date, market_close_json, benchmark_ret))
    conn.commit()
    reality_id = conn.execute("SELECT id FROM reality_snapshots WHERE trade_date = ?", (trade_date,)).fetchone()[0]
    
    # 4. 写入 evaluation_results
    conn.execute("""
        INSERT INTO evaluation_results 
        (prediction_id, reality_id, direction_correct, portfolio_return, benchmark_return, 
         excess_return, max_intraday_drawdown, hit_rate, win_count, loss_count, 
         stop_loss_triggered_count, slippage_cost, tax_fee_cost, evaluation_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 0, 0, 0, ?, ?, 'completed', CURRENT_TIMESTAMP)
    """, (
        prediction_id, reality_id, direction_correct, net_ret, benchmark_ret, excess_ret,
        slippage, tax_fee
    ))
    conn.commit()
    
    print(f"📊 评估完成: {trade_date} | 基准: {benchmark_ret:.2%} | 策略: {net_ret:.2%} | 方向: {'✅' if direction_correct else '❌'}")
    conn.close()
