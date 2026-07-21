# Crypto Universal Contract Compatibility Decision

## Decision

**DIRECT_COMPATIBILITY**

The Crypto Intelligence Platform can publish an initial Universal
Investment Platform package using the existing Universal Data Contract
version `1.0.0`.

No Universal Investment Platform contract extension is required for
the initial crypto integration.

## Certified crypto source

- Source repository: Crypto Intelligence Platform
- Certified source commit: `daced44`
- Certification tag: `crypto-post-remediation-replay-certified`
- Adapter branch: `integration/crypto-universal-export-adapter`
- Platform status: `RESEARCH ONLY`

## Canonical Universal Investment Platform contracts

The initial crypto package will use these existing contracts:

1. `asset_master`
2. `forecasts`
3. `platform_status`
4. `portfolio_positions`
5. `recommendations`
6. `risk_metrics`
7. `export_manifest`

Each dataset must conform exactly to the Universal Investment Platform
version `1.0.0` CSV and JSON schema definitions.

## Crypto-to-universal consolidation

### Market prices

The Universal Investment Platform does not currently define a
standalone `market_prices` package contract.

Latest crypto market prices will instead be used as:

- `forecasts.current_value`
- `portfolio_positions.unit_value`, when holdings are available
- the basis for calculating `portfolio_positions.position_value`

No standalone `market_prices.csv` will be published in the initial
package.

### Allocation targets

The Universal Investment Platform does not currently define a
standalone `allocation_targets` package contract.

Crypto analytical target allocations will be represented through:

- `recommendations.target_weight`
- `recommendations.minimum_weight`
- `recommendations.maximum_weight`

Target allocations must never be interpreted as actual holdings.

No standalone `allocation_targets.csv` will be published in the initial
package.

### Price projections

The Universal Investment Platform does not currently define a
standalone `price_projections` package contract.

Module 42 price projections will be transformed into universal
`forecasts.csv` records using:

- `current_value`
- `forecast_value_base`
- `forecast_value_bear`
- `forecast_value_bull`
- `expected_total_return`
- `expected_cagr`
- `forecast_confidence`
- `forecast_method`
- `scenario_name`

Module 39 calibrated forecasts may also produce short-horizon universal
forecast records.

No standalone `price_projections.csv` will be published in the initial
package.

## Portfolio positions

The crypto source database does not contain actual user ownership
records.

When no validated holdings input is supplied:

- `portfolio_positions.csv` will contain the canonical header only,
- its record count will be zero,
- the export manifest will mark the file valid,
- and the validation report will record
  `holdings_available=false`.

The adapter must not infer owned quantities or position values from:

- current portfolio weights,
- target weights,
- recommendation target units,
- model allocations,
- or risk-adjusted allocations.

## Universal field conversions

### Identifiers

Crypto platform asset IDs will be converted as follows:

- `bitcoin` becomes `crypto:bitcoin`
- `ethereum` becomes `crypto:ethereum`
- all other assets follow `crypto:<platform_asset_id>`

### Percentages and decimals

The crypto database contains a mixture of percentage-point values and
decimal weights.

The adapter must normalize values according to the universal contract:

- `annualized_volatility_pct / 100`
- `max_drawdown_365d_pct / 100`
- `var_95_pct / 100`
- forecast return percentages divided by `100`
- recommendation target percentages divided by `100`
- existing decimal portfolio weights remain unchanged
- probability fields remain within `0` to `1`
- universal recommendation and risk scores remain within `0` to `100`

### Forecast horizons

Universal forecast horizons are integer months.

Crypto horizons will be converted using documented deterministic
rules:

- 7 days becomes 1 month
- 30 days becomes 1 month
- 90 days becomes 3 months
- 180 days becomes 6 months
- Module 42 `horizon_months` values are rounded to the nearest integer

The exact source horizon remains recoverable through the validation and
lineage evidence.

### Recommendation vocabulary

Crypto-native actions will be preserved in
`platform_native_label`.

The universal `recommendation` field will use a normalized lower-case
vocabulary:

- `BUY` becomes `buy`
- `ACCUMULATE` becomes `accumulate`
- `HOLD` becomes `hold`
- `WAIT` becomes `wait`
- `REDUCE` becomes `reduce`
- `SELL` becomes `sell`

Unknown values must fail validation rather than being silently mapped.

### Risk levels

Crypto risk status values will be normalized to:

- `low`
- `medium`
- `high`
- `extreme`

A documented deterministic mapping must be used when the source status
uses another vocabulary.

## Export package

The initial universal package will contain:

- `asset_master.csv`
- `forecasts.csv`
- `platform_status.csv`
- `portfolio_positions.csv`
- `recommendations.csv`
- `risk_metrics.csv`
- `export_manifest.csv`
- `package_summary.json`
- `validation_report.json`

Only the seven CSV files governed by existing Universal Investment
Platform contracts will appear in the manifest.

## Read-only boundary

The adapter must:

- open the crypto DuckDB database in read-only mode,
- select only successful completed source runs,
- avoid data collection and model execution,
- write only to an isolated export directory,
- avoid direct writes to the Universal Investment Platform,
- preserve source run lineage,
- and calculate checksums after all output files are finalized.

## Conclusion

The initial crypto adapter will conform to Universal Data Contract
version `1.0.0` without changing the Universal Investment Platform
schemas.

Additional standalone contracts may be proposed later through a
separate versioned contract-governance process.