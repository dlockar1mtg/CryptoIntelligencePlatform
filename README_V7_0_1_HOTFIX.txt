Crypto Intelligence Platform v7.0.1
Module 25 Schema Collision Hotfix
=================================

Cause
-----

The original v7.0 release used generic market_regime_* physical table names.
Earlier modules may already contain tables with those names but different
schemas. DuckDB retained the existing tables because CREATE TABLE IF NOT EXISTS
does not replace or migrate them. The v7.0 latest-run views then failed during
creation.

Correction
----------

v7.0.1 stores Module 25 data in uniquely namespaced physical tables:

- m25_regime_features
- m25_regime_probabilities
- m25_regime_daily
- m25_regime_transitions
- m25_regime_durations
- m25_regime_validation
- m25_regime_contributions

The user-facing latest_market_regime_* views remain unchanged.

Existing tables from Modules 21-24 are preserved.

Installation
------------

Extract directly into:

C:\Users\DevonLockard\Crypto

Allow files to replace/merge, then run:

apply_v7_0_1_schema_hotfix.bat

After it succeeds:

python run_module25.py
python inspect_module25.py
