from __future__ import annotations

from types import MethodType

import numpy as np
import pandas as pd

from crypto_platform.module26 import (
    Module26Runner,
    REGIMES as MODULE26_REGIMES,
)
from crypto_platform.module28 import (
    Module28Runner,
    REGIMES as MODULE28_REGIMES,
)


def probability_vector(size: int = 6) -> np.ndarray:
    values = np.zeros(size, dtype=float)
    values[0] = 1.0
    return values


def module26_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    index = pd.date_range(
        "2020-01-01",
        periods=215,
        freq="D",
    )

    features = pd.DataFrame(
        {
            "feature_a": np.linspace(
                0.0,
                1.0,
                len(index),
            ),
            "feature_b": np.linspace(
                1.0,
                0.0,
                len(index),
            ),
        },
        index=index,
    )

    labels = pd.DataFrame(
        {
            "dominant_regime": [
                MODULE26_REGIMES[0]
                for _ in index
            ],
            "regime_confidence": np.repeat(
                0.80,
                len(index),
            ),
        },
        index=index,
    )

    return features, labels


def build_module26_runner(
    captured: list[pd.DataFrame],
) -> Module26Runner:
    runner = Module26Runner.__new__(
        Module26Runner
    )

    runner.run_id = "module26-strict-nesting"
    runner.cfg = {
        "nested_walk_forward": {
            "minimum_training_days": 201,
            "outer_test_days": 10,
            "inner_validation_days": 20,
        }
    }

    candidate = {
        "candidate_key": "TEST",
        "gmm_weight": 0.25,
        "kmeans_weight": 0.25,
        "rule_weight": 0.25,
        "markov_weight": 0.25,
        "smoothing": 0.50,
    }

    runner.weight_candidates = MethodType(
        lambda self: [candidate],
        runner,
    )

    runner.transition_matrix = MethodType(
        lambda self, labels: (
            pd.DataFrame(
                np.eye(len(MODULE26_REGIMES)),
                index=MODULE26_REGIMES,
                columns=MODULE26_REGIMES,
            ),
            pd.DataFrame(),
        ),
        runner,
    )

    runner.components = MethodType(
        lambda self, train, test, rows, transition, previous: [
            None
            for _ in range(len(test))
        ],
        runner,
    )

    runner.combine = MethodType(
        lambda self, component, candidate_value, previous: (
            probability_vector(
                len(MODULE26_REGIMES)
            )
        ),
        runner,
    )

    def select_features_for_fold(
        self,
        train,
        candidate_features=None,
    ):
        captured.append(
            train.copy(deep=True)
        )
        return ["feature_a"]

    runner.select_features_for_fold = MethodType(
        select_features_for_fold,
        runner,
    )

    return runner


def test_module26_reselects_features_after_inner_tuning() -> None:
    features, labels = module26_frames()
    captured: list[pd.DataFrame] = []

    runner = build_module26_runner(captured)

    _, predictions = runner.nested(
        features,
        labels,
        ["feature_a", "feature_b"],
    )

    assert not predictions.empty
    assert len(captured) >= 2

    inner_selection_frame = captured[0]
    outer_selection_frame = captured[1]

    first_fold = predictions[
        predictions["outer_fold"] == 1
    ]

    first_test_date = pd.Timestamp(
        first_fold["testing_start_date"].iloc[0]
    )

    assert len(inner_selection_frame) == 181
    assert len(outer_selection_frame) == 201

    assert (
        inner_selection_frame.index.max()
        < outer_selection_frame.index.max()
    )

    assert (
        outer_selection_frame.index.max()
        < first_test_date
    )

    inner_validation_dates = (
        outer_selection_frame.index.difference(
            inner_selection_frame.index
        )
    )

    assert len(inner_validation_dates) == 20
    assert not inner_selection_frame.index.isin(
        inner_validation_dates
    ).any()


def module28_frame() -> pd.DataFrame:
    index = pd.date_range(
        "2020-01-01",
        periods=261,
        freq="D",
    )

    return pd.DataFrame(
        {
            "feature_a": np.linspace(
                0.0,
                1.0,
                len(index),
            ),
            "feature_b": np.linspace(
                1.0,
                0.0,
                len(index),
            ),
            "dominant_regime": [
                MODULE28_REGIMES[0]
                for _ in index
            ],
        },
        index=index,
    )


def module28_result(length: int) -> dict[str, object]:
    return {
        "objective": 1.0,
        "agreement": 100.0,
        "calibration_mae": 0.0,
        "switch_rate": 0.0,
        "probabilities": [
            probability_vector(
                len(MODULE28_REGIMES)
            )
            for _ in range(length)
        ],
    }


def build_module28_runner(
    captured: list[pd.DataFrame],
) -> Module28Runner:
    runner = Module28Runner.__new__(
        Module28Runner
    )

    runner.run_id = "module28-strict-nesting"
    runner.cfg = {
        "nested_walk_forward": {
            "minimum_training_days": 251,
            "inner_validation_days": 10,
            "outer_test_days": 10,
        },
        "meta_ensemble": {
            "top_candidates": 1,
            "temperature": 1.0,
        },
    }

    candidate = {
        "candidate_id": "TEST",
        "generation": 0,
        "weights": np.array(
            [0.25, 0.25, 0.25, 0.25]
        ),
        "temperature": 1.0,
        "smoothing": 0.50,
        "transition_strength": 1.0,
    }

    def select_features_for_fold(
        self,
        train,
        candidate_features=None,
    ):
        captured.append(
            train.copy(deep=True)
        )
        return ["feature_a"]

    runner.select_features_for_fold = MethodType(
        select_features_for_fold,
        runner,
    )

    runner.components = MethodType(
        lambda self, train, labels, test: [
            None
            for _ in range(len(test))
        ],
        runner,
    )

    runner.adaptive_search = MethodType(
        lambda self, components, actual, fold: [
            (
                1.0,
                candidate,
                module28_result(
                    len(components)
                ),
            )
        ],
        runner,
    )

    runner.calibrators = MethodType(
        lambda self, raw, correct: {
            "IDENTITY": (
                None,
                0.0,
                0.0,
            )
        },
        runner,
    )

    runner.apply_calibrator = MethodType(
        lambda self, method, model, values: (
            np.asarray(values)
        ),
        runner,
    )

    runner.evaluate = MethodType(
        lambda self, components, actual, candidate_value: (
            module28_result(
                len(components)
            )
        ),
        runner,
    )

    return runner


def test_module28_reselects_features_after_inner_tuning() -> None:
    frame = module28_frame()
    captured: list[pd.DataFrame] = []

    runner = build_module28_runner(captured)

    _, predictions, _, _ = runner.nested_run(
        frame,
        ["feature_a", "feature_b"],
    )

    assert not predictions.empty
    assert len(captured) >= 2

    inner_selection_frame = captured[0]
    outer_selection_frame = captured[1]

    first_fold = predictions[
        predictions["outer_fold"] == 1
    ]

    first_test_date = pd.Timestamp(
        first_fold["testing_start_date"].iloc[0]
    )

    assert len(inner_selection_frame) == 241
    assert len(outer_selection_frame) == 251

    assert (
        inner_selection_frame.index.max()
        < outer_selection_frame.index.max()
    )

    assert (
        outer_selection_frame.index.max()
        < first_test_date
    )

    inner_validation_dates = (
        outer_selection_frame.index.difference(
            inner_selection_frame.index
        )
    )

    assert len(inner_validation_dates) == 10
    assert not inner_selection_frame.index.isin(
        inner_validation_dates
    ).any()