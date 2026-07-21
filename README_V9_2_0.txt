Crypto Intelligence Platform v9.2.0
Institutional Portfolio Optimizer
=================================

Module 37 adds five constrained portfolio methods:

- Minimum variance
- Maximum Sharpe
- Risk parity
- Black-Litterman-style
- Regime-aware optimization

Expected returns
----------------

Expected returns blend:

- 40% historical annualized return
- Up to 40% Module 31 regime-conditioned forward return
- 20% cross-asset shrinkage prior

The regime weight is scaled by current Module 35 confidence, so weak confidence
automatically shifts more weight toward historical and prior estimates.

Constraints
-----------

Default constraints preserve the current defensive portfolio:

- Minimum cash: 75%
- Maximum risky exposure: 25%
- Maximum individual risky-asset weight: 2.5%
- Turnover penalty
- Concentration penalty
- Covariance ridge stabilization

Analytics
---------

- Efficient frontier
- Portfolio covariance optimization
- Marginal and component risk contribution
- Diversification ratio
- Risky-sleeve effective asset count
- Risky-sleeve concentration
- Active share
- Information ratio
- Portfolio entropy
- Trade deltas versus Module 35

Important
---------

Cash is no longer included when calculating risky-sleeve diversification.
This prevents a valid defensive cash allocation from incorrectly appearing as
a poorly diversified crypto sleeve.

v9.1.1 export fix
-----------------

export_module35.py and export_module36.py now close the DuckDB connection only
after every requested CSV has been written.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v9_2_0_windows.bat
3. Run python run_module37.py
4. Run python inspect_module37.py
5. Run python export_module37.py
6. Re-run:
   python export_module35.py
   python export_module36.py

Modules 25-36 remain unchanged.
