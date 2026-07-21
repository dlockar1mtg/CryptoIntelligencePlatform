Crypto Intelligence Platform v10.2.0
Forecast Memory & Continuous Learning
=====================================

This release combines v10.1.1 corrections with Module 40.

v10.1.1 corrections
-------------------

1. Module 39 schema preflight now expects the actual 19-column schema.

2. Probability calibration is evidence-aware.

- Platt and isotonic calibration require at least 30 observations.
- Smaller samples use EVIDENCE_SHRINKAGE toward a neutral 50% prior.
- Three model-validation rows are no longer treated as sufficient proof.

3. Feature stability is evidence-aware.

- A single attribution snapshot receives INSUFFICIENT_EVIDENCE.
- Stability grades require at least five snapshots.
- One run can no longer produce a misleading 100% proven-stability result.

4. Advancement requires realized evidence.

- At least six realized scorecards
- At least 180 total calibration observations
- Existing Brier, coverage, accuracy, and drift thresholds

Until then Module 39 reports ACCUMULATING_EVIDENCE / BUILD_FORECAST_MEMORY.

Module 40
---------

Module 40 stores a permanent, versioned memory of:

- Every Module 38 forecast
- Raw and calibrated probabilities
- Raw and calibrated intervals
- Model confidence and agreement
- Predictive regime and confidence
- Every ensemble model and its weight
- Every attribution driver and rank
- Model version and source run IDs

Outcome maturation
------------------

On every Module 40 run:

1. Pending forecasts with due dates on or before today are identified.
2. The first available market price on or after the due date is attached.
3. Module 40 calculates:
   - Realized return
   - Forecast error
   - Absolute error
   - Directional correctness
   - Interval coverage
   - Positive-return outcome
4. The forecast becomes MATURED.

Continuous learning
-------------------

As outcomes mature, Module 40 builds:

- Learning summaries by asset and horizon
- Regime-specific performance
- Confidence-band performance
- Reliability/calibration curves
- Model leaderboards
- Realized MAE and directional accuracy
- Brier score and calibration gap
- Interval coverage
- Forecast-following Sharpe
- Retraining recommendations

Retraining
----------

A model receives higher retraining priority when:

- Recent MAE is materially worse than prior MAE
- Directional accuracy deteriorates
- Calibration gap exceeds tolerance

The first run will normally show:

- 24 stored forecasts
- 24 pending forecasts
- 0 matured forecasts
- Memory status: ACCUMULATING
- Continuous learning: BASELINE_CREATED

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v10_2_0_windows.bat
3. Re-run Module 39:
   python run_module39.py
4. Run Module 40:
   python run_module40.py
5. Inspect:
   python inspect_module40.py
6. Export:
   python export_module40.py

For future forecast cycles:

1. Run Module 38
2. Run Module 39
3. Run Module 40

Module 40 safely deduplicates forecasts and matures outcomes as dates arrive.
