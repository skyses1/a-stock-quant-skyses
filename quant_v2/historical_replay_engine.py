"""
历史回放调度器 (Historical Replay Engine)
按交易日循环：构建 08:00 信息集、生成预测、回填现实、评估归因。
严格避免未来函数。
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from db import get_conn
from point_in_time_dataset_builder import build_feature_snapshot
from premarket_predictor import generate_premarket_prediction
from postmarket_evaluator import evaluate_prediction

def run_historical_replay(start_date, end_date):
    """
    批量回放历史交易日。
    """
    conn = get_conn()
    
    # 获取交易日历 (这里简化处理，假设 raw_market_daily 里有数据的日期都是交易日)
    dates = conn.execute("""
        SELECT DISTINCT trade_date FROM raw_market_daily 
        WHERE trade_date BETWEEN ? AND ?
        ORDER BY trade_date ASC
    """, (start_date, end_date)).fetchall()
    
    conn.close()
    trading_days = [d[0] for d in dates]
    
    print(f"🔄 开始历史回放: {start_date} -> {end_date} (共 {len(trading_days)} 天)")
    
    for trade_date in trading_days:
        try:
            print(f"\n📅 正在回放: {trade_date}")
            
            # 1. 构建特征快照 (Cutoff: T 08:00)
            feat_id = build_feature_snapshot(trade_date, "08:00:00", "v5.0")
            if not feat_id:
                continue # 审计失败跳过
                
            # 2. 生成盘前预测 (Locked)
            pred_id = generate_premarket_prediction(trade_date, feat_id, "v5.0")
            
            # 3. 盘后评估 (加载 T 日真实收盘)
            evaluate_prediction(trade_date, pred_id)
            
        except Exception as e:
            print(f"❌ 回放 {trade_date} 失败: {e}")
            import traceback
            traceback.print_exc()
            break
            
    print("\n🎉 历史回放完成！")

if __name__ == "__main__":
    # 测试回放最近 10 天
    run_historical_replay("20260501", "20260530") # 使用 Mock 数据填充的日期范围
