from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, log_loss


def validate_probability_matrix(
    probabilities: np.ndarray,
    classes: np.ndarray,
) -> None:
    probabilities = np.asarray(probabilities, dtype=float)
    if probabilities.ndim != 2:
        raise ValueError("Probability matrix must be two-dimensional.")
    if probabilities.shape[1] != len(classes):
        raise ValueError(
            f"Probability matrix has {probabilities.shape[1]} columns "
            f"but {len(classes)} canonical classes were supplied."
        )
    if not np.all(np.isfinite(probabilities)):
        raise ValueError("Probability matrix contains non-finite values.")
    if np.any(probabilities < -1e-12):
        raise ValueError("Probability matrix contains negative values.")
    if not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-7):
        raise ValueError("Probability rows do not sum to one.")


def choose_blend_weight(
    gradient: np.ndarray,
    elastic: np.ndarray,
    labels,
    classes: np.ndarray,
    candidates: list[float],
) -> tuple[float, list[dict]]:
    results = []
    for weight in candidates:
        probabilities = (
            weight * gradient
            + (1.0 - weight) * elastic
        )
        probabilities = probabilities / probabilities.sum(
            axis=1,
            keepdims=True,
        )
        validate_probability_matrix(probabilities, classes)
        predictions = classes[np.argmax(probabilities, axis=1)]
        accuracy = accuracy_score(labels, predictions)
        loss = log_loss(
            labels,
            probabilities,
            labels=classes.tolist(),
        )
        objective = accuracy - 0.15 * loss
        results.append({
            "gradient_weight": float(weight),
            "validation_accuracy": float(accuracy),
            "validation_log_loss": float(loss),
            "objective_score": float(objective),
        })
    results.sort(
        key=lambda row: row["objective_score"],
        reverse=True,
    )
    return float(results[0]["gradient_weight"]), results


def multiclass_brier_score(
    probabilities: np.ndarray,
    labels,
    classes: np.ndarray,
) -> float:
    validate_probability_matrix(probabilities, classes)
    class_index = {
        value: index for index, value in enumerate(classes)
    }
    actual = np.zeros_like(probabilities)
    for row_index, value in enumerate(labels):
        if value not in class_index:
            raise ValueError(f"Unknown observed class: {value!r}")
        actual[row_index, class_index[value]] = 1.0
    return float(np.mean(np.sum(
        (probabilities - actual) ** 2,
        axis=1,
    )))
