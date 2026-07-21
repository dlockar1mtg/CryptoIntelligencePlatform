Crypto Intelligence Platform v7.0
Adaptive Market Regime Intelligence
===================================

v7.0 is a safe overlay for an installed v6.0 platform.

Module 25 classifies every eligible historical day into one of six regimes:

- LIQUIDITY_EXPANSION
- MOMENTUM_BULL
- RECOVERY
- RANGE_BOUND
- MACRO_STRESS
- VOLATILITY_SHOCK

Model Ensemble
--------------

The official probabilities combine:

- Gaussian Mixture Model
- K-means clustering
- Transparent rule-based regime scores
- Change-pressure / structural-shift evidence
- Probability smoothing for state persistence

The release does not claim to use a Hidden Markov Model because no HMM
dependency is included in the platform.

Outputs
-------

- Daily regime probabilities
- Dominant and secondary regime
- Confidence and model agreement
- Days in current regime
- Historical expected persistence
- Transition risk
- Regime transition matrix
- Duration statistics
- Feature contribution explanations
- Reproducibility and stability validation

Validation
----------

The engine validates:

- Historical coverage
- Mean classification confidence
- Daily regime-switch rate
- Model agreement
- Feature completeness
- Deterministic reproducibility

Installation
------------

Extract directly into:

C:\Users\DevonLockard\Crypto

Run:

install_v7_0_windows.bat

Then:

python run_module25.py
python inspect_module25.py
python export_module25.py

The overlay contains no data folder, .env, logs, credentials, or DuckDB files.
Modules 13 and 24 remain unchanged.
