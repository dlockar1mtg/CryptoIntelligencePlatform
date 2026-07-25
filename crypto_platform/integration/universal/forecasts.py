"""Universal forecast transformations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta
import math

from .analytics_models import (
    SourceCalibratedForecast,
    SourcePriceProjection,
)
from .context import ExportContext
from .normalization import (
    horizon_days_to_months,
    normalize_probability,
    percentage_points_to_decimal,
    universal_crypto_asset_id,
)


FORECAST_COLUMNS = [
    "contract_version",
    "platform_id",
    "run_id",
    "universal_asset_id",
    "forecast_origin_date",
    "forecast_horizon_months",
    "forecast_date",
    "current_value",
    "forecast_value_base",
    "forecast_value_bear",
    "forecast_value_bull",
    "expected_total_return",
    "expected_cagr",
    "probability_positive_return",
    "forecast_confidence",
    "forecast_method",
    "scenario_name",
    "model_version",
    "generated_at_utc",
]


@dataclass(frozen=True)
class UniversalForecastRecord:
    contract_version: str
    platform_id: str
    run_id: str
    universal_asset_id: str
    forecast_origin_date: object
    forecast_horizon_months: int
    forecast_date: object
    current_value: float | None
    forecast_value_base: float | None
    forecast_value_bear: float | None
    forecast_value_bull: float | None
    expected_total_return: float | None
    expected_cagr: float | None
    probability_positive_return: float | None
    forecast_confidence: float | None
    forecast_method: str
    scenario_name: str | None
    model_version: str | None
    generated_at_utc: str

    def to_dict(
        self,
    ) -> dict[str, object]:
        return asdict(self)


def _confidence_to_score(
    value: float | None,
) -> float | None:
    if value is None or not math.isfinite(value):
        return None

    score = value * 100.0 if value <= 1.0 else value

    if score < 0.0 or score > 100.0:
        raise ValueError(
            "Forecast confidence must normalize "
            "between 0 and 100."
        )

    return score


def _apply_return(
    current_value: float | None,
    return_pct: float | None,
) -> float | None:
    if current_value is None or return_pct is None:
        return None

    return current_value * (
        1.0 + return_pct / 100.0
    )


def _expected_cagr(
    total_return: float | None,
    horizon_months: int,
) -> float | None:
    if total_return is None:
        return None

    growth_factor = 1.0 + total_return

    if growth_factor <= 0.0:
        return None

    return (
        growth_factor
        ** (12.0 / horizon_months)
        - 1.0
    )


def transform_calibrated_forecast(
    source: SourceCalibratedForecast,
    context: ExportContext,
) -> UniversalForecastRecord:
    months = horizon_days_to_months(
        source.horizon_days
    )

    total_return = (
        percentage_points_to_decimal(
            source.predicted_return_pct
        )
    )

    probability = (
        None
        if source.probability_positive is None
        else normalize_probability(
            source.probability_positive
        )
    )

    return UniversalForecastRecord(
        contract_version=context.contract_version,
        platform_id=context.platform_id,
        run_id=context.run_id,
        universal_asset_id=(
            universal_crypto_asset_id(
                source.asset_id
            )
        ),
        forecast_origin_date=source.forecast_date,
        forecast_horizon_months=months,
        forecast_date=(
            source.forecast_date
            + timedelta(
                days=source.horizon_days
            )
        ),
        current_value=source.current_price,
        forecast_value_base=_apply_return(
            source.current_price,
            source.predicted_return_pct,
        ),
        forecast_value_bear=_apply_return(
            source.current_price,
            source.lower_return_pct,
        ),
        forecast_value_bull=_apply_return(
            source.current_price,
            source.upper_return_pct,
        ),
        expected_total_return=total_return,
        expected_cagr=_expected_cagr(
            total_return,
            months,
        ),
        probability_positive_return=probability,
        forecast_confidence=(
            _confidence_to_score(
                source.forecast_confidence
            )
        ),
        forecast_method=(
            source.calibration_method
            or "calibrated_forecast"
        ),
        scenario_name=(
            f"{source.forecast_status or 'calibrated_base'}"
            f"_{source.horizon_days}D"
        ),
        model_version=source.model_version,
        generated_at_utc=context.generated_at_iso,
    )


def transform_price_projection(
    source: SourcePriceProjection,
    context: ExportContext,
) -> UniversalForecastRecord:
    if source.horizon_months is not None:
        months = max(
            1,
            round(source.horizon_months),
        )
    elif source.horizon_days is not None:
        months = horizon_days_to_months(
            source.horizon_days
        )
    else:
        raise ValueError(
            "Price projection requires a horizon."
        )

    return UniversalForecastRecord(
        contract_version=context.contract_version,
        platform_id=context.platform_id,
        run_id=context.run_id,
        universal_asset_id=(
            universal_crypto_asset_id(
                source.asset_id
            )
        ),
        forecast_origin_date=(
            source.recommendation_date
        ),
        forecast_horizon_months=months,
        forecast_date=source.projection_date,
        current_value=source.current_price,
        forecast_value_base=source.median_price,
        forecast_value_bear=source.bear_price,
        forecast_value_bull=source.bull_price,
        expected_total_return=(
            percentage_points_to_decimal(
                source.median_return_pct
            )
        ),
        expected_cagr=(
            percentage_points_to_decimal(
                source.annualized_median_return_pct
            )
        ),
        probability_positive_return=None,
        forecast_confidence=(
            _confidence_to_score(
                source.projection_confidence
            )
        ),
        forecast_method=(
            source.projection_method
            or "price_projection"
        ),
        scenario_name=source.horizon_label,
        model_version=source.model_version,
        generated_at_utc=context.generated_at_iso,
    )


def build_forecasts(
    calibrated: list[SourceCalibratedForecast],
    projections: list[SourcePriceProjection],
    context: ExportContext,
) -> list[UniversalForecastRecord]:
    records = [
        transform_calibrated_forecast(
            item,
            context,
        )
        for item in calibrated
    ]

    records.extend(
        transform_price_projection(
            item,
            context,
        )
        for item in projections
    )

    records.sort(
        key=lambda item: (
            item.universal_asset_id,
            item.forecast_horizon_months,
            item.forecast_date,
            item.forecast_method,
        )
    )

    return records