# Bitcoin Diminishing-Return Transformation Design V1

## Design ID

`BITCOIN_DIMINISHING_RETURN_TRANSFORMATION_V1`

## Purpose

Evaluate bounded methods for compressing historical Bitcoin
approximately three-year cycle returns before those returns contribute
to the separate cycle-aware strategic forecast layer.

This design is frozen before any current-cycle strategic forecast is
selected.

## Historical authority

Only completed governed halving cycles may be used for transformation
validation.

The incomplete 2024 -> 2028 cycle is excluded from model selection.

The independent evidentiary unit remains the completed halving cycle.

Monthly observations within one cycle are not independent cycles.

## Comparable phases

The primary long-duration evidence pool consists of:

- `POST_HALVING_YEAR_2`
- `PRE_HALVING_YEAR`

using exact approximately 1095-day outcomes already preserved by the
governed extended-history study.

## Validation structure

Historical validation is walk-forward.

Cycle 1 may establish initial evidence but cannot be independently
validated because no earlier completed cycle exists.

Cycle 2 must be evaluated using Cycle 1 evidence only.

Cycle 3 must be evaluated using Cycles 1-2 evidence only.

No Cycle 3 observations may be used to construct the Cycle 3 forecast
band.

The incomplete current cycle may not participate.

## Candidate transformation family

Transformations operate on wealth multiples.

For an historical return `r` expressed as a decimal:

`wealth_multiple = 1 + r`

Transformed wealth is:

`transformed_wealth = wealth_multiple ^ gamma`

and transformed return is:

`transformed_return = transformed_wealth - 1`

Three predeclared candidates are evaluated:

- `WEALTH_POWER_033`: gamma = 1/3
- `WEALTH_POWER_050`: gamma = 1/2
- `WEALTH_POWER_067`: gamma = 2/3

The transformations compress exceptionally large early-cycle Bitcoin
returns while preserving ordering and positive-return structure.

The gamma values are frozen before validation and may not be altered
after viewing results.

## Strategic band construction

For each walk-forward training set:

- strategic lower = transformed P25;
- strategic base = transformed P50;
- strategic upper = transformed P75.

Monthly anchors estimate the historical distribution.

They do not increase the independent completed-cycle sample size.

## Validation targets

For each held-out completed cycle and phase, evaluate:

- held-out median return;
- strategic-base absolute error;
- P25-P75 band coverage;
- whether strategic bull captures held-out median;
- whether strategic bear remains below held-out median;
- consistency across held-out cycles.

## Selection rule

No candidate may be selected using the incomplete 2024 -> 2028 cycle.

A diagnostic leader may be identified from completed-cycle
walk-forward validation.

Because only two independent held-out cycles are available, no
single transformation receives production certification from this
study.

If robustness does not clearly favor one candidate, a bounded
ensemble should be considered rather than forcing a winner.

## Governance

`CURRENT_CYCLE_USED_FOR_SELECTION=FALSE`

`CURRENT_CYCLE_OUTCOMES_USED_FOR_SELECTION=FALSE`

`MONTHLY_ROWS_TREATED_AS_INDEPENDENT_CYCLES=FALSE`

`PRODUCTION_FORECAST_CHANGE_AUTHORIZED=FALSE`

`MODULE42_CHANGED=FALSE`

## Next gate

`REVIEW_BTC_DIMINISHING_RETURN_VALIDATION_AND_SELECT_RESEARCH_TRANSFORMATION`
