# Bitcoin First Prospective Observation Capture Authorization V1

## Authorization

`BITCOIN_FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_AUTHORIZATION_V1`

## Purpose

Authorize exactly one first prospective Bitcoin observation in `BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1` using the already-governed first-capture design, preserved V4 7-day operationalization evidence, and the current FRED-enabled scratch refresh evidence.

This authorization does not certify recommendation-policy skill, change production policy, authorize Module42 reconstruction, authorize V4 model reselection or tuning, or authorize autonomous execution.

## Accepted evidence

### Frozen V4 operationalization

Required artifact:

`data/research/bitcoin_strategic_regime_forward_evidence_v1/live_refresh_and_v4_operationalization.json`

Required content SHA-256:

`4fb9c06cc69ac47e22bb881954e05b61f5b8dba0392133d601f5946807b739c2`

Required V4 evidence:

- winner: `V4_7D_VOLATILITY_STATE_EXTRA_TREES`;
- forecast date: `2026-08-21`;
- raw probability positive: `0.7689586293159024`;
- predicted direction: `POSITIVE`;
- model selection reopened: `false`;
- post-holdout tuning performed: `false`;
- outcome peeking allowed: `false`;
- Module42 rerun performed: `false`.

The V4 forecast remains tactical evidence only and must not independently select the strategic state.

### FRED-enabled prospective scratch evidence

Required locally preserved artifact:

`data/research/bitcoin_strategic_regime_forward_evidence_v1/local_fred_macro_scratch_v1/local_fred_macro_refresh_evidence.json`

Required content SHA-256:

`67626cb87b9c041d47a685bc9a41fd47ab15c07f6db419a0e3c0d92b028d65c9`

Required properties:

- FRED API key configured: `true`;
- FRED API key value recorded: `false`;
- Module 1 incremental refresh executed: `true`;
- Module 1 full refresh executed: `false`;
- Module 6 sync executed: `true`;
- Module42 rerun performed: `false`;
- first prospective observation captured: `false`;
- ledger record count: `0`;
- production pipeline executed: `false`;
- production policy changed: `false`;
- autonomous execution authorized: `false`.

Observed scratch Bitcoin evidence after refresh:

- observation date: `2026-08-21`;
- price USD: `78345.0`.

Macro evidence after refresh:

- `macro_observations` latest date: `2026-08-21`;
- `latest_macro_observations` latest date: `2026-08-21`;
- `macro_regime_daily` latest date: `2026-07-28`;
- `latest_macro_regime` latest date: `2026-07-28`.

The current raw FRED observations are valid prospective evidence. The July 28 derived macro regime is stale for current strategic-state assignment and must not be silently treated as an August 21 regime.

## First observation state assignment

The first observation is authorized only with the following states:

`STRATEGIC_STATE=INSUFFICIENT_EVIDENCE`

Reason: current raw macro observations exist, but the governed derived macro regime remains dated `2026-07-28`; governed current portfolio/deployment context is unavailable; valuation/on-chain evidence is unavailable; the cycle phase cannot independently select a strategic action.

`TACTICAL_NEW_CAPITAL_STATE=INSUFFICIENT_EVIDENCE`

Reason: the frozen V4 7-day signal is positive and may support `ACCELERATE` only inside an already allowed strategic regime and governed deployment ceiling. Neither prerequisite is currently established. The raw V4 probability and direction must nevertheless be preserved as tactical evidence.

`EXISTING_POSITION_STATE=INSUFFICIENT_EVIDENCE`

Reason: governed current personal Bitcoin holdings/position context is unavailable and no strategic distribution or risk-reduction state is established.

No stronger state may be substituted during observation #1 capture.

## Required missingness

The initial record must preserve missing values rather than synthesize them where current governed evidence is unavailable, including as applicable:

- current personal Bitcoin portfolio weight;
- undeployed capital available to Bitcoin;
- current live Module42 action and score;
- current 30d/90d/180d governed forecast values;
- current derived macro-regime state beyond the stale July 28 record;
- governed point-in-time-safe valuation/on-chain evidence;
- deployment target or tranche amount;
- existing-position action.

`MISSING_EVIDENCE_SYNTHESIZED=FALSE`

## Observation-time price and V4 source-price distinction

The observation record may use the later FRED-enabled scratch refresh Bitcoin price (`78345.0`, `2026-08-21`) as the observation-time price source.

The V4 forecast must retain its own original governed source context from the operationalization artifact, including canonical Bitcoin price `78441.0` on `2026-08-21` and the original frozen feature values. The V4 forecast must not be recomputed merely because the later observation-time price differs.

`V4_RECOMPUTE_FOR_CAPTURE_AUTHORIZED=FALSE`

## Cycle handling

The most recent observed halving anchor remains `2024-04-20`.

Cycle position may be recorded descriptively when directly computable from the capture timestamp and preserved governance. No calendar-only action is authorized. Estimated next-halving date or distance must remain missing if not governed with sufficient uncertainty representation.

`BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE`

## Outcomes

All initial prospective outcome fields must be `null` because no forward horizon has matured at observation creation.

Required initial outcome fields:

- `return_7d_exact=null`;
- `return_30d_exact=null`;
- `return_90d_exact=null`;
- `return_180d_exact=null`;
- `return_365d_exact=null`;
- `return_1095d_exact=null`.

`OUTCOME_PEEKING_ALLOWED=FALSE`

`NEAREST_DATE_SUBSTITUTION_ALLOWED=FALSE`

## Write boundary

Observation #1 may write only:

1. one new immutable JSON observation record under `data/research/bitcoin_strategic_regime_forward_evidence_v1/records/`; and
2. the deterministic manifest update from `record_count=0` to `record_count=1`, with the created observation id/hash recorded.

The canonical Crypto database must not be modified.

The local scratch database must not be committed.

`FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_AUTHORIZED=TRUE`

`CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE`

`PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE`

`AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE`

`BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE`

## Next gate

`CAPTURE_AND_PRESERVE_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION`
