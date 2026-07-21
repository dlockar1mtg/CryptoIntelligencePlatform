Crypto Intelligence Platform v3.3.5 Recovery Hotfix
===================================================

This hotfix addresses two issues:

1. Full release archives must never contain the live data directory or .env.
2. Module 14 now marks prerequisite failures as FAILED instead of leaving
   runs stuck at RUNNING.

Install
-------
Extract directly into:

C:\Users\DevonLockard\Crypto

Run:

apply_v3_3_5_recovery_hotfix.bat

The diagnosis tells you which recovery sequence is required:

A. Canonical rows already exist:
   python run_module14.py

B. Raw rows exist but canonical is empty:
   python run_module6.py --phase sync
   python run_module14.py

C. Both raw and canonical are empty:
   python run_module1.py
   python run_module6.py --phase sync
   python run_module14.py
