# Point-in-Time (PIT) Replay System Architecture (v5.0)

## Core Principles
- **No Look-Ahead Bias**: All features at `T` must strictly use data where `source_timestamp` <= `T 08:00:00`.
- **Immutable Snapshots**: `prediction_snapshots` are written in `locked` state before any reality data is read.
- **Config-Driven**: No hardcoded thresholds. All parameters (cutoff, costs, gatekeeper rules) must reside in `*_configs` tables.

## Key Database Tables
| Table | Purpose |
| :--- | :--- |
| `replay_configs` | Stores cutoff times, universe, and benchmark settings. |
| `feature_snapshots` | Immutable record of the feature set used for each prediction. Includes `leakage_check_status`. |
| `prediction_snapshots` | The system's prediction at `T 08:00`, including `market_direction`, `confidence`, and `suggested_position`. |
| `evaluation_results` | Post-market reality check comparing prediction vs actual close. |
| `leakage_audit_logs` | Audit trail for any attempt to use future data (一票否决). |

## Evolution Workflow
1. **Backtest**: `historical_replay_engine.py` runs walk-forward simulation.
2. **Gatekeeper**: `gatekeeper_configs` defines promotion thresholds (min sample size, min excess return).
3. **Candidate**: Successful runs generate a `candidate` in `strategy_params` table.
4. **Promotion**: Only after passing Gatekeeper is a parameter promoted to `active`.
5. **History**: All changes are logged in `strategy_version_history` for rollback capability.

## Development Standards
- **Status Reporting**: Explicitly label features as **Prototype**, **Alpha**, **Beta**, or **Production**.
- **Data Verification**: Never claim a feature is "Done" if it relies on Mock data or lacks the leakage audit.
- **Safety**: Evolution Engine must NEVER modify Python source code. It only writes to the DB.