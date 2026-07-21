Crypto Intelligence Platform v10.0.1
Adaptive Forecast History Hotfix
================================

Cause
-----

Module 38 required 450 training rows plus 120 validation rows.

After calculating 200-day indicators and removing rows without a future
7-day target, Bitcoin had 328 usable rows. The forecast engine therefore
stopped before writing any forecast results.

Corrections
-----------

1. Adaptive training and validation windows

The configured 450/120 values remain preferred targets. When less history is
available, Module 38 now uses:

- At least 160 training observations
- At least 45 validation observations
- No more than 25% of usable history for validation
- The largest leakage-safe training sample available

For the reported 328-row Bitcoin 7-day dataset, the hotfix uses:

- 246 training rows
- 82 validation rows

2. Current feature row correction

Historical training rows require a known future return and therefore exclude
the most recent horizon. The live forecast now builds its feature row directly
from the latest market observation instead of forecasting from an older row.

3. Failure isolation

A prior failed Module 38 run remains in the audit history as FAILED. No tables
or earlier module results are deleted.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Allow files and crypto_platform to merge and replace
3. Run apply_v10_0_1_hotfix.bat
4. Run python run_module38.py
5. Run python inspect_module38.py
6. Run python export_module38.py
