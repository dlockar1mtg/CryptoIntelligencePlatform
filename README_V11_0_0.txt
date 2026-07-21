Crypto Intelligence Platform v11.0.0
Adaptive Meta-Learning Engine
====================================

Combined release:
- v10.2.1 Forecast Memory Idempotency Hotfix
- v11.0 Module 41 Adaptive Meta-Learning Engine

v10.2.1
-------
The prior memory key included source Module 38 run_id, so equivalent reruns
from the same forecast date created duplicate memories.

This release:
- Removes existing canonical duplicates safely
- Removes their child model and attribution records
- Keeps the newest copy
- Enforces a unique database index on:
  forecast_date + asset_id + horizon_days + model_version
- Uses canonical deterministic memory IDs for future ingestion
- Makes Module 40 safe to schedule and rerun

Expected repair:
48 stored forecasts should return to 24 for the July 14 baseline.

Module 41
---------
Module 41 converts forecast memory into adaptive controls:

1. Adaptive model weights
- Validation ensemble weights are the prior
- Realized performance weights become active as outcomes mature
- Evidence blends gradually up to 30 matured forecasts
- No realized evidence means no unsupported automatic reweighting

2. Horizon reliability
- Validation MAE
- Realized MAE
- Directional accuracy
- Brier score
- Interval coverage
- Evidence-adjusted reliability score

3. Confidence adjustments
- Raw confidence is discounted while evidence is sparse
- Reliability increasingly controls confidence as outcomes mature

4. Optimizer feedback
- Predictive return
- Realized forecast bias
- Reliability and confidence multipliers
- Adaptive expected-return signal
- OBSERVATION_ONLY until evidence is sufficient

5. Retraining plan
- Uses Module 40 drift/retraining evidence
- Priorities LOW, MEDIUM, HIGH
- Actions CONTINUE_OBSERVATION, REVIEW_MODEL_WEIGHT,
  or RETRAIN_AND_REVALIDATE

Expected first run:
- Meta-learning status: ACCUMULATING_EVIDENCE
- Recommendation: CONTINUE_MEMORY_ACCUMULATION
- Model status: VALIDATION_PRIOR
- Feedback status: OBSERVATION_ONLY

Installation
------------
1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v11_0_0_windows.bat
3. Run python run_module40.py
4. Run python inspect_module40.py
5. Run python run_module41.py
6. Run python inspect_module41.py
7. Run python export_module41.py
