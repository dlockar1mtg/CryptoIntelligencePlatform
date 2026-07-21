Crypto Intelligence Platform v8.1.1
Clean Regime Engine Stabilization Release
=========================================

Purpose
-------

v8.1.1 corrects statistical and compatibility issues found during the first
successful Module 30 run.

Corrections
-----------

1. Canonical class ordering

All probability matrices now use the same lexicographic class order required
by sklearn multiclass metrics:

- LIQUIDITY_EXPANSION
- MACRO_STRESS
- MOMENTUM_BULL
- RANGE_BOUND
- RECOVERY
- VOLATILITY_SHOCK

Model outputs, calibration, log loss, Brier scoring, probability exports, and
stored rankings all use this single shared ordering.

2. sklearn 1.9 compatibility

The deprecated explicit penalty="elasticnet" argument was removed.
Elastic-net behavior is selected using solver="saga" and l1_ratio=0.20.

3. Probability-matrix validation

Every matrix scored by log loss or Brier score is checked for:

- Correct number of columns
- Finite values
- Nonnegative probabilities
- Rows summing to one

4. Continuous model agreement

Agreement is no longer only 0% or 100%. It is calculated from total-variation
distance between gradient-boosting and elastic-net probability distributions.

5. Disagreement diagnostics

A new latest_clean_model_disagreement view shows:

- Each component model's preferred regime
- Each model's probability
- Continuous agreement
- Total-variation distance
- Blended regime and probability
- Disagreement flag

6. Observation safety

The model remains OBSERVATION only. No automatic promotion is performed.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Allow files to replace and merge
3. Run install_v8_1_1_windows.bat
4. Run python run_module30.py
5. Run python inspect_module30.py
6. Optional: python export_module30.py

The existing database and all v8.1.0 results are preserved.
