"""Validate universal transformations against the real crypto database."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[2]
)

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(REPOSITORY_ROOT),
    )

from crypto_platform.integration.universal import (
    CryptoAnalyticsRepository,
    CryptoSourceRepository,
    ExportContext,
    build_asset_master,
    build_forecasts,
    build_recommendations,
    build_risk_metrics,
)

ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    ROOT
    / "data"
    / "crypto_intelligence.duckdb"
).resolve()

OUTPUT_PATH = (
    ROOT
    / "docs"
    / "integration"
    / "universal"
    / "real_database_transformation_validation.json"
)

VALIDATION_RUN_ID = (
    "crypto-universal-real-data-validation"
)


def json_safe(
    value: Any,
) -> Any:
    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, float):
        if not math.isfinite(value):
            return None

        return value

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    if isinstance(
        value,
        (str, int, bool),
    ):
        return value

    return str(value)


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_assets(
    records: list[Any],
) -> None:
    require(
        bool(records),
        "Asset master contains no records.",
    )

    identifiers = [
        item.universal_asset_id
        for item in records
    ]

    require(
        len(identifiers)
        == len(set(identifiers)),
        "Asset master contains duplicate identifiers.",
    )

    for item in records:
        require(
            item.universal_asset_id.startswith(
                "crypto:"
            ),
            "Invalid universal crypto asset ID.",
        )

        require(
            item.asset_class == "crypto",
            "Asset class is not crypto.",
        )

        require(
            item.currency == "USD",
            "Asset currency is not USD.",
        )


def validate_forecasts(
    records: list[Any],
) -> None:
    require(
        bool(records),
        "Forecast output contains no records.",
    )

    for item in records:
        require(
            item.forecast_horizon_months > 0,
            "Forecast horizon is not positive.",
        )

        require(
            item.forecast_date
            >= item.forecast_origin_date,
            "Forecast date precedes its origin.",
        )

        if item.probability_positive_return is not None:
            require(
                0.0
                <= item.probability_positive_return
                <= 1.0,
                "Forecast probability is out of range.",
            )

        if item.forecast_confidence is not None:
            require(
                0.0
                <= item.forecast_confidence
                <= 100.0,
                "Forecast confidence is out of range.",
            )


def validate_recommendations(
    records: list[Any],
) -> None:
    require(
        bool(records),
        "Recommendation output contains no records.",
    )

    valid_actions = {
        "buy",
        "accumulate",
        "hold",
        "wait",
        "reduce",
        "sell",
    }

    for item in records:
        require(
            item.recommendation
            in valid_actions,
            "Recommendation vocabulary is invalid.",
        )

        require(
            0.0
            <= item.normalized_score
            <= 100.0,
            "Recommendation score is out of range.",
        )

        require(
            0.0
            <= item.confidence_score
            <= 100.0,
            "Recommendation confidence is out of range.",
        )

        if item.target_weight is not None:
            require(
                0.0 <= item.target_weight <= 1.0,
                "Recommendation target weight "
                "is out of range.",
            )


def validate_risk_metrics(
    records: list[Any],
) -> None:
    require(
        bool(records),
        "Risk output contains no records.",
    )

    valid_levels = {
        "low",
        "medium",
        "high",
        "extreme",
    }

    for item in records:
        require(
            0.0 <= item.risk_score <= 100.0,
            "Risk score is out of range.",
        )

        require(
            item.risk_level in valid_levels,
            "Risk level is invalid.",
        )

        if item.liquidity_risk_score is not None:
            require(
                0.0
                <= item.liquidity_risk_score
                <= 100.0,
                "Liquidity risk score is out of range.",
            )

        if item.concentration_risk_score is not None:
            require(
                0.0
                <= item.concentration_risk_score
                <= 100.0,
                "Concentration risk is out of range.",
            )


def serialize_samples(
    records: list[Any],
    limit: int = 5,
) -> list[dict[str, Any]]:
    return [
        json_safe(
            asdict(item)
        )
        for item in records[:limit]
    ]


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    generated_at = datetime.now(
        timezone.utc
    )

    context = ExportContext.create(
        source_database=DATABASE_PATH,
        output_directory=(
            ROOT
            / "data"
            / "exports"
            / "universal_validation"
        ),
        run_id=VALIDATION_RUN_ID,
        generated_at_utc=generated_at,
    )

    source_repository = CryptoSourceRepository(
        DATABASE_PATH
    )

    analytics_repository = (
        CryptoAnalyticsRepository(
            DATABASE_PATH
        )
    )

    module_runs = {
        str(module): asdict(
            source_repository.latest_successful_run(
                module
            )
        )
        for module in (36, 39, 42)
    }

    source_assets = (
        source_repository.load_active_assets()
    )

    calibrated = (
        analytics_repository
        .load_calibrated_forecasts()
    )

    projections = (
        analytics_repository
        .load_price_projections()
    )

    source_recommendations = (
        analytics_repository
        .load_recommendations()
    )

    source_risk_metrics = (
        analytics_repository
        .load_risk_metrics()
    )

    asset_master = build_asset_master(
        source_assets,
        context,
    )

    forecasts = build_forecasts(
        calibrated,
        projections,
        context,
    )

    recommendations = build_recommendations(
        source_recommendations,
        context,
    )

    risk_metrics = build_risk_metrics(
        source_risk_metrics,
        context,
    )

    validate_assets(asset_master)
    validate_forecasts(forecasts)
    validate_recommendations(
        recommendations
    )
    validate_risk_metrics(risk_metrics)

    asset_ids = {
        item.universal_asset_id
        for item in asset_master
    }

    analytical_asset_ids = {
        item.universal_asset_id
        for collection in (
            forecasts,
            recommendations,
            risk_metrics,
        )
        for item in collection
    }

    unknown_assets = sorted(
        analytical_asset_ids - asset_ids
    )

    require(
        not unknown_assets,
        "Analytical outputs contain assets "
        "missing from asset master: "
        + ", ".join(unknown_assets),
    )

    payload = {
        "status": "PASS",
        "database_path": str(DATABASE_PATH),
        "validation_run_id": VALIDATION_RUN_ID,
        "generated_at_utc": (
            generated_at.isoformat()
        ),
        "module_runs": json_safe(
            module_runs
        ),
        "source_row_counts": {
            "active_assets": len(
                source_assets
            ),
            "calibrated_forecasts": len(
                calibrated
            ),
            "price_projections": len(
                projections
            ),
            "recommendations": len(
                source_recommendations
            ),
            "risk_metrics": len(
                source_risk_metrics
            ),
        },
        "universal_row_counts": {
            "asset_master": len(
                asset_master
            ),
            "forecasts": len(
                forecasts
            ),
            "recommendations": len(
                recommendations
            ),
            "risk_metrics": len(
                risk_metrics
            ),
        },
        "asset_coverage": {
            "asset_master_assets": sorted(
                asset_ids
            ),
            "analytical_assets": sorted(
                analytical_asset_ids
            ),
            "unknown_assets": unknown_assets,
        },
        "samples": {
            "asset_master": serialize_samples(
                asset_master
            ),
            "forecasts": serialize_samples(
                forecasts
            ),
            "recommendations": (
                serialize_samples(
                    recommendations
                )
            ),
            "risk_metrics": serialize_samples(
                risk_metrics
            ),
        },
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            json_safe(payload),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(
        "PASS: Real crypto database "
        "transformations validated."
    )

    print()
    print("Latest source runs:")

    for module, run in module_runs.items():
        print(
            f"- Module {module}: "
            f"{run['run_id']} "
            f"({run['status']})"
        )

    print()
    print("Source row counts:")

    for name, count in (
        payload["source_row_counts"].items()
    ):
        print(f"- {name}: {count}")

    print()
    print("Universal row counts:")

    for name, count in (
        payload["universal_row_counts"].items()
    ):
        print(f"- {name}: {count}")

    print()
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()