"""
P2: 状态持久化 (SQLite)
用于记录每日报告数据、推荐标的、以及后续的实际涨跌幅 (Paper Trading)
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "/home/admin/.hermes/scripts/quant_v2/quant_system.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    # 1. 每日宏观数据快照
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_snapshots (
            date TEXT PRIMARY KEY,
            total_amount REAL,
            northbound_net REAL,
            sh_close REAL,
            sz_close REAL,
            cyb_close REAL,
            polymarket_risk_score REAL,
            system_score REAL
        )
    ''')

    # 2. 推荐标的 (Paper Trading)
    c.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            code TEXT,
            name TEXT,
            price REAL,
            current_price REAL,
            pnl_pct REAL,
            stop_loss REAL,
            target_position REAL,
            score INTEGER,
            logic TEXT,
            status TEXT DEFAULT 'PENDING'
        )
    ''')

    # 3. 映射关系历史 (用于动态学习)
    c.execute('''
        CREATE TABLE IF NOT EXISTS mapping_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            event_category TEXT, -- e.g. 'Geopolitics', 'Crypto'
            target_sector TEXT,  -- e.g. 'Gold', 'Tech'
            success_score REAL   -- -1.0 to 1.0 based on next day performance
        )
    ''')

    conn.commit()
    conn.close()
    return True

def save_daily_snapshot(date, data):
    conn = get_conn()
    conn.execute('''
        INSERT OR REPLACE INTO daily_snapshots 
        (date, total_amount, northbound_net, sh_close, sz_close, cyb_close, polymarket_risk_score, system_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        date,
        data.get('total_amount'),
        data.get('northbound_net'),
        data.get('sh_close'),
        data.get('sz_close'),
        data.get('cyb_close'),
        data.get('polymarket_risk'),
        data.get('system_score')
    ))
    conn.commit()
    conn.close()

def save_recommendations(date, stocks):
    """
    stocks: list of dicts {code, name, price, stop_loss, position, score, logic}
    """
    conn = get_conn()
    for s in stocks:
        conn.execute('''
            INSERT INTO recommendations (date, code, name, price, stop_loss, target_position, score, logic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            date, s['code'], s['name'], s['price'], 
            s['stop_loss'], s['position'], s['score'], s['logic']
        ))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized.")
