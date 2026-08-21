# Bitcoin Strategic Regime Forward Evidence Contract V1

## Contract

`BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_CONTRACT_V1`

## Purpose

Define the prospective evidence contract for using Bitcoin cycle phase as one governed strategic-regime input without converting historical cycle regularity into a deterministic calendar trading rule.

This contract follows the validated `BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE` governance decision and the preserved V2 historical result `PATTERN_SUPPORTED_DESCRIPTIVELY`.

## Current authority boundary

Authorized now:

- Bitcoin cycle phase may contribute strategic context to future Bitcoin recommendation records.
- The strategic layer may classify evidence into `ACCUMULATE`, `HOLD`, `DISTRIBUTE`, or `INSUFFICIENT_EVIDENCE` only when the full governed evidence set is considered.
- The certified V4 7-day model may contribute tactical entry-timing evidence for new capital.

Not authorized now:

- calendar-only BUY or SELL decisions;
- autonomous execution;
- production policy changes from this contract alone;
- certification of Bitcoin recommendation-policy skill;
- reopening or retuning frozen V4 model selection;
- treating the four-year cycle as causal, guaranteed, or deterministic.

`BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE`

## Evidence layers

Future Bitcoin recommendation evidence must remain separated into three decision layers.

### 1. Strategic regime

Allowed states:

- `ACCUMULATE`
- `HOLD`
- `DISTRIBUTE`
- `INSUFFICIENT_EVIDENCE`

The strategic state must consider multiple governed signals. Cycle phase is one input, not a standalone decision rule.

Minimum strategic evidence categories when available:

- governed Bitcoin cycle phase;
- drawdown from prior running or all-time high;
- medium-term and long-term trend/momentum;
- volatility and drawdown state;
- macro/liquidity evidence;
- governed valuation or on-chain evidence where point-in-time-safe inputs become available;
- historical forward-return context appropriate to the current regime;
- uncertainty and evidence-quality limitations.

No missing evidence may be replaced with synthetic neutral values, zeros, or worst-case placeholders.

### 2. Tactical new-capital timing

Allowed states:

- `ACCELERATE`
- `NORMAL`
- `DELAY`
- `NO_NEW_CAPITAL`
- `INSUFFICIENT_EVIDENCE`

The certified V4 7-day Bitcoin model may affect tactical timing or tranche aggressiveness for planned new capital.

A negative short-term forecast in a favorable strategic accumulation regime normally supports delaying or reducing the next tranche rather than selling existing long-duration holdings.

A positive short-term forecast in a favorable strategic accumulation regime may support accelerating a previously planned tranche, subject to portfolio limits and other live evidence.

Short-term forecasts do not independently define the long-horizon strategic regime.

### 3. Existing-position management

Allowed states:

- `HOLD_EXISTING`
- `STAGED_DISTRIBUTION`
- `RISK_REDUCTION`
- `INSUFFICIENT_EVIDENCE`

Existing holdings must be evaluated separately from undeployed new capital.

A tactical negative forecast is not by itself sufficient to move an existing long-duration Bitcoin position to distribution or risk reduction.

Distribution evidence must require strategic-regime deterioration or late-cycle evidence supported by more than calendar position alone.

## Cycle-phase semantics

The historically supported structural pattern may be represented prospectively as a regime feature, including:

- days since the most recent halving;
- normalized position within the current halving interval;
- descriptive phase label;
- distance from historically observed expansion/reset/recovery regions;
- whether current price behavior is confirming or contradicting the historical phase pattern.

The current working calendar labels remain descriptive hypotheses rather than deterministic execution rules:

- 2026: expected post-halving reset / accumulation context;
- 2027: expected pre-halving recovery / accumulation context;
- 2028: expected transition / halving context;
- 2029: potential late-cycle distribution opportunity.

These labels must be contradicted when live evidence warrants.

`BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE`

## Prospective immutable evidence ledger

Each governed Bitcoin recommendation observation must preserve, at minimum:

- observation timestamp and operating date;
- asset identifier;
- source run identifiers and hashes;
- observed Bitcoin price;
- current Bitcoin portfolio weight;
- undeployed capital available to Bitcoin;
- current strategic-regime state;
- current tactical new-capital state;
- current existing-position state;
- original Module42 action where available;
- recommendation score where available;
- V4 7-day forecast output and confidence where available;
- 30d, 90d, and 180d forecast values where governed and available;
- cycle phase and numeric cycle-position features;
- drawdown-from-high features;
- medium/long trend features;
- volatility/drawdown-state features;
- macro/liquidity evidence references;
- valuation/on-chain evidence references where governed and available;
- planned entry/tranche structure;
- current target/max deployment ceiling;
- explicit uncertainty notes;
- evidence class and point-in-time limitations;
- transaction-cost assumptions;
- whether the record concerns new capital, existing holdings, or both.

Records must be immutable once created except through a separately governed correction record. Historical recommendation states may not be retroactively rewritten after outcomes mature.

## Outcome maturation

Prospective outcomes must be attached only when exact governed endpoints mature.

Required tactical/policy horizons:

- 7 calendar days;
- 30 calendar days;
- 90 calendar days;
- 180 calendar days.

Strategic diagnostics should also retain:

- 365-day outcomes where useful;
- approximately three-year outcomes when matured and exact endpoints exist.

No nearest-date substitution, interpolation, synthetic return, forward-fill, backward-fill, or zero imputation is permitted.

Missing endpoint outcomes remain missing.

## Counterfactuals

Recommendation-policy evaluation must predeclare and retain the following counterfactuals where applicable:

- `IMMEDIATE_DEPLOYMENT`
- `FIXED_DCA`
- `BTC_BUY_AND_HOLD`
- `BTC_ETH_BUY_AND_HOLD`
- `BTC_DOMINANT_BTC_ETH`
- `UIP_TACTICAL_ACCUMULATION`
- `CASH_WHILE_WAITING` only for undeployed new capital

Benchmarks may not be selected or discarded after outcomes are observed.

## Evaluation separation

Three distinct questions must remain separate:

1. Did the V4 short-term forecast add tactical predictive skill?
2. Did the strategic-regime classification improve long-duration accumulation or distribution decisions relative to predeclared counterfactuals?
3. Did the combined recommendation policy improve outcomes after transaction costs without relying on one isolated market regime or action type?

Historical cycle V2 evidence answers none of these prospective policy-skill questions by itself.

## Prospective certification requirements

Bitcoin recommendation-policy skill remains uncertified until enough independent forward evidence exists to evaluate both timing and strategic-regime decisions.

Future certification must require, at minimum:

- prospective records created before outcomes are known;
- exact outcome maturation;
- sufficient action diversity rather than one repeated state;
- separate evaluation of new-capital and existing-position decisions;
- explicit transaction costs;
- predeclared counterfactuals;
- no post-hoc threshold tuning on matured evaluation observations;
- no single observation, asset state, or short market window dominating the result;
- uncertainty appropriate to the small number of independent Bitcoin cycles.

No fixed minimum sample size is invented in this contract. A later validation design must predeclare the sample-size and diversity gates before policy-skill scoring.

## Interaction with Module42 and Module44

Module42 remains the semantic authority for existing recommendation actions where those actions are recorded.

Module44 remains diagnostic only and must not replace Module42 semantics for certification.

The strategic-regime layer may contextualize Module42 recommendations but does not silently rewrite historical Module42 outputs.

## Portfolio and execution boundary

The configured Crypto allocation is a ceiling, not an automatic deployment target.

New capital deployment requires an allowed tactical state within an allowed strategic regime and must remain within governed portfolio limits.

Existing holdings are not automatically sold because new-capital deployment is delayed.

No autonomous purchase or sale execution is authorized.

## Frozen historical evidence

The strategic cycle input is supported by the preserved V2 result SHA-256:

`ed22cfb5eb83ac860527ca3c47c6b8d9e10a7cb3827ebb89ebd33fe8a324b9ca`

Historical interpretation:

`PATTERN_SUPPORTED_DESCRIPTIVELY`

Independent completed cycles evaluated:

`3`

The sample-size warning remains mandatory.

## Authority markers

`BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE`

`BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE`

`BITCOIN_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE`

`BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE`

`V4_MODEL_SELECTION_REOPENED=FALSE`

`PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE`

`AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE`

## Next gate

`BUILD_AND_VALIDATE_BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER`
