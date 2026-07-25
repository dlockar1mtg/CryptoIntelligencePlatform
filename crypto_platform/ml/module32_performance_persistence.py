from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd

from crypto_platform.ml.performance_drift import (
    PerformanceDriftResult,
    PerformanceWindowMetrics,
    performance_by_regime,
)
from crypto_platform.ml.module32_performance_adapter import (
    PerformanceWindowSplit,
)


MODULE32_PERFORMANCE_DRIFT_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS m32_performance_drift_evaluation(
    run_id VARCHAR,
    strategy_key VARCHAR,
    benchmark_key VARCHAR,
    reference_start_date DATE,
    reference_end_date DATE,
    current_start_date DATE,
    current_end_date DATE,
    reference_observations INTEGER,
    current_observations INTEGER,
    accuracy_change_pct_points DOUBLE,
    brier_change DOUBLE,
    calibration_error_change DOUBLE,
    excess_return_change_pct_points DOUBLE,
    drawdown_change_pct_points DOUBLE,
    sharpe_change DOUBLE,
    hit_rate_change_pct_points DOUBLE,
    breached_metrics_json VARCHAR,
    drift_score DOUBLE,
    drift_status VARCHAR,
    governance_action VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id,
        strategy_key,
        benchmark_key,
        current_end_date
    )
);

CREATE TABLE IF NOT EXISTS m32_performance_window_metrics(
    run_id VARCHAR,
    strategy_key VARCHAR,
    benchmark_key VARCHAR,
    window_type VARCHAR,
    window_start_date DATE,
    window_end_date DATE,
    observations INTEGER,
    directional_accuracy_pct DOUBLE,
    brier_score DOUBLE,
    calibration_error DOUBLE,
    cumulative_return_pct DOUBLE,
    benchmark_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    maximum_drawdown_pct DOUBLE,
    annualized_sharpe DOUBLE,
    decision_hit_rate_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id,
        strategy_key,
        benchmark_key,
        window_type
    )
);

CREATE TABLE IF NOT EXISTS m32_performance_regime_metrics(
    run_id VARCHAR,
    strategy_key VARCHAR,
    benchmark_key VARCHAR,
    window_type VARCHAR,
    market_regime VARCHAR,
    observations INTEGER,
    directional_accuracy_pct DOUBLE,
    brier_score DOUBLE,
    calibration_error DOUBLE,
    cumulative_return_pct DOUBLE,
    benchmark_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    maximum_drawdown_pct DOUBLE,
    annualized_sharpe DOUBLE,
    decision_hit_rate_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id,
        strategy_key,
        benchmark_key,
        window_type,
        market_regime
    )
);

CREATE OR REPLACE VIEW latest_m32_performance_drift_evaluation AS
SELECT *
FROM m32_performance_drift_evaluation
WHERE run_id=(
    SELECT run_id
    FROM module32_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
);

CREATE OR REPLACE VIEW latest_m32_performance_window_metrics AS
SELECT *
FROM m32_performance_window_metrics
WHERE run_id=(
    SELECT run_id
    FROM module32_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
)
ORDER BY window_type;

CREATE OR REPLACE VIEW latest_m32_performance_regime_metrics AS
SELECT *
FROM m32_performance_regime_metrics
WHERE run_id=(
    SELECT run_id
    FROM module32_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
)
ORDER BY window_type, market_regime;
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _window_metrics_row(
    *,
    run_id: str,
    strategy_key: str,
    benchmark_key: str,
    window_type: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    metrics: PerformanceWindowMetrics,
    calculated_at_utc: datetime,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "strategy_key": strategy_key,
        "benchmark_key": benchmark_key,
        "window_type": window_type,
        "window_start_date": start_date.date(),
        "window_end_date": end_date.date(),
        **asdict(metrics),
        "calculated_at_utc": calculated_at_utc,
    }


def build_performance_drift_frames(
    *,
    run_id: str,
    strategy_key: str,
    benchmark_key: str,
    split: PerformanceWindowSplit,
    result: PerformanceDriftResult,
    calculated_at_utc: datetime | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    timestamp = calculated_at_utc or utcnow()

    evaluation = pd.DataFrame(
        [
            {
                "run_id": run_id,
                "strategy_key": strategy_key,
                "benchmark_key": benchmark_key,
                "reference_start_date": (
                    split.reference_start_date.date()
                ),
                "reference_end_date": (
                    split.reference_end_date.date()
                ),
                "current_start_date": (
                    split.current_start_date.date()
                ),
                "current_end_date": (
                    split.current_end_date.date()
                ),
                "reference_observations": (
                    result.reference.observations
                ),
                "current_observations": (
                    result.current.observations
                ),
                "accuracy_change_pct_points": (
                    result.accuracy_change_pct_points
                ),
                "brier_change": result.brier_change,
                "calibration_error_change": (
                    result.calibration_error_change
                ),
                "excess_return_change_pct_points": (
                    result.excess_return_change_pct_points
                ),
                "drawdown_change_pct_points": (
                    result.drawdown_change_pct_points
                ),
                "sharpe_change": result.sharpe_change,
                "hit_rate_change_pct_points": (
                    result.hit_rate_change_pct_points
                ),
                "breached_metrics_json": json.dumps(
                    list(result.breached_metrics),
                    sort_keys=True,
                ),
                "drift_score": result.drift_score,
                "drift_status": result.drift_status,
                "governance_action": result.governance_action,
                "calculated_at_utc": timestamp,
            }
        ]
    )

    windows = pd.DataFrame(
        [
            _window_metrics_row(
                run_id=run_id,
                strategy_key=strategy_key,
                benchmark_key=benchmark_key,
                window_type="REFERENCE",
                start_date=split.reference_start_date,
                end_date=split.reference_end_date,
                metrics=result.reference,
                calculated_at_utc=timestamp,
            ),
            _window_metrics_row(
                run_id=run_id,
                strategy_key=strategy_key,
                benchmark_key=benchmark_key,
                window_type="CURRENT",
                start_date=split.current_start_date,
                end_date=split.current_end_date,
                metrics=result.current,
                calculated_at_utc=timestamp,
            ),
        ]
    )

    regime_frames: list[pd.DataFrame] = []

    for window_type, frame in (
        ("REFERENCE", split.reference),
        ("CURRENT", split.current),
    ):
        regime = performance_by_regime(frame)

        if regime.empty:
            continue

        regime.insert(0, "window_type", window_type)
        regime.insert(0, "benchmark_key", benchmark_key)
        regime.insert(0, "strategy_key", strategy_key)
        regime.insert(0, "run_id", run_id)
        regime["calculated_at_utc"] = timestamp
        regime_frames.append(regime)

    if regime_frames:
        regimes = pd.concat(
            regime_frames,
            ignore_index=True,
        )
    else:
        regimes = pd.DataFrame(
            columns=[
                "run_id",
                "strategy_key",
                "benchmark_key",
                "window_type",
                "market_regime",
                "observations",
                "directional_accuracy_pct",
                "brier_score",
                "calibration_error",
                "cumulative_return_pct",
                "benchmark_return_pct",
                "excess_return_pct",
                "maximum_drawdown_pct",
                "annualized_sharpe",
                "decision_hit_rate_pct",
                "calculated_at_utc",
            ]
        )

    return evaluation, windows, regimes


def upsert_frame(
    connection,
    *,
    table: str,
    frame: pd.DataFrame,
) -> None:
    if frame.empty:
        return

    stage_name = "_performance_drift_stage"
    connection.register(stage_name, frame)

    try:
        columns = ",".join(frame.columns)

        connection.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM {stage_name}"
        )
    finally:
        connection.unregister(stage_name)


def persist_performance_drift(
    connection,
    *,
    evaluation: pd.DataFrame,
    windows: pd.DataFrame,
    regimes: pd.DataFrame,
) -> None:
    connection.execute(MODULE32_PERFORMANCE_DRIFT_SCHEMA)

    upsert_frame(
        connection,
        table="m32_performance_drift_evaluation",
        frame=evaluation,
    )

    upsert_frame(
        connection,
        table="m32_performance_window_metrics",
        frame=windows,
    )

    upsert_frame(
        connection,
        table="m32_performance_regime_metrics",
        frame=regimes,
    )