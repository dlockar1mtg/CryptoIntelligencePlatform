"""Universal risk-metric transformations."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .analytics_models import SourceRiskMetric
from .context import ExportContext
from .normalization import (
    normalize_risk_level,
    normalize_score_100,
    percentage_points_to_decimal,
    risk_status_to_score,
    universal_crypto_asset_id,
)


RISK_METRIC_COLUMNS = [
    "contract_version",
    "platform_id",
    "run_id",
    "universal_asset_id",
    "as_of_date",
    "risk_score",
    "risk_level",
    "annualized_volatility",
    "maximum_drawdown",
    "downside_deviation",
    "value_at_risk_95",
    "liquidity_risk_score",
    "concentration_risk_score",
    "model_risk_score",
    "data_quality_score",
    "risk_notes",
    "lookback_days",
    "generated_at_utc",
]


@dataclass(frozen=True)
class UniversalRiskMetricRecord:
    contract_version: str
    platform_id: str
    run_id: str
    universal_asset_id: str
    as_of_date: object
    risk_score: float
    risk_level: str
    annualized_volatility: float | None
    maximum_drawdown: float | None
    downside_deviation: float | None
    value_at_risk_95: float | None
    liquidity_risk_score: float | None
    concentration_risk_score: float | None
    model_risk_score: float | None
    data_quality_score: float | None
    risk_notes: str | None
    lookback_days: int | None
    generated_at_utc: str

    def to_dict(
        self,
    ) -> dict[str, object]:
        return asdict(self)


def _liquidity_risk_score(
    liquidity_score: float | None,
) -> float | None:
    if liquidity_score is None:
        return None

    normalized = normalize_score_100(
        liquidity_score
    )

    return 100.0 - normalized


def transform_risk_metric(
    source: SourceRiskMetric,
    context: ExportContext,
) -> UniversalRiskMetricRecord:
    return UniversalRiskMetricRecord(
        contract_version=context.contract_version,
        platform_id=context.platform_id,
        run_id=context.run_id,
        universal_asset_id=(
            universal_crypto_asset_id(
                source.asset_id
            )
        ),
        as_of_date=source.observation_date,
        risk_score=risk_status_to_score(
            source.risk_status
        ),
        risk_level=normalize_risk_level(
            source.risk_status
        ),
        annualized_volatility=(
            percentage_points_to_decimal(
                source.annualized_volatility_pct
            )
        ),
        maximum_drawdown=(
            percentage_points_to_decimal(
                source.max_drawdown_365d_pct
            )
        ),
        downside_deviation=None,
        value_at_risk_95=(
            percentage_points_to_decimal(
                source.var_95_pct
            )
        ),
        liquidity_risk_score=(
            _liquidity_risk_score(
                source.liquidity_score
            )
        ),
        concentration_risk_score=(
            None
            if source.marginal_risk_contribution_pct
            is None
            else normalize_score_100(
                abs(
                    source.marginal_risk_contribution_pct
                )
            )
        ),
        model_risk_score=None,
        data_quality_score=None,
        risk_notes=(
            "Module 36 categorical risk status: "
            f"{source.risk_status}; "
            "universal risk score derived from "
            "the same categorical framework."
        ),
        lookback_days=365,
        generated_at_utc=context.generated_at_iso,
    )


def build_risk_metrics(
    source_records: list[SourceRiskMetric],
    context: ExportContext,
) -> list[UniversalRiskMetricRecord]:
    records = [
        transform_risk_metric(
            item,
            context,
        )
        for item in source_records
    ]

    records.sort(
        key=lambda item: item.universal_asset_id
    )

    return records