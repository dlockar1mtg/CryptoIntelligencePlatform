from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression


@dataclass
class MulticlassProbabilityCalibrator:
    """Multinomial calibration using log-probability features."""

    model: LogisticRegression | None
    target_classes: np.ndarray

    def predict(self, probabilities: np.ndarray) -> np.ndarray:
        probabilities = np.clip(probabilities, 1e-9, 1.0)
        if self.model is None:
            return probabilities / probabilities.sum(
                axis=1,
                keepdims=True,
            )

        calibrated = self.model.predict_proba(
            np.log(probabilities)
        )
        aligned = np.zeros(
            (len(probabilities), len(self.target_classes))
        )
        target_index = {
            value: index
            for index, value in enumerate(self.target_classes)
        }
        for source_index, value in enumerate(self.model.classes_):
            aligned[:, target_index[value]] = calibrated[:, source_index]

        row_sums = aligned.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        return aligned / row_sums


def fit_multiclass_calibrator(
    probabilities: np.ndarray,
    labels,
    target_classes: np.ndarray,
    random_state: int,
) -> MulticlassProbabilityCalibrator:
    unique = np.unique(labels)
    if len(unique) < 2 or len(probabilities) < 30:
        return MulticlassProbabilityCalibrator(
            model=None,
            target_classes=target_classes,
        )

    model = LogisticRegression(
        max_iter=2500,
        class_weight="balanced",
        C=0.75,
        random_state=random_state,
    )
    model.fit(
        np.log(np.clip(probabilities, 1e-9, 1.0)),
        labels,
    )
    return MulticlassProbabilityCalibrator(
        model=model,
        target_classes=target_classes,
    )
