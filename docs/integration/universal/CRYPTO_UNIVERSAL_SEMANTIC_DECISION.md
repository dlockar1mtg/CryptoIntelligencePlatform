# Crypto Universal Semantic Mapping Decision

## Recommendation target weights

The source field:

`m42_asset_recommendations.best_current_portfolio_pct`

is expressed in percentage points of the complete universal portfolio.

The latest validated recommendation set totaled:

`3.9631841680717987`

This represents a combined crypto target of approximately:

`3.963184%`

The universal contract requires decimal portfolio weights. Therefore:

`target_weight = best_current_portfolio_pct / 100`

The corresponding universal total is approximately:

`0.039631841680717987`

No change is required to the recommendation transformation.

## Crypto-sleeve allocation weights

The following Module 36 fields each total approximately `1.0`:

- `original_weight`
- `volatility_adjusted_weight`
- `final_risk_weight`

These fields describe relative allocations within the crypto asset
sleeve. They must not be published directly as whole-portfolio target
weights.

## Universal risk semantics

Module 42 `risk_score` and Module 36 `risk_status` are not one coherent
risk scale.

The initial universal adapter therefore uses Module 36 as the sole
source framework for both:

- `risk_level`
- `risk_score`

Deterministic risk scores are assigned as follows:

- `LOW` -> `25`
- `MODERATE` or `MEDIUM` -> `50`
- `ELEVATED` or `HIGH` -> `75`
- `SEVERE` or `EXTREME` -> `95`

Module 42 `risk_score` remains source analytical evidence but is not
published as the universal `risk_score`.