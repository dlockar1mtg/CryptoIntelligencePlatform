# Crypto Native Predictive Horizon Recovery V4 — 7d Final Holdout Closeout

## Experiment

`CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4`

## Scope

This closeout certifies the one-time final-holdout evaluation of the frozen 7-day development winner only. It does not reopen V4 development, authorize post-holdout tuning, open the 30-day or 365-day V4 final holdouts, open the V3 final holdout, change recommendation policy, or authorize production promotion.

## Frozen 7d winner

`V4_7D_VOLATILITY_STATE_EXTRA_TREES`

## Preserved evidence

- Final-holdout result artifact: `docs/predictive_horizon_recovery_v4_7d_final_holdout_results.json`
- Result SHA-256: `fe82f2b8cdfe817bfbb825cd2d97eb7d02711c8d1a2d3e5b3daf6c17fe756a48`
- Preservation commit: `77d6d7c64f0287e54fcdfca2f4a59b33c7139c5b`
- Development-results SHA-256: `a44e237112bf6521c8a770de120d4a0104731c280d7009568e6618cca1c1fbfb`
- Candidate-safe V4 manifest content SHA-256: `6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2`
- Evidence class: `HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME`
- Strict point-in-time claim allowed: false

## Final-holdout result

The frozen 7d winner passed the predeclared final-holdout confirmation gate.

Aggregate metrics:

- Final-holdout rows: 60
- Directional accuracy: 50.0%
- Training-window majority baseline accuracy: 36.666666666666664%
- Baseline-adjusted skill: +13.333333333333336 percentage points
- Assets with nonnegative baseline-adjusted skill: 6 of 6
- Single asset explains majority of positive gain: false
- Mean sign-strategy return after modeled 15 bps transaction cost: +0.40798767741205105%
- Complete prediction coverage: true
- Final-holdout confirmation: PASS

Asset-level directional accuracy:

- bitcoin: 80.0% versus 50.0% baseline
- ethereum: 90.0% versus 50.0% baseline
- chainlink: 60.0% versus 50.0% baseline
- xrp: 50.0% versus 50.0% baseline
- solana: 20.0% versus 20.0% baseline
- avalanche: 0.0% versus 0.0% baseline

Bitcoin and Ethereum together produced 17 correct directional predictions across 20 final-holdout observations. This is a practically important diagnostic because BTC and ETH are the primary intended investable Crypto assets, but the sample remains too small to claim that 80–90% accuracy will persist prospectively.

## Certification decision

`V4_7D_FINAL_HOLDOUT_CONFIRMATION=PASS`

The correct research claim is that the frozen V4 7d model demonstrated out-of-sample predictive skill relative to its frozen contemporaneous majority baseline and satisfied every predeclared V4 7d confirmation criterion.

This result does not establish universal Crypto forecasting skill, strict vintage point-in-time skill, recommendation-policy skill, portfolio-allocation superiority, or production readiness.

## Irreversible state

- V4 7d final holdout outcomes viewed: true
- V4 30d final holdout outcomes viewed: false
- V4 365d final holdout outcomes viewed: false
- V3 final holdout outcomes viewed: false
- Post-holdout V4 tuning allowed: false
- Recommendation policy changed: false
- Production promotion allowed: false
- V4 7d final-holdout rerun allowed: false

The V4 7d final holdout is consumed permanently. No rerun, threshold tuning, feature tuning, model tuning, or candidate substitution may use this holdout.

## Next governed work

1. Complete the remaining selection-neutral 365d development auxiliary diagnostics required by the frozen V4 contract without opening any 365d final-holdout outcomes.
2. Preserve V4 365d `NO_QUALIFIED_WINNER`; the strong `V4_365D_LONG_TREND_LOGIT` remains only a future V5 challenger.
3. After V4 contract completeness, evaluate Crypto recommendation-policy semantics and realized decision quality, with BTC and ETH as the primary practical investable assets while retaining the broader supported Crypto universe as contextual evidence.

`NEXT_GATE=COMPLETE_SELECTION_NEUTRAL_V4_365D_DEVELOPMENT_AUXILIARY_DIAGNOSTICS`
