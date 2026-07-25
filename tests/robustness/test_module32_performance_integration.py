from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from crypto_platform.module32 import Module32Runner


REGIMES = [
    "LIQUIDITY_EXPANSION",
    "MOMENTUM_BULL",
]


def runner() -> Module32Runner:
    instance = Module32Runner.__new__(Module32Runner)
    instance.run_id = "module32-drift-test"
    instance.cfg = {
        "performance_drift": {
            "minimum_observations": 30,
            "reference_window_days": 60,
            "current_window_days": 30,
        }
    }
    instance.conn = duckdb.connect(":memory:")
    instance.conn.execute(
        """
        CREATE TABLE module32_runs(
            run_id VARCHAR,
            started_at_utc TIMESTAMPTZ
        )
        """
    )
    instance.conn.execute(
        """
        INSERT INTO module32_runs
        VALUES (
            'module32-drift-test',
            TIMESTAMPTZ '2026-07-21 12:00:00+00'
        )
        """
    )
    return instance


def inputs(periods: int = 120):
    dates = pd.date_range(
        "2025-01-01",
        periods=periods,
        freq="D",
    )

    current_start = periods - 30
    rows = []

    for index, date in enumerate(dates):
        strategy_return = (
            0.002
            if index < current_start
            else -0.004
        )

        rows.extend(
            [
                {
                    "run_id": "module32-drift-test",
                    "observation_date": date,
                    "strategy_key": "CLEAN_PROBABILITY",
                    "daily_return": strategy_return,
                    "cumulative_return": 1.0,
                    "turnover": 0.0,
                    "transaction_cost": 0.0,
                    "calculated_at_utc": pd.Timestamp(
                        "2026-07-21",
                        tz="UTC",
                    ),
                },
                {
                    "run_id": "module32-drift-test",
                    "observation_date": date,
                    "strategy_key": "BTC_BUY_HOLD",
                    "daily_return": 0.001,
                    "cumulative_return": 1.0,
                    "turnover": 0.0,
                    "transaction_cost": 0.0,
                    "calculated_at_utc": pd.Timestamp(
                        "2026-07-21",
                        tz="UTC",
                    ),
                },
            ]
        )

    probabilities = pd.DataFrame(
        {
            REGIMES[0]: np.concatenate(
                [
                    np.repeat(0.80, current_start),
                    np.repeat(0.95, 30),
                ]
            ),
            REGIMES[1]: np.concatenate(
                [
                    np.repeat(0.20, current_start),
                    np.repeat(0.05, 30),
                ]
            ),
        },
        index=dates,
    )

    history = pd.DataFrame(
        {
            "actual_legacy_regime": np.concatenate(
                [
                    np.repeat(REGIMES[0], current_start),
                    np.repeat(REGIMES[1], 30),
                ]
            ),
            "clean_regime": np.repeat(
                REGIMES[0],
                periods,
            ),
            "model_agreement": np.repeat(
                0.90,
                periods,
            ),
        },
        index=dates,
    )

    benchmarks = pd.DataFrame(
        {
            "strategy_key": [
                "CLEAN_PROBABILITY",
                "BTC_BUY_HOLD",
            ],
            "selected": [True, False],
        }
    )

    return (
        pd.DataFrame(rows),
        probabilities,
        history,
        benchmarks,
    )


def test_module32_persists_realized_performance_drift() -> None:
    instance = runner()
    daily, probabilities, history, benchmarks = inputs()

    result = instance.realized_performance_drift(
        daily,
        probabilities,
        history,
        benchmarks,
    )

    assert result["strategy_key"] == "CLEAN_PROBABILITY"
    assert result["reference_days"] == 60
    assert result["current_days"] == 30
    assert result["governance_action"] in {
        "RETRAIN",
        "ROLLBACK",
    }

    evaluation_count = instance.conn.execute(
        """
        SELECT COUNT(*)
        FROM m32_performance_drift_evaluation
        """
    ).fetchone()[0]

    window_count = instance.conn.execute(
        """
        SELECT COUNT(*)
        FROM m32_performance_window_metrics
        """
    ).fetchone()[0]

    assert evaluation_count == 1
    assert window_count == 2


def test_module32_records_breached_metrics() -> None:
    instance = runner()
    daily, probabilities, history, benchmarks = inputs()

    result = instance.realized_performance_drift(
        daily,
        probabilities,
        history,
        benchmarks,
    )

    assert result["breached_metrics"]
    assert "directional_accuracy" in result["breached_metrics"]
    assert "excess_return" in result["breached_metrics"]