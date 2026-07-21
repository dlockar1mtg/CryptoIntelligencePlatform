from __future__ import annotations

import numpy as np
import pandas as pd

from crypto_platform.ml.models import (
    predict_component_probabilities,
    blend_probabilities,
)


def counterfactual_feature_contributions(
    bundle,
    calibrator,
    current: pd.DataFrame,
    training_medians: pd.Series,
    features: list[str],
    classes: np.ndarray,
    gradient_weight: float,
    predicted_regime: str,
) -> pd.DataFrame:
    gradient, elastic = predict_component_probabilities(
        bundle,
        current[features],
        classes,
    )
    baseline = calibrator.predict(
        blend_probabilities(
            gradient,
            elastic,
            gradient_weight,
        )
    )
    class_index = {
        value: index for index, value in enumerate(classes)
    }
    target = class_index[predicted_regime]
    baseline_probability = float(baseline[0, target])

    rows = []
    for feature in features:
        counterfactual = current[features].copy()
        counterfactual.loc[
            counterfactual.index[0],
            feature,
        ] = float(training_medians[feature])

        g, e = predict_component_probabilities(
            bundle,
            counterfactual,
            classes,
        )
        probability = calibrator.predict(
            blend_probabilities(
                g,
                e,
                gradient_weight,
            )
        )
        counterfactual_probability = float(
            probability[0, target]
        )
        contribution = (
            baseline_probability
            - counterfactual_probability
        )
        rows.append({
            "feature_key": feature,
            "feature_value": float(
                current.iloc[0][feature]
            ),
            "reference_value": float(
                training_medians[feature]
            ),
            "probability_contribution": float(contribution),
            "direction": (
                "SUPPORTS"
                if contribution > 0
                else "OPPOSES"
                if contribution < 0
                else "NEUTRAL"
            ),
        })
    frame = pd.DataFrame(rows)
    frame["absolute_contribution"] = frame[
        "probability_contribution"
    ].abs()
    frame = frame.sort_values(
        "absolute_contribution",
        ascending=False,
    )
    frame["rank"] = range(1, len(frame) + 1)
    return frame
