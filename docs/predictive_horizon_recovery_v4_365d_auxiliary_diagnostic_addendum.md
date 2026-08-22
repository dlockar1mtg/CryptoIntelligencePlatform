# Crypto Native Predictive Horizon Recovery V4 — 365d Auxiliary Diagnostic Addendum

## Purpose

This addendum completes the frozen V4 contract obligation to report 365-day auxiliary diagnostics without reopening model selection or exposing any sealed final holdout.

The governing candidate contract requires V4 365d to report, as diagnostics only:

- forward return exceeding +15%;
- forward return relative to Bitcoin where meaningful for non-Bitcoin assets;
- realized forward drawdown where available from point-in-time-safe price history.

The +15% diagnostic was already present in V4 development evidence. This addendum governs the remaining BTC-relative and realized-forward-drawdown diagnostics and any consolidated reporting of all three diagnostics.

## Selection-neutral boundary

These diagnostics are development-only and selection-neutral.

They MUST NOT:

- change any V4 development candidate metric already used by the frozen winner gate;
- change `development_selection_gate_pass` for any candidate;
- change `choose_winner` behavior;
- create a winner for 365d;
- reopen the frozen V4 365d `NO_QUALIFIED_WINNER` decision;
- tune or replace `V4_365D_LONG_TREND_LOGIT` or any other V4 candidate;
- access, derive, summarize, score, or otherwise expose V4 365d final-holdout outcomes;
- access V4 30d final-holdout outcomes;
- access V3 final-holdout outcomes;
- modify the source database;
- authorize recommendation-policy changes or production promotion.

`winner_gate_affected=false` is mandatory in the diagnostic result.

## Governed evidence scope

Use only the 365d V4 development origins already frozen in the candidate-safe V4 manifest.

Supported 365d assets:

- bitcoin
- ethereum
- solana
- chainlink
- avalanche

XRP365 is unsupported and MUST NOT be synthesized.

For each supported asset, the diagnostic scope is exactly the frozen 50 V4 development origins. No final-holdout origin may be included.

The existing V2 consumed origins, V3 development origins, V3 final-holdout origins, and V4 final-holdout origins remain excluded according to the frozen manifest and evidence contracts.

## Exact-calendar rule

All forward outcomes MUST use the governed exact 365-calendar-day target endpoint. No nearest-date approximation, interpolation, shortened horizon, or synthetic endpoint is allowed.

If a required exact endpoint or path observation is unavailable under the governed price history, the value remains missing and coverage MUST be reported explicitly.

## Diagnostic 1 — Forward return exceeding +15%

For each development origin:

`forward_return_exceeds_15pct = actual_forward_365d_return_pct > 15.0`

This diagnostic is already represented in the development evidence where available. Consolidated reporting may restate it but MUST NOT use it to redefine model selection.

Report at minimum:

- eligible rows;
- observed rows;
- missing rows;
- observed exceedance count;
- observed exceedance rate;
- per-asset coverage and exceedance rate.

## Diagnostic 2 — BTC-relative forward return

This diagnostic applies only to non-Bitcoin supported assets.

For each non-Bitcoin development origin, use Bitcoin's governed price history at the same exact forecast origin and the same exact +365-calendar-day target date.

Define:

`btc_relative_forward_return_pct = asset_forward_365d_return_pct - bitcoin_forward_365d_return_pct`

and

`beat_bitcoin = btc_relative_forward_return_pct > 0`

No date shifting or target approximation is allowed. If Bitcoin lacks the required exact origin or exact target price, the BTC-relative value remains missing.

Report at minimum:

- eligible non-Bitcoin rows;
- observed rows;
- missing rows;
- beat-Bitcoin count and rate;
- mean BTC-relative forward return;
- median BTC-relative forward return;
- per-asset coverage, beat rate, mean, and median relative return.

Bitcoin itself MUST be reported as `not_applicable` for BTC-relative diagnostics rather than given a synthetic zero.

## Diagnostic 3 — Realized forward drawdown

For each supported 365d development origin, use the governed price path from the forecast-origin price through the exact +365-calendar-day target date, inclusive.

Define each path return relative to the origin price as:

`path_return = path_price / origin_price - 1`

Define realized forward drawdown from the origin as:

`realized_forward_drawdown_pct = 100 * min(path_return)`

This measures the worst price decline relative to the forecast-origin price during the realized forward year. It is not a trailing drawdown feature and MUST NOT use future information as a model input.

If the origin price, exact target endpoint, or required governed path cannot be established, the value remains missing.

Report at minimum:

- eligible rows;
- observed rows;
- missing rows;
- mean realized forward drawdown;
- median realized forward drawdown;
- worst realized forward drawdown;
- per-asset coverage and drawdown summary.

## Model-conditioned reporting

The diagnostics MAY be summarized by frozen V4 365d candidate prediction/sign using already-preserved V4 development predictions if this can be done without refitting, retuning, or changing candidate selection.

Any such conditioned analysis is descriptive only. It MUST be labeled `selection_neutral=true` and `winner_gate_affected=false`.

No auxiliary metric may be substituted for the original 365d directional winner gate.

## Required integrity controls

Before execution, the diagnostic runner MUST verify:

- authoritative V4 development-results SHA-256 is `a44e237112bf6521c8a770de120d4a0104731c280d7009568e6618cca1c1fbfb`;
- candidate-safe V4 manifest content SHA-256 is `6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2`;
- V4 365d development decision is `NO_QUALIFIED_WINNER`;
- V4 365d final-holdout outcomes remain unopened;
- V4 30d final-holdout outcomes remain unopened;
- V3 final-holdout outcomes remain unopened;
- V4 7d final-holdout result remains preserved and consumed;
- post-holdout tuning remains prohibited.

The runner MUST hash all governed source evidence before and after execution and fail closed if any source evidence or the source database changes.

## Output requirements

The preserved diagnostic artifact MUST explicitly record:

- `experiment_id=CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4`;
- `diagnostic_scope=365D_DEVELOPMENT_AUXILIARY_ONLY`;
- `selection_neutral=true`;
- `winner_gate_affected=false`;
- `v4_365d_development_decision=NO_QUALIFIED_WINNER`;
- `v4_7d_final_holdout_outcomes_viewed=true`;
- `v4_30d_final_holdout_outcomes_viewed=false`;
- `v4_365d_final_holdout_outcomes_viewed=false`;
- `v3_final_holdout_outcomes_viewed=false`;
- `post_holdout_tuning_allowed=false`;
- `recommendation_policy_changed=false`;
- `production_promotion_allowed=false`;
- exact coverage counts for every diagnostic;
- no synthetic replacement of missing values.

## Interpretation boundary

These diagnostics may improve understanding of the 365d development evidence and help define future V5 research questions. They cannot strengthen V4 into a 365d winner and cannot weaken or modify the already-consumed V4 7d final-holdout result.

`V4_365D_LONG_TREND_LOGIT` remains reserved as a future V5 challenger because its V4 development evidence was strong but failed the frozen selection gate due to single-asset positive-gain concentration.

## Next gate

`BUILD_AND_VALIDATE_SELECTION_NEUTRAL_V4_365D_DEVELOPMENT_AUXILIARY_DIAGNOSTIC_RUNNER`
