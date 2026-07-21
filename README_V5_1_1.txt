Crypto Intelligence Platform v5.1.1 — Backtest Validation & Audit

Module 23 independently audits the latest successful Module 22 run.

Key correction:
Module 22 stores a running partial portfolio return on every asset row and its
summary uses MAX(portfolio_period_return_pct). That can select an incomplete
partial sum. Module 23 instead sums all asset contributions and subtracts the
period transaction cost exactly once, then reconciles the result to canonical
prices.

Additional audits:
- Weight, date, duplicate, and price reconciliation checks
- Bitcoin, equal-weight, BTC/cash, and inverse-volatility benchmarks
- Performance attribution
- Drawdown-label AUC and possible inversion
- 10,000-simulation bootstrap confidence interval
- Automatic promotion revocation when critical findings exist

Statuses:
AUDIT_VALIDATED_CANDIDATE
RESEARCH_ONLY
REVOKED_PENDING_FIX

Install into C:\Users\DevonLockard\Crypto and run:
install_v5_1_1_windows.bat
python run_module23.py
python inspect_module23.py
python export_module23.py

This overlay contains no data, .env, logs, or DuckDB files.
