Crypto Intelligence Platform v8.2.2
Module 31 Actual-Schema Alignment Hotfix
========================================

Cause
-----

The first v8.2.1 hotfix assumed a different module31_runs schema than the one
actually installed by v8.2.

The installed table contains:

- run_id
- source_module30_run_id
- started_at_utc
- completed_at_utc
- status
- historical_rows
- forward_return_rows
- calibration_rows
- persistence_rows
- investment_value_score
- validation_status
- recommendation
- notes
- platform_version

Correction
----------

v8.2.2:

- Uses the exact existing 14-column schema.
- Corrects the Module 31 run-start INSERT.
- Preserves the original successful completion UPDATE logic.
- Adds an exact-schema preflight.
- Does not drop, alter, or recreate the database table.
- Requires no database restoration.

Install
-------

Extract directly into:

C:\Users\DevonLockard\Crypto

Allow files to replace and merge, then run:

apply_v8_2_2_actual_schema_hotfix.bat

After it succeeds:

python run_module31.py
python inspect_module31.py
python export_module31.py
