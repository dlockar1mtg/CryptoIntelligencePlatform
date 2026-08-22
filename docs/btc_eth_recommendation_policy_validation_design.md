# Crypto BTC/ETH Recommendation Policy Validation Design

## Experiment

`CRYPTO_BTC_ETH_RECOMMENDATION_POLICY_VALIDATION_V1`

## Purpose

This experiment validates whether the existing Crypto recommendation policy produces economically useful BTC and ETH decisions. It is intentionally separate from forecast-model validation.

The practical investable focus is Bitcoin and Ethereum. Other supported crypto assets may remain contextual inputs elsewhere in the platform, but they are not co-primary investment targets in this validation.

This experiment MUST NOT modify Module 42 production recommendation rules, thresholds, target weights, production execution behavior, or the preserved V3/V4 predictive evidence.

## Governing predictive evidence

The experiment begins only after preservation of:

- V4 7d final-holdout result SHA-256 `fe82f2b8cdfe817bfbb825cd2d97eb7d02711c8d1a2d3e5b3daf6c17fe756a48`;
- V4 365d auxiliary diagnostic SHA-256 `f6a57ac6adefe5a0b187d9a3310b6d1cb4a7af20068c1eea779ca9b9d1b97735`;
- V4 7d final holdout consumed exactly once;
- V4 30d and 365d final holdouts still unopened;
- V3 final holdout still unopened;
- post-V4-holdout tuning prohibited.

The V4 7d result remains research evidence with evidence class `HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME`. Nothing in this recommendation-policy experiment upgrades that evidence to strict vintage point-in-time authority.

## Existing Module 42 semantic authority

For evaluation, the intended economic meaning of Module 42 actions is authoritative:

- `STRONG_BUY`: deploy new capital aggressively according to the governed entry strategy;
- `BUY`: deploy new capital according to the governed entry strategy;
- `SCALE_IN`: deploy new capital gradually;
- `HOLD`: preserve an existing position; do not treat the position as cash;
- `WAIT`: preserve an existing position but block new capital until reassessment;
- `REDUCE`: trim an existing long position; do not treat this as a short position;
- `AVOID`: do not initiate a new position; an existing position must not be silently transformed into a synthetic short.

The configured Crypto allocation percentage remains a ceiling rather than a mandatory deployment target.

## Module 44 diagnostic limitation

Current Module 44 is not certification authority for this experiment because its `ACTION_POSITION` diagnostic maps:

- `HOLD`, `WAIT`, and `AVOID` to `0.00`;
- `REDUCE` to `-0.50`.

That mapping does not preserve Module 42 portfolio semantics. In particular, it can treat HOLD/WAIT as cash and REDUCE as a partial short rather than an ownership-preserving hold or trim.

Module 44 also permits outcome lookup on or after the due date and compounds recommendation observations in benchmark summaries. Those behaviors may remain useful for operational monitoring but MUST NOT be used as certification-quality counterfactual evidence here.

This experiment is therefore a separate, read-only research evaluator. It does not rewrite Module 44 in place.

## Asset scope

Primary assets:

- `bitcoin`
- `ethereum`

No pooled result may conceal the separate BTC and ETH results. Every material metric MUST be reported:

1. BTC separately;
2. ETH separately;
3. BTC+ETH pooled only as a secondary summary.

## Evidence inventory gate

Before scoring, a preflight MUST inventory the historical recommendation evidence available for BTC and ETH, including at minimum:

- recommendation dates;
- recommendation action counts;
- investment-score distribution;
- forecast-confidence distribution;
- recommendation evidence status;
- current/target portfolio weights where recorded;
- maturity availability for exact 7d, 30d, 90d, and 180d outcome dates;
- duplicate or overlapping recommendation dates;
- source Module 42 run lineage;
- whether the recommendation record can be reconstructed without using information after its recommendation date.

Missing information remains missing. No synthetic action, score, confidence, price, weight, or outcome may be created.

If historical recommendation evidence is too sparse or not reconstructable under the governed evidence rules, the affected test MUST report `INSUFFICIENT_EVIDENCE` rather than manufacture a result.

## Point-in-time boundary

Historical policy evaluation MUST use only information that belonged to the recommendation record at the recommendation date or a separately governed historical reconstruction.

If recommendation history is reconstructed from present-day warehouse state rather than historical-as-known snapshots, it MUST be labeled `HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME`.

No strict real-time point-in-time claim is allowed unless provenance is independently proven.

## Outcome-date rule

All certification outcomes require the exact calendar endpoint:

- 7 days;
- 30 days;
- 90 days;
- 180 days.

No `price_on_or_after` substitution, nearest-date approximation, interpolation, or shortened horizon is allowed for certification scoring.

If the exact endpoint is unavailable, the observation remains missing and coverage is reported.

## Transaction costs

All policy strategies involving a change in invested capital MUST include a frozen 15 bps cost per transaction-side turnover unless a more conservative already-governed cost is demonstrated before scoring.

No cost may be omitted simply because it causes a policy to lose to a benchmark.

## Validation questions

### A. Action ordering

For BTC and ETH separately, test whether realized outcomes have an economically coherent ordering across available actions.

At minimum evaluate:

- `STRONG_BUY` / `BUY` / `SCALE_IN` versus `HOLD` / `WAIT` / `REDUCE` / `AVOID`;
- realized forward returns by action;
- median as well as mean returns;
- positive-return rate;
- downside-tail behavior;
- sample size and coverage for every action.

Do not claim ordinal skill for actions with inadequate sample size.

### B. Incremental-purchase timing

This is the primary practical test for new capital.

For each eligible BTC/ETH recommendation date, compare governed recommendation timing against a matched baseline in which the same fixed amount of new capital is purchased immediately.

The policy evaluation MUST preserve the meaning of actions:

- positive-entry actions may deploy capital according to their governed tranche timing;
- `WAIT` delays new capital rather than selling an existing holding;
- `HOLD` makes no incremental purchase unless the governed policy explicitly calls for one;
- `REDUCE` is not evaluated as a short;
- `AVOID` makes no new purchase.

Where the historical entry strategy contains conditional language such as buying "on weakness" or "on a 5-10% pullback", the evaluator MUST use a predeclared deterministic trigger rule based only on future price-path observations available after the recommendation. If the exact historical execution rule cannot be unambiguously reconstructed, report that component separately as `NOT_RECONSTRUCTABLE` rather than inventing an entry.

Primary timing measures:

- ending value of equal-dollar contributions;
- excess ending value versus immediate purchase;
- average acquisition price;
- units accumulated per contributed dollar;
- maximum drawdown of contributed capital where measurable;
- percentage of decisions in which timing added value.

### C. Existing-position management

For an investor already holding BTC or ETH, compare Module 42 action semantics against a continuous long-hold benchmark.

At minimum:

- `HOLD`: maintain 100% of the reference long position;
- `WAIT`: maintain the existing long position while withholding incremental capital;
- `REDUCE`: apply the governed trim fraction to the existing long position and retain the remainder plus cash;
- positive-entry actions: preserve the existing position and model only the incremental allocation decision;
- `AVOID`: evaluate no-new-entry behavior separately from treatment of an already-owned position.

The evaluator MUST NOT encode negative exposure unless the production policy explicitly authorizes shorting. Current validation assumes no autonomous shorting authority.

### D. Benchmark comparisons

Every more-complex policy must be compared with strong simple alternatives.

Required benchmarks:

1. BTC buy-and-hold for BTC observations;
2. ETH buy-and-hold for ETH observations;
3. immediate equal-dollar purchase on every eligible contribution date;
4. fixed-schedule DCA that ignores recommendation signals;
5. cash for incremental capital when the policy explicitly defers purchase;
6. a BTC-centered crypto allocation benchmark for portfolio-level BTC/ETH comparisons.

The BTC-centered benchmark MUST be frozen before policy scoring. It may include BTC-only and one simple BTC-dominant BTC/ETH mix, but weights may not be chosen after seeing policy outcomes.

### E. Economic value

Report at minimum:

- cumulative and annualized return only where non-overlapping cash-flow methodology makes those quantities valid;
- money-weighted or contribution-normalized ending-value comparisons for recurring-purchase tests;
- excess return/value versus each relevant benchmark;
- maximum drawdown;
- downside deviation where supported;
- turnover;
- transaction cost paid;
- positive-value rate;
- median excess value;
- worst observed excess value;
- observation count and coverage.

Overlapping recommendation horizons MUST NOT be naively compounded as sequential independent returns.

### F. Robustness

For BTC and ETH separately, test robustness across available regimes and time segments when sample size permits.

A result must not be certified as broad recommendation skill if substantially all positive value comes from:

- one asset;
- one short time segment;
- one market regime;
- one action class;
- a very small number of extreme returns.

Concentration diagnostics are mandatory.

## BTC/ETH practical hierarchy

This experiment may determine that the best practical Crypto policy is simpler than the current six-asset recommendation framework.

Allowed final conclusions include:

- BTC recommendation policy validated; ETH recommendation policy validated;
- BTC validated but ETH insufficient/unvalidated;
- ETH validated but BTC insufficient/unvalidated;
- recommendation timing not validated, use fixed BTC/ETH DCA;
- policy does not beat simple BTC-centered benchmark;
- insufficient historical evidence.

The experiment MUST NOT force a recommendation-policy winner.

## Promotion gate

Recommendation-policy promotion requires evidence of economic usefulness, not merely directional forecast accuracy.

At minimum, a policy can be considered for promotion only if:

- outcome coverage is complete enough to support the claim;
- BTC and ETH are reported independently;
- the policy has positive after-cost value versus the matched practical benchmark for the claimed use case;
- median value is not materially negative;
- positive value is not dominated by a tiny number of outliers;
- drawdown behavior is measured;
- action semantics match Module 42;
- no prohibited future information was used;
- results survive at least one time/regime robustness partition where sample size allows.

If these conditions do not hold, the result is `RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED` or `INSUFFICIENT_EVIDENCE`.

Passing this research gate does not by itself authorize autonomous execution or production changes. Production promotion remains a separate governance action.

## Frozen non-goals

This experiment does not:

- retune V4;
- reopen any V3/V4 holdout;
- transfer forecast-model winner gates into recommendation-policy gates;
- optimize action thresholds after viewing validation outcomes;
- optimize BTC/ETH portfolio weights after viewing validation outcomes;
- validate altcoin investment selection;
- authorize autonomous trading;
- convert missing values to zero, WAIT, AVOID, or worst-case observations.

## Required first implementation step

Before any policy scoring, build a read-only `BTC_ETH_RECOMMENDATION_POLICY_EVIDENCE_INVENTORY` that determines what historically reconstructable Module 42 / Module 44 / canonical-price evidence actually exists.

No policy score or threshold decision may be produced by the inventory step.

## Next gate

`BUILD_AND_VALIDATE_BTC_ETH_RECOMMENDATION_POLICY_EVIDENCE_INVENTORY`
