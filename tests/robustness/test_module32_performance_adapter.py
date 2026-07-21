from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crypto_platform.ml.module32_performance_adapter import (
    build_module32_performance_frame,
    split_reference_current_windows,
)


REGIMES = [
    "LIQUIDITY_EXPANSION",
    "MOMENTUM_BULL",
]


def daily_returns(periods: int = 100) -> pd.DataFrame:
    dates = pd.date_range(
        "2025-01-01",
        periods=periods,
        freq="D",
    )

    rows = []

    for date in dates:
        rows.append(
            {
                "observation_date": date,
                "strategy_key": "CLEAN_PROBABILITY",
                "daily_return": 0.002,
            }
        )
        rows.append(
            {
                "observation_date": date,
                "strategy_key": "BTC_BUY_HOLD",
                "daily_return": 0.001,
            }
        )

    return pd.DataFrame(rows)


def probability_history(
    periods: int = 100,
) -> pd.DataFrame:
    dates = pd.date_range(
        "2025-01-01",
        periods=periods,
        freq="D",
    )

    return pd.DataFrame(
        {
            REGIMES[0]: np.repeat(0.80, periods),
            REGIMES[1]: np.repeat(0.20, periods),
        },
        index=dates,
    )


def regime_history(
    periods: int = 100,
) -> pd.DataFrame:
    dates = pd.date_range(
        "2025-01-01",
        periods=periods,
        freq="D",
    )

    return pd.DataFrame(
        {
            "actual_legacy_regime": np.repeat(
                REGIMES[0],
                periods,
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


def test_adapter_builds_standard_performance_frame() -> None:
    result = build_module32_performance_frame(
        daily_returns(),
        probability_history(),
        regime_history(),
        strategy_key="CLEAN_PROBABILITY",
    )

    assert len(result) == 100
    assert result["prediction_correct"].mean() == 1.0
    assert result["predicted_probability"].mean() == pytest.approx(
        0.80
    )
    assert result["strategy_return"].mean() == pytest.approx(
        0.002
    )
    assert result["benchmark_return"].mean() == pytest.approx(
        0.001
    )
    assert set(result["market_regime"]) == {
        "LIQUIDITY_EXPANSION"
    }


def test_adapter_uses_only_common_dates() -> None:
    probabilities = probability_history().iloc[10:]

    result = build_module32_performance_frame(
        daily_returns(),
        probabilities,
        regime_history(),
        strategy_key="CLEAN_PROBABILITY",
    )

    assert len(result) == 90
    assert result["observation_date"].min() == pd.Timestamp(
        "2025-01-11"
    )


def test_missing_strategy_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="No daily returns exist for strategy",
    ):
        build_module32_performance_frame(
            daily_returns(),
            probability_history(),
            regime_history(),
            strategy_key="DOES_NOT_EXIST",
        )


def test_probability_rows_must_sum_to_one() -> None:
    probabilities = probability_history()
    probabilities.iloc[0] = [0.90, 0.90]

    with pytest.raises(
        ValueError,
        match="sum to one",
    ):
        build_module32_performance_frame(
            daily_returns(),
            probabilities,
            regime_history(),
            strategy_key="CLEAN_PROBABILITY",
        )


def test_reference_and_current_windows_are_non_overlapping() -> None:
    frame = build_module32_performance_frame(
        daily_returns(),
        probability_history(),
        regime_history(),
        strategy_key="CLEAN_PROBABILITY",
    )

    split = split_reference_current_windows(
        frame,
        reference_days=60,
        current_days=30,
    )

    assert len(split.reference) == 60
    assert len(split.current) == 30
    assert split.reference_end_date < split.current_start_date


def test_insufficient_history_is_rejected() -> None:
    frame = build_module32_performance_frame(
        daily_returns(periods=40),
        probability_history(periods=40),
        regime_history(periods=40),
        strategy_key="CLEAN_PROBABILITY",
    )

    with pytest.raises(
        ValueError,
        match="does not contain enough rows",
    ):
        split_reference_current_windows(
            frame,
            reference_days=30,
            current_days=30,
        )