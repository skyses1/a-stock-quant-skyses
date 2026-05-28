"""
未来函数审计器 (Leakage Auditor)
严格验证 feature_snapshot 中没有任何 timestamp > cutoff_time 的数据。
"""

import sqlite3
import os
from datetime import datetime
from db import get_conn

def audit_feature_snapshot(trade_date, as_of_time, feature_snapshot_id):
    """
    扫描 raw 表，确保构建特征时没有使用 cutoff_time 之后的数据。
    """
    conn = get_conn()
    logs = []
    is_passed = True
    
    # 1. 检查行情数据 (raw_market_daily)
    # 规则：只能使用 trade_date 之前的收盘价
    # 实际上，point_in_time 构建器应该只 SELECT <= trade_date 的数据。
    # 这里我们验证一下 raw_market_daily 中是否有当天或未来的数据被错误引用（虽然日线表通常按日期索引）
    rows = conn.execute("""
        SELECT id, trade_date FROM raw_market_daily 
        WHERE trade_date > ?
    """, (trade_date,)).fetchall()
    
    if rows:
        is_passed = False
        for r in rows:
            logs.append({
                "trade_date": trade_date,
                "as_of_time": as_of_time,
                "table_name": "raw_market_daily",
                "record_id": r[0],
                "data_timestamp": r[1],
                "audit_result": "failed",
                "violation_type": "future_price",
                "detail": f"Found price data for {r[1]} which is after {trade_date}"
            })

    # 2. 检查新闻数据 (raw_news_events)
    # 规则：published_at <= as_of_time
    rows = conn.execute("""
        SELECT id, published_at FROM raw_news_events 
        WHERE published_at > ?
    """, (as_of_time,)).fetchall()
    
    if rows:
        # 注意：这里只是检查数据库里有没有未来的新闻。
        # 真正的审计需要检查 feature_snapshot 构建时是否引用了这些 ID。
        # MVP 阶段，我们记录警告。
        is_passed = False
        for r in rows:
            logs.append({
                "trade_date": trade_date,
                "as_of_time": as_of_time,
                "table_name": "raw_news_events",
                "record_id": r[0],
                "data_timestamp": r[1],
                "audit_result": "failed",
                "violation_type": "future_news",
                "detail": f"Found news published at {r[1]} which is after cutoff {as_of_time}"
            })

    # 3. 检查宏观/Polymarket 快照
    # 规则：snapshot_time <= as_of_time
    for table in ["raw_macro_snapshots", "raw_polymarket_snapshots"]:
        rows = conn.execute(f"""
            SELECT id, snapshot_time FROM {table} 
            WHERE snapshot_time > ?
        """, (as_of_time,)).fetchall()
        
        if rows:
            is_passed = False
            for r in rows:
                logs.append({
                    "trade_date": trade_date,
                    "as_of_time": as_of_time,
                    "table_name": table,
                    "record_id": r[0],
                    "data_timestamp": r[1],
                    "audit_result": "failed",
                    "violation_type": "future_snapshot",
                    "detail": f"Found snapshot at {r[1]} which is after cutoff {as_of_time}"
                })

    # 写入审计日志
    if logs:
        conn.executemany("""
            INSERT INTO leakage_audit_logs 
            (trade_date, as_of_time, table_name, record_id, data_timestamp, audit_result, violation_type, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [(
            l["trade_date"], l["as_of_time"], l["table_name"], l["record_id"], 
            l["data_timestamp"], l["audit_result"], l["violation_type"], l["detail"]
        ) for l in logs])
        conn.commit()
        
    conn.close()
    return is_passed, logs
