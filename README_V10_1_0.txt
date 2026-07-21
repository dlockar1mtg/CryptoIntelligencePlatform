Crypto Intelligence Platform v10.1.0
Forecast Calibration & Live Validation
=======================================

Module 39 adds:
- Platt, isotonic, and shrinkage probability calibration
- Calibrated positive-return probabilities
- 80% conformal-style return intervals
- Rolling-origin validation summaries
- Feature contribution stability grades
- Forecast drift monitoring
- Realized forecast scorecards when outcomes become available
- Advancement gate for live monitoring

Important:
The first run may show zero realized scorecards because Module 38 has only one
successful forecast date. Scorecards populate automatically after future
forecast horizons mature and Module 39 is rerun.

Installation:
1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v10_1_0_windows.bat
3. Run python run_module39.py
4. Run python inspect_module39.py
5. Run python export_module39.py
