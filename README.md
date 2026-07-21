# Crypto Intelligence Platform v4.2 — Feature Expansion Release

v4.2 expands the research information set without changing the live Module 13
portfolio methodology.

## Module 17

Module 17 builds a daily feature warehouse containing:

- Bitcoin dominance from CoinGecko snapshots when available
- A historical BTC-dominance proxy from canonical market capitalization
- TOTAL2 and TOTAL3 market-cap proxies
- Stablecoin supply and 30-day supply growth
- Historical Fear & Greed observations
- Validated manual ETF net flows
- Core-market breadth above SMA-50
- Median 30-day core return
- U.S. dollar index
- VIX
- High-yield credit spread
- Macro-liquidity score
- Composite crypto risk-appetite score

## Source integrity

The release does not fabricate ETF-flow history. A manual CSV template is
provided for validated observations:

`python import_etf_flows.py`

The generated file is:

`data/manual/crypto_etf_flows.csv`

Required columns:

- observation_date
- net_flow_usd
- source

## Predictive validation

Every eligible feature is tested against subsequent Bitcoin returns over:

- 30 days
- 90 days
- 180 days

The platform reports:

- Pearson correlation
- Spearman correlation
- Top-quartile future return
- Bottom-quartile future return
- Top-minus-bottom spread
- Directional hit rate

## Feature readiness

Each feature receives:

- History start and end
- History length
- Non-null coverage
- Strongest absolute Spearman correlation
- READY_FOR_RESEARCH, LIMITED, or NO_DATA status

Features are not admitted into optimization merely because they exist.

## Safe installation

The release archive excludes the live data directory, logs, `.env`, and all
DuckDB files.

Install:

`install_v4_2_windows.bat`

Run:

`python run_module17.py`

Inspect:

`python inspect_module17.py`

Export:

`python export_module17.py`
