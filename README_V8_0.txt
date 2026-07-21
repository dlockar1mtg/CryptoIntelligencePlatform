Crypto Intelligence Platform v8.0
Explainable AI Research Framework
=================================

Requires successful Modules 25, 27, and 28.

Module 29 does not retrain or replace the regime engine.
It determines which features have repeatable evidence across:

- Expanding walk-forward test folds
- Bootstrap resamples
- Rolling historical windows
- Individual regimes
- Feature ablation tests
- Redundancy analysis

The resulting feature registry assigns each feature:

- Evidence grade
- Stability score
- Bootstrap selection rate
- Positive walk-forward fold rate
- Rolling positive-importance rate
- Regime separation score
- Ablation effect
- Stable or rejected status

Module 29 then compares four transparent models:

- Full feature set
- Core-only feature set
- Stable evidence-based feature set
- Top-five stable feature set

Advancement requires the stable model to achieve:

- At least 55% walk-forward accuracy
- At least 20% accuracy in its weakest fold
- No more than two retained representation features

Possible recommendations:

- READY_FOR_CLEAN_REGIME_RETRAINING
- CONTINUE_EXPLAINABILITY_RESEARCH

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v8_0_windows.bat
3. Run python run_module29.py
4. Run python inspect_module29.py
5. Optional: python export_module29.py

Modules 25-28 remain unchanged.
