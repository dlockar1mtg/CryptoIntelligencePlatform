Crypto Intelligence Platform v11.0.2
Canonical Forecast Identity
====================================

One forecast event is now uniquely identified by:

- forecast_date
- asset_id
- horizon_days

model_version and source run IDs remain lineage metadata.

The migration:
- Prefers a matured forecast as the survivor
- Otherwise keeps the newest forecast
- Consolidates model rows onto the survivor
- Consolidates attribution rows onto the survivor
- Preserves matured outcome fields
- Replaces the old four-column unique index
- Validates duplicates, orphan children, and matured outcomes
- Rolls back if any validation fails

Expected July 14 result:
48 forecasts -> 24 forecasts

Repeated Module 40 runs remain at 24 unless a genuinely new forecast date,
asset, or horizon is generated.

Installation:
1. Extract into C:\Users\DevonLockard\Crypto
2. Run apply_v11_0_2_canonical_identity.bat
3. Run python run_module40.py
4. Run python inspect_module40.py
5. Run python run_module40.py again
6. Confirm the count remains unchanged
7. Run python run_module41.py
