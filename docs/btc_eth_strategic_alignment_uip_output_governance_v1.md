# BTC/ETH Strategic Alignment & UIP Output Governance V1

## Governance

`CRYPTO_BTC_ETH_STRATEGIC_ALIGNMENT_UIP_OUTPUT_V1`

## Purpose

Align final Crypto behavior with the already-governed long-duration BTC/ETH mandate before prospective outcome maturation begins.

This governance does not reopen any consumed or sealed predictive holdout, does not certify recommendation-policy skill, does not authorize autonomous execution, and does not rewrite the first prospective Bitcoin observation.

## Asset roles

- Bitcoin is the **PRIMARY_LONG_DURATION_CRYPTO_ASSET**.
- Ethereum is the **SECONDARY_LONG_DURATION_CRYPTO_ASSET**.
- SOL, XRP, LINK, and AVAX remain **CONTEXTUAL_SECONDARY_CRYPTO_ASSETS** for breadth, regime, comparative, or research evidence unless separately promoted through governance and validation.
- No fixed BTC/ETH capital split is invented here. Primary/secondary status is semantic and priority-bearing, not a synthetic percentage allocation.

`BTC_PRIMARY=TRUE`

`ETH_SECONDARY=TRUE`

`FIXED_BTC_ETH_ALLOCATION_INVENTED=FALSE`

## Long-duration decision semantics

BTC and ETH must not be represented to UIP as ordinary short-horizon trading assets.

For BTC and ETH, the authoritative recommendation representation contains three distinct layers:

1. strategic regime: `ACCUMULATE`, `HOLD`, `DISTRIBUTE`, or `INSUFFICIENT_EVIDENCE`;
2. tactical new-capital timing: `ACCELERATE`, `NORMAL`, `DELAY`, `NO_NEW_CAPITAL`, or `INSUFFICIENT_EVIDENCE`;
3. existing-position management: `HOLD_EXISTING`, `STAGED_DISTRIBUTION`, `RISK_REDUCTION`, or `INSUFFICIENT_EVIDENCE`.

Module42 remains preserved as platform-native context but may not silently replace these three layers for BTC/ETH in the final UIP-facing strategic interpretation.

`MODULE42_BTC_ETH_FINAL_AUTHORITY=FALSE`

`MODULE42_CONTEXT_PRESERVED=TRUE`

## Bitcoin four-year cycle handling

Bitcoin's approximately four-year halving cycle remains a quantitative strategic-regime input supported descriptively by the preserved V2 historical study.

For Bitcoin, governed cycle evidence may include:

- most recent observed halving anchor;
- days since halving;
- defensible cycle-position features where governed;
- historical phase evidence;
- drawdown and trend confirmation;
- macro/liquidity corroboration;
- volatility/risk evidence;
- point-in-time-safe valuation/on-chain evidence when available.

No cycle feature, calendar year, or halving distance may independently force a buy or sell state.

`BITCOIN_CYCLE_STRATEGIC_INPUT_AUTHORIZED=TRUE`

`BITCOIN_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE`

## Ethereum relationship to the Bitcoin cycle

Ethereum does not receive a synthetic Ethereum four-year cycle rule.

Bitcoin cycle phase may be recorded for Ethereum only as **cross-market strategic context**. Ethereum state assignment must also consider ETH-specific evidence when available, including:

- ETH price/trend/momentum;
- ETH drawdown and volatility;
- ETH/BTC relative strength;
- market breadth and liquidity/macro conditions;
- governed ETH-specific valuation/network evidence when available;
- portfolio/deployment context.

Bitcoin cycle context alone may not select `ACCUMULATE`, `HOLD`, or `DISTRIBUTE` for Ethereum.

`ETH_BITCOIN_CYCLE_CONTEXT_ALLOWED=TRUE`

`ETH_BITCOIN_CYCLE_ACTION_RULE_ALLOWED=FALSE`

`SYNTHETIC_ETH_HALVING_CYCLE_ALLOWED=FALSE`

## Prospective evidence

Bitcoin already has one immutable prospective record in `BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1`.

Ethereum must begin its own append-only prospective evidence ledger before future BTC/ETH policy-skill certification.

The first Ethereum observation is authorized only with fail-closed state assignment. If current evidence cannot justify a stronger state, all applicable layers must remain `INSUFFICIENT_EVIDENCE`.

The first Ethereum record may preserve current ETH price and exact-date ETH market features available from the governed canonical database, Bitcoin-cycle context from the already-preserved Bitcoin observation, and current macro freshness metadata. It must not invent a live V4 Ethereum forecast, portfolio holdings, deployment amounts, Module42 action, valuation evidence, or missing outcomes.

`FIRST_ETHEREUM_PROSPECTIVE_OBSERVATION_AUTHORIZED=TRUE`

`ETH_V4_LIVE_FORECAST_SYNTHESIZED=FALSE`

`MISSING_EVIDENCE_SYNTHESIZED=FALSE`

## Macro-regime clarification

The August 21 Bitcoin prospective refresh intentionally ran Module 1 plus Module 6 only. Module 2 is the platform component that calculates and writes `macro_regime_daily` and `latest_macro_regime`.

The normal governed production sequence runs Module 1 collection followed by Module 2 as part of core analytics. Therefore the July 28 derived macro regime in Bitcoin observation #1 is preserved correctly as stale observation-time evidence, but it does not by itself establish a standing defect in the Module 2 macro formula.

No retroactive change to Bitcoin observation #1 is permitted.

`BITCOIN_OBSERVATION_1_REWRITE_AUTHORIZED=FALSE`

`MODULE2_MACRO_FORMULA_REPAIR_AUTHORIZED=FALSE`

## UIP output boundary

The legacy universal `recommendations.csv` remains compatibility output and may continue to preserve Module42-native recommendations for all supported assets.

A separate BTC/ETH strategic UIP overlay must be produced for long-duration interpretation. It must:

- contain BTC and ETH only;
- identify BTC as primary and ETH as secondary;
- expose the three decision layers separately;
- preserve native Module42 context when available without treating it as final authority;
- expose Bitcoin cycle context for BTC directly and for ETH only as cross-market context;
- expose evidence sufficiency/certification state;
- avoid invented target weights;
- avoid autonomous execution language.

The UIP consumer should prefer the strategic overlay for BTC/ETH interpretation while retaining legacy recommendations for lineage and compatibility.

`LEGACY_RECOMMENDATIONS_DATASET_DELETED=FALSE`

`BTC_ETH_STRATEGIC_OVERLAY_REQUIRED=TRUE`

`PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE`

`AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE`

`BTC_ETH_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE`

## Next gates

1. `BUILD_AND_VALIDATE_ETHEREUM_PROSPECTIVE_LEDGER_V1`
2. `CAPTURE_FIRST_ETHEREUM_PROSPECTIVE_OBSERVATION`
3. `BUILD_AND_VALIDATE_BTC_ETH_UIP_STRATEGIC_OVERLAY_V1`
4. `VALIDATE_BTC_ETH_STRATEGIC_ALIGNMENT_CLOSEOUT`
