from __future__ import annotations

import pandas as pd


def require_columns(
    frame: pd.DataFrame,
    columns: list[str],
    label: str,
) -> None:
    """Raise a clear error when a required dataset column is absent."""
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise RuntimeError(
            f"{label} is missing required columns: {missing}"
        )


def aligned_feature_label_frame(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    feature_columns: list[str],
    label_column: str,
) -> pd.DataFrame:
    """Align features and labels by date and remove incomplete observations."""
    require_columns(features, feature_columns, "Feature frame")
    require_columns(labels, [label_column], "Label frame")
    combined = pd.concat(
        [features[feature_columns], labels[[label_column]]],
        axis=1,
    )
    return (
        combined.replace([float("inf"), float("-inf")], pd.NA)
        .dropna()
        .sort_index()
    )
