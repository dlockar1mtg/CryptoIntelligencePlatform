Crypto Intelligence Platform v10.0.2
Long-Horizon Availability Hotfix
================================

Cause
-----

The v10.0.1 adaptive split successfully fixed the 7-day forecast, but a
180-day target leaves fewer historical labeled observations. Bitcoin had:

- 155 usable 180-day rows
- A previous minimum requirement of 205 total rows

Longer forecast horizons inherently remove more recent observations because
their future return is not yet known.

Corrections
-----------

1. Long-horizon adaptive minimums

A supported forecast now requires:

- At least 90 training observations
- At least 30 validation observations
- Validation no larger than 25% of usable history

For 155 usable rows, Module 38 uses:

- 117 training observations
- 38 validation observations

2. Graceful horizon skipping

When one asset/horizon still lacks sufficient history, Module 38 records it
as skipped in the run notes and continues with every supported forecast.

For example, a 365-day forecast may be unavailable while 7-, 30-, 90-, and
180-day forecasts complete successfully.

3. Portfolio horizon protection

The configured 90-day portfolio forecast remains mandatory. Module 38 will
fail transparently only if no 90-day asset forecasts are available.

4. Audit preservation

The earlier failed Module 38 runs remain in module38_runs as FAILED. No
historical result is deleted or overwritten.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Allow files and crypto_platform to merge and replace
3. Run apply_v10_0_2_hotfix.bat
4. Run python run_module38.py
5. Run python inspect_module38.py
6. Run python export_module38.py
