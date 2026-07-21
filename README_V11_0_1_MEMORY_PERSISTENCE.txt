Crypto Intelligence Platform v11.0.1
Memory Persistence Engine
====================================

Cause
-----

Module 40's m40_forecast_memory table now has:

- PRIMARY KEY(forecast_memory_id)
- UNIQUE INDEX(
    forecast_date,
    asset_id,
    horizon_days,
    model_version
  )

DuckDB cannot infer which conflict target INSERT OR REPLACE should use when
multiple uniqueness constraints exist.

Corrections
-----------

1. Explicit canonical forecast upsert

Forecast memory now uses:

ON CONFLICT(
    forecast_date,
    asset_id,
    horizon_days,
    model_version
)
DO UPDATE

Only forecast metadata is updated. Matured outcome fields are excluded from
the update so a rerun cannot erase realized results.

2. Explicit child-table upserts

Model memory uses:

ON CONFLICT(forecast_memory_id, model_key)

Attribution memory uses:

ON CONFLICT(forecast_memory_id, driver_key)

3. Transactional persistence

Forecast, model, attribution, maturation, learning, calibration, leaderboard,
retraining, summary, and run-status updates now occur in one DuckDB
transaction.

If any step fails, the transaction is rolled back.

4. Recovery

Stale RUNNING Module 40 rows are automatically closed as FAILED before a new
memory transaction begins.

5. Pre-commit validation

Before COMMIT, Module 40 verifies:

- No canonical duplicate forecasts
- No orphan model rows
- No orphan attribution rows
- Every MATURED forecast has complete realized-outcome fields

6. Audit-safe behavior

- Existing 24 pending forecasts remain intact.
- Existing failed and successful Module 40 runs remain in audit history.
- Module 41 tables and results remain unchanged.
- No forecast or realized outcome is deleted by this hotfix.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Allow files and crypto_platform to merge and replace
3. Run apply_v11_0_1_memory_persistence.bat
4. Run:
   python run_module40.py
5. Inspect:
   python inspect_module40.py
6. Run Module 40 a second time:
   python run_module40.py
7. Confirm forecasts remain 24 rather than increasing.
8. Refresh meta-learning:
   python run_module41.py
