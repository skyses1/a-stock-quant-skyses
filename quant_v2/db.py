"""
P2: 状态持久化 (SQLite)
用于记录每日报告数据、推荐标的、以及后续的实际涨跌幅 (Paper Trading)
"""

import sqlite3
import os
import json # Fix: Missing import
from datetime import datetime
from config import DB_PATH

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
            stop_loss REAL,
            target_position REAL,
            score INTEGER,
            logic TEXT,
            status TEXT DEFAULT 'PENDING',  -- PENDING, HIT_TP, HIT_SL, CLOSED
            current_price REAL,
            pnl_pct REAL,
            update_time TEXT
        )
    ''')

    # 3. 策略参数配置表 (P0 核心：替代 params.json 和源码修改)
    c.execute('''
        CREATE TABLE IF NOT EXISTS strategy_params (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            param_name TEXT NOT NULL,
            param_value REAL NOT NULL,
            status TEXT DEFAULT 'active', -- active, candidate, shadow, rejected, archived
            version TEXT DEFAULT '1.0',
            validation_score REAL DEFAULT 0,
            sample_size INTEGER DEFAULT 0,
            max_drawdown REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 初始化默认参数 (如果表是空的)
    c.execute("SELECT count(*) FROM strategy_params")
    if c.fetchone()[0] == 0:
        defaults = [
            ('atr_multiplier', 6.0, 'active'), # 根据之前的真实回测优化为 6.0
            ('weight_financial', 0.40, 'active'),
            ('weight_sentiment', 0.30, 'active'),
            ('weight_macro', 0.20, 'active'),
            ('weight_technical', 0.10, 'active'),
            ('max_single_position', 0.20, 'active'),
            ('stop_loss_pct', 0.05, 'active')
        ]
        c.executemany("INSERT INTO strategy_params (param_name, param_value, status) VALUES (?, ?, ?)", defaults)

    # 4. 映射关系历史
    c.execute('''
        CREATE TABLE IF NOT EXISTS mapping_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            event_category TEXT,
            target_sector TEXT,
            success_score REAL
        )
    ''')

    # 5. 进化与决策记录表 (新增)
    c.execute('''
        CREATE TABLE IF NOT EXISTS evolution_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT UNIQUE,
            run_type TEXT,
            train_start TEXT, train_end TEXT,
            test_start TEXT, test_end TEXT,
            candidate_version TEXT, champion_version TEXT,
            candidate_return REAL, champion_return REAL,
            candidate_max_drawdown REAL, champion_max_drawdown REAL,
            candidate_hit_rate REAL, champion_hit_rate REAL,
            decision TEXT, reason TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS gatekeeper_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evolution_run_id INTEGER NOT NULL,
            rule_name TEXT NOT NULL,
            rule_result TEXT NOT NULL,
            rule_detail TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(evolution_run_id) REFERENCES evolution_runs(id)
        )
    ''')
    
    # 6. P1 新增：配置表 (Config Tables - 消除硬编码)
    c.execute('''
        CREATE TABLE IF NOT EXISTS replay_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_name TEXT NOT NULL,
            cutoff_time TEXT NOT NULL, -- e.g., "08:00:00"
            timezone TEXT NOT NULL DEFAULT "Asia/Shanghai",
            universe TEXT NOT NULL DEFAULT "index",
            benchmark TEXT NOT NULL DEFAULT "sh000001",
            start_date TEXT,
            end_date TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS trading_cost_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_name TEXT NOT NULL,
            commission_rate REAL NOT NULL DEFAULT 0.0003,
            min_commission REAL NOT NULL DEFAULT 5.0,
            stamp_tax_sell REAL NOT NULL DEFAULT 0.0005,
            transfer_fee REAL NOT NULL DEFAULT 0.00001,
            slippage_bps REAL NOT NULL DEFAULT 20.0,
            limit_buy_policy TEXT NOT NULL DEFAULT "limit_up_reject",
            status TEXT NOT NULL DEFAULT "active",
            created_at TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS gatekeeper_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_name TEXT NOT NULL,
            min_sample_size INTEGER NOT NULL DEFAULT 60,
            min_excess_return REAL NOT NULL DEFAULT 0.03,
            max_drawdown_not_worse INTEGER NOT NULL DEFAULT 0,
            max_turnover_increase REAL NOT NULL DEFAULT 1.5,
            min_win_rate_delta REAL NOT NULL DEFAULT 0.0,
            min_profit_factor REAL NOT NULL DEFAULT 1.1,
            status TEXT NOT NULL DEFAULT "active",
            created_at TEXT NOT NULL
        )
    ''')
    
    # 7. P1 新增：版本历史与回滚 (Version History)
    c.execute('''
        CREATE TABLE IF NOT EXISTS strategy_version_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            old_version TEXT,
            new_version TEXT,
            promoted_at TEXT,
            promoted_by TEXT,
            reason TEXT,
            backtest_metrics TEXT,
            rollback_to_version TEXT,
            status TEXT NOT NULL DEFAULT "active"
        )
    ''')

    # 8. 补充 strategy_params 缺失字段
    try:
        c.execute("ALTER TABLE strategy_params ADD COLUMN train_start TEXT")
        c.execute("ALTER TABLE strategy_params ADD COLUMN train_end TEXT")
        c.execute("ALTER TABLE strategy_params ADD COLUMN test_start TEXT")
        c.execute("ALTER TABLE strategy_params ADD COLUMN test_end TEXT")
    except:
        pass # 字段可能已存在

    # 9. 初始化默认配置 (如果表是空的)
    c.execute("SELECT count(*) FROM replay_configs WHERE config_name = 'default'")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO replay_configs 
            (config_name, cutoff_time, timezone, universe, benchmark, created_at) 
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', ('default', '08:00:00', 'Asia/Shanghai', 'index', 'sh000001'))
        
        c.execute('''
            INSERT INTO trading_cost_configs 
            (config_name, commission_rate, stamp_tax_sell, slippage_bps, created_at) 
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', ('default', 0.0003, 0.0005, 20.0))
        
        c.execute('''
            INSERT INTO gatekeeper_configs 
            (config_name, min_sample_size, min_excess_return, status, created_at) 
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', ('default', 30, 0.02, 'active'))

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

def update_mark_to_market(stock_code, current_price, high=None, low=None):
    """
    任务 2: 每日盯市。更新持仓表现，检查是否触发止损。
    """
    conn = get_conn()
    
    # 获取当前记录
    row = conn.execute("SELECT * FROM recommendations WHERE code = ? AND status = 'PENDING' ORDER BY date DESC LIMIT 1", (stock_code,)).fetchone()
    
    if not row:
        conn.close()
        return False

    entry_price = row['price']
    stop_loss = row['stop_loss']
    pnl = (current_price - entry_price) / entry_price
    
    # 检查止损 (如果最低价触及)
    new_status = 'PENDING'
    if low is not None and low <= stop_loss:
        new_status = 'HIT_SL'
        pnl = (stop_loss - entry_price) / entry_price
    # 也可以在这里加止盈逻辑 (比如 pnl > 0.10 -> HIT_TP)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn.execute('''
        UPDATE recommendations 
        SET current_price = ?, pnl_pct = ?, status = ?, update_time = ?
        WHERE id = ?
    ''', (current_price, pnl, new_status, now, row['id']))
    
    conn.commit()
    conn.close()
    return True

def get_pending_stocks():
    """
    获取所有尚未平仓的股票
    """
    conn = get_conn()
    rows = conn.execute("SELECT * FROM recommendations WHERE status = 'PENDING'").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_history_for_evolution():
    """
    任务 1: 获取真实历史数据供进化引擎使用
    优先读取 DB，如果 DB 数据不足 (Sample < 5)，则回退读取 Mock 文件 (用于测试)
    """
    conn = get_conn()
    rows = conn.execute("SELECT * FROM recommendations WHERE status IN ('HIT_SL', 'HIT_TP', 'CLOSED')").fetchall()
    conn.close()
    
    real_data = [dict(row) for row in rows]
    
    if len(real_data) < 5:
        mock_path = os.path.join(os.path.dirname(__file__), "mock_history_v2.json")
        if os.path.exists(mock_path):
            print("   ⚠️ DB 真实记录不足，回退使用 Mock 数据进行回测演示。")
            with open(mock_path, 'r') as f:
                return json.load(f)
    
    return real_data

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized with new schema.")
