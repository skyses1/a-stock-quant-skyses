"""
P2: 动态学习映射关系引擎
根据历史表现调整 Polymarket -> A 股 的映射权重
"""

import sqlite3
import os

DB_PATH = "/home/admin/.hermes/scripts/quant_v2/quant_system.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def update_mapping_score(event_category, target_sector, success_score, date):
    """
    success_score: -1.0 到 1.0 (例如：如果推荐该板块涨了 5%，success_score 可能是 0.5)
    """
    # 记录历史
    conn = get_conn()
    conn.execute('''
        INSERT INTO mapping_history (date, event_category, target_sector, success_score)
        VALUES (?, ?, ?, ?)
    ''', (date, event_category, target_sector, success_score))
    conn.commit()
    conn.close()

def get_mapping_weight(event_category, target_sector):
    """
    获取当前映射权重。
    基于历史平均成功率计算。
    """
    conn = get_conn()
    row = conn.execute('''
        SELECT AVG(success_score) as avg_score, COUNT(*) as count
        FROM mapping_history
        WHERE event_category = ? AND target_sector = ?
    ''', (event_category, target_sector)).fetchone()
    conn.close()
    
    if row and row['count'] > 2:  # 至少 3 次样本才开始调整
        # 基础权重 1.0，根据历史表现上下浮动
        base = 1.0
        adj = row['avg_score'] * 0.5  # 最多调整 50%
        return round(base + adj, 2)
    else:
        return 1.0  # 默认权重

# Example usage for testing
if __name__ == "__main__":
    print("Testing learning engine...")
    # 模拟数据
    # update_mapping_score("Geopolitics", "Gold", 0.8, "20260527")
    # w = get_mapping_weight("Geopolitics", "Gold")
    # print(f"Weight for Geopolitics->Gold: {w}")
    print("✅ Engine loaded.")
