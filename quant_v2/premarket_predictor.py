"""
盘前预测引擎 (Premarket Predictor)
读取 feature_snapshot，生成 prediction_snapshot 并锁定。
"""

import sys
import os
import json
sys.path.append(os.path.dirname(__file__))

from db import get_conn
from scoring_risk import calculate_market_score
from param_loader import get_active_params

def generate_premarket_prediction(trade_date, feature_snapshot_id, strategy_version="v5.0"):
    """
    基于 T 日 08:00 的特征，生成盘前预测。
    """
    conn = get_conn()
    
    # 1. 加载特征
    feat = conn.execute("SELECT * FROM feature_snapshots WHERE id = ?", (feature_snapshot_id,)).fetchone()
    market_feats = json.loads(feat['market_features_json'])
    macro_feats = json.loads(feat['macro_features_json'])
    poly_feats = json.loads(feat['polymarket_features_json'])
    
    # 2. 准备打分数据
    # 将特征映射为 scoring_risk 需要的格式
    sh_data = market_feats.get("1.000001", market_feats.get("sh000001", {})) # 兼容不同 key
    cyb_data = market_feats.get("0.399001", market_feats.get("sz399006", {}))
    
    scoring_input = {
        "total_amount": sh_data.get("prev_amount", 0),
        "northbound_net": 0, # MVP 暂缺
        "sh_chg": sh_data.get("prev_pct_change", 0),
        "cyb_chg": cyb_data.get("prev_pct_change", 0),
        "polymarket_risk_score": 50 # MVP 暂缺真实映射
    }
    
    # 3. 计算得分与仓位
    params = get_active_params()
    scores = calculate_market_score(scoring_input)
    position = params.get("max_single_position", 0.2)
    
    if scores["total"] >= 80:
        direction = "bullish"
        risk_level = "low"
    elif scores["total"] >= 60:
        direction = "volatile_bullish"
        risk_level = "medium"
    elif scores["total"] >= 40:
        direction = "volatile_bearish"
        risk_level = "medium"
    else:
        direction = "bearish"
        risk_level = "high"
        
    # 4. 写入 prediction_snapshot (状态 locked)
    conn.execute("""
        INSERT INTO prediction_snapshots 
        (trade_date, as_of_time, strategy_version, param_version, feature_snapshot_id,
         market_direction, confidence, risk_level, suggested_position, expected_return, expected_max_drawdown,
         rationale, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'locked', CURRENT_TIMESTAMP)
    """, (
        trade_date, feat['as_of_time'], strategy_version, "v1.0", feature_snapshot_id,
        direction, scores["total"]/100.0, risk_level, position * 100, 
        scores["total"] * 0.001, 0.05, 
        f"基于资金面({scores['financial']:.1f})与情绪面({scores['sentiment']:.1f})的综合评分",
    ))
    conn.commit()
    
    pred_id = conn.execute("""
        SELECT id FROM prediction_snapshots WHERE trade_date = ? AND feature_snapshot_id = ?
    """, (trade_date, feature_snapshot_id)).fetchone()[0]
    
    conn.close()
    print(f"🔮 预测已生成并锁定 (ID: {pred_id}), 方向: {direction}")
    return pred_id
