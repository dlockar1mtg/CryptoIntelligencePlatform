Crypto Intelligence Platform v11.0.3
Canonical Memory Rebuild Engine
====================================

Why v11.0.2 failed
------------------

The in-place migration attempted to create a three-column unique index after
deleting duplicate parents. DuckDB still detected duplicate rows, so the
transaction rolled back and Module 40 had no matching conflict index.

v11.0.3 does not delete duplicates in place.

Rebuild process
---------------

1. Back up the active DuckDB database.
2. Read all existing forecast memory.
3. Group rows by:
   - forecast_date
   - asset_id
   - horizon_days
4. Select one canonical survivor:
   - Prefer a matured record
   - Otherwise prefer the newest record
5. Assign a new deterministic canonical forecast ID.
6. Build a new parent table from those canonical rows.
7. Consolidate model-memory children onto the new IDs.
8. Consolidate attribution-memory children onto the new IDs.
9. Validate the rebuilt tables.
10. Atomically rename the original tables to legacy names.
11. Rename rebuilt tables into production.
12. Create explicit unique indexes for:
    - Canonical forecasts
    - Model children
    - Attribution children
13. Revalidate the production tables.
14. Drop legacy tables only after every check passes.
15. Commit the transaction.

Rollback protection
-------------------

Any failure before the final commit restores the original tables and data.

Expected result
---------------

For the July 14 baseline:

Forecast rows:
48 -> 24

Model rows:
Duplicate children consolidate to one model snapshot per
forecast-memory ID and model.

Attribution rows:
Duplicate children consolidate to one driver snapshot per
forecast-memory ID and driver.

Matured forecasts:
Preserved as one canonical prediction event.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Allow files and crypto_platform to merge and replace.
3. Run:
   apply_v11_0_3_canonical_memory_rebuild.bat
4. Run:
   python run_module40.py
5. Inspect:
   python inspect_module40.py
6. Run Module 40 again.
7. Confirm the forecast count remains unchanged.
8. Refresh Module 41:
   python run_module41.py
