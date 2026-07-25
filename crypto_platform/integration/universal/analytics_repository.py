"""Read-only access to crypto analytical outputs."""

from __future__ import annotations

from pathlib import Path

import duckdb

from .analytics_models import (
    SourceCalibratedForecast,
    SourcePriceProjection,
    SourceRecommendation,
    SourceRiskMetric,
)
from .source_repository import CryptoSourceRepository


class CryptoAnalyticsRepository:
    """Read-only source access for universal transformations."""

    def __init__(
        self,
        database_path: Path,
    ) -> None:
        self._source = CryptoSourceRepository(
            database_path
        )

    def _connect(
        self,
    ) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(
            str(self._source.database_path),
            read_only=True,
        )

    def load_calibrated_forecasts(
        self,
    ) -> list[SourceCalibratedForecast]:
        run = self._source.latest_successful_run(
            39
        )

        connection = self._connect()

        try:
            rows = connection.execute(
                """
                SELECT
                    f.run_id,
                    f.forecast_date,
                    f.asset_id,
                    f.horizon_days,
                    f.predicted_return_pct,
                    f.calibrated_probability_positive,
                    f.conformal_lower_return_pct,
                    f.conformal_upper_return_pct,
                    f.forecast_confidence,
                    f.calibration_method,
                    f.forecast_status,
                    (
                        SELECT amd.price_usd
                        FROM asset_market_daily AS amd
                        WHERE amd.asset_id = f.asset_id
                          AND amd.observation_date
                              <= f.forecast_date
                        ORDER BY
                            amd.observation_date DESC,
                            amd.collected_at_utc DESC
                        LIMIT 1
                    ) AS current_price,
                    f.calculated_at_utc
                FROM m39_calibrated_forecasts AS f
                WHERE f.run_id = ?
                ORDER BY
                    f.asset_id,
                    f.horizon_days
                """,
                [run.run_id],
            ).fetchall()

        finally:
            connection.close()

        return [
            SourceCalibratedForecast(
                source_run_id=str(row[0]),
                forecast_date=row[1],
                asset_id=str(row[2]),
                horizon_days=int(row[3]),
                predicted_return_pct=(
                    None if row[4] is None
                    else float(row[4])
                ),
                probability_positive=(
                    None if row[5] is None
                    else float(row[5])
                ),
                lower_return_pct=(
                    None if row[6] is None
                    else float(row[6])
                ),
                upper_return_pct=(
                    None if row[7] is None
                    else float(row[7])
                ),
                forecast_confidence=(
                    None if row[8] is None
                    else float(row[8])
                ),
                calibration_method=(
                    None if row[9] is None
                    else str(row[9])
                ),
                forecast_status=(
                    None if row[10] is None
                    else str(row[10])
                ),
                current_price=(
                    None if row[11] is None
                    else float(row[11])
                ),
                calculated_at_utc=row[12],
                model_version=run.platform_version,
            )
            for row in rows
        ]

    def load_price_projections(
        self,
    ) -> list[SourcePriceProjection]:
        run = self._source.latest_successful_run(
            42
        )

        connection = self._connect()

        try:
            rows = connection.execute(
                """
                SELECT
                    run_id,
                    recommendation_date,
                    asset_id,
                    horizon_label,
                    horizon_days,
                    horizon_months,
                    projection_date,
                    current_price,
                    bear_price,
                    median_price,
                    bull_price,
                    bear_return_pct,
                    median_return_pct,
                    bull_return_pct,
                    annualized_median_return_pct,
                    projection_confidence,
                    projection_method,
                    evidence_status,
                    calculated_at_utc
                FROM m42_price_projections
                WHERE run_id = ?
                ORDER BY
                    asset_id,
                    horizon_days
                """,
                [run.run_id],
            ).fetchall()

        finally:
            connection.close()

        return [
            SourcePriceProjection(
                source_run_id=str(row[0]),
                recommendation_date=row[1],
                asset_id=str(row[2]),
                horizon_label=str(row[3]),
                horizon_days=(
                    None if row[4] is None
                    else int(row[4])
                ),
                horizon_months=(
                    None if row[5] is None
                    else float(row[5])
                ),
                projection_date=row[6],
                current_price=(
                    None if row[7] is None
                    else float(row[7])
                ),
                bear_price=(
                    None if row[8] is None
                    else float(row[8])
                ),
                median_price=(
                    None if row[9] is None
                    else float(row[9])
                ),
                bull_price=(
                    None if row[10] is None
                    else float(row[10])
                ),
                bear_return_pct=(
                    None if row[11] is None
                    else float(row[11])
                ),
                median_return_pct=(
                    None if row[12] is None
                    else float(row[12])
                ),
                bull_return_pct=(
                    None if row[13] is None
                    else float(row[13])
                ),
                annualized_median_return_pct=(
                    None if row[14] is None
                    else float(row[14])
                ),
                projection_confidence=(
                    None if row[15] is None
                    else float(row[15])
                ),
                projection_method=(
                    None if row[16] is None
                    else str(row[16])
                ),
                evidence_status=(
                    None if row[17] is None
                    else str(row[17])
                ),
                calculated_at_utc=row[18],
                model_version=run.platform_version,
            )
            for row in rows
        ]

    def load_recommendations(
        self,
    ) -> list[SourceRecommendation]:
        run = self._source.latest_successful_run(
            42
        )

        connection = self._connect()

        try:
            rows = connection.execute(
                """
                SELECT
                    run_id,
                    recommendation_date,
                    asset_id,
                    best_action,
                    investment_score,
                    best_current_portfolio_pct,
                    suggested_timeline,
                    conviction,
                    forecast_confidence,
                    primary_reason,
                    risk_warning,
                    calculated_at_utc
                FROM m42_asset_recommendations
                WHERE run_id = ?
                ORDER BY asset_id
                """,
                [run.run_id],
            ).fetchall()

        finally:
            connection.close()

        return [
            SourceRecommendation(
                source_run_id=str(row[0]),
                recommendation_date=row[1],
                asset_id=str(row[2]),
                best_action=str(row[3]),
                investment_score=float(row[4]),
                best_current_portfolio_pct=(
                    None if row[5] is None
                    else float(row[5])
                ),
                suggested_timeline=(
                    None if row[6] is None
                    else str(row[6])
                ),
                conviction=(
                    None if row[7] is None
                    else str(row[7])
                ),
                forecast_confidence=float(row[8]),
                primary_reason=(
                    None if row[9] is None
                    else str(row[9])
                ),
                risk_warning=(
                    None if row[10] is None
                    else str(row[10])
                ),
                calculated_at_utc=row[11],
                model_version=run.platform_version,
            )
            for row in rows
        ]

    def load_risk_metrics(
        self,
    ) -> list[SourceRiskMetric]:
        risk_run = (
            self._source.latest_successful_run(
                36
            )
        )

        connection = self._connect()

        try:
            rows = connection.execute(
                """
                SELECT
                    r.run_id,
                    r.observation_date,
                    r.asset_id,
                    r.annualized_volatility_pct,
                    r.var_95_pct,
                    r.cvar_95_pct,
                    r.max_drawdown_365d_pct,
                    r.liquidity_score,
                    r.marginal_risk_contribution_pct,
                    r.risk_status,
                    r.calculated_at_utc
                FROM m36_asset_risk AS r
                WHERE r.run_id = ?
                ORDER BY r.asset_id
                """,
                [risk_run.run_id],
            ).fetchall()

        finally:
            connection.close()

        return [
            SourceRiskMetric(
                source_run_id=str(row[0]),
                observation_date=row[1],
                asset_id=str(row[2]),
                annualized_volatility_pct=(
                    None
                    if row[3] is None
                    else float(row[3])
                ),
                var_95_pct=(
                    None
                    if row[4] is None
                    else float(row[4])
                ),
                cvar_95_pct=(
                    None
                    if row[5] is None
                    else float(row[5])
                ),
                max_drawdown_365d_pct=(
                    None
                    if row[6] is None
                    else float(row[6])
                ),
                liquidity_score=(
                    None
                    if row[7] is None
                    else float(row[7])
                ),
                marginal_risk_contribution_pct=(
                    None
                    if row[8] is None
                    else float(row[8])
                ),
                risk_status=str(row[9]),
                calculated_at_utc=row[10],
                model_version=(
                    risk_run.platform_version
                ),
            )
            for row in rows
        ]
