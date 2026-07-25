from __future__ import annotations

import json
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


def module26_frame() -> tuple[pd.DataFrame, pd.DataFrame]:
    index = pd.date_range(
        "2020-01-01",
        periods=215,
        freq="D",
    )

    features = pd.DataFrame(
        {
            "feature_a": np.linspace(0.0, 1.0, len(index)),
            "feature_b": np.linspace(1.0, 0.0, len(index)),
        },
        index=index,
    )

    labels = pd.DataFrame(
        {
            "dominant_regime": [
                MODULE26_REGIMES[0]
                for _ in index
            ],
            "regime_confidence": np.repeat(0.80, len(index)),
        },
        index=index,
    )

    return features, labels


def build_module26_runner(
    captured_training_frames: list[pd.DataFrame],
) -> Module26Runner:
    runner = Module26Runner.__new__(Module26Runner)

    runner.run_id = "module26-future-isolation"
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
            None for _ in range(len(test))
        ],
        runner,
    )

    runner.combine = MethodType(
        lambda self, component, candidate_value, previous: (
            probability_vector(len(MODULE26_REGIMES))
        ),
        runner,
    )

    def select_features_for_fold(
        self,
        train,
        candidate_features=None,
    ):
        captured_training_frames.append(train.copy(deep=True))
        return ["feature_a"]

    runner.select_features_for_fold = MethodType(
        select_features_for_fold,
        runner,
    )

    return runner


def first_fold_feature_record(
    predictions: pd.DataFrame,
    column: str,
) -> list[str]:
    first_fold = predictions[
        predictions["outer_fold"] == predictions["outer_fold"].min()
    ]

    assert not first_fold.empty

    values = first_fold[column].drop_duplicates().tolist()

    assert len(values) == 1

    return json.loads(values[0])


def test_module26_future_rows_cannot_change_first_fold_selection() -> None:
    features, labels = module26_frame()

    altered_features = features.copy(deep=True)
    altered_features.iloc[201:, :] = 1_000_000.0

    original_captured: list[pd.DataFrame] = []
    altered_captured: list[pd.DataFrame] = []

    original_runner = build_module26_runner(original_captured)
    altered_runner = build_module26_runner(altered_captured)

    _, original_predictions = original_runner.nested(
        features,
        labels,
        ["feature_a", "feature_b"],
    )

    _, altered_predictions = altered_runner.nested(
        altered_features,
        labels,
        ["feature_a", "feature_b"],
    )

    assert original_captured
    assert altered_captured

    pd.testing.assert_frame_equal(
        original_captured[0],
        altered_captured[0],
    )

    first_test_date = pd.Timestamp(
        original_predictions[
            original_predictions["outer_fold"] == 1
        ]["testing_start_date"].iloc[0]
    )

    assert original_captured[0].index.max() < first_test_date

    assert first_fold_feature_record(
        original_predictions,
        "selected_features_json",
    ) == ["feature_a"]

    assert first_fold_feature_record(
        altered_predictions,
        "selected_features_json",
    ) == ["feature_a"]


def module28_frame() -> pd.DataFrame:
    index = pd.date_range(
        "2020-01-01",
        periods=261,
        freq="D",
    )

    return pd.DataFrame(
        {
            "feature_a": np.linspace(0.0, 1.0, len(index)),
            "feature_b": np.linspace(1.0, 0.0, len(index)),
            "dominant_regime": [
                MODULE28_REGIMES[0]
                for _ in index
            ],
        },
        index=index,
    )


def module28_result(length: int) -> dict[str, object]:
    probabilities = [
        probability_vector(len(MODULE28_REGIMES))
        for _ in range(length)
    ]

    return {
        "objective": 1.0,
        "agreement": 100.0,
        "calibration_mae": 0.0,
        "switch_rate": 0.0,
        "probabilities": probabilities,
    }


def build_module28_runner(
    captured_training_frames: list[pd.DataFrame],
) -> Module28Runner:
    runner = Module28Runner.__new__(Module28Runner)

    runner.run_id = "module28-future-isolation"
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
        "weights": np.array([0.25, 0.25, 0.25, 0.25]),
        "temperature": 1.0,
        "smoothing": 0.50,
        "transition_strength": 1.0,
    }

    def select_features_for_fold(
        self,
        train,
        candidate_features=None,
    ):
        captured_training_frames.append(train.copy(deep=True))
        return ["feature_a"]

    runner.select_features_for_fold = MethodType(
        select_features_for_fold,
        runner,
    )

    runner.components = MethodType(
        lambda self, train, labels, test: [
            None for _ in range(len(test))
        ],
        runner,
    )

    runner.adaptive_search = MethodType(
        lambda self, components, actual, fold: [
            (
                1.0,
                candidate,
                module28_result(len(components)),
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
        lambda self, method, model, values: np.asarray(values),
        runner,
    )

    runner.evaluate = MethodType(
        lambda self, components, actual, candidate_value: (
            module28_result(len(components))
        ),
        runner,
    )

    return runner


def test_module28_future_rows_cannot_change_first_fold_selection() -> None:
    frame = module28_frame()

    altered_frame = frame.copy(deep=True)
    altered_frame.iloc[251:, 0:2] = 1_000_000.0

    original_captured: list[pd.DataFrame] = []
    altered_captured: list[pd.DataFrame] = []

    original_runner = build_module28_runner(original_captured)
    altered_runner = build_module28_runner(altered_captured)

    _, original_predictions, _, _ = original_runner.nested_run(
        frame,
        ["feature_a", "feature_b"],
    )

    _, altered_predictions, _, _ = altered_runner.nested_run(
        altered_frame,
        ["feature_a", "feature_b"],
    )

    assert original_captured
    assert altered_captured

    pd.testing.assert_frame_equal(
        original_captured[0],
        altered_captured[0],
    )

    first_test_date = pd.Timestamp(
        original_predictions[
            original_predictions["outer_fold"] == 1
        ]["testing_start_date"].iloc[0]
    )

    assert original_captured[0].index.max() < first_test_date

    assert first_fold_feature_record(
        original_predictions,
        "retained_features_json",
    ) == ["feature_a"]

    assert first_fold_feature_record(
        altered_predictions,
        "retained_features_json",
    ) == ["feature_a"]