"""
时间点数据集构建器 (Point-in-time Dataset Builder)
严格按 as_of_time (T 08:00:00) 过滤数据，生成不可变特征快照。
"""

import sys
import os
import json
import hashlib
from datetime import datetime
sys.path.append(os.path.dirname(__file__))

from db import get_conn
from leakage_auditor import audit_feature_snapshot

def build_feature_snapshot(trade_date, as_of_time="08:00:00", strategy_version="v5.0"):
    """
    构建 T 日 08:00 前的所有可见特征，写入 feature_snapshots 表。
    """
    conn = get_conn()
    cutoff_time = f"{trade_date} {as_of_time}"
    
    print(f"🏗️ 构建特征快照: {trade_date} (Cutoff: {cutoff_time})")
    
    # 1. 市场特征 (Market Features) - 只能取 T-1 及以前的日线
    market_rows = conn.execute("""
        SELECT symbol, close, pct_change, amount, volume 
        FROM raw_market_daily 
        WHERE trade_date <= ? AND asset_type = 'index'
        ORDER BY trade_date DESC
    """, (trade_date,)).fetchall()
    
    market_features = {}
    # 取最近一天的数据作为盘前特征
    if market_rows:
        for sym, close, pct, amt, vol in market_rows:
            market_features[sym] = {
                "prev_close": close,
                "prev_pct_change": pct,
                "prev_amount": amt
            }

    # 2. 宏观特征 (Macro Features) - snapshot_time <= cutoff
    macro_rows = conn.execute("""
        SELECT indicator_name, indicator_value, pct_change 
        FROM raw_macro_snapshots 
        WHERE snapshot_time <= ?
        ORDER BY snapshot_time DESC
    """, (cutoff_time,)).fetchall()
    
    macro_features = {}
    seen_indicators = set()
    for name, val, pct in macro_rows:
        if name not in seen_indicators:
            macro_features[name] = {"value": val, "pct_change": pct}
            seen_indicators.add(name)

    # 3. Polymarket 特征 - snapshot_time <= cutoff
    poly_rows = conn.execute("""
        SELECT market_id, probability, mapped_factor, mapped_direction 
        FROM raw_polymarket_snapshots 
        WHERE snapshot_time <= ?
        ORDER BY snapshot_time DESC
    """, (cutoff_time,)).fetchall()
    
    polymarket_features = {}
    seen_markets = set()
    for mid, prob, factor, direction in poly_rows:
        if mid not in seen_markets:
            polymarket_features[mid] = {
                "probability": prob, 
                "mapped_factor": factor, 
                "mapped_direction": direction
            }
            seen_markets.add(mid)
            
    # 序列化并计算 Hash
    feature_payload = json.dumps({
        "market": market_features,
        "macro": macro_features,
        "polymarket": polymarket_features
    }, sort_keys=True)
    
    feature_hash = hashlib.sha256(feature_payload.encode()).hexdigest()
    
    # 写入数据库 (默认状态 pending，等待审计)
    conn.execute("""
        INSERT OR IGNORE INTO feature_snapshots 
        (trade_date, as_of_time, strategy_version, feature_set_hash, 
         market_features_json, macro_features_json, polymarket_features_json, 
         leakage_check_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
    """, (
        trade_date, cutoff_time, strategy_version, feature_hash,
        json.dumps(market_features), json.dumps(macro_features), json.dumps(polymarket_features)
    ))
    conn.commit()
    
    # 获取 snapshot ID
    feat_id = conn.execute("""
        SELECT id FROM feature_snapshots 
        WHERE trade_date = ? AND as_of_time = ?
    """, (trade_date, cutoff_time)).fetchone()[0]
    
    conn.close()
    
    # 运行未来函数审计 (严格模式)
    from leakage_auditor import audit_feature_snapshot
    is_safe, logs = audit_feature_snapshot(trade_date, cutoff_time, feat_id)
    
    # 更新审计状态
    conn = get_conn()
    conn.execute("""
        UPDATE feature_snapshots SET leakage_check_status = ? WHERE id = ?
    """, ("passed" if is_safe else "failed", feat_id))
    conn.commit()
    conn.close()
    
    if not is_safe:
        print(f"🚨 审计失败: {trade_date} 存在未来函数泄漏风险！已阻断。")
        for log in logs:
            print(f"   📝 {log['violation_type']}: {log['detail']}")
        return None # 阻断构建
        
    print(f"✅ 特征快照构建成功 (ID: {feat_id}), 审计通过。")
    return feat_id
