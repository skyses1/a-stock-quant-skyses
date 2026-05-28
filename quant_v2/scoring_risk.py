"""
P0 + P1: 风控引擎 & 四维打分卡
"""

def calculate_market_score(data):
    """
    P1: 量化四维融合公式
    满分 100 分。
    """
    # ... (existing code)
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
    
    sh_chg = data.get('sh_chg', 0)
    cyb_chg = data.get('cyb_chg', 0)
    
    sentiment_score = 15
    if sh_chg > 0.5: sentiment_score += 10
    elif sh_chg < -1.0: sentiment_score -= 10
    
    if cyb_chg > 1.0: sentiment_score += 5
    sentiment_score = max(0, min(30, sentiment_score))
    
    pm_risk = data.get('polymarket_risk_score', 50)
    macro_score = max(0, 20 - (pm_risk / 5))
    
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

def calculate_dynamic_stop_loss(current_price, high, low, multiplier=2):
    """
    动态波动率止损 (ATR Proxy)
    使用当日振幅作为波动率代理: Daily Range = High - Low
    止损距离 = 2 * Daily Range
    """
    daily_range = high - low
    if daily_range <= 0:
        # 极端情况 (如一字涨停/跌停)，回退到 5%
        return current_price * 0.95
    
    stop_distance = daily_range * multiplier
    stop_loss = current_price - stop_distance
    return round(stop_loss, 2)

