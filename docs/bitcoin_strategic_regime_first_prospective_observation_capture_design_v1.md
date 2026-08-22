# Bitcoin Strategic Regime First Prospective Observation Capture Design V1

## Design

`BITCOIN_STRATEGIC_REGIME_FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_DESIGN_V1`

## Purpose

Define the governed procedure for creating the first real prospective Bitcoin strategic-regime recommendation observation in `BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1` without manufacturing missing evidence, peeking at future outcomes, changing production policy, or granting autonomous execution authority.

This design authorizes observation capture only after its validator passes. It does not itself create an observation.

## Governing inputs

The capture process must read and preserve the following governed authorities before creating observation #1:

- `docs/bitcoin_strategic_regime_forward_evidence_contract_v1.md`
- `docs/bitcoin_strategic_regime_forward_evidence_ledger_v1.md`
- `data/research/bitcoin_strategic_regime_forward_evidence_v1/manifest.json`
- `docs/bitcoin_cycle_phase_strategic_regime_governance_v1.md`
- preserved V2 historical result SHA-256 `ed22cfb5eb83ac860527ca3c47c6b8d9e10a7cb3827ebb89ebd33fe8a324b9ca`
- frozen V2 extended-history source SHA-256 `549bc0172dbefaf9936705df9da58ead29cd583141c5eaf294dd2fed5a693961`

The canonical Crypto database remains a read-only source for this research capture unless a separately governed write authorization is granted.

## Observation-time boundary

The observation must be created using only information available at the capture timestamp.

Required timestamp semantics:

- operating timezone: `America/Chicago`;
- observation timestamp must be recorded with timezone offset;
- operating date must be derived from the observation timestamp;
- no evidence first observed after the capture timestamp may be inserted into the initial record;
- outcomes for 7/30/90/180 days, 365 days, and approximately three years must be `null` or absent at initial capture because they are not yet matured.

`OUTCOME_PEEKING_ALLOWED=FALSE`

## Source provenance

Every populated evidence value must identify its source run, source artifact, database query authority, or governed static authority when applicable.

If a required evidence category is unavailable, stale beyond its governed use, or cannot be reproduced at capture time, it must be represented as missing with an explicit reason.

`MISSING_EVIDENCE_SYNTHESIZED=FALSE`

`SYNTHETIC_ZERO_ALLOWED=FALSE`

`SYNTHETIC_NEUTRAL_ALLOWED=FALSE`

`SYNTHETIC_WORST_CASE_ALLOWED=FALSE`

## Required record structure

Observation #1 must be a single immutable JSON record under:

`data/research/bitcoin_strategic_regime_forward_evidence_v1/records/`

The record filename must contain the operating date, capture time, and a deterministic content-safe observation identifier.

The record must preserve at minimum:

- ledger id and schema version;
- observation id;
- observation timestamp and operating date;
- operating timezone;
- asset id `bitcoin`;
- source run identifiers and hashes;
- observed Bitcoin price and price-source authority;
- current Bitcoin portfolio weight when governed and available;
- undeployed capital available to Bitcoin when governed and available;
- strategic state;
- tactical new-capital state;
- existing-position state;
- original Module42 action when available;
- recommendation score when available;
- frozen V4 7-day forecast output and confidence when a governed live inference path is available;
- 30d/90d/180d forecast values only when governed and genuinely available at capture time;
- most recent observed halving anchor;
- days since halving;
- estimated next-halving date or distance with uncertainty explicitly represented;
- normalized cycle position when defensibly computable;
- descriptive cycle phase;
- drawdown from running/all-time high when governed price history is available;
- medium/long trend features when governed and available;
- volatility/drawdown-state features when governed and available;
- macro/liquidity evidence references when governed and available;
- valuation/on-chain evidence references when governed and available;
- planned entry/tranche structure when applicable;
- target/max deployment ceiling when governed and available;
- evidence class and point-in-time limitations;
- explicit uncertainty notes;
- transaction-cost assumptions;
- record scope: new capital, existing holdings, or both;
- all outcome fields initialized as unknown/unmatured;
- policy certification status;
- production/execution authority markers.

## State assignment rules

The capture process must preserve the three-layer separation.

Strategic states:

- `ACCUMULATE`
- `HOLD`
- `DISTRIBUTE`
- `INSUFFICIENT_EVIDENCE`

Tactical new-capital states:

- `ACCELERATE`
- `NORMAL`
- `DELAY`
- `NO_NEW_CAPITAL`
- `INSUFFICIENT_EVIDENCE`

Existing-position states:

- `HOLD_EXISTING`
- `STAGED_DISTRIBUTION`
- `RISK_REDUCTION`
- `INSUFFICIENT_EVIDENCE`

Cycle phase is one strategic input and may not independently select a state.

A negative V4 7-day signal during an otherwise favorable accumulation regime may support `DELAY`; it does not automatically support selling existing Bitcoin.

A positive V4 7-day signal may support `ACCELERATE` only inside an already allowed strategic regime and governed deployment ceiling.

If the available live evidence is insufficient to justify a state at any layer, that layer must be `INSUFFICIENT_EVIDENCE`.

`BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE`

## Module42 and V4 handling

Module42 remains semantic authority for an existing governed recommendation action when such an action exists at capture time. The capture process must not recreate a historical Module42 action from later data.

Module44 remains diagnostic only and is not certification authority.

The V4 7-day model remains tactical evidence only. This design does not reopen model selection or authorize retraining.

`V4_MODEL_SELECTION_REOPENED=FALSE`

`V4_RETRAINING_AUTHORIZED=FALSE`

## Portfolio information

Portfolio weight and undeployed-capital fields may remain missing if no governed capture source exists at observation time. The process must not infer them from informal assumptions.

The configured Crypto allocation remains a ceiling, not an automatic deployment target.

## Initial outcome fields

At first capture, all prospective outcome fields must be unknown.

No exact endpoint may be backfilled at record creation, even if the capture process is tested later on a historical date. The first production-like prospective record must use the actual current capture timestamp.

`INITIAL_OUTCOMES_MUST_BE_UNMATURED=TRUE`

`NEAREST_DATE_SUBSTITUTION_ALLOWED=FALSE`

## Immutable evidence mechanics

Before writing the first record, the capture runner must require ledger manifest `record_count=0` and no existing JSON observation records.

After writing the record:

- the original record must never be edited to add matured outcomes;
- outcome maturation must be represented through a separately governed outcome attachment or derived evaluation artifact;
- factual corrections require a separately governed correction record referencing the original observation id;
- manifest updates must be explicit and deterministic;
- the record content SHA-256 must be printed and preserved.

`APPEND_ONLY_OBSERVATION_RECORDS=TRUE`

`CORRECTION_REQUIRES_SEPARATE_RECORD=TRUE`

## First-capture authorization boundary

This design does not authorize writing observation #1 until:

1. the capture design validator passes;
2. the capture runner is implemented;
3. the capture runner receives its own static preflight validation;
4. all expected source files and database authorities are verified at runtime;
5. the ledger is still empty.

`FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE`

## Policy boundary

Historical V2 supports cycle phase descriptively but does not certify recommendation-policy skill.

`BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE`

`PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE`

`AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE`

`CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE`

## Next gate

`BUILD_AND_VALIDATE_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_RUNNER`
