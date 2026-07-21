# CRYPTO-ROBUST-001 Remediation Certification

## Finding

Modules 26 and 28 previously selected features using the complete
labeled dataset before beginning outer walk-forward validation.

That design allowed future outer-test observations to influence feature
selection for earlier historical folds.

## Remediation

### Module 26

Module 26 now:

- Sends all eligible candidate columns into nested validation.
- Calls `select_features_for_fold` inside each outer fold.
- Supplies only the outer-training frame to the selector.
- Uses the resulting fold feature list for inner validation.
- Uses the frozen fold feature list for outer testing.
- Records the selected feature list in each fold prediction.

### Module 28

Module 28 now:

- Sends all core and representation candidate features into nested validation.
- Calls `select_features_for_fold` inside each outer fold.
- Supplies only the outer-training frame to the selector.
- Uses the fold feature list for adaptive inner search.
- Uses the frozen list for outer prediction and calibration.
- Records the fold feature list and count in the output records.

## Verification

### Structural tests

`test_nested_feature_selection_contract.py` verifies:

- Both runners define a fold-local feature selector.
- Both nested-validation methods invoke the selector internally.

### Behavioral tests

`test_future_data_isolation.py` verifies:

- Future outer-test rows can be changed materially.
- The earlier fold's captured outer-training frame remains identical.
- The captured training period ends before the outer-test period starts.
- The earlier fold's recorded feature list remains unchanged.

### Regression status

- Robustness tests: 6 passed
- Complete test suite: 18 passed
- Python compilation: passed

## Certification result

**CRYPTO-ROBUST-001: PASS — REMEDIATED**

## Remaining limitation

CRYPTO-ROBUST-002 remains open because explicit realized-performance
drift monitoring has not yet been implemented.

Therefore:

- Leakage protection status: PASS — REMEDIATED
- Overall model status: RESEARCH ONLY
- Universal integration status: BLOCKED