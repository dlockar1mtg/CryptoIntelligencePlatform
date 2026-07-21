Crypto Intelligence Platform v8.1.0
Clean Regime Model & Production Intelligence Foundation
========================================================

Requires a successful, passed Module 29 run.

v8.1.0 adds:

- Module 30 Clean Regime Engine
- Shared crypto_platform/ml package
- Permanent machine-learning experiment registry
- Histogram gradient boosting model
- Elastic-net logistic benchmark
- Historical blend-weight selection
- Multiclass probability calibration
- Expanding walk-forward validation
- Feature drift and PSI monitoring
- Counterfactual feature contributions
- Side-by-side legacy Module 25 comparison
- Observation-only promotion state

Stable features are loaded directly from the latest passed Module 29
feature registry. No feature names are hard-coded into the production run.

Important
---------

Module 30 is not automatically promoted. Even when its historical validation
passes, its promotion_status remains OBSERVATION. A later release can evaluate
accumulated live observations against the configured minimum observation period.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v8_1_0_windows.bat
3. Run python run_module30.py
4. Run python inspect_module30.py
5. Optional: python export_module30.py

Modules 25-29 remain unchanged.
