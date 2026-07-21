Crypto Intelligence Platform v5.1
Intelligence Expansion Release
================================

v5.1 is a safe overlay for an installed v5.0 platform.

Module 22 adds:

- Expanded derived feature matrix
- Five-classifier model comparison
- Automatic best-model selection
- Ensemble market-regime engine
- Dynamic six-asset plus cash allocation
- Rolling walk-forward validation
- Direct Bitcoin benchmark comparison

Model Candidates
----------------

- Logistic Regression
- Random Forest
- Extra Trees
- Gradient Boosting
- HistGradientBoosting

Expanded Features
-----------------

The release derives market, macro, liquidity, and cross-asset features from
the existing warehouse, including:

- BTC momentum over multiple windows
- Distance from 50-day and 200-day averages
- Realized volatility
- Equal-weight core returns
- Cross-asset dispersion
- Altcoin relative strength versus Bitcoin
- Breadth changes
- Stablecoin-growth acceleration
- Fear & Greed change
- VIX, credit-spread, and dollar changes
- Liquidity, risk-off, and trend composites

Portfolio
---------

The shadow portfolio allocates dynamically across:

- Bitcoin
- Ethereum
- Solana
- Chainlink
- XRP
- Avalanche
- Cash

Allocation considers momentum, relative strength, volatility, correlation,
ensemble regime, and risk-off conditions.

Production Safety
-----------------

v5.1 remains shadow-only. It does not change Module 13 recommendations or
live allocations.

Installation
------------

Extract directly into:

C:\Users\DevonLockard\Crypto

Run:

install_v5_1_windows.bat

Then:

python run_module22.py
python inspect_module22.py
python export_module22.py
