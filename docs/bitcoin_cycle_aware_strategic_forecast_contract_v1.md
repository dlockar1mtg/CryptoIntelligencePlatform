# Bitcoin Cycle-Aware Strategic Forecast Contract V1

## Contract ID

`BITCOIN_CYCLE_AWARE_STRATEGIC_FORECAST_CONTRACT_V1`

## Purpose

This contract governs creation of a separate Bitcoin long-duration
strategic forecast layer that incorporates the already-authorized
Bitcoin four-year-cycle evidence without overwriting or relabeling
the existing Module 42 statistical scenario model.

The intended strategic horizon is approximately three years.

This contract is Bitcoin-specific.

It does not automatically extend to Ethereum or other crypto assets.

---

## Existing statistical authority

The existing Module 42 long-range forecast remains preserved as:

`BTC_NATIVE_LONG_RANGE_STATISTICAL_SCENARIO`

The current July 28, 2026 M36 authority is:

- current price: approximately $63,656;
- projection date: 2029-07-28;
- statistical bear: approximately $24,399;
- statistical median: approximately $54,098;
- statistical bull: approximately $119,945;
- statistical bull return: approximately +88.4%;
- projection method: `LONG_RANGE_SCENARIO_MODEL`;
- evidence status: `SCENARIO_ONLY`;
- projection confidence: approximately 0.069.

These values must not be silently replaced, rewritten, or presented
as if they were produced by the Bitcoin cycle model.

The native statistical output remains useful as one evidence source.

---

## Architecture finding

The current Module 42 long-range scenario model is not explicitly
Bitcoin-cycle-aware.

Its long-range return estimate is primarily constructed from:

1. annualized shorter-horizon forecast information;
2. historical annual return;
3. a neutral long-range prior;
4. generic regime adjustment;
5. historical volatility used to create scenario width.

The governed four-year-cycle forward-return distribution is not an
explicit input to the M36 price scenario.

Therefore:

`MODULE42_M36_IS_NOT_AUTHORITATIVE_BTC_CYCLE_AWARE_STRATEGIC_FORECAST`

---

## New strategic authority

A separate output family is authorized for implementation research:

`BTC_CYCLE_AWARE_STRATEGIC_SCENARIO`

It must remain distinguishable from:

`BTC_NATIVE_LONG_RANGE_STATISTICAL_SCENARIO`

The dashboard and UIP package must never present the two as if they
were the same model.

---

## Required strategic outputs

At minimum, the Bitcoin strategic layer must produce:

- `strategic_bear_price`
- `strategic_base_price`
- `strategic_bull_price`
- `strategic_bear_return_pct`
- `strategic_base_return_pct`
- `strategic_bull_return_pct`
- `strategic_horizon_date`
- `strategic_confidence`
- `strategic_evidence_status`
- `cycle_phase`
- `cycle_evidence_weight`
- `native_model_weight`
- `macro_liquidity_weight`
- `trend_risk_weight`
- `valuation_onchain_weight` when available
- explicit missing-evidence flags
- human-readable rationale

The layer must also retain the native Module 42 M36 bear/median/bull
values separately for comparison.

---

## Strategic evidence categories

The Bitcoin strategic forecast may use the following governed evidence.

### 1. Native forecast evidence

Permitted inputs include:

- native short- and medium-horizon forecasts;
- validated forecast confidence;
- forecast reliability;
- native M36 scenario outputs as contextual evidence.

Short-horizon model weakness may lower strategic confidence or alter
the base case.

It must not automatically erase long-duration cycle evidence.

### 2. Bitcoin cycle evidence

Permitted inputs include:

- most recent observed halving;
- days since halving;
- estimated distance to next halving with uncertainty;
- normalized cycle position;
- descriptive cycle phase;
- drawdown from running high;
- recovery from observed cycle trough;
- return since halving;
- exact historical 1-year, 2-year and approximately 3-year returns
  from comparable governed cycle phases;
- expansion -> reset -> recovery structure from the preserved
  extended-history study.

The incomplete 2024 -> 2028 cycle may not be counted as a fourth
completed historical cycle.

### 3. Trend and risk evidence

The layer must consider available:

- medium-duration trend;
- long-duration trend;
- momentum;
- realized volatility;
- drawdown state;
- risk regime.

### 4. Macro and liquidity evidence

Available governed macro/liquidity evidence must be considered when
current enough for the strategic observation date.

Missing macro evidence remains missing.

### 5. Valuation and on-chain evidence

Governed point-in-time-safe valuation and on-chain evidence may be used
when available.

Missing evidence must not be converted to a synthetic neutral value.

---

## Small-sample governance

The four-year-cycle historical study contains only three independent
completed halving intervals.

Daily and monthly anchors must not be treated as independent completed
cycles.

Historical monthly forward-return observations are useful for
estimating within-cycle distributions, but confidence must reflect the
three-cycle independent-history limitation.

Therefore:

`BITCOIN_CYCLE_SAMPLE_WARNING=TRUE`

---

## Diminishing-return requirement

Historical Bitcoin returns may not be copied directly into the current
strategic forecast.

A governed diminishing-return transformation is mandatory.

The transformation must be determined before prospective outcomes are
used to judge its performance.

It must not be optimized retrospectively to force a desired Bitcoin
price.

Candidate transformations may consider:

- logarithmic shrinkage;
- market-cap-aware shrinkage;
- previous-cycle peak multiple decay;
- percentile shrinkage;
- weighted combinations of these methods.

No single arbitrary percentage multiplier may be promoted merely
because it produces an intuitively attractive forecast.

---

## Prior-cycle-high plausibility rule

The prior observed Bitcoin cycle high is a plausibility reference,
not a mandatory price floor.

A strategic bull scenario may be below the prior cycle high only if
the model records an explicit evidence-supported reason.

Examples may include:

- severe adverse macro/liquidity regime;
- structural adoption deterioration;
- extreme regulatory or market impairment;
- persistent negative long-duration trend;
- valuation evidence incompatible with a new-cycle expansion;
- other governed contradictory strategic evidence.

Absence of such evidence should produce:

`BULL_BELOW_PRIOR_CYCLE_HIGH_REQUIRES_REVIEW=TRUE`

This rule does not require Bitcoin to make a new all-time high.

---

## Horizon / cycle-position rule

For a strategic forecast whose endpoint intersects an expected
post-halving expansion window, the cycle evidence must be explicitly
represented.

For the July 2026 approximately 36-month forecast, the July 2029
endpoint lies after the expected 2028 halving window.

The model therefore may not label the forecast `CYCLE_AWARE` unless
the expected halving transition and post-halving historical structure
are included in the strategic evidence set.

Calendar timing alone may not force a bullish result.

---

## Scenario semantics

### Strategic bear

The bear scenario represents a defensible adverse long-duration
outcome under materially unfavorable strategic evidence.

It must not simply equal the native statistical lower-volatility band.

### Strategic base

The base scenario represents the central long-duration outcome after
blending:

- native predictive information;
- cycle-position evidence;
- historical cycle forward returns;
- trend/risk;
- macro/liquidity;
- valuation/on-chain evidence when available.

### Strategic bull

The bull scenario represents a favorable but still evidence-supported
realization of the strategic regime.

It is not merely:

`base + fixed percentage`

or:

`native median + volatility`

The bull case must reflect favorable strategic evidence across multiple
categories and must remain subject to diminishing-return controls.

### Extreme upside

Extreme historical-cycle outcomes must not be folded into the normal
bull estimate.

If retained, they must be shown separately as:

`EXTREME_UPSIDE_DIAGNOSTIC`

and must not be used as the normal UIP bull forecast.

---

## Evidence-weighting requirements

No single evidence category may receive 100% authority.

Cycle evidence may materially influence the long-duration Bitcoin
scenario, but it must be corroborated.

A future implementation must explicitly record the effective weights
or contribution strengths for:

- native predictive evidence;
- Bitcoin cycle evidence;
- trend/risk evidence;
- macro/liquidity evidence;
- valuation/on-chain evidence.

If an evidence category is missing, the implementation must record
that it is missing rather than silently redistributing its weight
unless such redistribution is separately governed.

---

## Confidence semantics

Strategic confidence is distinct from Module 42 projection confidence.

The current Module 42 M36 confidence must not be relabeled as strategic
confidence.

Strategic confidence should account for:

- three-cycle historical sample limitation;
- cycle comparability;
- agreement/disagreement between native and cycle evidence;
- macro evidence quality;
- trend/risk consistency;
- valuation/on-chain availability;
- horizon uncertainty;
- next-halving timing uncertainty.

---

## Required comparison surface

For Bitcoin, the UIP/dashboard should ultimately show both:

### Native statistical scenario

- native bear;
- native median;
- native bull;
- native confidence;
- native method.

### Cycle-aware strategic scenario

- strategic bear;
- strategic base;
- strategic bull;
- strategic confidence;
- cycle phase;
- major evidence contributions;
- rationale.

This prevents users from confusing statistical extrapolation with
long-duration strategic interpretation.

---

## Current diagnostic evidence

The preserved design audit found:

- current Module 42 M36 bull: approximately $119,945;
- current M36 confidence: approximately 6.9%;
- current M36 evidence status: `SCENARIO_ONLY`;
- current M36 bull is below the approximately $126,000 prior-cycle-high
  reference;
- historical cycle evidence contains 68 exact approximately three-year
  monthly-anchor outcomes across the two strategically relevant phase
  groups;
- independent completed-cycle count remains only 3.

Historical combined approximately three-year return percentiles were
observed near:

- P10: +102%;
- P25: +144%;
- P50: +431%;
- P75: +1,020%;
- P90: +2,681%.

These historical percentages are descriptive evidence only.

They are not approved production return assumptions.

---

## Diagnostic diminishing-return examples

The design audit tested deliberately severe shrinkage of the historical
distribution.

At 25% historical magnitude:

- lower diagnostic price: approximately $86.5K;
- center diagnostic price: approximately $132.2K;
- upper diagnostic price: approximately $226.0K.

At 35% historical magnitude:

- lower diagnostic price: approximately $95.7K;
- center diagnostic price: approximately $159.6K;
- upper diagnostic price: approximately $291.0K.

At 45% historical magnitude:

- lower diagnostic price: approximately $104.8K;
- center diagnostic price: approximately $187.0K;
- upper diagnostic price: approximately $355.9K.

These are not production scenarios.

They demonstrate that the current native $119.9K bull case occupies a
very conservative position relative to even heavily shrunk historical
cycle evidence.

---

## Prohibited implementation behavior

The implementation may not:

- overwrite Module 42 historical projections;
- call the native M36 scenario cycle-aware when it is not;
- set the strategic bull manually to a desired dollar amount;
- force the bull above the prior all-time high;
- assume 2029 must be bullish;
- assume the next cycle must reproduce any prior cycle;
- use calendar year alone as a forecast;
- treat monthly anchors as independent completed cycles;
- optimize shrinkage after seeing future outcomes;
- use future data unavailable at the forecast date;
- replace missing evidence with synthetic neutral values;
- authorize autonomous execution;
- reopen V3 or V4 model selection;
- reopen the closed BTC/ETH recommendation-policy validation.

---

## Implementation sequence

The governed implementation sequence is:

1. inventory currently available cycle, macro, trend/risk, valuation
   and native-model evidence for the forecast date;
2. define candidate diminishing-return transformations;
3. evaluate those transformations only against historical completed
   cycles using a predeclared methodology;
4. select or ensemble a transformation based on robustness rather
   than desired output price;
5. implement the strategic forecast as a separate output authority;
6. validate scenario ordering and evidence lineage;
7. compare strategic vs native outputs;
8. only then consider UIP/dashboard promotion.

---

## Production authority

This contract authorizes implementation research only.

It does not authorize changing the production/dashboard Bitcoin
strategic forecast.

`BTC_CYCLE_AWARE_STRATEGIC_FORECAST_IMPLEMENTATION_RESEARCH_AUTHORIZED=TRUE`

`BTC_CYCLE_AWARE_STRATEGIC_FORECAST_PRODUCTION_PROMOTION_AUTHORIZED=FALSE`

`MODULE42_NATIVE_FORECAST_CHANGED=FALSE`

`AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE`

---

## Next gate

`DESIGN_AND_VALIDATE_BTC_DIMINISHING_RETURN_TRANSFORMATION`
