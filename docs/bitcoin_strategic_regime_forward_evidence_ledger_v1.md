# Bitcoin Strategic Regime Forward Evidence Ledger V1

## Ledger identity

`BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1`

## Purpose

Define the append-only prospective evidence ledger used to evaluate Bitcoin strategic-regime and tactical recommendation-policy research under `BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_CONTRACT_V1`.

The ledger begins with zero recommendation observations. No synthetic or retrospective observation is created merely to initialize the ledger.

## Storage model

Prospective recommendation observations are stored as one immutable JSON record per observation under:

`data/research/bitcoin_strategic_regime_forward_evidence_v1/records/`

The ledger manifest is stored at:

`data/research/bitcoin_strategic_regime_forward_evidence_v1/manifest.json`

The manifest records ledger identity, schema version, governing authorities, record count, and immutable-record rules. It is not itself a recommendation observation.

Once a recommendation observation record is created, that record must not be rewritten after outcomes become known. Corrections require a separate correction record that references the original observation identifier and explains the reason for correction.

## Observation identifier

Each prospective observation must have a unique immutable `observation_id` derived from the governed operating timestamp and asset, using a deterministic collision-safe representation.

The asset for V1 is Bitcoin only:

`bitcoin`

Ethereum does not inherit Bitcoin cycle evidence automatically and is outside this ledger V1.

## Required observation fields

Every recommendation observation record must preserve these fields or explicit missing-state metadata where the contract allows the evidence itself to be unavailable:

- `observation_id`
- `observation_timestamp`
- `operating_date`
- `asset_id`
- `source_run_identifiers_and_hashes`
- `observed_price_usd`
- `current_bitcoin_portfolio_weight`
- `undeployed_capital_available_to_bitcoin`
- `strategic_regime_state`
- `tactical_new_capital_state`
- `existing_position_state`
- `original_module42_action`
- `recommendation_score`
- `v4_7d_forecast_output`
- `v4_7d_forecast_confidence`
- `forecast_30d`
- `forecast_90d`
- `forecast_180d`
- `cycle_phase`
- `days_since_halving`
- `estimated_days_to_next_halving`
- `next_halving_estimate_uncertainty`
- `normalized_cycle_position`
- `drawdown_from_high_features`
- `medium_long_trend_features`
- `volatility_drawdown_state_features`
- `macro_liquidity_evidence_references`
- `valuation_onchain_evidence_references`
- `planned_entry_tranche_structure`
- `target_max_deployment_ceiling`
- `uncertainty_notes`
- `evidence_class`
- `point_in_time_limitations`
- `transaction_cost_assumptions`
- `decision_scope`
- `counterfactuals_predeclared`
- `outcomes`
- `record_created_before_outcomes_known`
- `record_correction_of_observation_id`
- `record_correction_reason`

## Allowed state values

Strategic state:

- `ACCUMULATE`
- `HOLD`
- `DISTRIBUTE`
- `INSUFFICIENT_EVIDENCE`

Tactical new-capital state:

- `ACCELERATE`
- `NORMAL`
- `DELAY`
- `NO_NEW_CAPITAL`
- `INSUFFICIENT_EVIDENCE`

Existing-position state:

- `HOLD_EXISTING`
- `STAGED_DISTRIBUTION`
- `RISK_REDUCTION`
- `INSUFFICIENT_EVIDENCE`

Decision scope:

- `NEW_CAPITAL`
- `EXISTING_HOLDINGS`
- `BOTH`

## Missing evidence semantics

Missing evidence remains missing.

Unavailable numeric evidence must be represented as `null`, never zero unless the observed value is actually zero.

Unavailable categorical evidence must be represented as `null` or the governed `INSUFFICIENT_EVIDENCE` state when that state is itself the recommendation output.

No neutral, favorable, unfavorable, worst-case, or synthetic placeholder may be manufactured for a missing input.

## Prospective outcome structure

At record creation, outcome values must be unknown and therefore `null` unless an observation is itself a separately governed maturation/correction record.

The `outcomes` object must reserve exact-calendar fields for:

- `return_7d_exact`
- `return_30d_exact`
- `return_90d_exact`
- `return_180d_exact`
- `return_365d_exact`
- `return_1095d_exact`

Each outcome must retain its exact endpoint date and evidence status when matured.

No nearest-date substitution, interpolation, forward-fill, backward-fill, or synthetic return is permitted.

## Counterfactuals

Each observation must predeclare applicable counterfactuals from the frozen contract before outcomes are known:

- `IMMEDIATE_DEPLOYMENT`
- `FIXED_DCA`
- `BTC_BUY_AND_HOLD`
- `BTC_ETH_BUY_AND_HOLD`
- `BTC_DOMINANT_BTC_ETH`
- `UIP_TACTICAL_ACCUMULATION`
- `CASH_WHILE_WAITING` only for undeployed new capital

A counterfactual that is not applicable must be explicitly marked not applicable rather than silently omitted after outcomes mature.

## Current authority

`BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE`

`BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE`

`BITCOIN_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE`

`BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE`

`V4_MODEL_SELECTION_REOPENED=FALSE`

`PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE`

`AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE`

## Initialization rule

The ledger may be initialized with a zero-record manifest only.

`INITIAL_LEDGER_RECORD_COUNT=0`

`SYNTHETIC_INITIAL_OBSERVATION_ALLOWED=FALSE`

The first record may be created only when a real governed prospective Bitcoin recommendation observation is available and all required available-at-decision-time evidence can be frozen.

## Next gate

`INITIALIZE_AND_VALIDATE_ZERO_RECORD_BITCOIN_FORWARD_EVIDENCE_LEDGER`
