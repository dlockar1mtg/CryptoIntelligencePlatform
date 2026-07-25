"""Source analytical records used by the universal adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class SourceCalibratedForecast:
    source_run_id: str
    forecast_date: date
    asset_id: str
    horizon_days: int
    predicted_return_pct: float | None
    probability_positive: float | None
    lower_return_pct: float | None
    upper_return_pct: float | None
    forecast_confidence: float | None
    calibration_method: str | None
    forecast_status: str | None
    current_price: float | None
    calculated_at_utc: datetime
    model_version: str | None


@dataclass(frozen=True)
class SourcePriceProjection:
    source_run_id: str
    recommendation_date: date
    asset_id: str
    horizon_label: str
    horizon_days: int | None
    horizon_months: float | None
    projection_date: date
    current_price: float | None
    bear_price: float | None
    median_price: float | None
    bull_price: float | None
    bear_return_pct: float | None
    median_return_pct: float | None
    bull_return_pct: float | None
    annualized_median_return_pct: float | None
    projection_confidence: float | None
    projection_method: str | None
    evidence_status: str | None
    calculated_at_utc: datetime
    model_version: str | None


@dataclass(frozen=True)
class SourceRecommendation:
    source_run_id: str
    recommendation_date: date
    asset_id: str
    best_action: str
    investment_score: float
    best_current_portfolio_pct: float | None
    suggested_timeline: str | None
    conviction: str | None
    forecast_confidence: float
    primary_reason: str | None
    risk_warning: str | None
    calculated_at_utc: datetime
    model_version: str | None


@dataclass(frozen=True)
class SourceRiskMetric:
    source_run_id: str
    observation_date: date
    asset_id: str
    annualized_volatility_pct: float | None
    var_95_pct: float | None
    cvar_95_pct: float | None
    max_drawdown_365d_pct: float | None
    liquidity_score: float | None
    marginal_risk_contribution_pct: float | None
    risk_status: str
    calculated_at_utc: datetime
    model_version: str | None