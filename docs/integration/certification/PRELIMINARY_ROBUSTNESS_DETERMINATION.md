# Crypto Model Preliminary Robustness Determination

## Scope

This determination covers the Crypto Intelligence Platform v13.0.0
before integration with the Universal Investment Platform.

## Current determination

| Gate | Status |
|---|---|
| Structural module inventory | PASS |
| Runtime dependency imports | PASS |
| Python compilation | PASS |
| Baseline pytest suite | PASS |
| Walk-forward capability present | PASS |
| Chronological train/test splitting present | PASS |
| Transaction-cost modeling present | PASS |
| Benchmark comparison present | PASS |
| Forecast calibration present | PASS |
| Feature-selection leakage protection | PASS — REMEDIATED |
| Performance-drift monitoring | PASS — IMPLEMENTED |
| Universal integration certification | BLOCKED |

## Overall status

**RESEARCH ONLY**

The model must not be treated as Universal Integration Certified until
the blocking findings below are corrected and independently retested.

## Remediated Finding CRYPTO-ROBUST-001

### Modules affected

- Module 26
- Module 28

### Severity

**Critical**

### Category

Feature-selection leakage / incomplete nested validation

### Description

Both modules select features using the complete available labeled
dataset before their nested or walk-forward validation processes begin.

Consequently, observations belonging to later outer test periods can
influence the feature set used in earlier historical folds.

### Module 26 evidence

The feature research routine:

1. Joins the complete feature and regime-label datasets.
2. Fits a StandardScaler over the complete joined dataset.
3. Calculates mutual information and feature rankings.
4. Produces a selected feature list.
5. Supplies that list to the nested walk-forward routine.

The model fitting inside each fold does fit transformations on training
data only, but the feature-selection decision itself is not isolated
inside the fold.

### Module 28 evidence

The feature-selection routine:

1. Fits a scaler and classifier over the complete frame.
2. Calculates permutation importance and ablation values over that frame.
3. Produces one retained feature list.
4. Supplies that retained list to nested_run for all outer folds.

This invalidates a fully nested interpretation of the reported
out-of-sample results.

### Required remediation

For each outer fold:

1. Construct the outer training and testing periods chronologically.
2. Perform all feature scoring and selection using only outer-training data.
3. Fit all transformations using only outer-training data.
4. Freeze the resulting feature list for that fold.
5. Apply the frozen transformations and feature list to the outer-test data.
6. Record the fold-specific selected feature list.
7. Aggregate only genuinely unseen outer-test results.


### Remediation implemented

Modules 26 and 28 now:

1. Begin production nested validation with all eligible candidate features.
2. Construct outer-training and outer-test periods chronologically.
3. Select features independently from each outer-training period.
4. Use the fold-specific feature list for inner validation.
5. Use the same frozen fold-specific list for the corresponding outer test.
6. Record the fold-specific feature list with each prediction.
7. Prevent future outer-test rows from affecting an earlier fold's training input.

### Verification evidence

The remediation is protected by:

- Structural contract tests confirming fold-local selectors exist.
- Structural tests confirming nested validation calls those selectors.
- Behavioral tests that materially alter future rows.
- Assertions that earlier outer-training frames remain unchanged.
- Assertions that earlier fold feature records remain unchanged.
- Full-suite regression testing.
- Complete Python compilation testing.

### Remediation result

**CRYPTO-ROBUST-001: PASS — REMEDIATED**

The crypto platform remains **RESEARCH ONLY** because additional
integration-certification requirements remain outstanding, including
clean historical replay, deterministic replay certification, and
Universal export-contract validation.

## Implemented Finding CRYPTO-ROBUST-002

### Modules affected

- Platform-wide model monitoring

### Original severity

**High**

### Category

Performance drift

### Description

Feature drift and prediction drift capabilities were previously
present, but explicit realized-performance drift monitoring had not
yet been implemented.

### Required remediation — completed

Rolling realized-performance monitoring now includes:

- Directional accuracy
- Brier score
- Calibration error
- Benchmark excess return
- Maximum drawdown
- Sharpe or downside-adjusted performance
- Decision hit rate
- Performance by market regime

The monitoring layer must generate warning, retraining, rollback, or
research-only statuses when degradation thresholds are crossed.


### Implementation evidence

The performance-drift monitoring layer now:

1. Aligns cost-adjusted strategy and benchmark returns by observation date.
2. Combines realized returns with model probabilities and realized regimes.
3. Creates chronological, non-overlapping reference and current windows.
4. Calculates directional accuracy, Brier score, calibration error,
   benchmark excess return, maximum drawdown, Sharpe ratio, decision hit
   rate, and performance by market regime.
5. Detects warning and critical deterioration across monitored metrics.
6. Produces `NONE`, `MONITOR`, `RETRAIN`, or `ROLLBACK` governance actions.
7. Persists evaluation, window, and regime-level evidence.
8. Prevents Module 32 advancement when retraining or rollback is required.

### Verification evidence

The capability is protected by engine, adapter, persistence, and Module 32
integration tests.

### Implementation result

**CRYPTO-ROBUST-002: PASS — IMPLEMENTED**

## Certification rule

The crypto platform remains **RESEARCH ONLY** until:

- CRYPTO-ROBUST-001 remains remediated and continuously tested.
- CRYPTO-ROBUST-002 remains implemented and continuously tested.
- Historical validation is rerun from clean inputs.
- Cost-adjusted benchmark results are reproduced.
- Promotion decisions use only unseen validation results.
- Deterministic replay is certified.
- Universal export contracts are validated.