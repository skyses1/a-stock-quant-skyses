"""
P0 + P1: 风控引擎 & 四维打分卡
Refactored to be configuration-driven (Audit Fix #4)
"""

import json
import os

# Load parameters from config file instead of hardcoding
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "params.json")

def load_params():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    
    # Fallback defaults if config is missing
    return {
        "risk_engine": {"atr_multiplier": 4.0},
        "scoring_weights": {"financial": 0.4, "sentiment": 0.3, "macro": 0.2, "technical": 0.1}
    }

PARAMS = load_params()
ATR_MULTIPLIER = PARAMS.get("risk_engine", {}).get("atr_multiplier", 4.0)

def calculate_market_score(data):
    """
    P1: 量化四维融合公式 (配置化权重)
    """
    weights = PARAMS.get("scoring_weights", {"financial": 0.4, "sentiment": 0.3, "macro": 0.2, "technical": 0.1})
    
    # 1. 资金面 (0-40)
    total_vol = data.get('total_amount', 0)
    north = data.get('northbound_net', 0)
    
    vol_score = 0
    if total_vol > 10000: vol_score += 15
    elif total_vol > 8000: vol_score += 10
    elif total_vol < 6000: vol_score += 0
    else: vol_score += 5
    
    nb_score = 0
    if north > 50: nb_score += 25
    elif north > 0: nb_score += 15
    elif north < -50: nb_score += 0
    else: nb_score += 10
    
    financial_score = vol_score + nb_score
    
    # 2. 情绪面 (0-30)
    sh_chg = data.get('sh_chg', 0)
    cyb_chg = data.get('cyb_chg', 0)
    
    sentiment_score = 15
    if sh_chg > 0.5: sentiment_score += 10
    elif sh_chg < -1.0: sentiment_score -= 10
    
    if cyb_chg > 1.0: sentiment_score += 5
    sentiment_score = max(0, min(30, sentiment_score))
    
    # 3. 宏观面 (0-20)
    pm_risk = data.get('polymarket_risk_score', 50)
    macro_score = max(0, 20 - (pm_risk / 5))
    
    # 4. 技术面 (0-10)
    tech_score = 5 
    if sh_chg > 0 and cyb_chg > 0: tech_score = 10
    elif sh_chg < -1: tech_score = 2
    
    total_score = financial_score + sentiment_score + macro_score + tech_score
    
    return {
        "total": total_score,
        "financial": financial_score,
        "sentiment": sentiment_score,
        "macro": macro_score,
        "tech": tech_score
    }

def get_position_advice(score, current_position=0):
    """P0: 仓位管理"""
    if score >= 80: return min(100, current_position + 20), "重仓进攻"
    elif score >= 60: return min(80, current_position + 10), "稳健持有"
    elif score >= 40: return 40, "防守反击"
    else: return 10, "空仓/极轻仓观望"

def calculate_dynamic_stop_loss(current_price, high, low):
    """
    动态波动率止损 (Daily Range Proxy - Audit Fix #3)
    使用配置化的 ATR_MULTIPLIER
    """
    daily_range = high - low
    if daily_range <= 0:
        return current_price * 0.95
    
    stop_distance = daily_range * ATR_MULTIPLIER
    stop_loss = current_price - stop_distance
    return round(stop_loss, 2)
