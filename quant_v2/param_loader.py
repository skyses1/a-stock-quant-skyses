"""
参数加载器 (Param Loader)
P0 核心：从数据库读取 active 参数，替代硬编码和源码修改。
"""

import sqlite3
import os
from config import DB_PATH

def get_active_params():
    """
    从 strategy_params 表读取所有 active 状态的参数。
    返回格式：{'atr_multiplier': 6.0, ...}
    """
    if not os.path.exists(DB_PATH):
        # 如果数据库不存在，返回默认值
        return {
            "atr_multiplier": 6.0,
            "weight_financial": 0.4,
            "weight_sentiment": 0.3,
            "weight_macro": 0.2,
            "weight_technical": 0.1
        }

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # 查询 active 参数
    rows = conn.execute("SELECT param_name, param_value FROM strategy_params WHERE status = 'active'").fetchall()
    conn.close()
    
    params = {}
    for row in rows:
        params[row['param_name']] = row['param_value']
        
    return params
