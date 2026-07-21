Crypto Intelligence Platform v4.2.2
Research Promotion Release
===================================

This is a safe overlay for an installed v4.2.1 platform.

Module 19 adds:

- Refreshed feature validation after stablecoin-history backfills
- Rolling out-of-sample feature validation
- Grouped permutation importance
- Formal feature registry
- Promotion and demotion audit history
- Snapshot-only feature labeling
- Research-only, watchlist, and shadow-promotion stages

Feature Groups
--------------

MACRO
- dollar_index
- high_yield_spread
- vix
- macro_liquidity_score

SENTIMENT
- fear_greed_index
- risk_appetite_score

MARKET_STRUCTURE
- btc_dominance_proxy_pct
- total2_market_cap_proxy_usd
- total3_market_cap_proxy_usd
- core_breadth_above_sma50_pct
- core_median_return_30d_pct
- btc_return_30d_pct

LIQUIDITY_FLOWS
- stablecoin_supply_usd
- stablecoin_growth_30d_pct
- etf_net_flow_usd

Registry Statuses
-----------------

PROMOTED_SHADOW
- Cleared the configured research thresholds.
- Eligible only for future shadow testing.
- Does not alter Module 13.

WATCHLIST
- Promising evidence but not enough for promotion.

RESEARCH_ONLY
- Did not clear the configured promotion thresholds.

INSUFFICIENT_HISTORY
- History or coverage is inadequate.

SNAPSHOT_REFERENCE
- Latest snapshot only.
- Not production eligible.
- Historical proxy should be used instead.

Installation
------------

Extract directly into:

C:\Users\DevonLockard\Crypto

Allow the crypto_platform folder to merge.

Run:

install_v4_2_2_windows.bat

Then:

python run_module19.py
python inspect_module19.py
python export_module19.py

The overlay contains no data folder, .env, logs, or DuckDB files.
