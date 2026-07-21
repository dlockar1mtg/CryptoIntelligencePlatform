Crypto Intelligence Platform v3.3.3 Identifier Hotfix
=====================================================

Problem
-------
Module 13 analyzed all six core assets, but the optimizer recognized only four.

The configured identifiers were:

- ripple
- avalanche-2

The canonical warehouse uses:

- xrp
- avalanche

Fix
---
This hotfix changes the Module 13 core IDs to:

- bitcoin
- ethereum
- solana
- chainlink
- xrp
- avalanche

Installation
------------
Extract all files directly into:

C:\Users\DevonLockard\Crypto

Run:

apply_v3_3_3_identifier_hotfix.bat

Then run:

python run_module13.py
python inspect_module13.py

Expected result
---------------
Module 13 should report:

Core assets recommended: 6
Portfolio rows: 7

The portfolio should include:

- bitcoin
- ethereum
- solana
- chainlink
- xrp
- avalanche
- CASH
