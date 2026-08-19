# Crypto Native Predictive Horizon Recovery V4 — Candidate and Holdout Contract

## Experiment

`CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4`

## Scope

This contract governs V4 recovery research for 7d, 30d, and 365d only. V3 remains preserved and authoritative for its own evidence set. V3 90d and 180d winners are not reopened. V3 final-holdout outcomes remain unopened and are not reused by V4.

## Fresh-evidence capacity basis

The V4 fresh-evidence capacity audit passed for all 17 supported asset × horizon groups with zero capacity failures under the V3 feature-completeness contract. The minimum fresh feature-safe capacity was 191 origins for Avalanche 365d, which is sufficient for the frozen V4 allocation below.

## Frozen V4 evidence allocation

For every supported V4 asset × horizon group:

- V4 development origins: 50
- V4 development folds: 5
- Development origins per fold: 10
- V4 final-holdout origins: 10
- Required fresh origins per group: 60

Supported groups:

- 7d: bitcoin, ethereum, solana, chainlink, xrp, avalanche
- 30d: bitcoin, ethereum, solana, chainlink, xrp, avalanche
- 365d: bitcoin, ethereum, solana, chainlink, avalanche

XRP365 remains unsupported and must not be synthesized.

### Deterministic membership rule

For each supported group, start from fresh feature-safe origins after excluding all V2 consumed holdout origins, all V3 development-selected origins, and all V3 final-holdout origins.

1. Reserve the latest 10 eligible fresh origins as the V4 final holdout.
2. From the remaining eligible fresh origins, select exactly 50 development origins using deterministic chronological spacing across the available range.
3. Assign the 50 development origins chronologically to five folds of 10 origins each.
4. No V4 final-holdout outcome may be read, summarized, scored, or used in feature/candidate selection before the development winners or `NO_QUALIFIED_WINNER` sentinels are frozen.

The V4 holdout manifest must contain dates only, the evidence exclusions, a canonical content hash, and `holdout_outcomes_viewed_before_freeze=false`.

## Common controls

All horizons use:

- matured forward labels only;
- chronological origin selection;
- purged training/validation boundaries;
- training-only scaling and feature bounds;
- common development origins across candidate families within a horizon;
- no missing-value synthesis;
- no post-hoc candidate additions;
- no large hyperparameter sweep;
- no V3 final-holdout reuse;
- 15 bps modeled transaction cost for sign-strategy diagnostics;
- reconstructed-history evidence class unless strict historical-as-known provenance is separately proven.

## 7d candidate contract

### Primary target

Forward 7-day return direction: positive versus non-positive.

### Trivial baseline

Training-window majority class for the same 7-day direction target.

### Frozen candidate families

1. `V4_7D_SHORT_TREND_REVERSAL_LOGIT`
   - balanced logistic regression;
   - short price-derived trend/reversal features only;
   - candidate feature concepts: 1d/3d/7d/14d/30d returns, 7d/14d/30d realized volatility, distance from 20d/50d moving averages.

2. `V4_7D_RELATIVE_STRENGTH_GB`
   - gradient boosting classifier;
   - price-derived features plus cross-asset relative-strength, breadth, and dispersion features derived only from historically available prices;
   - candidate relative concepts: asset-minus-BTC returns, asset-minus-core-median returns, core breadth positive percentage, and cross-sectional return dispersion over short windows.

3. `V4_7D_VOLATILITY_STATE_EXTRA_TREES`
   - ExtraTrees classifier;
   - bounded short-horizon trend, volatility-state, and relative-market features;
   - no external/native-context features unless separately proven available under the governed historical rule.

### 7d development gate

A winner must:

- have aggregate baseline-adjusted directional skill > 0;
- have nonnegative baseline-adjusted skill on at least 4 of 6 assets;
- not have one asset explain a majority of total positive net correct gain;
- not have one fold explain a majority of total positive net correct gain;
- have positive mean modeled sign-strategy return after 15 bps costs;
- retain full required prediction coverage.

## 30d candidate contract

### Primary target

Forward 30-day return direction: positive versus non-positive.

### Trivial baseline

Training-window majority class for the same 30-day direction target.

### Frozen candidate families

1. `V4_30D_TREND_REVERSAL_LOGIT`
   - balanced logistic regression;
   - medium-horizon trend/reversal decomposition using price-derived features.

2. `V4_30D_RELATIVE_CONTEXT_GB`
   - gradient boosting classifier;
   - price-derived trend plus relative-market breadth/dispersion state;
   - governed lagged native context may be included only from the existing approved native-context set and must retain the reconstructed-history evidence class.

3. `V4_30D_VOLATILITY_STATE_EXTRA_TREES`
   - ExtraTrees classifier;
   - medium-horizon volatility-state interactions, trend, moving-average distance, and relative-market state.

No confidence-gated or abstaining model is introduced in this V4 round; all three families must make a prediction at every selected development origin so coverage comparisons remain direct.

### 30d development gate

A winner must:

- have aggregate baseline-adjusted directional skill > 0;
- have nonnegative baseline-adjusted skill on at least 4 of 6 assets;
- not have one asset explain a majority of total positive net correct gain;
- not have one fold explain a majority of total positive net correct gain;
- have positive mean modeled sign-strategy return after 15 bps costs;
- retain full required prediction coverage.

## 365d candidate contract

### Primary target

Forward 365-day return direction: positive versus non-positive. This remains the selection target so V4 must directly attempt to beat the strong V3 directional baseline rather than redefining success after observing V3.

### Trivial baseline

Training-window majority class for the same 365-day direction target.

### Frozen candidate families

1. `V4_365D_LONG_TREND_LOGIT`
   - balanced logistic regression;
   - long-horizon price-derived trend and drawdown state.

2. `V4_365D_LONG_REGIME_GB`
   - gradient boosting classifier;
   - long-horizon trend plus governed lagged macro/liquidity/risk context under the existing reconstructed-history evidence rules.

3. `V4_365D_RETURN_MAGNITUDE_ENSEMBLE`
   - bounded regression-first challenger using native scikit-learn regression families already available in the repository;
   - predicts forward return magnitude from long-horizon price, relative-market, and governed lagged context features;
   - directional class is the sign of the predicted forward return;
   - candidate ensemble is limited to GradientBoostingRegressor, RandomForestRegressor, and BayesianRidge with weights determined only from leakage-safe development validation performance.

### Required 365d features/concepts

Permitted feature concepts include 90d/180d/365d returns, 90d/180d volatility, distance from 200d moving average, trailing 365d drawdown, asset-relative 90d/180d performance, cross-asset breadth/dispersion, and governed lagged native context. All must be computed only from information available on or before the forecast origin under the governing evidence rules.

### Auxiliary diagnostics

In addition to the original up/down target, V4 365d must report, without using them to redefine the winner after scoring:

- forward return exceeding +15%;
- forward return relative to Bitcoin where meaningful for non-Bitcoin assets;
- realized forward drawdown where available from point-in-time-safe price history.

These are diagnostics only in V4. They cannot create a winner if the original directional gate fails.

### 365d development gate

A winner must:

- have aggregate baseline-adjusted directional skill > 0 against the original majority baseline;
- have nonnegative baseline-adjusted skill on at least 3 of 5 supported assets;
- not have one asset explain a majority of total positive net correct gain;
- not have one fold explain a majority of total positive net correct gain;
- have positive mean modeled sign-strategy return after 15 bps costs;
- retain full required prediction coverage.

## Winner selection within a horizon

Only candidates passing the full horizon gate are eligible. Among eligible candidates, select by:

1. highest aggregate baseline-adjusted directional skill;
2. highest directional accuracy;
3. more assets with nonnegative baseline-adjusted skill;
4. lower leakage-safe calibrated Brier score where applicable;
5. lower raw Brier score where applicable;
6. lower fold-level variability;
7. simpler model if still tied.

A horizon with no candidate passing the full frozen gate remains `NO_QUALIFIED_WINNER`.

## Final-holdout rule

The 10-origin-per-group V4 final holdout is opened exactly once only after the three horizon development decisions are frozen. A `NO_QUALIFIED_WINNER` horizon does not receive a post-hoc final-holdout model. No tuning is permitted after any V4 final-holdout outcome is viewed.

## Production boundary

V4 success remains research evidence. It does not automatically change production forecast authority, recommendation-policy thresholds, portfolio weights, or execution behavior.

## Next gate

`FREEZE_V4_FINAL_HOLDOUT_MEMBERSHIP_BEFORE_DEVELOPMENT_SCORING`
