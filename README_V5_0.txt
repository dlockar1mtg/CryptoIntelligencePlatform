Crypto Intelligence Platform v5.0
Investment Decision Engine
=================================

v5.0 is a safe overlay for an installed v4.2.3 platform.

Module 21 converts governed research into shadow-only decisions:

- Five-state market-regime probabilities
- Positive-return probability
- Greater-than-20-percent drawdown probability
- Liquidity-expansion probability
- Model-quality reporting
- Historical VaR and CVaR
- Volatility and drawdown risk scoring
- Confidence-based BTC/cash allocation
- Plain-English decision rationale
- Monthly decision-shadow portfolio

Governance Boundary
-------------------

Only features with the configured registry status may affect position sizing.
The default is:

PROMOTED_SHADOW

Watchlist features remain available for research context but cannot move
capital.

Probability Quality
-------------------

Every classifier reports:

- Accuracy
- ROC AUC
- Brier score
- Training and testing rows
- ACCEPTABLE or WEAK quality status

Weak probabilities are automatically dampened in allocation sizing.

Decision Stances
----------------

- STRONG_BUY
- BUY
- HOLD
- REDUCE
- DEFENSIVE

The decision engine produces a target BTC weight and target cash weight.
It does not alter Module 13.

Installation
------------

Extract directly into:

C:\Users\DevonLockard\Crypto

Allow the crypto_platform folder to merge.

Run:

install_v5_0_windows.bat

Then:

python run_module21.py
python inspect_module21.py
python export_module21.py

The overlay contains no data folder, .env, logs, or DuckDB files.
