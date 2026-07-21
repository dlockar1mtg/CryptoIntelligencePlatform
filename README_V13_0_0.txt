Crypto Intelligence Platform v13.0.0
Economic Value & Strategy Validation Engine
============================================

Module 44 answers: Did following the platform's decisions add investment value?

It evaluates Module 42 and Module 43 decisions across 7-, 30-, 90-, and 180-day realized horizons.

Benchmarks:
- Module 42 action strategy
- Buy and hold
- Cash
- Equal-weight crypto

Metrics:
- Realized and strategy return
- Excess return versus cash and buy-and-hold
- Cumulative and annualized return
- Volatility, Sharpe ratio, and maximum drawdown
- Directional accuracy
- Positive economic-value rate

It also evaluates:
- Which actions created value
- Whether WAIT timing improved entry prices
- Which horizon created the most value
- Whether the target-weighted portfolio beat equal-weight crypto and cash

Expected first run:
- 24 decision rows
- 0 matured decisions
- 24 pending decisions
- ACCUMULATING_EVIDENCE
- NOT_YET_MEASURABLE
- WAIT_FOR_MATURED_OUTCOMES

Installation:
1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v13_0_0_windows.bat
3. Run python run_module44.py
4. Run python inspect_module44.py
5. Run python export_module44.py
