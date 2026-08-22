# Bitcoin Live Input Refresh and V4 Operationalization Governance V1

## Governance ID

`BITCOIN_LIVE_INPUT_REFRESH_AND_V4_OPERATIONALIZATION_GOVERNANCE_V1`

## Purpose

This document governs the live-input refresh path and the operational use of the frozen Bitcoin 7-day predictive winner before the first prospective Bitcoin strategic-regime observation is captured.

This gate does not certify recommendation-policy skill, change production policy, authorize autonomous execution, reopen V4 model selection, or authorize post-holdout tuning.

## Preserved starting state

- Forward-evidence ledger record count: `0`.
- First prospective Bitcoin observation captured: `FALSE`.
- Preserved live-input authority resolution SHA-256: `4b63171f9ee1e0bc0ccbda70418b301b09461c3b1c8976697d1d51ae387697aa`.
- Frozen 7-day winner: `V4_7D_VOLATILITY_STATE_EXTRA_TREES`.
- V4 30-day decision: `NO_QUALIFIED_WINNER`.
- V4 365-day decision: `NO_QUALIFIED_WINNER`.
- Recommendation-policy authority remains `BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED`.

## Live market refresh authority

The existing governed collection and canonicalization path is authorized for prospective evidence preparation:

1. `run_module1.py` may be executed in normal incremental mode.
2. `--full-refresh` is not authorized by this gate.
3. Module 1 may collect provider-aware current market, historical market, exchange OHLCV, ecosystem, and macro data according to existing configuration.
4. `run_module6.py --phase sync` may be executed after a successful Module 1 incremental collection to propagate newly available source history into `canonical_market_daily`.
5. Module 6 `research` or `all` phases are not authorized by this gate.
6. The resulting database change is an authorized source-data refresh only; it is not a production-policy change or model retraining event.
7. Before and after hashes and freshness dates must be recorded for the database and relevant evidence artifacts.

Authority markers:

- `MODULE1_INCREMENTAL_REFRESH_AUTHORIZED=TRUE`
- `MODULE1_FULL_REFRESH_AUTHORIZED=FALSE`
- `MODULE6_SYNC_AUTHORIZED=TRUE`
- `MODULE6_RESEARCH_PHASE_AUTHORIZED=FALSE`
- `LIVE_SOURCE_DATA_REFRESH_AUTHORIZED=TRUE`

## Macro refresh authority

Module 1 may refresh macro observations only through its existing governed provider logic.

- If `FRED_API_KEY` is configured, the existing FRED path may be used.
- If `FRED_API_KEY` is not configured, the existing local cache may be retained.
- Stale macro evidence must remain explicitly stale or missing.
- No substitute macro series, synthetic values, interpolation, or web-sourced replacement may be inserted under this gate.

Authority markers:

- `EXISTING_MODULE1_MACRO_REFRESH_AUTHORIZED=TRUE`
- `SYNTHETIC_MACRO_EVIDENCE_ALLOWED=FALSE`

## Frozen V4 operationalization decision

The frozen 7-day winner was certified as a candidate family plus fixed feature, split, fitting, random-state, and evaluation contract. The historical implementation fits the scaler and frozen ExtraTrees candidate on the governed training window before producing a prediction.

For prospective operation, this governance distinguishes **contract-preserving operational refit** from **model redevelopment or tuning**.

A contract-preserving operational refit is authorized only when all of the following are true:

1. The candidate family remains exactly `V4_7D_VOLATILITY_STATE_EXTRA_TREES`.
2. The feature list and feature-construction logic remain exactly those frozen by the V4 model specification.
3. The chronological training/validation policy remains fixed and uses only data available at the prospective forecast timestamp.
4. The frozen random-state/configuration is reused.
5. No hyperparameter search, feature addition/removal, candidate comparison, threshold tuning, calibration redesign, target redesign, benchmark redesign, or post-holdout optimization occurs.
6. The 30-day and 365-day V4 horizons remain `NO_QUALIFIED_WINNER` and cannot be replaced by legacy M38 forecasts.
7. The resulting output is a prospective tactical evidence item, not a newly certified model tournament result.
8. The refit must not inspect any future outcome relative to the prospective observation timestamp.

This narrow refit authority does not reopen V4. It operationalizes the already frozen candidate contract against newly available prospective inputs.

Authority markers:

- `V4_7D_FROZEN_FAMILY_OPERATIONAL_REFIT_AUTHORIZED=TRUE`
- `V4_MODEL_SELECTION_REOPENED=FALSE`
- `V4_POST_HOLDOUT_TUNING_AUTHORIZED=FALSE`
- `V4_HYPERPARAMETER_SEARCH_AUTHORIZED=FALSE`
- `V4_FEATURE_CONTRACT_CHANGE_AUTHORIZED=FALSE`
- `V4_30D_QUALIFIED_PREDICTION_AUTHORIZED=FALSE`
- `V4_365D_QUALIFIED_PREDICTION_AUTHORIZED=FALSE`
- `LEGACY_M38_SUBSTITUTION_FOR_V4_ALLOWED=FALSE`

## Prospective forecast provenance requirements

Every prospective V4 7-day forecast used by the Bitcoin forward-evidence ledger must preserve at minimum:

- forecast timestamp and America/Chicago observation date;
- asset id;
- frozen winner id;
- repository commit SHA;
- database SHA-256 used for the fit and forecast;
- latest canonical Bitcoin source date used;
- exact feature list;
- feature values used for Bitcoin;
- training-window start/end;
- validation-window start/end where applicable;
- number of complete training and validation rows;
- random state;
- raw positive-class probability;
- predicted direction;
- evidence class and point-in-time limitation;
- explicit marker that model selection and tuning were not reopened.

If any required V4 feature is missing at the prospective timestamp, the V4 tactical forecast must remain missing. Missing values may not be filled to force a prediction.

## Module42 use

A historical Module42 recommendation may be preserved as historical context but must not be relabeled as current.

A new Module42 action may only be used if it is generated after refreshed governed upstream evidence and its execution is separately shown not to alter the frozen V4 model contract or recommendation-policy governance.

This gate does not authorize a Module42 rerun yet.

Authority markers:

- `MODULE42_HISTORICAL_CONTEXT_ALLOWED=TRUE`
- `MODULE42_RERUN_AUTHORIZED=FALSE`

## Portfolio state

Model portfolio weights remain distinct from personal holdings.

- No M35/M42/model weight may be treated as the user's actual current portfolio merely because a field is named `current_weight`.
- Personal portfolio/current-capital evidence remains missing until a separate governed authority is established.

Authority marker:

- `MODEL_PORTFOLIO_AS_PERSONAL_HOLDINGS_ALLOWED=FALSE`

## First prospective observation boundary

This governance does not itself capture observation #1.

Observation #1 remains blocked until:

1. incremental Module 1 refresh is executed and reviewed;
2. Module 6 sync is executed and reviewed;
3. refreshed Bitcoin price freshness is acceptable for the capture timestamp;
4. macro freshness/status is recorded without synthesis;
5. one prospective frozen-contract V4 7-day Bitcoin forecast is produced under the operational-refit rules above;
6. any Module42 field is either genuinely current or left historical/missing;
7. personal portfolio context is either governed or left missing;
8. the ledger is still at zero records immediately before capture.

Authority markers:

- `FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_AUTHORIZED=FALSE`
- `BTC_ETH_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE`
- `PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE`
- `AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE`

## Next gate

`BUILD_AND_VALIDATE_BITCOIN_LIVE_REFRESH_AND_V4_OPERATIONALIZATION_RUNNER`
