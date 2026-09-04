# Bitcoin 36-Month Scenario-Conditioned Modifier Design V2

## Status

`BITCOIN_36M_SCENARIO_CONDITIONED_MODIFIER_DESIGN_V2`

Research methodology only.

This design corrects the V1 semantic implementation defect identified
by the governed V1 semantic audit.

`V2_FINAL_STRATEGIC_FORECAST_CALCULATED=FALSE`

`V2_PRODUCTION_PROMOTION_AUTHORIZED=FALSE`

---

## V1 Failure Being Corrected

V1 applied the same current supportive trend/risk and macro/liquidity
modifier to:

- bear;
- base;
- bull.

That implementation preserved arithmetic ordering but failed the
pre-existing strategic bear semantic contract.

The strategic bear must represent:

`A_DEFENSIBLE_ADVERSE_LONG_DURATION_OUTCOME_UNDER_MATERIALLY_UNFAVORABLE_STRATEGIC_EVIDENCE`

Therefore:

`CURRENT_STATE_MODIFIER_IS_NOT_EQUIVALENT_TO_SCENARIO_CONDITIONED_MODIFIER`

---

## Frozen Structural Methodology

The V2 correction does NOT reopen structural weighting.

The following remain unchanged:

| Evidence family | Weight |
|---|---:|
| Bitcoin cycle | 0.50 |
| Native Module 42 | 0.30 |
| Trend/risk | 0.10 |
| Macro/liquidity | 0.10 |
| Valuation/on-chain | 0.00 |

Within the structural 0.80 allocation:

- cycle share = 0.625
- native Module 42 share = 0.375

`STRUCTURAL_WEIGHTS_CHANGED_FROM_V1=FALSE`

`CYCLE_METHOD_CHANGED_FROM_V1=FALSE`

`MODULE42_CHANGED_FROM_V1=FALSE`

---

## Scenario Conditioning Principle

Trend/risk and macro/liquidity are strategic scenario modifiers.

They must be conditioned on the scenario being represented.

Therefore:

### Bear

The bear scenario receives materially unfavorable realizations of
both corroborating channels.

### Base

The base scenario receives the actual governed current-state
trend/risk and macro/liquidity measurements.

### Bull

The bull scenario receives materially favorable realizations of
both corroborating channels.

The bear and bull scenario assumptions are symmetric.

No scenario assumption may be selected after viewing V2 prices.

---

## Modifier Bounds

Existing family bounds remain unchanged.

Trend/risk maximum absolute adjustment:

`10 percentage points`

Macro/liquidity maximum absolute adjustment:

`10 percentage points`

Combined absolute stress bound:

`20 percentage points`

The standard bear and bull scenarios do NOT consume the absolute
channel extremes.

Full +/-10 percentage-point channel realizations are reserved for
separate stress/extreme diagnostics.

---

## Standard Scenario Severity

Predeclared standard scenario severity:

`0.75`

Rationale:

- bear and bull should represent materially adverse/favorable states;
- they should not equal absolute stress extremes;
- 75% of the bounded channel range creates a strong standard
  scenario while reserving 100% for extreme diagnostics;
- the rule is symmetric;
- the rule is frozen before V2 prices are calculated.

`SCENARIO_SEVERITY_SELECTED_AFTER_VIEWING_V2_PRICES=FALSE`

---

## Bear Scenario Modifier

Trend/risk realization:

`-0.75 normalized`

Trend/risk return adjustment:

`-7.5 percentage points`

Macro/liquidity realization:

`-0.75 normalized`

Macro/liquidity return adjustment:

`-7.5 percentage points`

Combined standard bear corroborating adjustment:

`-15.0 percentage points`

This adjustment is applied to the already-governed structural bear
return.

The bear scenario is therefore explicitly conditioned on materially
unfavorable strategic corroborating evidence.

---

## Base Scenario Modifier

The base scenario uses the ACTUAL governed current state.

Trend/risk:

Use the deterministic current trend/risk modifier formula already
declared in V1.

Macro/liquidity:

Use the deterministic current macro modifier formula already declared
in V1.

No scenario severity override is applied to the base case.

`BASE_USES_CURRENT_GOVERNED_STATE=TRUE`

This preserves the information content of the current market and
macro evidence.

---

## Bull Scenario Modifier

Trend/risk realization:

`+0.75 normalized`

Trend/risk return adjustment:

`+7.5 percentage points`

Macro/liquidity realization:

`+0.75 normalized`

Macro/liquidity return adjustment:

`+7.5 percentage points`

Combined standard bull corroborating adjustment:

`+15.0 percentage points`

This adjustment is applied to the already-governed structural bull
return.

The bull scenario is therefore explicitly conditioned on materially
favorable strategic corroborating evidence.

---

## Extreme Corroborating Stress Diagnostics

Separate diagnostics may later report:

### Adverse stress

Trend/risk:

`-10.0 percentage points`

Macro/liquidity:

`-10.0 percentage points`

Combined:

`-20.0 percentage points`

### Favorable extreme

Trend/risk:

`+10.0 percentage points`

Macro/liquidity:

`+10.0 percentage points`

Combined:

`+20.0 percentage points`

These are NOT standard bear/bull outcomes.

They are diagnostic boundaries only.

---

## Structural Scenario Inputs

V2 preserves the V1 structural calculations:

### Structural Bear

Blend:

- cycle P25 return;
- native Module 42 bear return.

### Structural Base

Blend:

- cycle P50 return;
- native Module 42 median return.

### Structural Bull

Blend:

- cycle P75 return;
- native Module 42 bull return.

P90 remains a separate:

`EXTREME_UPSIDE_DIAGNOSTIC`

and is not substituted for the standard bull scenario.

---

## V2 Final Return Formulas

### Bear

`V2_BEAR_RETURN = STRUCTURAL_BEAR_RETURN - 0.15`

### Base

`V2_BASE_RETURN = STRUCTURAL_BASE_RETURN + CURRENT_TREND_ADJUSTMENT + CURRENT_MACRO_ADJUSTMENT`

### Bull

`V2_BULL_RETURN = STRUCTURAL_BULL_RETURN + 0.15`

No V2 prices are calculated in this design artifact.

---

## Required Semantic Checks

The future V2 calculation must fail closed unless:

`bear_return < base_return < bull_return`

and:

`bear_price < base_price < bull_price`

Additionally:

`BEAR_SCENARIO_CONDITIONED_ON_ADVERSE_EVIDENCE=TRUE`

`BASE_SCENARIO_CONDITIONED_ON_CURRENT_EVIDENCE=TRUE`

`BULL_SCENARIO_CONDITIONED_ON_FAVORABLE_EVIDENCE=TRUE`

A bear outcome is NOT required to be below the current Bitcoin price
as an arbitrary numeric rule.

Semantic validity comes from adverse scenario conditioning, not from
forcing a negative return.

However, if the bear remains positive after adverse conditioning,
that fact must be explicitly surfaced and reviewed.

`POSITIVE_BEAR_REQUIRES_EXPLICIT_REVIEW=TRUE`

No automatic price replacement is permitted.

---

## Strategic Confidence

V2 retains the existing strategic-confidence methodology unless a
separate governance gate changes it.

The semantic defect identified in V1 concerned scenario conditioning,
not confidence construction.

`STRATEGIC_CONFIDENCE_METHOD_CHANGED=FALSE`

---

## Prior High Review

The previous-cycle/running-high reference remains a plausibility
diagnostic only.

It is not:

- a floor;
- a target;
- a forced bull minimum.

`PRIOR_HIGH_USED_AS_PRICE_FLOOR=FALSE`

---

## Missing Valuation / On-Chain Evidence

Valuation/on-chain remains:

`MISSING`

Weight remains:

`0.00`

No synthetic evidence may be introduced.

---

## V1 Preservation

V1 remains permanently preserved as:

`FAILED_RESEARCH_IMPLEMENTATION`

Its forecast file and semantic audit must not be modified or deleted.

`V1_OVERWRITE_AUTHORIZED=FALSE`

`V1_DELETE_AUTHORIZED=FALSE`

---

## Prohibited Actions

V2 design does NOT authorize:

- changing 50/30/10/10 weights;
- changing cycle transformation methodology;
- changing native Module 42;
- desired-price tuning;
- selecting scenario severity after viewing V2 prices;
- using prior ATH as a price floor;
- folding P90 into standard bull;
- synthesizing valuation/on-chain evidence;
- reopening recommendation-policy validation;
- reopening V3/V4 validation;
- database writes;
- autonomous execution;
- production promotion.

---

## Authorization

`V2_SCENARIO_CONDITIONING_DESIGN_FROZEN=TRUE`

`V2_FORECAST_CALCULATION_AUTHORIZED=TRUE`

`V2_PRODUCTION_PROMOTION_AUTHORIZED=FALSE`

`DATABASE_WRITE_AUTHORIZED=FALSE`

Next gate:

`CALCULATE_BTC_36M_SCENARIO_CONDITIONED_STRATEGIC_FORECAST_V2`
