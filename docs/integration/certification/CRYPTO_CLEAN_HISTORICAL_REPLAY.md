# Crypto Clean Historical Replay Certification

Generated: 2026-07-21T17:18:54.593664+00:00

## Determination

**CLEAN HISTORICAL REPLAY: PASS**

The current Crypto Module 25–32 implementation produced logically equivalent results in two independent replay databases created from identical frozen historical inputs.

This certification establishes deterministic execution and database isolation. It does not independently establish statistical validity, absence of all model leakage, or production readiness.

**Platform status remains RESEARCH ONLY.**

## Scope

- First module: 25
- Last module: 32
- Replay databases: 2
- Network access during replay: disabled
- Active production/research database used for writes: no
- Row ordering ignored during comparison: yes
- UUID and timestamp fields normalized: yes
- Floating-point comparison precision: 10 decimal places

## Frozen input evidence

| Input table | Rows | Content SHA-256 |
|---|---:|---|
| canonical_market_daily | 12253 | `3caa9d0c1bea5ae282c7974436ad9a7f1340300a11bfa49bc03754461a791406` |
| crypto_features_daily | 2388 | `d5257b14e63ef39db54dd00fefc0b932c25fe7a82e765cc5c623ba65539f5792` |

Source database evidence:

- Size: 155463680 bytes
- Source SHA-256 at seed creation: `6382dfcc49422d4d8164a9e5fb4087c7a43380687a73a3ec62e1b0f6615d2156`

The active database later experienced a physical-file hash change, but the frozen input fingerprints and all Module 25–32 logical row counts remained unchanged. No new Module 25–32 runs were created after seed generation.

## Replay seed preparation

- Standard Module 25–32 tables cleared per replay: 60
- Standard derived rows removed per replay: 25570
- Additional Module 30 `clean_...` rows removed per replay: 7807
- Module 30 experiment-registry rows removed per replay: 2

## Replay A

- Status: SUCCESS
- Started: 2026-07-21T17:05:26.880491+00:00
- Completed: 2026-07-21T17:07:42.375568+00:00

| Module | Success | Run status | Duration seconds | Changed tables | Frozen inputs unchanged |
|---:|---|---|---:|---:|---|
| 25 | True | SUCCESS | 7.782479 | 8 | True |
| 26 | True | SUCCESS | 3.014457 | 8 | True |
| 27 | True | SUCCESS | 15.736139 | 8 | True |
| 28 | True | SUCCESS | 25.815056 | 8 | True |
| 29 | True | SUCCESS | 10.012427 | 9 | True |
| 30 | True | SUCCESS | 8.487062 | 11 | True |
| 31 | True | SUCCESS | 1.053269 | 8 | True |
| 32 | True | SUCCESS | 57.349492 | 13 | True |

## Replay B

- Status: SUCCESS
- Started: 2026-07-21T17:10:12.925493+00:00
- Completed: 2026-07-21T17:12:55.381931+00:00

| Module | Success | Run status | Duration seconds | Changed tables | Frozen inputs unchanged |
|---:|---|---|---:|---:|---|
| 25 | True | SUCCESS | 4.928187 | 8 | True |
| 26 | True | SUCCESS | 3.380077 | 8 | True |
| 27 | True | SUCCESS | 18.007276 | 8 | True |
| 28 | True | SUCCESS | 28.723973 | 8 | True |
| 29 | True | SUCCESS | 11.952169 | 9 | True |
| 30 | True | SUCCESS | 11.059993 | 11 | True |
| 31 | True | SUCCESS | 1.189453 | 8 | True |
| 32 | True | SUCCESS | 76.080746 | 13 | True |

## Deterministic comparison

| Check | Result |
|---|---|
| Replay A status | SUCCESS |
| Replay B status | SUCCESS |
| Tables compared | 72 |
| Missing from Replay A | 0 |
| Missing from Replay B | 0 |
| Mismatched tables | 0 |
| Module 30 registry match | True |
| Execution manifests match | True |
| Overall comparison status | **PASS** |

## Certification boundary

This result certifies repeatability of the current code and frozen-input pipeline. It does not certify:

- Production readiness
- Trading suitability
- Economic profitability
- Complete absence of feature-selection or label leakage
- Correctness of every modeling assumption

The Crypto platform remains **RESEARCH ONLY**. Universal platform integration remains blocked until the outstanding model-methodology review is completed and the broader certification gates are satisfied.
