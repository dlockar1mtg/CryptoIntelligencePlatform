Crypto Intelligence Platform v7.2
Regime Representation & Optimization Release
=============================================

Requires successful Module 25 and v7.1 installation.

Module 27 adds:

- Cross-asset correlation and beta dispersion
- Volatility term structure
- Downside participation and return skew
- Breadth momentum
- Altcoin relative strength
- Drawdown velocity and trend acceleration
- Liquidity, credit, and dollar impulses
- Stress concentration and transition pressure
- Gaussian state-space emission model
- 240-candidate randomized ensemble search per fold
- Temperature and transition-strength optimization
- Nested isotonic probability calibration
- Empirical feature-ablation sensitivity reruns

The Gaussian state-space layer provides sequence-aware emission probabilities
without adding an external HMM dependency. It combines regime-conditioned
Gaussian emissions with a learned transition prior.

The release remains research-only. Module 25 classifications are unchanged.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v7_2_windows.bat
3. Run python run_module27.py
4. Run python inspect_module27.py
5. Optional: python export_module27.py
