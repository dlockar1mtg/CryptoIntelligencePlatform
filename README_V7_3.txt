Crypto Intelligence Platform v7.3
Feature Selection & Adaptive Optimization
=========================================

Requires a successful Module 27 run.

Module 28 adds:

- Permutation and ablation-based feature evaluation
- Correlation-aware feature pruning
- Minimum preservation of core Module 25 features
- Multi-generation adaptive parameter search
- Search concentration around elite candidates
- Validation-weighted top-five meta-ensemble
- Isotonic, Platt, and identity calibration comparison
- Per-fold calibration-method selection
- Empirical robustness reruns using core-only and reduced feature sets
- Strict advancement gates

This release does not add Optuna or another external optimizer dependency.
The adaptive optimizer uses successive generations of elite-guided stochastic
search and is reproducible from the configured random seed.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v7_3_windows.bat
3. Run python run_module28.py
4. Run python inspect_module28.py
5. Optional: python export_module28.py

Modules 25, 26, and 27 remain unchanged.
