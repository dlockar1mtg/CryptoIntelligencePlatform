from __future__ import annotations

from datetime import datetime, timezone

import duckdb
import numpy as np
import pandas as pd

from crypto_platform.ml.module32_performance_adapter import (
    build_module32_performance_frame,
    split_reference_current_windows,
)
from crypto_platform.ml.module32_performance_persistence import (
    MODULE32_PERFORMANCE_DRIFT_SCHEMA,
    build_performance_drift_frames,
    persist_performance_drift,
)
from crypto_platform.ml.performance_drift import (
    evaluate_performance_drift,
)


def source_frame(periods: int = 120) -> pd.DataFrame:
    dates = pd.date_range(
        "2025-01-01",
        periods=periods,
        freq="D",
    )

    current_start = periods - 30

    strategy_returns = np.concatenate(
        [
            np.repeat(0.002, current_start),
            np.repeat(-0.003, 30),
        ]
    )

    benchmark_returns = np.repeat(0.001, periods)

    prediction_correct = np.concatenate(
        [
            np.repeat(1.0, current_start),
            np.repeat(0.0, 30),
        ]
    )

    return pd.DataFrame(
        {
            "observation_date": dates,
            "strategy_return": strategy_returns,
            "benchmark_return": benchmark_returns,
            "prediction_correct": prediction_correct,
            "predicted_probability": np.concatenate(
                [
                    np.repeat(0.80, current_start),
                    np.repeat(0.95, 30),
                ]
            ),
            "actual_probability": prediction_correct,
            "market_regime": np.concatenate(
                [
                    np.repeat("EXPANSION", current_start),
                    np.repeat("CONTRACTION", 30),
                ]
            ),
            "predicted_regime": np.repeat(
                "EXPANSION",
                periods,
            ),
            "strategy_key": np.repeat(
                "CLEAN_PROBABILITY",
                periods,
            ),
            "benchmark_key": np.repeat(
                "BTC_BUY_HOLD",
                periods,
            ),
        }
    )


def result_frames():
    frame = source_frame()

    split = split_reference_current_windows(
        frame,
        reference_days=60,
        current_days=30,
    )

    result = evaluate_performance_drift(
        split.reference,
        split.current,
    )

    return build_performance_drift_frames(
        run_id="run-001",
        strategy_key="CLEAN_PROBABILITY",
        benchmark_key="BTC_BUY_HOLD",
        split=split,
        result=result,
        calculated_at_utc=datetime(
            2026,
            7,
            21,
            tzinfo=timezone.utc,
        ),
    )


def connection():
    conn = duckdb.connect(":memory:")

    conn.execute(
        """
        CREATE TABLE module32_runs(
            run_id VARCHAR,
            started_at_utc TIMESTAMPTZ
        )
        """
    )

    conn.execute(
        """
        INSERT INTO module32_runs
        VALUES ('run-001', TIMESTAMPTZ '2026-07-21 12:00:00+00')
        """
    )

    return conn


def test_schema_creates_all_performance_drift_tables() -> None:
    conn = connection()

    conn.execute(MODULE32_PERFORMANCE_DRIFT_SCHEMA)

    tables = {
        row[0]
        for row in conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='main'
            """
        ).fetchall()
    }

    assert "m32_performance_drift_evaluation" in tables
    assert "m32_performance_window_metrics" in tables
    assert "m32_performance_regime_metrics" in tables


def test_frames_include_evaluation_windows_and_regimes() -> None:
    evaluation, windows, regimes = result_frames()

    assert len(evaluation) == 1
    assert set(windows["window_type"]) == {
        "REFERENCE",
        "CURRENT",
    }
    assert set(regimes["window_type"]) == {
        "REFERENCE",
        "CURRENT",
    }

    assert evaluation.iloc[0]["drift_status"] in {
        "DEGRADED",
        "CRITICAL",
    }

    assert evaluation.iloc[0]["governance_action"] in {
        "RETRAIN",
        "ROLLBACK",
    }


def test_persistence_writes_all_records() -> None:
    conn = connection()
    evaluation, windows, regimes = result_frames()

    persist_performance_drift(
        conn,
        evaluation=evaluation,
        windows=windows,
        regimes=regimes,
    )

    evaluation_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM m32_performance_drift_evaluation
        """
    ).fetchone()[0]

    window_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM m32_performance_window_metrics
        """
    ).fetchone()[0]

    regime_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM m32_performance_regime_metrics
        """
    ).fetchone()[0]

    assert evaluation_count == 1
    assert window_count == 2
    assert regime_count == len(regimes)


def test_persistence_is_idempotent() -> None:
    conn = connection()
    evaluation, windows, regimes = result_frames()

    for _ in range(2):
        persist_performance_drift(
            conn,
            evaluation=evaluation,
            windows=windows,
            regimes=regimes,
        )

    assert conn.execute(
        """
        SELECT COUNT(*)
        FROM m32_performance_drift_evaluation
        """
    ).fetchone()[0] == 1

    assert conn.execute(
        """
        SELECT COUNT(*)
        FROM m32_performance_window_metrics
        """
    ).fetchone()[0] == 2


def test_latest_views_return_current_run() -> None:
    conn = connection()
    evaluation, windows, regimes = result_frames()

    persist_performance_drift(
        conn,
        evaluation=evaluation,
        windows=windows,
        regimes=regimes,
    )

    status = conn.execute(
        """
        SELECT drift_status
        FROM latest_m32_performance_drift_evaluation
        """
    ).fetchone()[0]

    assert status in {"DEGRADED", "CRITICAL"}