"""Universal recommendation transformations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

from .analytics_models import SourceRecommendation
from .context import ExportContext
from .normalization import (
    normalize_recommendation,
    normalize_score_100,
    percentage_points_to_decimal,
    universal_crypto_asset_id,
)


RECOMMENDATION_COLUMNS = [
    "contract_version",
    "platform_id",
    "run_id",
    "universal_asset_id",
    "as_of_date",
    "recommendation",
    "normalized_score",
    "confidence_score",
    "platform_native_score",
    "platform_native_label",
    "time_horizon",
    "target_weight",
    "minimum_weight",
    "maximum_weight",
    "rationale_summary",
    "primary_risk",
    "model_version",
    "generated_at_utc",
]


@dataclass(frozen=True)
class UniversalRecommendationRecord:
    contract_version: str
    platform_id: str
    run_id: str
    universal_asset_id: str
    as_of_date: object
    recommendation: str
    normalized_score: float
    confidence_score: float
    platform_native_score: float | None
    platform_native_label: str | None
    time_horizon: str | None
    target_weight: float | None
    minimum_weight: float | None
    maximum_weight: float | None
    rationale_summary: str | None
    primary_risk: str | None
    model_version: str | None
    generated_at_utc: str

    def to_dict(
        self,
    ) -> dict[str, object]:
        return asdict(self)


def _confidence_score(
    value: float,
) -> float:
    if not math.isfinite(value):
        raise ValueError(
            "Recommendation confidence must be finite."
        )

    score = value * 100.0 if value <= 1.0 else value

    return normalize_score_100(score)


def transform_recommendation(
    source: SourceRecommendation,
    context: ExportContext,
) -> UniversalRecommendationRecord:
    return UniversalRecommendationRecord(
        contract_version=context.contract_version,
        platform_id=context.platform_id,
        run_id=context.run_id,
        universal_asset_id=(
            universal_crypto_asset_id(
                source.asset_id
            )
        ),
        as_of_date=source.recommendation_date,
        recommendation=(
            normalize_recommendation(
                source.best_action
            )
        ),
        normalized_score=(
            normalize_score_100(
                source.investment_score
            )
        ),
        confidence_score=(
            _confidence_score(
                source.forecast_confidence
            )
        ),
        platform_native_score=(
            source.investment_score
        ),
        platform_native_label=(
            source.best_action
        ),
        time_horizon=(
            source.suggested_timeline
        ),
        target_weight=(
            percentage_points_to_decimal(
                source.best_current_portfolio_pct
            )
        ),
        minimum_weight=None,
        maximum_weight=None,
        rationale_summary=source.primary_reason,
        primary_risk=source.risk_warning,
        model_version=source.model_version,
        generated_at_utc=context.generated_at_iso,
    )


def build_recommendations(
    source_records: list[SourceRecommendation],
    context: ExportContext,
) -> list[UniversalRecommendationRecord]:
    records = [
        transform_recommendation(
            item,
            context,
        )
        for item in source_records
    ]

    records.sort(
        key=lambda item: item.universal_asset_id
    )

    return records