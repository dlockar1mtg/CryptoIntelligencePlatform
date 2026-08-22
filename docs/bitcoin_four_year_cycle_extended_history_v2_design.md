# Bitcoin Four-Year Cycle Extended-History Study V2 — Design

## Study

`BITCOIN_FOUR_YEAR_CYCLE_EXTENDED_HISTORY_V2`

## Purpose

Extend the preserved V1 Bitcoin cycle study backward far enough to evaluate multiple independent halving cycles without modifying the canonical UIP database.

V1 is preserved at its governed result and remains authoritative for what the existing canonical database actually contains. V2 does not rewrite V1.

## Research question

Across multiple mature Bitcoin cycles, did capital deployed during the second post-halving/reset year and the pre-halving/recovery year historically produce favorable approximately three-year forward outcomes, and did the broad post-halving expansion -> reset -> recovery sequence recur often enough to justify Bitcoin cycle phase as a strategic-regime input?

## Source boundary

V2 uses a frozen external research snapshot from Coin Metrics Community API.

Metric:

`ReferenceRateUSD`

Asset:

`btc`

Frequency:

`1d`

The source is research evidence only. It is not merged into `data/crypto_intelligence.duckdb` and does not replace the canonical source used by V1.

Evidence class:

`EXTERNAL_HISTORICAL_RESEARCH_SNAPSHOT_NOT_STRICT_VINTAGE_POINT_IN_TIME`

## Source acquisition

The governed acquisition script must request daily Bitcoin `ReferenceRateUSD` observations from Coin Metrics Community API, paginate until complete, normalize to one UTC calendar date and one positive USD reference rate per date, sort ascending, and write a new immutable JSON snapshot plus metadata.

Required study coverage begins no later than `2011-01-01` and extends through at least `2024-04-19`, the day before the 2024 halving anchor. Later observations may be retained for forward-outcome calculation, but V2 cycle-structure scoring must not use the incomplete 2024->2028 interval as an independent completed cycle.

No synthetic prices, interpolation, nearest-date substitution, forward-fill, backward-fill, or zero imputation are allowed.

The raw/normalized source artifact must be hashed before V2 analysis. Missing exact endpoint outcomes remain missing.

## Halving anchors

Frozen anchors:

- 2012-11-28
- 2016-07-09
- 2020-05-11
- 2024-04-20

Completed cycle intervals eligible for independent structural evaluation:

1. 2012-11-28 -> 2016-07-09
2. 2016-07-09 -> 2020-05-11
3. 2020-05-11 -> 2024-04-20

The 2024->2028 interval is incomplete and may be described only as current-cycle context.

## Phase framework

For historical calendar-year diagnostics:

- `HALVING_YEAR`
- `POST_HALVING_YEAR_1`
- `POST_HALVING_YEAR_2`
- `PRE_HALVING_YEAR`

The present working mapping is descriptive, not deterministic policy authority.

## Refined peak/reset diagnostic

V1's full halving-to-halving maximum is too coarse for the hypothesis because a late-cycle recovery can exceed the prior post-halving high before the next halving.

V2 therefore separates:

1. `POST_HALVING_EXPANSION_PEAK`: maximum observed price from the halving date through the end of the first full post-halving calendar year.
2. `RESET_TROUGH`: minimum observed price after that expansion peak through the end of the second post-halving calendar year.
3. `PRE_HALVING_RECOVERY`: return from the reset trough through the end of the pre-halving calendar year or the day before the next halving, whichever comes first.

This diagnostic tests the specific expansion -> reset -> recovery pattern rather than the absolute maximum price anywhere before the next halving.

## Forward-return diagnostics

Exact calendar endpoints only:

- 365 days
- 730 days
- 1095 days

The primary accumulation diagnostic is the exact 1095-calendar-day forward return.

V2 must report daily-origin summaries and monthly-anchor robustness summaries. Monthly anchors reduce duplication but are still overlapping observations and must not be described as independent cycles.

## Independent-cycle emphasis

The main evidentiary unit for claims about the four-year cycle is the completed halving interval, not the number of daily or monthly observations.

V2 must explicitly report:

- number of adequately covered completed cycles;
- number matching expansion-peak -> reset-trough ordering;
- cycle-specific 3-year accumulation results;
- whether one cycle dominates pooled outcomes;
- small-sample limitations.

Three completed cycles remain a very small sample. Even unanimous historical agreement is descriptive structural evidence, not a guarantee.

## Accumulation thesis evaluation

Primary phases:

- `POST_HALVING_YEAR_2`
- `PRE_HALVING_YEAR`

For each completed cycle and each phase, V2 must report where available:

- exact 3-year outcome count;
- median 3-year return;
- positive 3-year return rate;
- worst and best 3-year return;
- drawdown from running historical high at origin;
- cycle-specific values before any pooled summary.

A pooled positive result is insufficient if one historical cycle explains most of the apparent effect.

## Interpretation states

Allowed study interpretations:

- `PATTERN_SUPPORTED_DESCRIPTIVELY`
- `PATTERN_PARTIALLY_SUPPORTED`
- `PATTERN_NOT_SUPPORTED`
- `INSUFFICIENT_EXTENDED_HISTORY`

`PATTERN_SUPPORTED_DESCRIPTIVELY` requires at minimum:

- all three completed halving intervals have adequate source coverage;
- at least two of three completed cycles match the refined expansion -> reset ordering;
- both accumulation phases have positive median exact 3-year returns in each cycle where exact outcomes are available;
- no single completed cycle is the sole source of positive accumulation evidence.

This interpretation still does not itself grant production authority.

## Governance boundaries

V2 must not:

- alter V1 results;
- modify `crypto_intelligence.duckdb`;
- reopen V3 or V4 holdouts;
- affect frozen V4 model selection;
- fit or tune a predictive model;
- optimize recommendation thresholds;
- select a recommendation-policy winner;
- infer deterministic 2026/2027 buying or 2029 selling from calendar year alone;
- authorize autonomous execution.

## Relationship to BTC/ETH mandate

The frozen BTC/ETH accumulation contract remains governing:

- Bitcoin is the primary investable Crypto asset;
- Bitcoin and Ethereum are long-duration accumulation assets;
- new Bitcoin capital during the current thesis is generally evaluated against an approximately three-year intended holding period;
- short-term forecasts are tactical entry-timing evidence rather than automatic sell signals;
- calendar year or halving distance alone cannot force a purchase or sale.

## Authority after V2

V2 may support a recommendation to promote Bitcoin cycle phase to a governed strategic-regime input, but any such promotion requires a separate closeout/governance decision after results are reviewed.

Until that separate decision:

`BITCOIN_CYCLE_POLICY_AUTHORITY_GRANTED=FALSE`

## Next gate

`BUILD_AND_VALIDATE_EXTENDED_HISTORY_SOURCE_SNAPSHOT`
