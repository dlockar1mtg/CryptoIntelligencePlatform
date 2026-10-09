"""Regression tests for the 2026-10 audit fixes (synthetic data only)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
import json
from pathlib import Path

import pytest

from crypto_platform.integration.universal import package_builder
from crypto_platform.integration.universal.analytics_models import (
    SourceCalibratedForecast,
    SourcePriceProjection,
)
from crypto_platform.integration.universal.context import ExportContext
from crypto_platform.integration.universal.forecasts import (
    DIRECTION_INCONSISTENT_CONFIDENCE_CAP,
    LOWER_BOUND_RETURN_FLOOR_PCT,
    direction_consistent,
    transform_calibrated_forecast,
    transform_price_projection,
)
from crypto_platform.integration.universal.package_builder import (
    PackageValidationError,
    UniversalPackageBuilder,
    failed_validation_checks,
)
from crypto_platform.integration.universal.source_models import SourceRun
from crypto_platform.module39 import log_space_return_interval


def _context(output: Path = Path("output")) -> ExportContext:
    return ExportContext.create(
        source_database=Path("source.duckdb"),
        output_directory=output,
        run_id="audit-run-001",
        generated_at_utc=datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc),
    )


def _calibrated(**overrides) -> SourceCalibratedForecast:
    base = SourceCalibratedForecast(
        source_run_id="m39-synthetic",
        forecast_date=date(2026, 10, 1),
        asset_id="bitcoin",
        horizon_days=365,
        predicted_return_pct=20.0,
        probability_positive=0.70,
        lower_return_pct=-10.0,
        upper_return_pct=45.0,
        forecast_confidence=0.80,
        calibration_method="EVIDENCE_SHRINKAGE",
        forecast_status="POSITIVE",
        current_price=100.0,
        calculated_at_utc=datetime(2026, 10, 1, tzinfo=timezone.utc),
        model_version="synthetic",
    )
    return replace(base, **overrides)


# --- Finding 1: interval bounds and direction consistency -------------------


@pytest.mark.parametrize(
    "predicted, half_width",
    [(0.0, 300.0), (181.0, 400.0), (-60.0, 250.0), (-150.0, 50.0), (20.0, 1.0)],
)
def test_log_space_interval_lower_bound_stays_above_minus_100(predicted, half_width):
    lower, upper = log_space_return_interval(predicted, half_width)
    assert lower > -100.0
    assert lower < upper


def test_log_space_interval_matches_symmetric_band_for_small_widths():
    lower, upper = log_space_return_interval(0.0, 1.0)
    assert lower == pytest.approx(-1.0, abs=0.02)
    assert upper == pytest.approx(1.0, abs=0.02)


def test_log_space_interval_contains_prediction():
    lower, upper = log_space_return_interval(181.0, 200.0)
    assert lower < 181.0 < upper


def test_export_floors_lower_bound_so_bear_price_is_positive():
    record = transform_calibrated_forecast(
        _calibrated(lower_return_pct=-181.3, current_price=100000.0),
        _context(),
    )
    assert record.forecast_value_bear == pytest.approx(
        100000.0 * (1 + LOWER_BOUND_RETURN_FLOOR_PCT / 100.0)
    )
    assert record.forecast_value_bear > 0


def test_export_leaves_valid_lower_bound_unchanged():
    record = transform_calibrated_forecast(_calibrated(), _context())
    assert record.forecast_value_bear == pytest.approx(90.0)


def test_projection_bear_price_is_floored_above_zero():
    projection = SourcePriceProjection(
        source_run_id="m42-synthetic",
        recommendation_date=date(2026, 10, 1),
        asset_id="ethereum",
        horizon_label="12M",
        horizon_days=365,
        horizon_months=12.0,
        projection_date=date(2027, 10, 1),
        current_price=1000.0,
        bear_price=-500.0,
        median_price=1200.0,
        bull_price=2000.0,
        bear_return_pct=-150.0,
        median_return_pct=20.0,
        bull_return_pct=100.0,
        annualized_median_return_pct=20.0,
        projection_confidence=0.6,
        projection_method="synthetic",
        evidence_status="synthetic",
        calculated_at_utc=datetime(2026, 10, 1, tzinfo=timezone.utc),
        model_version="synthetic",
    )
    record = transform_price_projection(projection, _context())
    assert record.forecast_value_bear > 0


@pytest.mark.parametrize(
    "predicted, probability, expected",
    [
        (181.0, 0.0, False),
        (-20.0, 0.9, False),
        (20.0, 0.7, True),
        (-20.0, 0.2, True),
        (0.0, 0.0, True),
        (10.0, 0.5, True),
        (None, 0.1, True),
        (10.0, None, True),
    ],
)
def test_direction_consistent(predicted, probability, expected):
    assert direction_consistent(predicted, probability) is expected


def test_inconsistent_row_has_confidence_lowered_and_columns_unchanged():
    consistent = transform_calibrated_forecast(_calibrated(), _context())
    inconsistent = transform_calibrated_forecast(
        _calibrated(predicted_return_pct=181.0, probability_positive=0.0),
        _context(),
    )
    assert consistent.forecast_confidence == pytest.approx(80.0)
    assert inconsistent.forecast_confidence == DIRECTION_INCONSISTENT_CONFIDENCE_CAP
    assert set(consistent.to_dict()) == set(inconsistent.to_dict())


# --- Finding 2: validation gates on its checks -----------------------------


def test_failed_validation_checks_respects_expected_false():
    assert failed_validation_checks(
        {"forecasts_nonempty": True, "portfolio_positions_inferred": False}
    ) == []
    assert failed_validation_checks(
        {"forecasts_nonempty": False, "portfolio_positions_inferred": True}
    ) == ["forecasts_nonempty", "portfolio_positions_inferred"]


class _FakeSource:
    def latest_successful_run(self, module):
        return SourceRun(
            module_number=module,
            table_name=f"module{module}_runs",
            run_id=f"m{module}-synthetic",
            status="COMPLETED",
            started_at_utc=datetime(2026, 10, 9, 10, tzinfo=timezone.utc),
            completed_at_utc=datetime(2026, 10, 9, 11, tzinfo=timezone.utc),
            platform_version="synthetic",
        )

    def load_active_assets(self):
        return []


class _FakeAnalytics:
    def load_calibrated_forecasts(self):
        return [_calibrated()]

    def load_price_projections(self):
        return []

    def load_recommendations(self):
        return []

    def load_risk_metrics(self):
        return []


def _patched_builder(monkeypatch, output: Path, recommendations: list):
    columns = package_builder.RECOMMENDATION_COLUMNS
    row = {column: None for column in columns}
    monkeypatch.setattr(
        package_builder, "build_asset_master",
        lambda *_: [{c: None for c in package_builder.ASSET_MASTER_COLUMNS}],
    )
    monkeypatch.setattr(
        package_builder, "build_recommendations",
        lambda *_: [dict(row) for _ in recommendations],
    )
    monkeypatch.setattr(
        package_builder, "build_btc_eth_strategic_overlay",
        lambda *_: [
            {c: None for c in package_builder.BTC_ETH_STRATEGIC_OVERLAY_COLUMNS}
            for _ in range(2)
        ],
    )
    monkeypatch.setattr(
        package_builder, "build_risk_metrics",
        lambda *_: [{c: None for c in package_builder.RISK_METRIC_COLUMNS}],
    )
    builder = UniversalPackageBuilder.__new__(UniversalPackageBuilder)
    builder._context = _context(output)
    builder._source = _FakeSource()
    builder._analytics = _FakeAnalytics()
    return builder


def test_empty_recommendations_fail_validation_and_raise(monkeypatch, tmp_path):
    output = tmp_path / "package"
    builder = _patched_builder(monkeypatch, output, recommendations=[])
    with pytest.raises(PackageValidationError) as excinfo:
        builder.build()
    assert excinfo.value.failed_checks == ["recommendations_nonempty"]
    report = json.loads((output / "validation_report.json").read_text())
    summary = json.loads((output / "package_summary.json").read_text())
    assert report["status"] == "FAIL"
    assert summary["status"] == "FAIL"
    assert report["failed_checks"] == ["recommendations_nonempty"]
    assert report["errors"]


def test_complete_package_passes_validation(monkeypatch, tmp_path):
    output = tmp_path / "package"
    builder = _patched_builder(monkeypatch, output, recommendations=[1])
    result = builder.build()
    assert result.validation_status == "PASS"
    report = json.loads((output / "validation_report.json").read_text())
    assert report["status"] == "PASS"
    assert report["failed_checks"] == []
    assert report["direction_inconsistent_forecasts"] == []
