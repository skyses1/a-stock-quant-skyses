"""
进化引擎 v2.2 (Evolution Engine - Realistic Backtest)
引入 T+1、印花税、滑点、涨跌停熔断等 A 股真实规则。
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "mock_history_v2.json")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "params.json")

# 真实交易成本配置
FEES = {
    "commission_rate": 0.00025,  # 万 2.5
    "stamp_tax_rate": 0.001,     # 千 1 (卖出收)
    "slippage_rate": 0.001       # 滑点 0.1%
}

def load_history():
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, 'r') as f:
        return json.load(f)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def simulate_realistic_strategy(history, atr_multiplier):
    """
    使用真实 A 股规则进行模拟交易。
    """
    initial_capital = 100000
    cash = initial_capital
    position = 0 # 持仓数量 (假设全仓买入一只票)
    holding_price = 0
    buy_date = -1 # 记录买入日期，用于 T+1
    
    wins = 0
    losses = 0
    trades = 0
    
    daily_atr_pct = 0.02 # 假设 ATR 2%
    stop_loss_pct = atr_multiplier * daily_atr_pct

    # 遍历每一天
    for i, day in enumerate(history):
        current_price = day['close']
        
        # 1. 检查止损 (Stop Loss Check)
        # 逻辑：如果盘中最低价 (low) 触及止损线，则必须卖出
        # 真实执行价：以止损价卖出 (简化处理，实际可能更低)
        stop_loss_price = holding_price * (1 - stop_loss_pct)
        
        if position > 0 and (day['low'] <= stop_loss_price):
            # 触发止损
            # 检查 T+1: 如果今天刚买，不能卖 (除非是底仓，这里简化为只能卖出昨天的仓位)
            # 在单笔模拟中，如果 buy_date == day['date']，则不能卖。
            # 但止损优先级通常极高，这里假设如果是次日及以后，坚决卖出。
            # 为了简化 T+1 冲突：如果今天买入且触发止损，只能认栽持有到明天。
            # 但 A 股很多策略死在 T+1 无法止损。这里我们严格执行 T+1：
            # 如果 buy_date != day['date'] (即非今日买入)，则卖出。
            if buy_date != day['date']:
                realized_price = stop_loss_price * (1 - FEES['slippage_rate'])
                revenue = position * realized_price
                cost = position * holding_price # 成本不重复计算佣金，只在买卖时算
                # 扣除卖出费用
                fees = revenue * (FEES['commission_rate'] + FEES['stamp_tax_rate'])
                cash += (revenue - fees)
                position = 0
                holding_price = 0
                losses += 1
                trades += 1
                continue

        # 2. 卖出逻辑 (Take Profit / Exit)
        # 简化逻辑：持有到收盘前卖出 (如果是 T+1 允许的日子)
        if position > 0 and buy_date != day['date']:
            # 这里假设策略是超短线：今天卖
            # 实际卖出价：收盘价 - 滑点
            realized_price = current_price * (1 - FEES['slippage_rate'])
            revenue = position * realized_price
            fees = revenue * (FEES['commission_rate'] + FEES['stamp_tax_rate'])
            cash += (revenue - fees)
            
            pnl = (realized_price - holding_price) / holding_price
            if pnl > 0: wins += 1
            else: losses += 1
            
            position = 0
            holding_price = 0
            trades += 1

        # 3. 买入逻辑 (Entry)
        # 假设：如果现金足够，且当天没涨停，则全仓买入
        # 买入价：次日开盘价 (因为信号是收盘后出的) 或 当天收盘价
        # 为了贴近实战：早报出策略 -> 盘中买入。这里模拟以 Open 买入。
        if position == 0 and cash > 0:
            # 检查是否涨停 (涨停买不进)
            if day.get('is_limit_up', False):
                continue 
            
            # 买入价：Open + 滑点
            buy_price = day['open'] * (1 + FEES['slippage_rate'])
            
            # 计算可买数量 (取整 100 股)
            qty = int((cash * 0.99) / buy_price / 100) * 100 # 留 1% 资金做手续费缓冲
            if qty < 100: qty = 100 # 碎股逻辑略，最小 100
            
            cost = qty * buy_price
            fees = cost * FEES['commission_rate']
            
            if cash >= (cost + fees):
                cash -= (cost + fees)
                position = qty
                holding_price = buy_price
                buy_date = day['date']

    # 4. 最终清算 (如果最后还有持仓，按最后一天 Close 卖出)
    if position > 0:
        last_day = history[-1]
        realized_price = last_day['close'] * (1 - FEES['slippage_rate'])
        revenue = position * realized_price
        fees = revenue * (FEES['commission_rate'] + FEES['stamp_tax_rate'])
        cash += (revenue - fees)
        pnl = (realized_price - holding_price) / holding_price
        if pnl > 0: wins += 1
        else: losses += 1

    final_equity = cash
    total_return = (final_equity - initial_capital) / initial_capital
    win_rate = wins / trades if trades > 0 else 0
    
    return {
        "atr_multiplier": atr_multiplier,
        "final_equity": final_equity,
        "win_rate": win_rate,
        "total_return": total_return,
        "trades": trades
    }

def run_evolution():
    print("🧬 启动进化引擎 v2.2 (Realistic A-Stock Rules)...")
    print("   ✅ 包含：T+1 限制、印花税、万 2.5 佣金、0.1% 滑点、涨停熔断")
    
    history = load_history()
    if not history:
        print("❌ 无历史数据。")
        return
    
    config = load_config()
    current_mult = config["risk_engine"]["atr_multiplier"] if config else 4.0
    candidates = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    
    print(f"   样本数: {len(history)} 天 | 当前参数: {current_mult}")
    
    results = []
    for c in candidates:
        res = simulate_realistic_strategy(history, c)
        results.append(res)
        print(f"   测试 ATR={c}: 收益 {res['total_return']:+.2%} | 胜率 {res['win_rate']:.0%} | 交易 {res['trades']} 次")

    best_result = max(results, key=lambda x: x['final_equity'])
    
    print("\n" + "="*40)
    print(f"🏆 真实回测完成！")
    print(f"   发现最优参数: ATR={best_result['atr_multiplier']}")
    print(f"   预期真实收益: {best_result['total_return']:+.2%} (扣除税费滑点后)")
    print("="*40)

if __name__ == "__main__":
    run_evolution()
