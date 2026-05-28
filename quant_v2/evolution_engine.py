"""
进化引擎 (Evolution Engine)
通过回溯历史数据 (Backtest) 自动寻找最优策略参数，并自我修改代码。
"""

import json
import os
import re
import subprocess

DATA_PATH = os.path.join(os.path.dirname(__file__), "mock_history.json")

def load_history():
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, 'r') as f:
        return json.load(f)

def simulate_strategy(history, atr_multiplier):
    """
    使用给定的 atr_multiplier 在历史数据上模拟交易。
    """
    equity = 10000
    wins = 0
    losses = 0
    
    # 假设每日 ATR 约为 2%
    daily_atr_pct = 0.02 
    
    for day in history:
        # 计算动态止损线 (例如 multiplier=3.0 -> 止损 6%)
        stop_loss_threshold = -(atr_multiplier * daily_atr_pct)
        
        # 模拟判断
        intraday_low = day.get('intraday_min', day.get('final_pnl'))
        final_pnl = day.get('final_pnl')
        
        realized_pnl = 0
        
        if intraday_low <= stop_loss_threshold:
            # 触发止损
            realized_pnl = stop_loss_threshold # 假设在止损线卖出
            losses += 1
        else:
            # 持有到收盘
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

def update_source_code(file_path, old_mult, new_mult):
    """
    自动修改 scoring_risk.py 中的 multiplier 参数
    """
    if not file_path or not os.path.exists(file_path):
        print("❌ 找不到源文件，无法自动进化。")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换逻辑：查找 multiplier=OLD 并替换为 multiplier=NEW
    old_str = f"multiplier={old_mult}"
    new_str = f"multiplier={new_mult}"
    
    if old_str in content:
        new_content = content.replace(old_str, new_str)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ 已成功将 scoring_risk.py 中的 multiplier 从 {old_mult} 更新为 {new_mult}")
        print("🔄 下次运行系统时将自动应用新参数。")
        
        # Git Commit the change automatically
        try:
            repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            subprocess.run(["git", "-C", repo_dir, "add", file_path], check=True)
            subprocess.run(["git", "-C", repo_dir, "commit", "-m", f"🧬 Auto-evolution: update ATR multiplier to {new_mult}"], check=True)
            print("🚀 已自动提交代码变更到 Git。")
        except Exception as e:
            print(f"⚠️ Git 提交失败: {e}")
    else:
        print(f"⚠️ 未在代码中找到 multiplier={old_mult}，跳过自动更新。")

def run_evolution():
    print("🧬 启动进化引擎 (Evolution Engine)...")
    history = load_history()
    if not history:
        print("❌ 无历史数据，无法进化。")
        return
    
    print(f"   加载历史数据: {len(history)} 天")
    
    candidates = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    results = []
    
    for c in candidates:
        res = simulate_strategy(history, c)
        results.append(res)
        print(f"   测试参数 ATR Multiplier={c}: "
              f"收益 {res['total_return']:+.2%} | "
              f"胜率 {res['win_rate']:.0%}")

    # 寻找最优参数
    best_result = max(results, key=lambda x: x['final_equity'])
    
    # 读取当前代码中的参数
    current_mult = 2.0 
    risk_file = os.path.join(os.path.dirname(__file__), "scoring_risk.py")
    if os.path.exists(risk_file):
        with open(risk_file, 'r') as f:
            content = f.read()
            match = re.search(r"multiplier=([0-9.]+)", content)
            if match:
                current_mult = float(match.group(1))

    print("\n" + "="*40)
    print(f"🏆 进化完成！")
    print(f"   当前参数: ATR Multiplier = {current_mult}")
    print(f"   发现最优参数: ATR Multiplier = {best_result['atr_multiplier']}")
    print(f"   预期收益提升: {best_result['total_return']:+.2%}")
    print("="*40)
    
    # 如果最优参数与当前不同，且收益更好，则执行更新
    # 这里只要不一样就更新，因为我们假设进化是为了寻找更优解
    if abs(best_result['atr_multiplier'] - current_mult) > 0.01:
        # 进一步检查：新参数的收益是否真的比当前参数好？
        # 找到当前参数的结果
        current_res = next((r for r in results if abs(r['atr_multiplier'] - current_mult) < 0.01), None)
        
        if current_res and best_result['final_equity'] > current_res['final_equity']:
            print(f"\n📝 收益提升确认，正在更新源代码...")
            update_source_code(risk_file, current_mult, best_result['atr_multiplier'])
        else:
            print(f"\n⚠️ 虽然参数不同，但收益未提升 (当前 {current_res['total_return']:+.2%} vs 最优 {best_result['total_return']:+.2%})，不更新代码。")
    else:
        print("✅ 策略参数已处于最优状态，无需更新。")

if __name__ == "__main__":
    run_evolution()
