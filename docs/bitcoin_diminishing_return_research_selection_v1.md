# Bitcoin Diminishing-Return Research Selection V1

## Decision ID

`BITCOIN_DIMINISHING_RETURN_RESEARCH_SELECTION_V1`

## Validation finding

Completed-cycle walk-forward validation did not support exclusive
selection of one transformation.

Diagnostic ranking:

1. `WEALTH_POWER_033`
2. `WEALTH_POWER_050`
3. `WEALTH_POWER_067`

`WEALTH_POWER_033` produced the lowest central error but insufficient
upper-band capture.

`WEALTH_POWER_067` improved upper-band capture but materially increased
central error.

Therefore:

`SINGLE_TRANSFORMATION_RESEARCH_SELECTION=NOT_AUTHORIZED`

## Research ensemble

The research method is:

`BTC_DIMINISHING_RETURN_RESEARCH_METHOD=EQUAL_WEIGHT_WEALTH_POWER_ENSEMBLE`

Components:

- `WEALTH_POWER_033`: 1/3
- `WEALTH_POWER_050`: 1/3
- `WEALTH_POWER_067`: 1/3

Weights are intentionally equal.

They were not optimized using the historical validation results.

`ENSEMBLE_WEIGHTS_OPTIMIZED_AFTER_VALIDATION=FALSE`

## Calculation

For each historical forward-return observation:

1. transform wealth with gamma 1/3;
2. transform wealth with gamma 1/2;
3. transform wealth with gamma 2/3;
4. average the three transformed returns.

The resulting historical ensemble distribution is summarized as:

- P25 = cycle lower component;
- P50 = cycle center component;
- P75 = cycle upper component.

These are cycle components only.

They are not final strategic forecasts.

## Current-cycle boundary

The incomplete 2024 -> 2028 cycle was not used to choose the
transformation family or ensemble weights.

`CURRENT_CYCLE_USED_FOR_ENSEMBLE_SELECTION=FALSE`

## Corroboration

Before cycle evidence may become a final strategic forecast, it must be
considered with:

- native predictive evidence;
- trend and risk evidence;
- macro/liquidity evidence;
- valuation/on-chain evidence when available.

Missing evidence remains missing.

## Production boundary

`CYCLE_COMPONENT_IS_FINAL_STRATEGIC_FORECAST=FALSE`

`PRODUCTION_FORECAST_CHANGE_AUTHORIZED=FALSE`

`MODULE42_CHANGED=FALSE`

`AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE`

## Next gate

`BUILD_CURRENT_BTC_CYCLE_COMPONENT_AND_INVENTORY_CORROBORATING_EVIDENCE`
