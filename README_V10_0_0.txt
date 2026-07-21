Crypto Intelligence Platform v10.0.0
Predictive Intelligence Engine
================================

This release combines:

1. v9.2.1 Stabilization Hotfix
2. Module 38 Predictive Intelligence Engine

v9.2.1 corrections
------------------

- Eliminates divide-by-zero and invalid-value warnings in portfolio entropy.
- Computes entropy using only strictly positive risky-sleeve weights.
- Suppresses misleading information ratios when active share is below 5%.
- Uses annualized active return divided by annualized tracking error.

Module 38 capabilities
----------------------

Multi-horizon forecasts:

- 7 days
- 30 days
- 90 days
- 180 days
- 365 days

Assets:

- Bitcoin
- Ethereum
- Solana
- Chainlink
- XRP
- Avalanche

Models:

- Gradient Boosting Regressor
- Random Forest Regressor
- Bayesian Ridge

The ensemble weights each model inversely to validation MAE.

Forecast outputs
----------------

- Predicted return and price
- 10th and 90th percentile uncertainty bounds
- Probability of a positive return
- Forecast confidence
- Model agreement
- Validation MAE and RMSE
- Directional accuracy
- Feature-driver attribution
- Current-to-next regime transition probabilities
- Expected regime duration
- Portfolio-level forecast
- Forecast risk status
- Predictive recommendation

Optimizer feedback
------------------

Module 38 blends predictive annualized returns with Module 37 expected returns:

- 35% predictive forecast
- 65% existing institutional optimizer estimate

The blended estimates are stored in:

latest_m38_predictive_expected_returns

This release does not automatically overwrite Module 37 allocations. It creates
a controlled forecast-feedback layer for the next optimizer run or v10.1.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v10_0_0_windows.bat
3. Optional: python run_module37.py
4. Run python run_module38.py
5. Run python inspect_module38.py
6. Run python export_module38.py

Modules 25-37 and all prior data remain unchanged.
