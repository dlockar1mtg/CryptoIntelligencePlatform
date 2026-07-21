from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


@dataclass
class CleanModelBundle:
    """Fitted nonlinear and transparent clean-regime models."""

    scaler: StandardScaler
    gradient_boosting: HistGradientBoostingClassifier
    elastic_net: LogisticRegression
    classes: np.ndarray


def build_clean_models(
    random_state: int,
) -> tuple[HistGradientBoostingClassifier, LogisticRegression]:
    gradient_boosting = HistGradientBoostingClassifier(
        learning_rate=0.06,
        max_iter=240,
        max_leaf_nodes=15,
        min_samples_leaf=20,
        l2_regularization=0.20,
        random_state=random_state,
    )

    # sklearn 1.9 deprecates the explicit penalty argument. Supplying
    # l1_ratio with saga selects elastic-net behavior without the warning.
    elastic_net = LogisticRegression(
        solver="saga",
        l1_ratio=0.20,
        C=1.0,
        max_iter=3000,
        class_weight="balanced",
        random_state=random_state,
    )
    return gradient_boosting, elastic_net


def fit_clean_models(
    x,
    y,
    random_state: int,
) -> CleanModelBundle:
    scaler = StandardScaler()
    scaled = scaler.fit_transform(x)
    gradient_boosting, elastic_net = build_clean_models(random_state)
    gradient_boosting.fit(scaled, y)
    elastic_net.fit(scaled, y)
    classes = np.asarray(gradient_boosting.classes_)
    return CleanModelBundle(
        scaler=scaler,
        gradient_boosting=gradient_boosting,
        elastic_net=elastic_net,
        classes=classes,
    )


def align_probabilities(
    probabilities: np.ndarray,
    model_classes: np.ndarray,
    target_classes: np.ndarray,
) -> np.ndarray:
    aligned = np.zeros((len(probabilities), len(target_classes)))
    class_index = {
        value: index for index, value in enumerate(target_classes)
    }
    for source_index, value in enumerate(model_classes):
        if value not in class_index:
            raise RuntimeError(
                f"Model emitted unknown class {value!r}; "
                f"expected one of {target_classes.tolist()}."
            )
        aligned[:, class_index[value]] = probabilities[:, source_index]

    row_sums = aligned.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return aligned / row_sums


def predict_component_probabilities(
    bundle: CleanModelBundle,
    x,
    target_classes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    scaled = bundle.scaler.transform(x)
    gradient = align_probabilities(
        bundle.gradient_boosting.predict_proba(scaled),
        np.asarray(bundle.gradient_boosting.classes_),
        target_classes,
    )
    elastic = align_probabilities(
        bundle.elastic_net.predict_proba(scaled),
        np.asarray(bundle.elastic_net.classes_),
        target_classes,
    )
    return gradient, elastic


def blend_probabilities(
    gradient: np.ndarray,
    elastic: np.ndarray,
    gradient_weight: float,
) -> np.ndarray:
    blended = (
        float(gradient_weight) * gradient
        + (1.0 - float(gradient_weight)) * elastic
    )
    row_sums = blended.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return blended / row_sums


def probability_agreement(
    first: np.ndarray,
    second: np.ndarray,
) -> np.ndarray:
    """Continuous model agreement from 0 to 1 using total-variation distance."""
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    if first.shape != second.shape:
        raise ValueError(
            f"Probability matrices must have equal shape; "
            f"received {first.shape} and {second.shape}."
        )
    return np.clip(
        1.0 - 0.5 * np.abs(first - second).sum(axis=1),
        0.0,
        1.0,
    )
