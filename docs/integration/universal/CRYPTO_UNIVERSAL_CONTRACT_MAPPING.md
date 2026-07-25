# Crypto Universal Contract Mapping

## Status

**MAPPING STATUS: APPROVED FOR ADAPTER DEVELOPMENT**

## Certified source

- Repository: Crypto Intelligence Platform
- Source branch: `integration/universal-platform-v1`
- Certified commit: `daced44`
- Certification tag: `crypto-post-remediation-replay-certified`
- Adapter branch: `integration/crypto-universal-export-adapter`
- Platform status: `RESEARCH ONLY`

## Integration principles

The crypto export adapter is read-only against the source database.

The adapter must:

- read from `data/crypto_intelligence.duckdb`,
- select only the latest completed source runs,
- preserve source run identifiers and observation dates,
- normalize crypto asset identifiers,
- write an isolated universal export package,
- provide row counts and file hashes,
- validate required fields,
- and distinguish actual holdings from analytical target allocations.

The adapter must not:

- modify the crypto database,
- invoke market-data collection,
- run analytical modules,
- infer actual holdings from target allocations,
- treat recommendation quantities as owned quantities,
- or write directly into the Universal Investment Platform database.

## Universal dataset mapping

### 1. Asset master

Universal dataset:

`asset_master.csv`

Primary source:

`assets`

Source fields:

| Universal field | Crypto source |
|---|---|
| asset_id | `asset_id` |
| symbol | `symbol` |
| asset_name | `asset_name` |
| asset_class | Constant: `crypto` |
| asset_subclass | `asset_tier` |
| native_chain | `native_chain` |
| active | `active` |
| portfolio_enabled | `portfolio_enabled` |
| research_enabled | `research_enabled` |
| external_id | `coingecko_id` |
| source_platform | Constant: `crypto_intelligence_platform` |

Selection rule:

Export all active assets.

### 2. Market prices

Universal dataset:

`market_prices.csv`

Primary source:

`asset_market_daily`

Source fields:

| Universal field | Crypto source |
|---|---|
| asset_id | `asset_id` |
| price_date | `observation_date` |
| price | `price_usd` |
| currency | Constant: `USD` |
| market_cap | `market_cap_usd` |
| volume_24h | `volume_24h_usd` |
| source | `source` |
| collected_at_utc | `collected_at_utc` |

Selection rule:

Export the latest available observation for each asset.

Fallback source:

`asset_ohlcv.close`, using the most recent daily record when an
`asset_market_daily` price is unavailable.

### 3. Forecasts

Universal dataset:

`forecasts.csv`

Primary source:

`m39_calibrated_forecasts`

Source fields:

| Universal field | Crypto source |
|---|---|
| asset_id | `asset_id` |
| forecast_date | `forecast_date` |
| horizon_days | `horizon_days` |
| expected_return_pct | `predicted_return_pct` |
| probability_positive | `calibrated_probability_positive` |
| lower_return_pct | `conformal_lower_return_pct` |
| upper_return_pct | `conformal_upper_return_pct` |
| confidence | `forecast_confidence` |
| forecast_status | `forecast_status` |
| methodology | `calibration_method` |
| source_run_id | `run_id` |
| calculated_at_utc | `calculated_at_utc` |

Selection rule:

Export all rows belonging to the latest successful Module 39 run.

### 4. Recommendations

Universal dataset:

`recommendations.csv`

Primary source:

`m42_asset_recommendations`

Source fields:

| Universal field | Crypto source |
|---|---|
| asset_id | `asset_id` |
| recommendation_date | `recommendation_date` |
| action | `best_action` |
| investment_score | `investment_score` |
| target_weight_pct | `best_current_portfolio_pct` |
| weight_change_pct | `weight_change_pct` |
| timeline | `suggested_timeline` |
| entry_strategy | `entry_strategy` |
| conviction | `conviction` |
| forecast_confidence | `forecast_confidence` |
| reliability_score | `reliability_score` |
| risk_score | `risk_score` |
| primary_reason | `primary_reason` |
| risk_warning | `risk_warning` |
| evidence_status | `evidence_status` |
| source_run_id | `run_id` |
| calculated_at_utc | `calculated_at_utc` |

Selection rule:

Export all rows belonging to the latest successful Module 42 run.

### 5. Risk metrics

Universal dataset:

`risk_metrics.csv`

Primary source:

`m36_asset_risk`

Source fields:

| Universal field | Crypto source |
|---|---|
| asset_id | `asset_id` |
| observation_date | `observation_date` |
| annualized_volatility_pct | `annualized_volatility_pct` |
| var_95_pct | `var_95_pct` |
| cvar_95_pct | `cvar_95_pct` |
| max_drawdown_365d_pct | `max_drawdown_365d_pct` |
| liquidity_score | `liquidity_score` |
| marginal_risk_contribution_pct | `marginal_risk_contribution_pct` |
| risk_status | `risk_status` |
| target_weight | `target_weight` |
| source_run_id | `run_id` |
| calculated_at_utc | `calculated_at_utc` |

Selection rule:

Export all rows belonging to the latest successful Module 36 run.

### 6. Allocation targets

Universal dataset:

`allocation_targets.csv`

Primary source:

`m36_risk_adjusted_allocations`

Source fields:

| Universal field | Crypto source |
|---|---|
| asset_id | `asset_id` |
| observation_date | `observation_date` |
| original_weight | `original_weight` |
| volatility_adjusted_weight | `volatility_adjusted_weight` |
| target_weight | `final_risk_weight` |
| risk_reduction_pct | `risk_reduction_pct` |
| action | `action` |
| source_run_id | `run_id` |
| calculated_at_utc | `calculated_at_utc` |

Selection rule:

Export all rows belonging to the latest successful Module 36 run.

Important:

These are analytical target allocations. They are not actual portfolio
positions or holdings.

### 7. Price projections

Universal dataset:

`price_projections.csv`

Primary source:

`m42_price_projections`

Source fields:

| Universal field | Crypto source |
|---|---|
| asset_id | `asset_id` |
| recommendation_date | `recommendation_date` |
| projection_date | `projection_date` |
| horizon_label | `horizon_label` |
| horizon_days | `horizon_days` |
| current_price | `current_price` |
| bear_price | `bear_price` |
| median_price | `median_price` |
| bull_price | `bull_price` |
| bear_return_pct | `bear_return_pct` |
| median_return_pct | `median_return_pct` |
| bull_return_pct | `bull_return_pct` |
| annualized_median_return_pct | `annualized_median_return_pct` |
| confidence | `projection_confidence` |
| methodology | `projection_method` |
| evidence_status | `evidence_status` |
| source_run_id | `run_id` |
| calculated_at_utc | `calculated_at_utc` |

Selection rule:

Export all rows belonging to the latest successful Module 42 run.

### 8. Platform status

Universal dataset:

`platform_status.csv`

Primary sources:

- `module36_runs`
- `module39_runs`
- `module42_runs`
- post-remediation certification JSON

Required fields:

| Universal field | Source |
|---|---|
| platform_id | Constant: `crypto` |
| platform_name | Constant: `Crypto Intelligence Platform` |
| platform_status | Constant: `RESEARCH_ONLY` |
| certification_status | Certification JSON `status` |
| source_commit | Constant: `daced44` |
| source_tag | Constant: `crypto-post-remediation-replay-certified` |
| module36_status | Latest `module36_runs.status` |
| module39_status | Latest `module39_runs.status` |
| module42_status | Latest `module42_runs.status` |
| evidence_status | Latest Module 42 `evidence_status` |
| generated_at_utc | Adapter execution timestamp |

### 9. Portfolio positions

Universal dataset:

`portfolio_positions.csv`

Source:

Separate user-maintained holdings input.

No source table in the Crypto Intelligence Platform contains sufficient
actual ownership data.

Required input fields:

| Field | Description |
|---|---|
| account_id | Universal investment account |
| asset_id | Crypto asset identifier |
| quantity | Actual units owned |
| cost_basis_total | Total cost basis |
| average_cost | Average acquisition price |
| acquisition_date | Optional first or representative acquisition date |
| custodian | Exchange or wallet |
| position_status | `OPEN` or `CLOSED` |
| as_of_date | Holdings effective date |
| source | Manual, exchange export, or wallet import |

The adapter must not create position records when no holdings input is
provided. It must instead emit an empty valid file and declare
`holdings_available=false` in the export manifest.

## Export package contents

The initial adapter package will conform to Universal Data Contract
version `1.0.0` and contain:

- `asset_master.csv`
- `forecasts.csv`
- `platform_status.csv`
- `portfolio_positions.csv`
- `recommendations.csv`
- `risk_metrics.csv`
- `export_manifest.csv`
- `package_summary.json`
- `validation_report.json`

`market_prices`, analytical allocation targets, and Module 42 price
projections remain source datasets. They will be transformed into the
existing universal contracts rather than published as standalone files.

The controlling compatibility determination is documented in:

`CRYPTO_UNIVERSAL_COMPATIBILITY_DECISION.md`

## Lineage requirements

Every exported analytical record must include:

- source platform,
- source table,
- source run ID where available,
- source observation or forecast date,
- adapter version,
- source commit,
- and export timestamp.

## Approval decision

The source inspection is sufficient to proceed with adapter
implementation.

The holdings contract remains intentionally separate from analytical
allocations.