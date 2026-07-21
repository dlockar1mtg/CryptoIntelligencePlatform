Crypto Intelligence Platform v7.0.2
Module 25 Feature-Matrix Hotfix
================================

Cause
-----

Module 25's rule_scores() function uses btc_drawdown_180d when mapping
Gaussian-mixture and K-means cluster centers to named regimes.

The clustering matrix omitted btc_drawdown_180d. Therefore, reconstructed
cluster-center rows did not contain that field and raised:

KeyError: 'btc_drawdown_180d'

Correction
----------

v7.0.2:

- Adds btc_drawdown_180d to the clustering matrix.
- Keeps the cluster-center schema aligned with rule_scores().
- Makes rule_scores() use safe optional-field access for volatility,
  drawdown, and breadth.
- Preserves all existing data and Module 25 schema changes from v7.0.1.

Installation
------------

Extract directly into:

C:\Users\DevonLockard\Crypto

Allow files to replace/merge, then run:

apply_v7_0_2_feature_matrix_hotfix.bat

After it succeeds:

python run_module25.py
python inspect_module25.py
