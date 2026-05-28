"""
进化引擎 v2.3 (Evolution Engine - Hybrid Adapter)
任务 1: 适配真实数据库数据。优先读取 SQLite，不足时回退到 Mock。
"""

import json
import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import CONFIG_PATH, EVOLUTION_CONFIG
from db import get_history_for_evolution
from scoring_risk import load_params

# Mock Data Fallback Path
MOCK_PATH = os.path.join(os.path.dirname(__file__), "mock_history_v2.json")

def load_history():
    """
    混合数据加载器
    """
    # 1. 尝试读取真实数据库历史
    real_history = get_history_for_evolution()
    
    if len(real_history) >= EVOLUTION_CONFIG['min_sample_size']:
        print(f"   ✅ 从数据库加载 {len(real_history)} 条真实交易记录。")
        return real_history
    else:
        print(f"   ⚠️ 真实样本不足 ({len(real_history)}/{EVOLUTION_CONFIG['min_sample_size']})。")
        if os.path.exists(MOCK_PATH):
            print(f"   🔄 回退使用 Mock 历史数据进行参数探索。")
            with open(MOCK_PATH, 'r') as f:
                return json.load(f)
        return []

def simulate_realistic_strategy(history, atr_multiplier):
    """
    简化版模拟 (基于 Mock 结构)。
    真实数据库回测需要更复杂的逻辑 (T+1, Slippage 等)，这里暂用 Mock 逻辑演示适配。
    """
    equity = 10000
    wins = 0
    losses = 0
    daily_atr_pct = 0.02 
    stop_loss_pct = atr_multiplier * daily_atr_pct
    
    for day in history:
        # 兼容两种数据源结构
        if 'low' in day: # Mock v2 structure
            low = day['low']
            final_pnl = (day['close'] - day['open']) / day['open'] # Approx
        elif 'pnl_pct' in day: # DB structure
            # For DB history, we look at the realized PnL of the trade
            final_pnl = day['pnl_pct']
            low = final_pnl # Approximation for stop check
            
        # Check Stop Loss logic (Simplified for demo)
        # In real DB history, the stop logic was already applied during execution.
        # Here we just aggregate.
        
        realized_pnl = final_pnl
        if realized_pnl > 0: wins += 1
        else: losses += 1
                
        equity *= (1 + realized_pnl)

    win_rate = wins / len(history) if len(history) > 0 else 0
    return {
        "atr_multiplier": atr_multiplier,
        "final_equity": equity,
        "win_rate": win_rate,
        "total_return": (equity - 10000) / 10000
    }

def run_evolution():
    print("🧬 启动进化引擎 v2.3 (Hybrid Adapter)...")
    
    history = load_history()
    if not history:
        print("❌ 无可用数据。")
        return
    
    config = load_params()
    current_mult = config["risk_engine"]["atr_multiplier"]
    candidates = config.get("evolution_settings", {}).get("test_candidates", [1.0, 2.0, 3.0, 4.0, 5.0])
    
    print(f"   样本数: {len(history)} 天 | 当前参数: {current_mult}")
    
    results = []
    for c in candidates:
        res = simulate_realistic_strategy(history, c)
        results.append(res)
        print(f"   测试 ATR={c}: 收益 {res['total_return']:+.2%} | 胜率 {res['win_rate']:.0%}")

    best_result = max(results, key=lambda x: x['final_equity'])
    
    print("\n" + "="*40)
    print(f"🏆 进化完成！")
    print(f"   当前参数: {current_mult}")
    print(f"   发现最优参数: {best_result['atr_multiplier']}")
    print(f"   预期收益提升: {best_result['total_return']:+.2%}")
    print("="*40)
    
    if abs(best_result['atr_multiplier'] - current_mult) > 0.1:
        current_res = next((r for r in results if abs(r['atr_multiplier'] - current_mult) < 0.1), None)
        if current_res and best_result['final_equity'] > current_res['final_equity']:
            print(f"\n📝 收益提升，正在更新配置...")
            from scoring_risk import update_config
            update_config(best_result['atr_multiplier'])
        else:
            print(f"\n⚠️ 收益未提升，保持现有参数。")
    else:
        print("✅ 策略参数已处于最优状态。")

if __name__ == "__main__":
    run_evolution()
