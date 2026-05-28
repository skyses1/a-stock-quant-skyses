"""
P0 + P1: 风控引擎 & 四维打分卡
Refactored to be database-driven (Audit Fix #4 - P0)
"""

from param_loader import get_active_params
from config import TRADING_FEES

# 每次调用时动态加载 active 参数
PARAMS = get_active_params()

# 获取关键参数，带默认值
ATR_MULTIPLIER = PARAMS.get("atr_multiplier", 4.0)
W_WEIGHTS = {
    "financial": PARAMS.get("weight_financial", 0.4),
    "sentiment": PARAMS.get("weight_sentiment", 0.3),
    "macro": PARAMS.get("weight_macro", 0.2),
    "technical": PARAMS.get("weight_technical", 0.1)
}

def calculate_market_score(data):
    """
    P1: 量化四维融合公式 (DB-Driven 权重)
    """
    w = W_WEIGHTS
    
    # 1. 资金面 (0-40 * weight) -> 简化处理：保持总分 100，权重用于加权
    # 实际逻辑：计算各分项原始分 (0-100)，然后加权求和
    
    # 资金面原始分 (0-100)
    total_vol = data.get('total_amount', 0)
    north = data.get('northbound_net', 0)
    
    vol_score = 0
    if total_vol > 10000: vol_score += 40
    elif total_vol > 8000: vol_score += 30
    elif total_vol < 6000: vol_score += 0
    else: vol_score += 15
    
    nb_score = 0
    if north > 50: nb_score += 60
    elif north > 0: nb_score += 40
    elif north < -50: nb_score += 0
    else: nb_score += 20
    
    financial_raw = vol_score + nb_score # 0-100
    
    # 2. 情绪面原始分 (0-100)
    sh_chg = data.get('sh_chg', 0)
    cyb_chg = data.get('cyb_chg', 0)
    
    sentiment_raw = 50 # 基准
    if sh_chg > 0.5: sentiment_raw += 30
    elif sh_chg < -1.0: sentiment_raw -= 30
    
    if cyb_chg > 1.0: sentiment_raw += 20
    sentiment_raw = max(0, min(100, sentiment_raw))
    
    # 3. 宏观面原始分 (0-100)
    pm_risk = data.get('polymarket_risk_score', 50)
    macro_raw = max(0, 100 - pm_risk) # 风险越低分越高
    
    # 4. 技术面原始分 (0-100)
    tech_raw = 50 
    if sh_chg > 0 and cyb_chg > 0: tech_raw = 80
    elif sh_chg < -1: tech_raw = 20
    
    # 加权求和
    total_score = (
        financial_raw * w['financial'] +
        sentiment_raw * w['sentiment'] +
        macro_raw * w['macro'] +
        tech_raw * w['technical']
    )
    
    return {
        "total": total_score,
        "financial": financial_raw * w['financial'],
        "sentiment": sentiment_raw * w['sentiment'],
        "macro": macro_raw * w['macro'],
        "tech": tech_raw * w['technical']
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
