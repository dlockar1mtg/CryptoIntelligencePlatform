from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crypto_platform.ml.performance_drift import (
    PerformanceDriftThresholds,
    calculate_window_metrics,
    evaluate_performance_drift,
    performance_by_regime,
)


def performance_frame(
    *,
    periods: int = 60,
    strategy_return: float = 0.002,
    benchmark_return: float = 0.001,
    accuracy: float = 0.70,
    confidence: float = 0.70,
    regime: str = "EXPANSION",
) -> pd.DataFrame:
    correct_count = int(periods * accuracy)

    correctness = np.array(
        [1.0] * correct_count
        + [0.0] * (periods - correct_count)
    )

    return pd.DataFrame(
        {
            "observation_date": pd.date_range(
                "2025-01-01",
                periods=periods,
                freq="D",
            ),
            "strategy_return": np.repeat(
                strategy_return,
                periods,
            ),
            "benchmark_return": np.repeat(
                benchmark_return,
                periods,
            ),
            "prediction_correct": correctness,
            "predicted_probability": np.repeat(
                confidence,
                periods,
            ),
            "actual_probability": correctness,
            "market_regime": np.repeat(regime, periods),
        }
    )


def test_window_metrics_include_required_realized_measures() -> None:
    metrics = calculate_window_metrics(performance_frame())

    assert metrics.observations == 60
    assert metrics.directional_accuracy_pct == pytest.approx(70.0)
    assert metrics.cumulative_return_pct > 0
    assert metrics.excess_return_pct > 0
    assert metrics.maximum_drawdown_pct == pytest.approx(0.0)
    assert metrics.decision_hit_rate_pct == pytest.approx(100.0)


def test_healthy_performance_produces_no_action() -> None:
    reference = performance_frame()
    current = performance_frame()

    result = evaluate_performance_drift(reference, current)

    assert result.drift_status == "HEALTHY"
    assert result.governance_action == "NONE"
    assert result.breached_metrics == ()


def test_multiple_degradations_trigger_retraining() -> None:
    reference = performance_frame(
        strategy_return=0.003,
        benchmark_return=0.001,
        accuracy=0.80,
        confidence=0.80,
    )

    current = performance_frame(
        strategy_return=-0.002,
        benchmark_return=0.001,
        accuracy=0.50,
        confidence=0.90,
    )

    result = evaluate_performance_drift(reference, current)

    assert result.drift_status in {"DEGRADED", "CRITICAL"}
    assert result.governance_action in {"RETRAIN", "ROLLBACK"}
    assert "directional_accuracy" in result.breached_metrics
    assert "excess_return" in result.breached_metrics


def test_severe_broad_degradation_triggers_rollback() -> None:
    reference = performance_frame(
        strategy_return=0.004,
        benchmark_return=0.001,
        accuracy=0.90,
        confidence=0.90,
    )

    current = performance_frame(
        strategy_return=-0.01,
        benchmark_return=0.002,
        accuracy=0.30,
        confidence=0.95,
    )

    result = evaluate_performance_drift(reference, current)

    assert result.drift_status == "CRITICAL"
    assert result.governance_action == "ROLLBACK"
    assert len(result.breached_metrics) >= 5


def test_minimum_observation_gate_is_enforced() -> None:
    thresholds = PerformanceDriftThresholds(
        minimum_observations=30
    )

    with pytest.raises(
        ValueError,
        match="minimum observation",
    ):
        evaluate_performance_drift(
            performance_frame(periods=20),
            performance_frame(periods=60),
            thresholds,
        )


def test_performance_is_reported_by_market_regime() -> None:
    expansion = performance_frame(
        periods=30,
        regime="EXPANSION",
    )
    contraction = performance_frame(
        periods=30,
        strategy_return=-0.002,
        regime="CONTRACTION",
    )

    combined = pd.concat(
        [expansion, contraction],
        ignore_index=True,
    )

    result = performance_by_regime(combined)

    assert set(result["market_regime"]) == {
        "EXPANSION",
        "CONTRACTION",
    }
    assert len(result) == 2