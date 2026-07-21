# Crypto Post-Remediation Historical Replay Certification

## Certification status

**STATUS: PASS**

The Crypto Intelligence Platform completed an isolated, deterministic
historical replay after the CRYPTO-ROBUST-001 strict nested
feature-selection remediation.

## Certified implementation boundary

The replay covers Modules 25 through 32 and includes the corrected
strict-nesting behavior in Modules 26 and 28.

Relevant implementation commits:

- Strict-nesting remediation: `9fed1d4`
- Integration merge: `addc7e1`
- Replay infrastructure: `dd9b97c`
- Documentation correction: `aadd74c`

## Strict-nesting determination

CRYPTO-ROBUST-001 is remediated.

For Module 26:

1. The outer-training frame is split into inner training and inner
   validation.
2. Inner feature selection uses inner-training rows only.
3. Candidate tuning uses the inner-selected feature set.
4. Outer feature selection is recomputed from the complete
   outer-training frame after tuning.
5. The final candidate is evaluated once against the untouched
   outer-test frame.

For Module 28:

1. The outer-training frame is split into inner training and inner
   validation.
2. Inner feature retention uses inner-training rows only.
3. Adaptive search and calibration use the inner-retained features.
4. Outer feature retention is recomputed from the complete
   outer-training frame after tuning.
5. Selected candidates are evaluated once against the untouched
   outer-test frame.

## Replay preparation

Two independent replay databases were copied from the same active
database and then purged of derived Module 25–32 outputs.

Preparation results for each replay:

- Derived tables purged: 69
- Derived rows removed: 33,377
- Module 30 experiment-registry rows removed: 2
- Module 25–32 run-table records after purge: 0
- Frozen input fingerprints preserved: PASS

The active production database was not used as the replay target.

## Replay execution

Replay A:

- Modules completed: 25 through 32
- Module failures: 0
- Frozen inputs unchanged after every module: PASS
- Overall status: SUCCESS

Replay B:

- Modules completed: 25 through 32
- Module failures: 0
- Frozen inputs unchanged after every module: PASS
- Overall status: SUCCESS

The database-path environment override was cleared after each replay,
and active-database metadata remained unchanged.

## Deterministic comparison

The Replay A and Replay B databases were compared semantically.

Comparison results:

- Base tables compared: 332
- Tables missing from Replay A: 0
- Tables missing from Replay B: 0
- Mismatched tables: 0
- Execution manifests equivalent: PASS
- Overall deterministic comparison: PASS

Row order was ignored. Floating-point values were normalized to ten
decimal places. Execution-specific identifiers and timestamps were
excluded from semantic comparison, including:

- `run_id`
- `source_run_id`
- `experiment_id`
- columns ending in `_run_id`
- execution timestamp columns

The excluded fields are administrative execution metadata and do not
represent analytical outputs.

## Test evidence

- Focused strict-nesting and future-data isolation tests: 4 passed
- Replay-path and robustness tests: 9 passed
- Complete certification-branch suite: 44 passed
- Python compilation checks: PASS
- Git whitespace checks: PASS
- Final working tree: clean

## Certification conclusion

The post-remediation implementation is deterministic under the frozen
historical replay inputs and the documented normalization boundary.

The following gates pass:

- CRYPTO-ROBUST-001 strict nesting: PASS
- Outer-test isolation: PASS
- Inner-validation feature-selection isolation: PASS
- Replay database isolation: PASS
- Frozen-input preservation: PASS
- Replay A execution: PASS
- Replay B execution: PASS
- A/B semantic determinism: PASS

## Certification limitations

This certification demonstrates deterministic execution and historical
data isolation for the tested implementation and frozen inputs.

It does not independently establish:

- economic profitability,
- predictive validity,
- absence of all possible model bias,
- suitability for live trading,
- suitability for unsupervised production deployment,
- or performance under future market conditions.

## Platform status

**RESEARCH ONLY**

The deterministic replay gate is complete. Any promotion beyond
research status requires separate statistical, economic, operational,
and production-readiness approval.