"""
进化引擎 v4.0 (Evolution Engine + Gatekeeper)
P4 门禁核心：只有击败 Champion (旧参数)，且风控达标，才能晋升 Active。
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from db import get_conn, get_history_for_evolution
from config import TRADING_FEES

# 门禁标准 (Audit Standards)
GATEKEEPER_RULES = {
    "min_sample_days": 30,          # 最少样本天数
    "min_return_improvement": 0.02, # 收益至少提升 2% (防止过度折腾)
    "max_drawdown_tolerance": 0.05  # 允许的最大回撤增加容忍度 (5%)
}

def get_db_active_param(param_name):
    """获取数据库中当前激活的参数"""
    conn = get_conn()
    row = conn.execute(
        "SELECT param_value FROM strategy_params WHERE param_name = ? AND status = 'active'", 
        (param_name,)
    ).fetchone()
    conn.close()
    return float(row['param_value']) if row else None

def promote_to_active(param_name, new_value, score, sample_size, drawdown):
    """将 candidate 提升为 active"""
    conn = get_conn()
    try:
        # 1. 将旧 active 变为 archived
        conn.execute("UPDATE strategy_params SET status='archived' WHERE param_name = ? AND status = 'active'", (param_name,))
        
        # 2. 将新参数写入 active
        conn.execute('''
            INSERT INTO strategy_params (param_name, param_value, status, validation_score, sample_size, max_drawdown)
            VALUES (?, ?, 'active', ?, ?, ?)
        ''', (param_name, new_value, score, sample_size, drawdown))
        
        conn.commit()
        print(f"   🚀 门禁通过：参数 {param_name} 已从 {get_db_active_param(param_name) or 'None'} 升级为 {new_value}")
    except Exception as e:
        conn.rollback()
        print(f"   ❌ 数据库更新失败: {e}")
    finally:
        conn.close()

def reject_candidate(param_name, value):
    conn = get_conn()
    conn.execute("DELETE FROM strategy_params WHERE param_name = ? AND status = 'candidate'", (param_name,))
    conn.commit()
    conn.close()

def simulate_with_drawdown(history, atr_multiplier):
    """
    带最大回撤计算的 A 股真实规则回测
    """
    if not history: return None
    
    initial_capital = 10000
    cash = initial_capital
    position = 0
    holding_price = 0
    buy_date = -1
    
    equity_curve = [initial_capital]
    
    daily_atr_pct = 0.02 
    stop_loss_pct = atr_multiplier * daily_atr_pct

    for i, day in enumerate(history):
        current_price = day['close']
        stop_loss_price = holding_price * (1 - stop_loss_pct)
        
        # 1. 止损检查
        if position > 0 and (day['low'] <= stop_loss_price):
            if buy_date != day['date']: # T+1 check
                realized_price = stop_loss_price * (1 - TRADING_FEES['slippage_rate'])
                revenue = position * realized_price
                fees = revenue * (TRADING_FEES['commission_rate'] + TRADING_FEES['stamp_tax_rate'])
                cash += (revenue - fees)
                position = 0
                holding_price = 0
                continue

        # 2. 卖出逻辑 (T+1 后)
        if position > 0 and buy_date != day['date']:
            realized_price = current_price * (1 - TRADING_FEES['slippage_rate'])
            revenue = position * realized_price
            fees = revenue * (TRADING_FEES['commission_rate'] + TRADING_FEES['stamp_tax_rate'])
            cash += (revenue - fees)
            position = 0
            holding_price = 0

        # 3. 买入逻辑
        if position == 0 and cash > 0:
            if not day.get('is_limit_up', False):
                buy_price = day['open'] * (1 + TRADING_FEES['slippage_rate'])
                qty = int((cash * 0.99) / buy_price / 100) * 100
                if qty >= 100:
                    cost = qty * buy_price
                    fees = cost * TRADING_FEES['commission_rate']
                    if cash >= (cost + fees):
                        cash -= (cost + fees)
                        position = qty
                        holding_price = buy_price
                        buy_date = day['date']
        
        # 记录权益曲线
        current_equity = cash + (position * current_price if position > 0 else 0)
        equity_curve.append(current_equity)

    # 计算指标
    final_equity = equity_curve[-1]
    total_return = (final_equity - initial_capital) / initial_capital
    
    # 计算最大回撤
    peak = initial_capital
    max_dd = 0
    for val in equity_curve:
        if val > peak: peak = val
        dd = (peak - val) / peak
        if dd > max_dd: max_dd = dd

    return {
        "atr_multiplier": atr_multiplier,
        "final_equity": final_equity,
        "total_return": total_return,
        "max_drawdown": max_dd
    }

def run_evolution():
    print("🧬 启动进化引擎 v4.0 (Gatekeeper Enabled)...")
    
    history = get_history_for_evolution()
    
    # 获取样本天数 (简化处理：假设每条记录代表一天)
    sample_size = len(history)
    print(f"   样本数: {sample_size} 天")

    if sample_size < GATEKEEPER_RULES['min_sample_days']:
        print(f"   ⚠️ 样本不足 ({sample_size} < {GATEKEEPER_RULES['min_sample_days']} 天)，跳过进化。")
        return

    # 1. 确定 Champion (当前 active)
    champion_mult = get_db_active_param("atr_multiplier")
    if not champion_mult:
        champion_mult = 6.0 # 默认
    print(f"   🏆 Champion (当前 Active): ATR={champion_mult}")
    
    # 2. 跑 Champion 基准
    champ_perf = simulate_with_drawdown(history, champion_mult)
    print(f"   📊 Champion 表现: 收益 {champ_perf['total_return']:+.2%} | 回撤 {champ_perf['max_drawdown']:.2%}")

    # 3. 生成 Challengers
    candidates = [x * 0.5 for x in range(4, 17)] # 2.0, 2.5 ... 8.0
    best_challenger = None
    
    print("   ⚔️ 开始挑战者回测...")
    for c in candidates:
        perf = simulate_with_drawdown(history, c)
        print(f"   测试 ATR={c}: 收益 {perf['total_return']:+.2%} | 回撤 {perf['max_drawdown']:.2%}")
        
        if best_challenger is None or perf['final_equity'] > best_challenger['final_equity']:
            best_challenger = perf

    # 4. Gatekeeper 审核
    print("\n👮 启动 Gatekeeper 门禁审核...")
    
    # 条件 1: 收益提升
    ret_improvement = best_challenger['total_return'] - champ_perf['total_return']
    is_profit_better = ret_improvement >= GATEKEEPER_RULES['min_return_improvement']
    
    # 条件 2: 回撤控制 (新回撤 <= 旧回撤 + 容忍度)
    is_risk_ok = best_challenger['max_drawdown'] <= (champ_perf['max_drawdown'] + GATEKEEPER_RULES['max_drawdown_tolerance'])
    
    if is_profit_better and is_risk_ok:
        print(f"   ✅ 挑战者胜出！(收益提升 {ret_improvement:.2%}，回撤 {best_challenger['max_drawdown']:.2%})")
        promote_to_active("atr_multiplier", best_challenger['atr_multiplier'], best_challenger['total_return'], sample_size, best_challenger['max_drawdown'])
    else:
        reason = []
        if not is_profit_better: reason.append(f"收益提升不足 ({ret_improvement:.2%})")
        if not is_risk_ok: reason.append(f"回撤过大 ({best_challenger['max_drawdown']:.2%})")
        print(f"   ❌ 门禁拦截: {', '.join(reason)}")
        reject_candidate("atr_multiplier", best_challenger['atr_multiplier'])

if __name__ == "__main__":
    run_evolution()
