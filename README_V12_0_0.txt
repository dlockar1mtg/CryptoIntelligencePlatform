Crypto Intelligence Platform v12.0.0
Investment Decision & Long-Range Projection Engine
===================================================

Module 42 answers:

- Which asset?
- What is the best action?
- What percentage of the total portfolio should it represent now?
- What is the suggested entry or reduction timeline?
- What are bear, median, and bull projected prices?
- What are the projections at:
  - 7 days
  - 30 days
  - Every 3 months from month 3 through month 48?

Outputs
-------

1. latest_m42_asset_recommendations.csv

One row per asset with:

- Current price
- Investment score
- Best action
- Current weight
- Best current portfolio percentage
- Required weight change
- Suggested timeline
- Entry strategy
- Conviction
- Confidence
- Reliability
- Short-, medium-, and long-term signals
- Reason and risk warning
- Evidence status

Actions
-------

- STRONG_BUY
- BUY
- SCALE_IN
- HOLD
- WAIT
- REDUCE
- AVOID

2. latest_m42_price_projections.csv

One row per asset and horizon.

There are 18 horizons per asset:

- 7D
- 30D
- M03
- M06
- M09
- M12
- M15
- M18
- M21
- M24
- M27
- M30
- M33
- M36
- M39
- M42
- M45
- M48

Each row includes:

- Projection date
- Current price
- Bear price
- Median price
- Bull price
- Bear/median/bull return
- Annualized median return
- Scenario width
- Projection confidence
- Projection method
- Evidence status

3. latest_m42_projection_matrix.csv

A wide, user-friendly table with all bear, median, and bull prices by asset
and horizon.

4. latest_m42_portfolio_plan.csv

A staged execution plan containing:

- Target weight
- Current weight
- Trade weight
- Buy/sell/hold action
- Execution stage
- Execution window
- Tranche percentage
- Entry trigger

Projection methodology
----------------------

7D and 30D:
- Module 39 calibrated forecast
- Module 41 adaptive feedback when available
- Conformal bear/bull intervals

3M and 6M:
- Uses calibrated Module 38/39 forecasts where available
- Blends Module 41 adaptive expected returns

9M through 48M:
- Scenario model, not a precise point forecast
- Blends predictive forecasts, historical return, a conservative prior,
  regime alignment, and historical volatility
- Bear and bull paths expand with the square root of time
- Confidence declines as the horizon lengthens
- Long-range annual returns are capped to prevent unrealistic compounding

Portfolio safeguards
--------------------

Default constraints:

- Minimum cash: 75% of total portfolio
- Maximum one asset: 8% of total portfolio
- Recommendations remain conservative while Module 40/41 evidence is sparse

The percentages are percentages of the total portfolio, not merely the
crypto sleeve.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v12_0_0_windows.bat
3. Run python run_module42.py
4. Run python inspect_module42.py
5. Run python export_module42.py

Important
---------

Long-range bear, median, and bull prices are conditional scenarios. They are
not guaranteed prices and should become more reliable only after live forecast
outcomes accumulate in Modules 40 and 41.
