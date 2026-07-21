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
| Feature-selection leakage protection | FAIL |
| Performance-drift monitoring | NOT IMPLEMENTED |
| Universal integration certification | BLOCKED |

## Overall status

**RESEARCH ONLY**

The model must not be treated as Universal Integration Certified until
the blocking findings below are corrected and independently retested.

## Blocking Finding CRYPTO-ROBUST-001

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

## Blocking Finding CRYPTO-ROBUST-002

### Modules affected

- Platform-wide model monitoring

### Severity

**High**

### Category

Performance drift

### Description

Feature drift and prediction drift capabilities were detected, but no
explicit performance-drift capability was detected.

### Required remediation

Implement rolling realized-performance monitoring for at least:

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

## Certification rule

The crypto platform remains **RESEARCH ONLY** until:

- CRYPTO-ROBUST-001 is remediated and tested.
- CRYPTO-ROBUST-002 is implemented and tested.
- Historical validation is rerun from clean inputs.
- Cost-adjusted benchmark results are reproduced.
- Promotion decisions use only unseen validation results.
- Deterministic replay is certified.
- Universal export contracts are validated.