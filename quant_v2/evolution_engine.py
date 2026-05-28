"""
进化引擎 v2.1 (Evolution Engine)
通过回溯历史数据自动寻找最优参数，并更新 params.json 配置表。
不再修改源代码 (Audit Fix #4)。
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "mock_history.json")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "params.json")

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

def simulate_strategy(history, atr_multiplier):
    """
    使用给定的 atr_multiplier 在历史数据上模拟交易。
    """
    equity = 10000
    wins = 0
    losses = 0
    daily_atr_pct = 0.02
    
    for day in history:
        stop_loss_threshold = -(atr_multiplier * daily_atr_pct)
        intraday_low = day.get('intraday_min', day.get('final_pnl'))
        final_pnl = day.get('final_pnl')
        
        if intraday_low <= stop_loss_threshold:
            realized_pnl = stop_loss_threshold
            losses += 1
        else:
            realized_pnl = final_pnl
            if realized_pnl > 0:
                wins += 1
            else:
                losses += 1
                
        equity *= (1 + realized_pnl)

    win_rate = wins / len(history) if len(history) > 0 else 0
    return {
        "atr_multiplier": atr_multiplier,
        "final_equity": equity,
        "win_rate": win_rate,
        "total_return": (equity - 10000) / 10000
    }

def update_config(new_mult):
    """
    更新 params.json 中的配置，而不是修改源代码。
    """
    if not os.path.exists(CONFIG_PATH):
        print("❌ Config file not found.")
        return

    config = load_config()
    old_mult = config.get("risk_engine", {}).get("atr_multiplier")
    
    config["risk_engine"]["atr_multiplier"] = new_mult
    
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print(f"✅ 已成功将 params.json 中的 atr_multiplier 从 {old_mult} 更新为 {new_mult}")
    print("🔄 下次运行系统时将自动加载新配置。")

def run_evolution():
    print("🧬 启动进化引擎 v2.1 (Config-Driven Evolution)...")
    history = load_history()
    if not history:
        print("❌ 无历史数据，无法进化。")
        return
    
    config = load_config()
    if not config:
        print("❌ 无配置文件，无法进化。")
        return

    current_mult = config["risk_engine"]["atr_multiplier"]
    candidates = config.get("evolution_settings", {}).get("test_candidates", [1.0, 2.0, 3.0, 4.0, 5.0])
    
    print(f"   当前参数: {current_mult} | 样本数: {len(history)}")
    
    results = []
    for c in candidates:
        res = simulate_strategy(history, c)
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
        # Check against current return to ensure improvement
        current_res = next((r for r in results if abs(r['atr_multiplier'] - current_mult) < 0.1), None)
        
        if current_res and best_result['final_equity'] > current_res['final_equity']:
            print(f"\n📝 收益确认提升，正在更新配置表 (params.json)...")
            update_config(best_result['atr_multiplier'])
        else:
            print(f"\n⚠️ 收益未提升，保持现有参数。")
    else:
        print("✅ 策略参数已处于最优状态，无需更新。")

if __name__ == "__main__":
    run_evolution()
