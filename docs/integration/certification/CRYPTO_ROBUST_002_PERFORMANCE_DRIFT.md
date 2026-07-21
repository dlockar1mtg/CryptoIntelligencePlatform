# CRYPTO-ROBUST-002 Performance Drift Certification

## Finding

The crypto platform previously contained feature-drift and
probability-drift monitoring, but it did not contain an explicit
realized-performance drift decision layer.

The missing capability prevented the platform from determining whether
recent realized model and strategy performance had degraded relative to
a historical reference period.

## Implementation

CRYPTO-ROBUST-002 adds a realized-performance monitoring stack composed
of four layers.

### Performance metric engine

`crypto_platform/ml/performance_drift.py` calculates:

- Directional accuracy
- Brier score
- Calibration error
- Cost-adjusted cumulative return
- Benchmark cumulative return
- Benchmark excess return
- Maximum drawdown
- Annualized Sharpe ratio
- Decision hit rate
- Performance by market regime

The engine compares a current window with a non-overlapping historical
reference window.

### Drift classification

Each monitored metric has warning and critical degradation thresholds.

The engine produces:

- `HEALTHY`
- `WARNING`
- `DEGRADED`
- `CRITICAL`

### Governance action

The drift classification produces an operational action:

- `NONE`
- `MONITOR`
- `RETRAIN`
- `ROLLBACK`

Broad or severe performance degradation therefore prevents automatic
advancement.

### Module 32 adapter

`crypto_platform/ml/module32_performance_adapter.py` aligns:

- Cost-adjusted Module 32 strategy returns
- BTC buy-and-hold benchmark returns
- Clean regime probabilities
- Realized regime labels

Only common observation dates are used.

The adapter creates non-overlapping reference and current windows.

### Persistence layer

`crypto_platform/ml/module32_performance_persistence.py` stores:

- Drift evaluation and governance action
- Reference and current window metrics
- Performance metrics by market regime

The persistence functions are idempotent and expose latest-run views.

### Module 32 orchestration

Module 32 now:

1. Selects the approved clean strategy.
2. Builds the standardized realized-performance frame.
3. Creates chronological, non-overlapping windows.
4. Evaluates realized-performance drift.
5. Persists evaluation, window, and regime evidence.
6. Blocks advancement when action is `RETRAIN` or `ROLLBACK`.
7. Records performance status and breached metrics in the run notes.

## Verification

### Engine tests

`test_performance_drift.py` verifies:

- All required realized-performance metrics
- Healthy status behavior
- Retraining behavior
- Rollback behavior
- Minimum-history controls
- Performance reporting by regime

### Adapter tests

`test_module32_performance_adapter.py` verifies:

- Common-date alignment
- Strategy and benchmark mapping
- Probability validation
- Missing-strategy rejection
- Non-overlapping windows
- Minimum-history enforcement

### Persistence tests

`test_module32_performance_persistence.py` verifies:

- All three tables are created
- Evaluation, window, and regime records are produced
- Records persist successfully
- Repeated persistence is idempotent
- Latest-run views resolve correctly

### Integration tests

`test_module32_performance_integration.py` verifies:

- Module 32 executes the realized-performance workflow
- Drift evidence is persisted
- Breached metrics are returned
- Degraded performance produces `RETRAIN` or `ROLLBACK`

### Regression status

- Performance-drift tests: 19 passed
- Robustness tests: 25 passed
- Complete test suite: 37 passed
- Python compilation: passed

## Certification result

**CRYPTO-ROBUST-002: PASS — IMPLEMENTED**

## Remaining certification work

The explicit performance-drift capability is now implemented and tested.

The crypto platform remains **RESEARCH ONLY** until the remaining
integration-certification requirements are completed:

- Historical validation is rerun from clean inputs.
- Cost-adjusted benchmark results are reproduced.
- Promotion decisions use only unseen validation results.
- Deterministic replay is certified.
- Universal export contracts are validated.