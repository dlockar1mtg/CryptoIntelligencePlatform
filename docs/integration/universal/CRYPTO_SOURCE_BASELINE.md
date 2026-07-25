# Crypto Universal Integration Source Baseline

## Source repository

Crypto Intelligence Platform

## Certified source branch

`integration/universal-platform-v1`

## Certified source commit

`daced44`

## Certification tag

`crypto-post-remediation-replay-certified`

## Certification status

- Strict nested feature selection: PASS
- Outer-test isolation: PASS
- Inner-validation isolation: PASS
- Historical Replay A: PASS
- Historical Replay B: PASS
- Semantic deterministic comparison: PASS
- Base tables compared: 332
- Mismatched tables: 0
- Complete test suite: 44 passed

## Integration boundary

The Universal Investment Platform integration must consume crypto data
from this certified baseline or a documented descendant of it.

The adapter must not:

- modify the active crypto database,
- trigger external market-data collection,
- rerun research modules,
- change crypto model outputs,
- or write directly into the Universal Investment Platform database.

The adapter may:

- read certified crypto database tables,
- normalize crypto identifiers,
- transform records into universal contract formats,
- create an isolated export package,
- produce manifests and validation evidence,
- and record source lineage.

## Platform status

The crypto platform remains RESEARCH ONLY.

Universal integration does not imply approval for live trading,
automated execution, or production deployment.