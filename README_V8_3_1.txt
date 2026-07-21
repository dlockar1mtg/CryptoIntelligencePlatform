Crypto Intelligence Platform v8.3.1
Portfolio Decision Optimization & Drift Repair
================================================

Purpose
-------

Module 32 showed that the clean regime model reduced drawdown but did not beat
BTC buy-and-hold on Sharpe, generated approximately 1,310% annual turnover,
and marked every probability-drift window CRITICAL.

Module 33 corrects the decision layer rather than adding more raw features.

New capabilities
----------------

1. Probability regularization

- Temperature scaling
- Probability floors
- Entropy restoration
- Reduced near-100% confidence

2. Regime hysteresis

- A new regime must exceed the currently held regime by a configured margin
- Minimum holding periods of 7, 14, or 30 days
- Prevents low-information switching

3. Confidence-scaled exposure

- Exposure falls toward cash when probability is near the confidence floor
- Exposure is also scaled by regime risk
- Maximum portfolio risk exposure is optimized

4. Portfolio-aware parameter search

486 candidate decision policies are evaluated across:

- Temperature
- Probability floor
- Switch margin
- Minimum holding period
- Confidence floor
- Maximum risk exposure

The objective rewards:

- Sharpe ratio
- Calmar ratio
- CAGR

and penalizes:

- Drawdown
- Turnover above 250%
- Transaction costs

5. Adjusted probability drift

Drift is compared with the immediately preceding 180-day distribution rather
than one remote fixed baseline. The monitor combines:

- Top-probability PSI
- Entropy PSI
- Confidence shift
- Component-model disagreement

6. Cost sensitivity

The selected policy is tested at:

- 10 basis points
- 25 basis points
- 50 basis points

Advancement gate
----------------

READY_FOR_PORTFOLIO_INTELLIGENCE requires:

- Sharpe at least as high as BTC buy-and-hold
- Maximum drawdown better than BTC
- Annualized turnover no greater than 250%
- At least 66.67% of cost scenarios passing
- Adjusted current drift not CRITICAL

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v8_3_1_windows.bat
3. Run python run_module33.py
4. Run python inspect_module33.py
5. Run python export_module33.py

Modules 25-32 remain unchanged.
