Crypto Intelligence Platform v8.2.1
Module 31 Run-Start Schema Hotfix
=================================

Cause
-----

The v8.2 Module 31 run-start statement supplied 15 VALUES to module31_runs,
but the table contains 14 columns. DuckDB correctly rejected the insert before
any validation data was written.

Correction
----------

- Replaces the positional 15-value insert with an explicit 14-column INSERT.
- Updates Module 31 run metadata to platform_version 8.2.1.
- Adds a schema-aware preflight that verifies the exact module31_runs column list.
- Preserves Modules 25-30, the database, and all existing exports.
- No database restore is needed.

Install
-------

Extract into:

C:\Users\DevonLockard\Crypto

Allow files to replace and merge, then run:

apply_v8_2_1_module31_hotfix.bat

After it succeeds:

python run_module31.py
python inspect_module31.py
python export_module31.py
