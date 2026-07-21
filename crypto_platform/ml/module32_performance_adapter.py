from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


REQUIRED_DAILY_COLUMNS = {
    "observation_date",
    "strategy_key",
    "daily_return",
}

REQUIRED_HISTORY_COLUMNS = {
    "actual_legacy_regime",
}


@dataclass(frozen=True)
class PerformanceWindowSplit:
    reference: pd.DataFrame
    current: pd.DataFrame
    reference_start_date: pd.Timestamp
    reference_end_date: pd.Timestamp
    current_start_date: pd.Timestamp
    current_end_date: pd.Timestamp


def _normalize_daily_returns(
    daily_returns: pd.DataFrame,
) -> pd.DataFrame:
    missing = sorted(
        REQUIRED_DAILY_COLUMNS - set(daily_returns.columns)
    )

    if missing:
        raise ValueError(
            "Daily benchmark data is missing required columns: "
            + ", ".join(missing)
        )

    result = daily_returns.copy()
    result["observation_date"] = pd.to_datetime(
        result["observation_date"],
        errors="raise",
    )
    result["daily_return"] = pd.to_numeric(
        result["daily_return"],
        errors="raise",
    )

    return result.sort_values(
        ["observation_date", "strategy_key"]
    )


def _normalize_probabilities(
    probabilities: pd.DataFrame,
) -> pd.DataFrame:
    if probabilities.empty:
        raise ValueError(
            "Clean probability history cannot be empty."
        )

    result = probabilities.copy()
    result.index = pd.to_datetime(
        result.index,
        errors="raise",
    )
    result = result.sort_index()

    numeric = result.apply(
        pd.to_numeric,
        errors="raise",
    )

    row_sums = numeric.sum(axis=1)

    if not np.allclose(
        row_sums.to_numpy(),
        1.0,
        atol=1e-6,
    ):
        raise ValueError(
            "Clean probability rows must sum to one."
        )

    if ((numeric < 0) | (numeric > 1)).any().any():
        raise ValueError(
            "Clean probabilities must be between zero and one."
        )

    return numeric


def _normalize_history(
    history: pd.DataFrame,
) -> pd.DataFrame:
    missing = sorted(
        REQUIRED_HISTORY_COLUMNS - set(history.columns)
    )

    if missing:
        raise ValueError(
            "Regime history is missing required columns: "
            + ", ".join(missing)
        )

    result = history.copy()
    result.index = pd.to_datetime(
        result.index,
        errors="raise",
    )

    return result.sort_index()


def build_module32_performance_frame(
    daily_returns: pd.DataFrame,
    probabilities: pd.DataFrame,
    history: pd.DataFrame,
    *,
    strategy_key: str,
    benchmark_key: str = "BTC_BUY_HOLD",
) -> pd.DataFrame:
    daily = _normalize_daily_returns(daily_returns)
    probs = _normalize_probabilities(probabilities)
    hist = _normalize_history(history)

    strategy = daily[
        daily["strategy_key"] == strategy_key
    ][
        ["observation_date", "daily_return"]
    ].rename(
        columns={"daily_return": "strategy_return"}
    )

    benchmark = daily[
        daily["strategy_key"] == benchmark_key
    ][
        ["observation_date", "daily_return"]
    ].rename(
        columns={"daily_return": "benchmark_return"}
    )

    if strategy.empty:
        raise ValueError(
            f"No daily returns exist for strategy {strategy_key!r}."
        )

    if benchmark.empty:
        raise ValueError(
            f"No daily returns exist for benchmark {benchmark_key!r}."
        )

    duplicate_strategy_dates = strategy[
        "observation_date"
    ].duplicated()

    if duplicate_strategy_dates.any():
        raise ValueError(
            "Strategy daily returns contain duplicate dates."
        )

    duplicate_benchmark_dates = benchmark[
        "observation_date"
    ].duplicated()

    if duplicate_benchmark_dates.any():
        raise ValueError(
            "Benchmark daily returns contain duplicate dates."
        )

    returns = strategy.merge(
        benchmark,
        on="observation_date",
        how="inner",
        validate="one_to_one",
    ).set_index("observation_date")

    common = (
        returns.index
        .intersection(probs.index)
        .intersection(hist.index)
    )

    if common.empty:
        raise ValueError(
            "No common dates exist across returns, probabilities, "
            "and regime history."
        )

    returns = returns.reindex(common)
    probs = probs.reindex(common)
    hist = hist.reindex(common)

    predicted_regime = probs.idxmax(axis=1)
    predicted_probability = probs.max(axis=1)
    actual_regime = hist["actual_legacy_regime"].astype(str)

    result = pd.DataFrame(
        {
            "observation_date": common,
            "strategy_return": returns[
                "strategy_return"
            ].to_numpy(),
            "benchmark_return": returns[
                "benchmark_return"
            ].to_numpy(),
            "prediction_correct": (
                predicted_regime.astype(str)
                == actual_regime
            ).astype(float).to_numpy(),
            "predicted_probability": (
                predicted_probability.to_numpy()
            ),
            "actual_probability": (
                predicted_regime.astype(str)
                == actual_regime
            ).astype(float).to_numpy(),
            "market_regime": actual_regime.to_numpy(),
            "predicted_regime": (
                predicted_regime.astype(str).to_numpy()
            ),
            "strategy_key": strategy_key,
            "benchmark_key": benchmark_key,
        }
    )

    return result.sort_values(
        "observation_date"
    ).reset_index(drop=True)


def split_reference_current_windows(
    performance_frame: pd.DataFrame,
    *,
    reference_days: int,
    current_days: int,
) -> PerformanceWindowSplit:
    if reference_days <= 0:
        raise ValueError(
            "reference_days must be greater than zero."
        )

    if current_days <= 0:
        raise ValueError(
            "current_days must be greater than zero."
        )

    required_rows = reference_days + current_days

    if len(performance_frame) < required_rows:
        raise ValueError(
            "Performance history does not contain enough rows for "
            f"{reference_days} reference days and "
            f"{current_days} current days."
        )

    ordered = performance_frame.copy()
    ordered["observation_date"] = pd.to_datetime(
        ordered["observation_date"],
        errors="raise",
    )
    ordered = ordered.sort_values(
        "observation_date"
    ).reset_index(drop=True)

    current = ordered.iloc[-current_days:].copy()
    reference = ordered.iloc[
        -(reference_days + current_days):-current_days
    ].copy()

    if reference.empty or current.empty:
        raise ValueError(
            "Reference and current windows must both contain data."
        )

    if (
        reference["observation_date"].max()
        >= current["observation_date"].min()
    ):
        raise ValueError(
            "Reference and current performance windows overlap."
        )

    return PerformanceWindowSplit(
        reference=reference,
        current=current,
        reference_start_date=reference[
            "observation_date"
        ].min(),
        reference_end_date=reference[
            "observation_date"
        ].max(),
        current_start_date=current[
            "observation_date"
        ].min(),
        current_end_date=current[
            "observation_date"
        ].max(),
    )