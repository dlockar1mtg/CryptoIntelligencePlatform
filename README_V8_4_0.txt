Crypto Intelligence Platform v8.4.0
Institutional Portfolio Execution Engine
========================================

Module 34 converts Module 33 target allocations into realistic trades.

Execution controls
------------------

- Rebalance frequencies: daily, weekly, and biweekly
- Rebalance bands: 2.5%, 5%, and 10%
- Minimum trade sizes: 1%, 2.5%, and 5%
- Exposure smoothing alpha: 0.10, 0.20, and 0.35
- Annual turnover budgets: 100%, 150%, and 250%
- Transaction-cost testing: 10, 25, and 50 basis points

The optimizer evaluates 243 institutional execution policies.

A trade occurs only when:

1. The rebalance calendar permits a trade.
2. The target leaves its tolerance band.
3. The proposed trade exceeds the minimum trade size.
4. The annual turnover budget has capacity.

Drift repair
------------

Module 34 replaces PSI as the primary drift measure with:

- Jensen-Shannon distance across the full regime probability vector
- Wasserstein distance for top probability
- Wasserstein distance for entropy
- Component-model disagreement
- Execution tracking error

Advancement gate
----------------

READY_FOR_PORTFOLIO_INTELLIGENCE requires:

- Sharpe at least as high as BTC buy-and-hold
- Maximum drawdown better than BTC
- Annualized turnover no more than 250%
- At least two of three cost scenarios passing
- Current execution drift not CRITICAL

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v8_4_0_windows.bat
3. Run python run_module34.py
4. Run python inspect_module34.py
5. Run python export_module34.py

Modules 25-33 remain unchanged.
