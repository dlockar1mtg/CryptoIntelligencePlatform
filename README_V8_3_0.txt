Crypto Intelligence Platform v8.3.0
Validation Hardening & Benchmark Release
========================================

Module 32 adds five pre-v9 validation systems:

1. Feature Stability History
   - Point-in-time fold contributions
   - Contribution variability
   - Sign-flip frequency
   - Rank persistence
   - Evidence grades

2. Probability Drift Monitoring
   - Rolling accuracy, log loss, and Brier score
   - Confidence entropy
   - Probability PSI
   - Model disagreement
   - Calibration deterioration
   - STABLE / WARNING / CRITICAL status

3. Rolling Retraining Study
   - Static, 30-, 60-, 90-, and 180-day policies
   - Point-in-time fitting only
   - Accuracy, log loss, Brier, switching, and computation score

4. Stress Testing
   - Automatically detected drawdowns, volatility spikes, and recoveries
   - Synthetic 1-, 2-, and 3-sigma feature shocks
   - Monotonic-response validation

5. Benchmark Comparison
   - BTC buy-and-hold
   - Equal-weight six-asset portfolio
   - BTC/ETH 60/40
   - Risk parity
   - Volatility-targeted BTC
   - Legacy regime allocation
   - Clean regime allocation
   - Clean probability-weighted allocation
   - Common dates and 10 bps transaction costs

Advancement requires:
- Acceptable retraining log loss
- At least 80% synthetic stress monotonicity
- Clean strategy Sharpe at least as high as BTC
- Clean strategy maximum drawdown better than BTC
- No critical current probability drift

Possible recommendations:
- READY_FOR_PORTFOLIO_INTELLIGENCE
- RESEARCH_VALIDATION_REQUIRES_REFINEMENT

Installation:
1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v8_3_0_windows.bat
3. Run python run_module32.py
4. Run python inspect_module32.py
5. Run python export_module32.py
