# Crypto Holdings Input

The Crypto Intelligence Platform does not currently maintain an actual
holdings ledger.

The universal export adapter therefore accepts an optional external
holdings file based on:

`crypto_holdings_template.csv`

## Required fields

- `account_id`
- `asset_id`
- `quantity`
- `cost_basis_total`
- `average_cost`
- `acquisition_date`
- `custodian`
- `position_status`
- `as_of_date`
- `source`

## Rules

- Do not enter target allocation percentages as holdings.
- Do not enter recommendation target units as owned units.
- Quantities must represent actual assets owned.
- Cost basis values must be denominated in USD.
- `asset_id` must match the crypto asset registry.
- Closed positions may be included with quantity zero.
- The adapter must validate all holdings records before export.

When no holdings input is supplied, the adapter will produce an empty
valid `portfolio_positions.csv` and record that actual holdings were
not available.