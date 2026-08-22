# Crypto Native Predictive Horizon Recovery V4 — Design

## Experiment

`CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4`

## Purpose

V4 is a new, separately governed research experiment for the three horizons that did not produce a qualified winner in V3: 7d, 30d, and 365d.

V4 does not rewrite, reopen, or reinterpret V3. The preserved V3 result remains authoritative for the V3 candidate families and evidence set.

## Frozen V3 evidence

- V3 development results SHA-256: `33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1`
- 7d: `NO_QUALIFIED_WINNER`
- 30d: `NO_QUALIFIED_WINNER`
- 90d: `RELATIVE_MARKET_DIRECTION`
- 180d: `NATIVE_CONTEXT_DIRECTION_FIRST`
- 365d: `NO_QUALIFIED_WINNER`
- V3 final holdout outcomes remain unopened.

## Scope

V4 research is limited to 7d, 30d, and 365d.

The V3 90d and 180d development winners are not retuned in V4.

Recommendation-policy thresholds and BUY / ACCUMULATE / HOLD / WAIT / REDUCE / SELL / AVOID semantics are outside V4 and remain unchanged.

## Evidence boundary

V4 must use a new development protocol and a fresh final holdout that is disjoint from:

1. V2 consumed holdout origins;
2. V3 development-selected origins;
3. V3 final-holdout origins; and
4. any V4 development origins.

The sealed V3 final holdout must not be repurposed as V4 tuning or final-test evidence.

No V4 final-holdout outcome may be viewed until the V4 candidate families, horizon-specific targets, features, selection rules, and development winners are frozen.

## Research objective

The objective is not to force a winner. The objective is to determine whether a horizon-specific model can add reproducible information beyond the governed baseline.

A V4 horizon may close with `NO_QUALIFIED_WINNER`.

## Horizon hypotheses

### 7d

V3 showed a near-miss rather than universal failure. `GRADIENT_BOOSTED_DIRECTION` achieved positive baseline-adjusted directional skill but failed robustness and after-cost economics.

V4 7d research should therefore prioritize short-horizon robustness rather than broad model proliferation.

Permitted challenger concepts:

- short-term trend persistence and reversal features;
- cross-sectional relative-strength features;
- volatility-adjusted momentum;
- breadth / dispersion features derived only from historically available prices;
- regime interaction only if the regime inputs satisfy the governed historical-availability rule.

Primary 7d requirement: positive baseline-adjusted directional skill with broad asset support and positive modeled after-cost economic value.

### 30d

V3 showed that every tested family underperformed the majority baseline.

V4 30d research must therefore test whether a materially different representation contains signal rather than merely retuning the same classifiers.

Permitted challenger concepts:

- medium-horizon trend / reversal decomposition;
- asset-relative return and breadth state;
- volatility-state interactions;
- native-context interaction features only under the governed lag/evidence-class rules;
- abstaining or confidence-gated directional models, provided coverage is reported and missing predictions are never converted to a directional class.

Primary 30d requirement: demonstrate positive baseline-adjusted skill before any promotion discussion.

### 365d

V3 produced high raw directional accuracy but materially underperformed the 73.6% majority baseline. This indicates that simple annual up/down direction is dominated by crypto's historical upward drift.

V4 must not lower or redefine the V3 baseline after seeing that result.

Permitted 365d research may introduce a predeclared economically stronger target in addition to the original direction target, but the original direction baseline comparison must still be reported.

Permitted auxiliary target concepts include:

- excess return versus Bitcoin;
- excess return versus a frozen core-asset benchmark;
- return exceeding a predeclared economically meaningful hurdle;
- drawdown-aware forward outcome classification.

Any auxiliary target must be frozen before V4 development results are evaluated and must have its own explicit trivial baseline.

Primary 365d requirement: demonstrate incremental information beyond long-run upward drift rather than merely reproducing a high unconditional positive rate.

## Candidate-family discipline

V4 is bounded research, not brute-force search.

For each horizon, the candidate set must be frozen before development scoring. Hyperparameter grids must be small and predeclared. No candidate may be added because another candidate's development score was disappointing.

Prefer native scikit-learn families already available in the repository unless a new dependency is explicitly justified and approved.

No automated architecture search, large hyperparameter sweep, or post-hoc feature mining is permitted.

## Point-in-time and reconstruction controls

The existing V3 native-context evidence limitation remains in force: historical native-context data is reconstructed history, not strict vintage point-in-time data.

V4 must preserve that evidence class unless a new source proves strict historical-as-known provenance.

All external/native-context inputs must continue to use governed lags. Price-derived and relative-market features must use only observations available on or before the forecast origin.

Missing values remain missing. No synthetic zero, worst value, neutral value, class label, or forward fill may be introduced solely to increase coverage.

## Development protocol

Each supported asset × horizon group must use chronological development origins with leakage-safe target maturity and purged train/validation boundaries.

Training-only feature bounds/scaling must be preserved.

Development comparison dates must be common across candidate families within a horizon wherever family comparison is claimed.

The protocol must report at minimum:

- directional accuracy;
- trivial-baseline accuracy;
- baseline-adjusted directional skill;
- raw Brier score where probabilistic direction is applicable;
- leakage-safe calibrated Brier score where applicable;
- asset-level baseline-adjusted skill;
- fold-level variability;
- prediction coverage for abstaining models;
- modeled economic return after transaction costs;
- turnover;
- sample size.

## Promotion gate

A V4 development winner must, at minimum:

1. beat its predeclared trivial baseline on the primary target;
2. show nonnegative baseline-adjusted skill on a majority of supported assets;
3. avoid having a single asset explain a majority of positive aggregate gain;
4. avoid relying on one development fold for the majority of positive gain;
5. satisfy the horizon-specific economic guardrail;
6. have adequate prediction coverage if abstention is permitted; and
7. remain valid under the governed missing-data and point-in-time controls.

Calibration improvement alone cannot create a winner.

A horizon with no candidate passing the frozen gate remains `NO_QUALIFIED_WINNER`.

## Final holdout

A fresh V4 final holdout must be selected and frozen before V4 development outcomes are used to choose winners.

Its membership must be content-hashed and the manifest must state that outcomes were not viewed before freeze.

The final holdout may be opened exactly once after horizon-specific development winners or explicit `NO_QUALIFIED_WINNER` sentinels are frozen.

No tuning is allowed after V4 final-holdout outcomes are viewed.

## Production and recommendation boundaries

V4 is predictive research only.

A V4 development or final-holdout success does not automatically change production forecast authority, recommendation thresholds, portfolio weights, or execution behavior.

Production promotion requires a separate governed decision.

Recommendation-policy validation remains a separate task after predictive horizon recovery.

## Next gate

`AUDIT_V4_FRESH_EVIDENCE_CAPACITY_AND_FREEZE_HORIZON_SPECIFIC_CANDIDATE_CONTRACTS`
