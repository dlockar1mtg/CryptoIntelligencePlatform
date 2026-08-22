# BTC/ETH Forward Accumulation & Cycle Policy Contract

## Contract

`CRYPTO_BTC_ETH_FORWARD_ACCUMULATION_CYCLE_POLICY_V1`

## Purpose

This contract governs forward evidence collection and future recommendation-policy validation for Bitcoin and Ethereum within UIP.

It does not modify or reopen the frozen V4 predictive-model tournament, does not reinterpret prior holdout outcomes, and does not authorize production trading or autonomous execution.

## Investment mandate

Bitcoin and Ethereum are treated as long-duration accumulation assets rather than conventional short-horizon tactical trading assets.

The governing investment intent is:

- Bitcoin is the primary investable Crypto asset.
- Ethereum is the secondary investable Crypto asset.
- New Bitcoin capital deployed during the current accumulation thesis is generally evaluated against an approximately three-year intended holding period.
- Existing holdings and new-capital deployment are separate decisions.
- Short-term forecasts are primarily tactical entry-timing evidence for new capital, not automatic sell signals on existing long-duration holdings.
- Routine high-frequency trading is outside this mandate.
- No autonomous purchase or sale execution is authorized.

## Strategic cycle hypothesis

Bitcoin's approximately four-year halving cycle is a research hypothesis and prospective regime input, not a guaranteed calendar rule.

The current working cycle thesis is:

- 2026-2027: expected accumulation / post-peak reset and recovery window;
- 2028: expected halving / transition regime;
- 2029: expected late-cycle distribution opportunity window.

These year labels are not deterministic execution rules. The system must be able to contradict the calendar thesis when governed evidence indicates the cycle is early, late, structurally different, or no longer useful.

The strategic regime must ultimately be inferred from quantitative evidence, including where available:

- days since prior Bitcoin halving;
- estimated days until next halving;
- normalized position within the halving cycle;
- drawdown from prior cycle/all-time high;
- return from relevant cycle low;
- realized return since halving;
- momentum and trend structure;
- volatility and drawdown state;
- liquidity / macro regime evidence;
- valuation or on-chain evidence only when governed, historically available, and point-in-time safe;
- historical forward return distributions at comparable cycle ages.

No one feature, including calendar year or halving distance, may independently force a BUY or SELL.

## Three decision layers

Future Crypto recommendations must separate three distinct decisions.

### 1. Strategic regime

Allowed strategic states:

- `ACCUMULATE`
- `HOLD`
- `DISTRIBUTE`
- `INSUFFICIENT_EVIDENCE`

This layer answers whether the multi-year backdrop favors adding to long-duration exposure, maintaining existing exposure, or beginning staged distribution.

### 2. Tactical new-capital deployment

Allowed tactical states:

- `ACCELERATE`
- `NORMAL`
- `DELAY`
- `NO_NEW_CAPITAL`
- `INSUFFICIENT_EVIDENCE`

This layer controls timing and tranche aggressiveness for capital already intended for Crypto allocation.

A negative 7d forecast during a strategic `ACCUMULATE` regime should normally be evaluated as evidence to delay or reduce the size of the next tranche, not as an automatic instruction to sell existing BTC/ETH.

A positive 7d forecast during a strategic `ACCUMULATE` regime may support accelerating a planned tranche, subject to risk, valuation, and portfolio constraints.

### 3. Existing-position management

Allowed position-management states:

- `HOLD_EXISTING`
- `STAGED_DISTRIBUTION`
- `RISK_REDUCTION`
- `INSUFFICIENT_EVIDENCE`

The existing-position decision is separate from the new-capital decision.

`WAIT` or `DELAY` for new capital must never be interpreted as equivalent to liquidating an existing long-duration position.

## Relationship to existing Module 42 semantics

Module 42's current semantics are treated as operational context only until future policy certification:

- `HOLD`: preserve existing position; no immediate increase;
- `WAIT`: preserve existing position; block new capital until conditions improve;
- `REDUCE`: trim an existing long position;
- `AVOID`: do not initiate a new position;
- `BUY`, `STRONG_BUY`, and `SCALE_IN`: deploy new capital at different aggressiveness levels.

Future certification must preserve these economic meanings when constructing counterfactuals.

Module 44's simplified action-position mapping is not certification authority because it can treat HOLD/WAIT/AVOID as zero exposure and REDUCE as negative exposure, which is not equivalent to the intended long-only position-management semantics.

## Forward evidence ledger

Every governed BTC/ETH recommendation used for future certification must be captured prospectively and immutably with, at minimum:

- recommendation timestamp and operating date;
- asset id;
- source run ids and source hashes where available;
- current canonical price;
- current portfolio weight;
- available new capital allocated to Crypto, if applicable;
- strategic regime state;
- tactical new-capital state;
- existing-position state;
- original Module 42 action, if still produced;
- investment score;
- forecast confidence;
- relevant 7d/30d/90d/180d forecast values and uncertainty;
- long-cycle regime features available at decision time;
- entry strategy / tranche plan;
- intended target weight or maximum deployment;
- evidence status;
- explicit uncertainty / insufficiency flags;
- transaction-cost assumption;
- evidence-class / point-in-time limitations.

Historical recommendations may not be rewritten after outcomes mature.

## Outcome horizons

Prospective evidence should mature at exact calendar endpoints where canonical data exists:

- 7 days;
- 30 days;
- 90 days;
- 180 days;
- 365 days where useful for long-horizon diagnostics;
- approximately three-year forward outcomes for strategic accumulation-thesis validation when enough time has elapsed.

No nearest-date substitution, interpolation, or synthetic return may be used for certification unless separately governed in advance.

Missing exact outcomes remain missing.

## Strategic-horizon evaluation

Because new BTC capital is intended to be held for approximately three years during the current accumulation thesis, future validation must distinguish:

1. short-horizon entry quality; and
2. long-horizon investment-thesis quality.

A tactical entry may look poor after 7 or 30 days while still being successful over the intended multi-year holding horizon.

Therefore, short-horizon tactical validation must not be allowed to redefine long-horizon strategic success by itself.

Likewise, strong long-horizon returns must not be used to excuse consistently poor tactical entry timing if the tactical layer claims to add value.

## Required counterfactuals

Future BTC/ETH recommendation-policy validation must compare against predeclared, economically valid alternatives.

At minimum:

- `IMMEDIATE_DEPLOYMENT`: invest planned capital immediately when available;
- `FIXED_DCA`: deploy equal planned tranches on a fixed calendar schedule independent of signal;
- `BTC_BUY_AND_HOLD`: Bitcoin benchmark for long-duration capital;
- `BTC_ETH_BUY_AND_HOLD`: frozen BTC/ETH allocation benchmark;
- `BTC_DOMINANT_BTC_ETH`: a predeclared BTC-dominant allocation benchmark, frozen before scoring;
- `UIP_TACTICAL_ACCUMULATION`: strategic regime plus tactical accelerate/normal/delay decisions;
- `CASH_WHILE_WAITING`: only for undeployed new capital during a governed delay window, never as a replacement for existing holdings.

No benchmark may be chosen after outcome inspection.

## Transaction costs

All tactical counterfactuals involving purchase or sale actions must include a predeclared transaction-cost/slippage assumption.

The existing 15 bps diagnostic convention may be used only if frozen before scoring for the relevant test. If a different cost assumption is adopted, it must be governed before outcome evaluation.

## Cycle-regime research gate

Before the strategic cycle layer receives policy authority, a separate historical Bitcoin cycle study must quantify the proposed four-year structure using canonical historical price data.

The study must evaluate, at minimum:

- historical halving dates;
- cycle age at major troughs and peaks;
- drawdown from prior cycle high;
- recovery from cycle low;
- forward 1-year, 2-year, and 3-year returns by cycle phase where data support them;
- robustness across mature cycles;
- sensitivity to exact phase definitions;
- whether apparent cycle effects remain meaningful after accounting for the very small number of historical cycles.

The study must explicitly report small-sample uncertainty.

A visually recognizable pattern is not sufficient for certification.

## Evidence sufficiency for policy-skill claims

No BTC/ETH recommendation-policy skill claim is allowed until prospective evidence has sufficient independence, maturity, and action diversity.

Minimum certification design must be frozen before scoring and should include thresholds for:

- distinct recommendation dates;
- matured exact outcomes by horizon;
- BTC and ETH separately;
- sufficient representation of multiple tactical states;
- sufficient representation of more than one strategic regime where feasible;
- no single date/regime dominating positive value;
- transaction-cost-adjusted economic value;
- robustness against simple DCA and BTC-centered benchmarks;
- risk / drawdown effects;
- uncertainty and confidence calibration.

The current preserved historical inventory remains:

`INSUFFICIENT_EVIDENCE_FOR_POLICY_SKILL`

and may not be retroactively upgraded from the same limited observations.

## Asset scope

Primary capital-decision certification scope:

- Bitcoin
- Ethereum

Contextual/secondary assets may continue to provide breadth, regime, or comparative evidence, but SOL/XRP/LINK/AVAX may not automatically receive capital-allocation authority from this BTC/ETH mandate.

## Relationship to frozen V4 predictive evidence

This contract does not alter the frozen V4 decisions.

Preserved state remains:

- 7d: `V4_7D_VOLATILITY_STATE_EXTRA_TREES` confirmed on the one-time final holdout;
- 30d: `NO_QUALIFIED_WINNER`;
- 365d: `NO_QUALIFIED_WINNER`;
- 365d Long Trend: reserved as a future V5 challenger;
- V4 30d and 365d final holdouts remain sealed;
- V3 final holdout remains sealed;
- post-holdout V4 tuning remains prohibited.

The 7d model may be used prospectively as one tactical-entry input after implementation governance, but its predictive certification does not itself certify recommendation-policy skill.

## Production boundary

This contract authorizes evidence collection and research design only.

It does not authorize:

- autonomous trading;
- automatic order placement;
- retroactive recommendation rewriting;
- threshold optimization on outcomes already viewed;
- reopening consumed/sealed holdouts;
- changing current production policy without separate governance;
- deterministic buying or selling based only on calendar year or halving date.

## Current authority

`BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED`

## Next gates

1. `VALIDATE_BTC_ETH_FORWARD_ACCUMULATION_CYCLE_POLICY_CONTRACT`
2. `DESIGN_BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY`
3. `BUILD_FORWARD_BTC_ETH_RECOMMENDATION_EVIDENCE_LEDGER`
4. Continue prospective evidence collection while UIP development proceeds.
