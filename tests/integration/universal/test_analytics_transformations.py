from __future__ import annotations

from datetime import (
    date,
    datetime,
    timezone,
)
from pathlib import Path

from crypto_platform.integration.universal.analytics_models import (
    SourceCalibratedForecast,
    SourcePriceProjection,
    SourceRecommendation,
    SourceRiskMetric,
)
from crypto_platform.integration.universal.context import (
    ExportContext,
)
from crypto_platform.integration.universal.forecasts import (
    transform_calibrated_forecast,
    transform_price_projection,
)
from crypto_platform.integration.universal.recommendations import (
    transform_recommendation,
)
from crypto_platform.integration.universal.risk_metrics import (
    transform_risk_metric,
)


def context() -> ExportContext:
    return ExportContext.create(
        source_database=Path("source.duckdb"),
        output_directory=Path("output"),
        run_id="adapter-run-001",
        generated_at_utc=datetime(
            2026,
            7,
            21,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_transform_calibrated_forecast() -> None:
    source = SourceCalibratedForecast(
        source_run_id="m39-run",
        forecast_date=date(2026, 7, 14),
        asset_id="bitcoin",
        horizon_days=90,
        predicted_return_pct=20.0,
        probability_positive=0.72,
        lower_return_pct=-10.0,
        upper_return_pct=45.0,
        forecast_confidence=0.80,
        calibration_method="EVIDENCE_SHRINKAGE",
        forecast_status="POSITIVE",
        current_price=100000.0,
        calculated_at_utc=datetime(
            2026,
            7,
            16,
            tzinfo=timezone.utc,
        ),
        model_version="8.1.1",
    )

    record = transform_calibrated_forecast(
        source,
        context(),
    )

    assert record.universal_asset_id == "crypto:bitcoin"
    assert record.forecast_horizon_months == 3
    assert record.forecast_value_base == 120000.0
    assert record.forecast_value_bear == 90000.0
    assert record.forecast_value_bull == 145000.0
    assert record.expected_total_return == 0.20
    assert record.probability_positive_return == 0.72
    assert record.forecast_confidence == 80.0


def test_transform_price_projection() -> None:
    source = SourcePriceProjection(
        source_run_id="m42-run",
        recommendation_date=date(2026, 7, 14),
        asset_id="ethereum",
        horizon_label="M36",
        horizon_days=1096,
        horizon_months=36.0,
        projection_date=date(2029, 7, 14),
        current_price=2000.0,
        bear_price=1000.0,
        median_price=3500.0,
        bull_price=7000.0,
        bear_return_pct=-50.0,
        median_return_pct=75.0,
        bull_return_pct=250.0,
        annualized_median_return_pct=20.5,
        projection_confidence=0.65,
        projection_method="LONG_RANGE_SCENARIO_MODEL",
        evidence_status="SCENARIO_ONLY",
        calculated_at_utc=datetime(
            2026,
            7,
            16,
            tzinfo=timezone.utc,
        ),
        model_version="8.1.1",
    )

    record = transform_price_projection(
        source,
        context(),
    )

    assert record.forecast_horizon_months == 36
    assert record.forecast_value_base == 3500.0
    assert record.expected_total_return == 0.75
    assert record.expected_cagr == 0.205
    assert record.forecast_confidence == 65.0


def test_transform_recommendation() -> None:
    source = SourceRecommendation(
        source_run_id="m42-run",
        recommendation_date=date(2026, 7, 14),
        asset_id="bitcoin",
        best_action="BUY",
        investment_score=82.5,
        best_current_portfolio_pct=15.0,
        suggested_timeline="BUY_NOW",
        conviction="HIGH",
        forecast_confidence=0.88,
        primary_reason="Strong long-term evidence.",
        risk_warning="High volatility.",
        calculated_at_utc=datetime(
            2026,
            7,
            16,
            tzinfo=timezone.utc,
        ),
        model_version="8.1.1",
    )

    record = transform_recommendation(
        source,
        context(),
    )

    assert record.recommendation == "buy"
    assert record.normalized_score == 82.5
    assert record.confidence_score == 88.0
    assert record.target_weight == 0.15
    assert record.platform_native_label == "BUY"


def test_transform_risk_metric() -> None:
    source = SourceRiskMetric(
        source_run_id="m36-run",
        observation_date=date(2026, 7, 14),
        asset_id="bitcoin",
        annualized_volatility_pct=62.0,
        var_95_pct=-5.0,
        cvar_95_pct=-8.0,
        max_drawdown_365d_pct=-70.0,
        liquidity_score=95.0,
        marginal_risk_contribution_pct=25.0,
        risk_status="HIGH",
        calculated_at_utc=datetime(
            2026,
            7,
            16,
            tzinfo=timezone.utc,
        ),
        model_version="8.1.1",
    )

    record = transform_risk_metric(
        source,
        context(),
    )

    assert record.risk_score == 75.0
    assert record.risk_level == "high"
    assert record.annualized_volatility == 0.62
    assert record.maximum_drawdown == -0.70
    assert record.value_at_risk_95 == -0.05
    assert record.liquidity_risk_score == 5.0
    assert record.concentration_risk_score == 25.0