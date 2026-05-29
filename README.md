# 🇨🇳 A-Stock Quantitative Trading System (A 股量化系统)

> **⚠️ Project Status: v0.5-beta**  
> This system is currently in the **Data Pipeline & Paper Trading (Virtual Observation)** phase.  
> **Strategy Validity: NOT VALIDATED** (See Audit Report below).

## 📖 Project Overview

A quantitative trading framework designed for the A-share market, integrating **macro-probability signals from Polymarket** with **micro-market data (Capital Flow, Northbound, Price/Volume)**.

The system acts as an **"Automated Trading Advisor"** that performs:
1.  **Macro-Micro Mapping**: Translating global prediction market probabilities (e.g., rate cuts, geopolitics) into A-share sector opportunities.
2.  **4D Scoring Card**: Quantitative scoring of market sentiment, capital flow, and technical resonance.
3.  **Adaptive Risk Control**: Dynamic stop-loss logic based on intraday volatility (Daily Range Proxy), not fixed percentages.
4.  **Self-Auditing**: Point-in-time data isolation to prevent look-ahead bias (Future Leakage).

---

## 🧠 Core Working Principles

### 1. The "4D" Market Observation Model
The system calculates a daily "Market Observation Score" (0-100) to gauge overall market health:
*   **Capital Flow (40 pts)**: Total market turnover + Northbound fund flows (HK-Shanghai/Shenzhen).
*   **Sentiment (30 pts)**: Index momentum (Shanghai/Shenzhen/ChiNext) + Limit-up/down ratios.
*   **Macro (20 pts)**: Systemic risk derived from Polymarket events (e.g., Fed rate cuts, trade wars).
*   **Technical (10 pts)**: Technical resonance across major indices.

### 2. Recommendation & Review Engine (v0.6)
*   **Morning (08:00)**: Scans T-1 sector capital flows (East Money API). Identifies Top 3 sectors -> Top 3 stocks per sector. Writes to DB as `PENDING`.
*   **Afternoon (15:30)**: Reviews `PENDING` stocks against actual T-day closing prices. Calculates theoretical returns, max drawdown, and excess returns vs. benchmark. Updates status to `REVIEWED`.

### 3. Paper Trading Loop
The system maintains a virtual portfolio (`Paper Trading`) that:
*   Tracks entry prices (Open + 0.2% slippage).
*   Monitors daily performance against the **CSI 300** and **Equal-Weight** benchmarks.
*   Triggers a "Kill Switch" if drawdowns exceed safety thresholds.

### 4. Strict Anti-Look-Ahead Bias
*   **Point-in-Time (PIT)**: All features are strictly timestamped. Predictions for Day T can *only* use data available before 08:00 on Day T.
*   **Locked Predictions**: Once a prediction is generated, it is written to a snapshot table and locked. Reality (closing prices) is only applied *after* market close.
*   **RAW Prices**: Backtests use un-adjusted (RAW) prices to avoid distortions from forward-adjustment factors.

---

## 📂 Directory Structure

```text
.
├── SKILL.md                   # 🔑 Core Agent Instruction (Logic, APIs, Constraints)
├── README.md                  # 📖 This file: Project overview and docs
├── references/                # 📚 Detailed Documentation & Audits
│   ├── v05-beta-v3-evaluation.md   # Complete backtest evaluation & failure analysis
│   ├── evolution-engine.md         # Champion/Challenger mechanism docs
│   ├── data-sources-api.md         # API details (East Money, Sina, Tencent)
│   ├── cron-compliance-framework.md# Reporting standards
│   └── ...
└── scripts/                   # 🛠️ Core Scripts
    └── quant_v2/              # v0.6 Modules (Recommendation/Review Engines)
```

---

## 📊 Current System Status (As of 2026-05-30)

### ✅ Completed & Working
*   **Data Pipeline**: Stable connection to East Money & Sina APIs via proxy architecture.
*   **Scoring Engine**: 4D scoring card and capital flow analysis running daily.
*   **Recommendation Logic**: Sector -> Stock mapping logic implemented (v0.6).
*   **Compliance**: System strictly reports as "v0.5-beta Paper Trading", no live signals.

### ❌ Known Issues / To-Do
*   **Strategy Invalidation**: Momentum strategy (+3.68%) significantly underperformed Equal-Weight (+23.14%). 62% of random portfolios beat the strategy.
*   **Data Universe**: Currently testing on only 78 stocks (Deep Market Small Caps). Needs expansion to full market (5000+).
*   **Execution Simulation**: Needs minute-level data for precise limit-up/down handling.

---

## 🚫 Disclaimer

**This is a monitoring and research tool, NOT a trading signal generator.**  
All outputs are for **Paper Trading / Data Chain Verification** purposes only. Do not execute real trades based on these reports.

---

## 🛠️ Deployment (For Developers)

1.  **Requirements**: Python 3.11+, SQLite.
2.  **Environment**: Requires HTTP proxy for accessing Chinese financial APIs (East Money, etc.) if outside China.
3.  **Scripts**:
    *   `scripts/a_stock_data.py`: Data collector.
    *   `scripts/quant_v2/main.py`: Main scoring engine.
4.  **Configuration**: Edit `config.py` or set env vars (`EASTMONEY_PROXY`).

---

*Developed by XiaoMing (skyeses1) & Hermes Agent*
