from __future__ import annotations

import numpy as np
import pandas as pd


def population_stability_index(
    expected: pd.Series,
    actual: pd.Series,
    bins: int = 10,
) -> float:
    expected = expected.dropna().astype(float)
    actual = actual.dropna().astype(float)
    if expected.empty or actual.empty:
        return 0.0

    edges = np.unique(
        np.quantile(
            expected,
            np.linspace(0, 1, bins + 1),
        )
    )
    if len(edges) < 3:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf

    expected_counts, _ = np.histogram(expected, bins=edges)
    actual_counts, _ = np.histogram(actual, bins=edges)
    expected_pct = np.clip(
        expected_counts / max(expected_counts.sum(), 1),
        1e-6,
        None,
    )
    actual_pct = np.clip(
        actual_counts / max(actual_counts.sum(), 1),
        1e-6,
        None,
    )
    return float(np.sum(
        (actual_pct - expected_pct)
        * np.log(actual_pct / expected_pct)
    ))


def feature_drift_table(
    training: pd.DataFrame,
    recent: pd.DataFrame,
    current: pd.Series,
) -> pd.DataFrame:
    rows = []
    for feature in training.columns:
        mean = float(training[feature].mean())
        std = max(float(training[feature].std()), 1e-9)
        current_value = float(current[feature])
        z_score = (current_value - mean) / std
        psi = population_stability_index(
            training[feature],
            recent[feature],
        )
        rows.append({
            "feature_key": feature,
            "training_mean": mean,
            "training_std": std,
            "current_value": current_value,
            "current_z_score": float(z_score),
            "psi": psi,
            "feature_drift_score": float(
                0.55 * min(abs(z_score) / 4, 1)
                + 0.45 * min(psi / 0.5, 1)
            ),
        })
    return pd.DataFrame(rows)


def drift_status(
    table: pd.DataFrame,
) -> tuple[float, str]:
    score = float(table["feature_drift_score"].mean())
    maximum = float(table["feature_drift_score"].max())
    combined = max(score, maximum * 0.75)
    if combined >= 0.70:
        return combined, "HIGH"
    if combined >= 0.40:
        return combined, "MODERATE"
    return combined, "LOW"
