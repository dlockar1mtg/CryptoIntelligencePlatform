Crypto Intelligence Platform v4.2.3 — Research Maturity Release

Safe overlay for v4.2.2. Adds Module 20:
- Chronological model comparison: Random Forest, Extra Trees, Gradient Boosting, HistGradientBoosting
- Out-of-sample permutation explainability for the selected model
- Feature redundancy detection and preferred-feature selection
- Evidence aging and automatic shadow/watchlist decay
- Monthly BTC/cash shadow portfolio using only promoted, nonredundant features
- Promotion gate versus Bitcoin buy-and-hold

This release does not change Module 13 or live allocations.

Install into C:\Users\DevonLockard\Crypto and run:
  install_v4_2_3_windows.bat
  python run_module20.py
  python inspect_module20.py
  python export_module20.py

No data, .env, logs, or DuckDB files are included.
