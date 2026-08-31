# Bitcoin 36-Month Strategic Forecast Blend Design V1

## Status

`BITCOIN_36M_STRATEGIC_FORECAST_BLEND_DESIGN_V1`

Research methodology only.

This design is frozen before calculation of the final strategic
bear/base/bull forecast.

`FINAL_STRATEGIC_FORECAST_CALCULATED=FALSE`

`PRODUCTION_FORECAST_CHANGE_AUTHORIZED=FALSE`

`MODULE42_NATIVE_FORECAST_CHANGED=FALSE`

---

## Objective

Construct a Bitcoin-specific 36-month strategic scenario that
integrates:

1. Bitcoin four-year-cycle evidence.
2. Native Module 42 long-range statistical evidence.
3. Current trend/risk evidence.
4. Current macro/liquidity evidence.

Valuation/on-chain evidence remains explicitly unavailable and is
not synthesized.

---

## Strategic Operating Date

Strategic operating date:

`2026-08-28`

Current governed Bitcoin price anchor:

`79408.00 USD`

The final strategic scenario MUST be anchored to the current governed
operating-date Bitcoin price, not the older July 28 Module 42 current
price.

The validated cycle component therefore contributes RETURNS, not its
older July 28 absolute price levels.

---

## Evidence Family Roles

### 1. Bitcoin Cycle Evidence

Role:

`PRIMARY_LONG_HORIZON_STRUCTURAL_EVIDENCE`

Fixed family weight:

`0.50`

Inputs:

- cycle-component lower return
- cycle-component center return
- cycle-component upper return
- P90 extreme upside diagnostic remains separate

The cycle family may materially influence the 36-month strategic
forecast because the horizon spans the expected 2028 halving
transition and subsequent post-halving period.

The cycle family is NOT deterministic calendar authority.

The historical sample remains only three completed cycles.

`BITCOIN_CYCLE_SAMPLE_WARNING=TRUE`

---

### 2. Native Module 42

Role:

`INDEPENDENT_LONG_RANGE_STATISTICAL_ANCHOR`

Fixed family weight:

`0.30`

Module 42 remains unchanged and independently visible.

Its native bear/median/bull absolute prices must first be converted
to returns relative to the Module 42 native current-price anchor.

Those native scenario returns may then be blended with the
cycle-component returns.

The native scenario itself is never overwritten.

`MODULE42_NATIVE_FORECAST_CHANGED=FALSE`

---

### 3. Trend / Risk

Role:

`BOUNDED_CURRENT_STATE_MODIFIER`

Fixed family weight:

`0.10`

Trend/risk does NOT create a standalone 36-month price target.

It modifies the blended long-horizon return distribution only within
a bounded range.

Maximum absolute return adjustment attributable to trend/risk:

`10 percentage points`

Trend/risk adjustment is symmetric and bounded:

- strongly adverse state: as low as -10 percentage points
- neutral state: 0 percentage points
- strongly supportive state: as high as +10 percentage points

The exact normalized modifier must be calculated deterministically
from the already-governed current trend/risk measurements.

No post-hoc tuning is permitted.

---

### 4. Macro / Liquidity

Role:

`BOUNDED_STRATEGIC_REGIME_MODIFIER`

Fixed family weight:

`0.10`

Current governed macro regime:

`SUPPORTIVE`

Current governed macro score:

approximately `68.1682 / 100`

Macro/liquidity does NOT create a standalone 36-month price target.

Maximum absolute return adjustment attributable to macro/liquidity:

`10 percentage points`

Normalize macro score around neutral 50:

`normalized_macro = (macro_score - 50) / 50`

Clamp normalized macro to:

`[-1.0, +1.0]`

Macro return adjustment:

`normalized_macro * 10 percentage points`

Thus macro evidence is bounded and cannot dominate the long-horizon
cycle/native forecast.

---

## Fixed Evidence Weights

| Evidence family | Weight |
|---|---:|
| Bitcoin cycle | 0.50 |
| Native Module 42 | 0.30 |
| Trend/risk | 0.10 |
| Macro/liquidity | 0.10 |
| Valuation/on-chain | 0.00 |

Weights are fixed before strategic forecast calculation.

`WEIGHTS_OPTIMIZED_AFTER_SEEING_OUTPUT=FALSE`

`DESIRED_PRICE_TARGET_USED_IN_WEIGHT_SELECTION=FALSE`

---

## Long-Horizon Scenario Construction

### Step A — Cycle Returns

Use the already-governed cycle-component returns:

- lower = cycle P25
- center = cycle P50
- upper = cycle P75

P90 remains:

`EXTREME_UPSIDE_DIAGNOSTIC`

and is not part of the standard bull forecast.

---

### Step B — Native Returns

Convert Module 42:

- bear price
- median price
- bull price

to returns relative to the Module 42 native current price.

This preserves Module 42 scenario geometry while separating it from
its stale July 28 price anchor.

---

### Step C — Structural Blend

For each scenario:

`structural_return =`

`(0.625 * cycle_return) + (0.375 * native_return)`

Why 0.625 / 0.375?

The total structural allocation is 0.80.

Cycle has 0.50 total weight and native has 0.30.

Within the structural component:

`0.50 / 0.80 = 0.625`

`0.30 / 0.80 = 0.375`

---

## Current-State Modifiers

Trend/risk and macro/liquidity jointly account for the remaining
0.20 evidence allocation.

They affect returns additively after the structural blend.

The total combined adjustment MUST remain bounded to:

`[-20 percentage points, +20 percentage points]`

Neither modifier may independently exceed:

`10 percentage points`

This prevents short-term evidence from overwhelming a 36-month
Bitcoin forecast.

---

## Scenario Ordering

The final strategic output must satisfy:

`bear_return < base_return < bull_return`

and therefore:

`bear_price < base_price < bull_price`

If ordering fails, the calculation is invalid and must stop.

No manual reordering is permitted.

---

## Prior Cycle High Plausibility Review

Prior cycle high is a plausibility reference only.

It is NOT:

- a price floor
- a mandatory bull minimum
- a target
- a deterministic recurrence assumption

However:

`BULL_BELOW_PRIOR_CYCLE_HIGH_REQUIRES_REVIEW=TRUE`

A bull result below the previous cycle high must trigger explicit
review and rationale, not automatic replacement.

---

## Current Price Re-Anchoring

Final prices are calculated from the governed August 28 current
Bitcoin authority:

`79408.00 USD`

Formula:

`strategic_price = current_price * (1 + strategic_return)`

The previously generated cycle-component absolute prices based on
the July 28 `$63,656` anchor are NOT used directly.

---

## Strategic Confidence

Strategic confidence is distinct from Module 42 confidence.

It must incorporate:

- small completed-cycle sample penalty
- native Module 42 evidence quality
- current trend/risk availability
- current macro availability
- valuation/on-chain missing flag

Confidence must remain bounded:

`0.00 <= strategic_confidence <= 1.00`

No confidence value is assigned in this design step.

The confidence formula must be declared before final forecast
production.

---

## Missing Valuation / On-Chain Evidence

`VALUATION_ONCHAIN_STATUS=MISSING`

`VALUATION_ONCHAIN_WEIGHT=0.00`

Missing evidence is not synthesized.

Existing weights are not post-hoc optimized because this category is
missing.

---

## Output Contract for Next Gate

The subsequent forecast-calculation artifact must report:

- strategic operating date
- current Bitcoin anchor price
- horizon date
- strategic bear price
- strategic base price
- strategic bull price
- bear/base/bull returns
- cycle returns
- native returns
- structural blended returns
- trend modifier
- macro modifier
- evidence-family weights
- strategic confidence
- cycle sample warning
- valuation/on-chain missing flag
- prior-cycle-high plausibility review
- native Module 42 comparison
- P90 extreme-upside diagnostic separately
- rationale
- all governance boundaries

---

## Prohibited Actions

The following remain prohibited:

- desired-price forcing
- selecting weights after viewing prices
- treating prior ATH as a floor
- treating cycle calendar as deterministic
- treating 68 monthly observations as 68 independent cycles
- synthesizing missing valuation/on-chain evidence
- changing native Module 42
- reopening recommendation-policy validation
- reopening V3/V4 validation lanes
- autonomous execution
- production promotion

---

## Authorization

`BTC_STRATEGIC_BLEND_DESIGN_FROZEN=TRUE`

`BTC_STRATEGIC_FORECAST_CALCULATION_AUTHORIZED=TRUE`

`BTC_STRATEGIC_FORECAST_PRODUCTION_PROMOTION_AUTHORIZED=FALSE`

`MODULE42_NATIVE_FORECAST_CHANGED=FALSE`

`DATABASE_WRITE_AUTHORIZED=FALSE`

Next gate:

`CALCULATE_BTC_36M_CYCLE_AWARE_STRATEGIC_FORECAST`
