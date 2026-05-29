# Evolution Engine v4.0 — Gatekeeper & Self-Evolution

## ⛔ ABSOLUTE RULES
1. **NEVER modify source code** — no string-replace in `.py` files. Evolution ONLY writes to `strategy_params` DB table.
2. **NEVER promote without Gatekeeper** — Challenger must beat Champion on BOTH return improvement (≥2%) AND drawdown tolerance (≤+5%).
3. **NEVER evolve without real data** — minimum 30 trading days sample. Fallback to mock only for initial demo/testing.

## 🧬 Evolution Pipeline
```
DB Paper Trading Records → Realistic Backtest (T+1, fees, slippage)
  → Generate Candidates → Gatekeeper Audit → Promote to Active
```

## 🛡️ Gatekeeper Logic
| Component | Role |
|-----------|------|
| **Champion** | Current `active` param in `strategy_params` table |
| **Challenger** | Tested params (e.g., ATR multiplier 2.0-8.0 range) |
| **Pass Criteria** | `return_improvement >= 0.02` AND `max_drawdown <= champ_dd + 0.05` |
| **Action** | Archive old active → Insert new active. Zero source code changes |

## 🚨 Kill Switch (v2.3+)
Integrated in `main.py`:
- Scans `recommendations` table for pending stocks
- If ≥3 stocks have `pnl_pct < -0.05`, force position to 10%
- Report output: "🚨 触发失效报警: 建议仓位强制调整为 10% (防守模式)"

## 📊 Audit Checklist (2026-05-28)
| Level | Feature | Status |
|-------|---------|--------|
| P0 | Parameter governance (DB-driven, no source modification) | ✅ |
| P1 | Realistic backtest (T+1, stamp tax 0.1%, commission 0.025%, slippage 0.1%) | ✅ |
| P2 | Kill Switch (consecutive loss alarm) | ✅ |
| P3 | Candidate generation (writes `candidate` status only) | ✅ |
| P4 | Gatekeeper (Champion vs Challenger auto-promotion) | ✅ |
| P5 | Shadow Mode | ❌ Skipped (replaced by full-history backtest) |

## 📂 Key Files
- `quant_v2/evolution_engine.py` — v4.0 with Gatekeeper
- `quant_v2/param_loader.py` — DB-driven param loading (hot-reload)
- `quant_v2/db.py` — `strategy_params` table schema
- `quant_v2/scoring_risk.py` — weights loaded from DB params
- `quant_v2/main.py` — Kill Switch integration
