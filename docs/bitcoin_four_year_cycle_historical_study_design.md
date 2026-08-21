# Bitcoin Four-Year Cycle Historical Study Design

## Study

`BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY_V1`

## Purpose

Quantitatively test the Bitcoin four-year-cycle hypothesis for the UIP Crypto long-duration accumulation mandate before granting the hypothesis any recommendation-policy authority.

The study is descriptive and hypothesis-testing only. It must not alter V4 predictive-model decisions, recommendation thresholds, production policy, existing holdings, or autonomous execution authority.

## Governing investment context

The current governed Crypto mandate treats Bitcoin and Ethereum as long-duration accumulation assets rather than ordinary tactical trading assets.

For new Bitcoin capital, the working investment horizon is approximately three years. Short-term predictive evidence may influence tranche timing, but a short-term negative forecast must not automatically imply selling an existing long-duration Bitcoin position.

The working calendar hypothesis to test is:

- halving year: transition / early expansion;
- first calendar year after halving: expansion / historically plausible cycle-peak zone;
- second calendar year after halving: reset / accumulation-zone hypothesis;
- calendar year immediately before the next halving: recovery / accumulation-to-transition hypothesis.

For the current cycle this corresponds descriptively to:

- 2024: halving year;
- 2025: first post-halving year;
- 2026: second post-halving/reset-year hypothesis;
- 2027: pre-halving/recovery-year hypothesis;
- next halving expected approximately in 2028, with exact future date not hard-coded as an execution trigger.

These are hypotheses, not guaranteed market outcomes.

## Historical halving anchors

The study uses the following historical Bitcoin halving dates as fixed protocol-event anchors:

- 2012-11-28
- 2016-07-09
- 2020-05-11
- 2024-04-20

The 2024 date reflects the actual fourth halving. Future halving dates are not treated as exact until they occur.

## Canonical evidence source

Price evidence must come only from the existing governed DuckDB table:

`canonical_market_daily`

with:

- `asset_id='bitcoin'`
- `observation_date`
- `price_usd`

The database must be opened read-only.

No web prices, interpolated prices, nearest-date substitutions, synthetic values, or reconstructed missing prices may enter the numerical study.

If the canonical database does not cover an early cycle or an exact endpoint, that evidence remains unavailable and coverage must be reported explicitly.

## Evidence class

`HISTORICAL_CANONICAL_PRICE_STUDY_NOT_STRICT_VINTAGE_POINT_IN_TIME`

This study analyzes realized historical prices. It does not establish that a cycle state would have been known with certainty in real time.

## Cycle definitions

Each historical calendar year is classified relative to the most recent halving and the next known historical halving.

Primary phase labels:

- `HALVING_YEAR`
- `POST_HALVING_YEAR_1`
- `POST_HALVING_YEAR_2`
- `PRE_HALVING_YEAR`
- `OTHER_OR_INCOMPLETE`

For completed intervals, the labels correspond to calendar years:

2012 / 2016 / 2020 / 2024 -> `HALVING_YEAR`

2013 / 2017 / 2021 / 2025 -> `POST_HALVING_YEAR_1`

2014 / 2018 / 2022 / 2026 -> `POST_HALVING_YEAR_2`

2015 / 2019 / 2023 / 2027 -> `PRE_HALVING_YEAR`

The current incomplete cycle may be described through the latest canonical observation, but incomplete future outcomes must remain missing.

## Required study questions

### 1. Canonical coverage

Report:

- first Bitcoin observation date;
- last Bitcoin observation date;
- number of unique daily Bitcoin observations;
- missing duplicate/nonpositive-price checks;
- which historical halving cycles and phase-years are represented.

No claim may rely on a phase absent from the canonical data.

### 2. Calendar-phase performance

For each supported calendar year and phase, report:

- first available canonical price in the year;
- last available canonical price in the year;
- calendar-year return;
- minimum price and its date;
- maximum price and its date;
- maximum drawdown from the running historical peak during that year;
- return from the year's first available price to its minimum;
- return from the year's minimum to its last available price.

These are descriptive realized-history statistics and must not be interpreted as ex-ante timing skill.

### 3. Cross-cycle phase consistency

For each primary phase label, aggregate only completed supported historical phase-years and report:

- represented cycle-years;
- observations/cycles represented;
- mean and median calendar-year return;
- positive-year rate;
- mean and median maximum drawdown;
- minimum and maximum phase-year returns.

The study must explicitly report the small number of independent cycles and must not use daily-row count as a substitute for independent-cycle sample size.

### 4. Peak/reset sequence diagnostics

For each sufficiently covered completed halving interval, identify descriptively:

- maximum canonical price after the halving and before the next halving;
- date of that maximum;
- minimum canonical price after that maximum and before the next halving;
- date of that post-peak minimum;
- drawdown from interval peak to subsequent minimum;
- calendar-year phase containing the interval peak;
- calendar-year phase containing the subsequent minimum.

This is a realized-history sequence diagnostic only. It may test whether peaks tended to occur in `POST_HALVING_YEAR_1` and subsequent lows in `POST_HALVING_YEAR_2`; it must not imply those dates were forecastable in advance.

### 5. Forward holding-period returns

For every canonical Bitcoin observation with an exact canonical endpoint, calculate:

- exact 365-calendar-day forward return;
- exact 730-calendar-day forward return;
- exact 1095-calendar-day forward return.

No nearest-date endpoint, interpolation, or synthesized return is allowed.

Aggregate these returns by the origin observation's cycle phase and report:

- eligible origin rows;
- observed exact-endpoint rows;
- missing rows;
- mean forward return;
- median forward return;
- positive-return rate;
- 25th and 75th percentiles;
- worst and best observed forward returns.

Because daily origins overlap heavily, these are descriptive distributions, not independent trials.

### 6. Monthly-anchor robustness

To reduce serial-overlap dominance, construct one deterministic monthly anchor per calendar month: the earliest available canonical Bitcoin observation in that month.

For monthly anchors, repeat exact 365/730/1095-day forward-return summaries by cycle phase.

The runner must not select anchors based on subsequent returns or prices.

### 7. Three-year accumulation relevance

The 1095-day horizon is the primary holding-period diagnostic for the current BTC mandate.

The study must report, for each phase with available 1095-day outcomes:

- count of monthly anchors;
- exact-endpoint coverage;
- median 3-year return;
- mean 3-year return;
- positive 3-year return rate;
- worst observed 3-year return;
- best observed 3-year return.

The study may describe whether `POST_HALVING_YEAR_2` and `PRE_HALVING_YEAR` historically produced stronger three-year outcomes than other phases, but only if supported by the canonical evidence.

No fixed future return may be inferred from historical phase averages.

### 8. Drawdown-from-prior-high context

For every canonical Bitcoin observation, calculate drawdown from the running historical canonical high:

`100 * (price / running_peak_price - 1)`

Summarize drawdown-from-high by phase using both daily observations and monthly anchors.

This can help distinguish a calendar-cycle effect from the simpler fact that large historical drawdowns offered better entry prices.

## Interpretation hierarchy

The study must distinguish:

1. `PATTERN_SUPPORTED_DESCRIPTIVELY`
2. `PATTERN_PARTIALLY_SUPPORTED`
3. `PATTERN_NOT_SUPPORTED`
4. `INSUFFICIENT_CANONICAL_HISTORY`

No category by itself authorizes a production recommendation change.

A descriptive-support conclusion requires, at minimum:

- at least two completed historical halving intervals with adequate canonical price coverage;
- a repeated peak/reset ordering consistent with the hypothesis in a majority of adequately covered completed intervals;
- and phase-level 3-year forward-return evidence that does not contradict the accumulation thesis.

Because Bitcoin has very few mature cycles, even `PATTERN_SUPPORTED_DESCRIPTIVELY` is not equivalent to statistically established causal or predictive skill.

## Required controls

The study must be:

- Bitcoin-only;
- read-only against the source database;
- selection-neutral relative to V4;
- independent of V4 holdout outcomes other than already preserved public governance state;
- free of model fitting;
- free of recommendation-threshold optimization;
- free of policy-winner selection;
- free of production-policy changes;
- free of autonomous execution.

The source database must be hashed before and after execution and remain byte-identical.

## Frozen V4 boundaries

These remain unchanged:

- V4 7d final holdout is consumed and preserved;
- V4 30d final holdout remains unopened;
- V4 365d final holdout remains unopened;
- V3 final holdout remains unopened;
- post-holdout V4 tuning remains prohibited;
- V4 365d remains `NO_QUALIFIED_WINNER`;
- the V4 365d Long Trend model remains reserved only as a future V5 challenger.

## Recommendation-policy boundary

Historical BTC/ETH recommendation-policy skill remains:

`INSUFFICIENT_EVIDENCE_FOR_POLICY_SKILL`

This cycle study cannot override that status.

The study may inform a future accumulation-policy design only after its results are preserved, reviewed, and separately governed.

## Output

The governed output artifact will be:

`docs/bitcoin_four_year_cycle_historical_study_results.json`

It must contain:

- source hashes;
- canonical coverage;
- per-year/phase statistics;
- cross-cycle phase summaries;
- peak/reset interval diagnostics;
- daily exact-endpoint forward-return summaries;
- monthly-anchor exact-endpoint forward-return summaries;
- drawdown-from-high summaries;
- three-year accumulation diagnostics;
- evidence limitations;
- study interpretation;
- explicit no-policy-change state.

## Next gate

`BUILD_AND_VALIDATE_BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY_RUNNER`
