"""v8.1.1 lightweight stabilization smoke tests."""

import warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from crypto_platform.ml.classes import canonical_classes
from crypto_platform.ml.models import probability_agreement
from crypto_platform.ml.validation import validate_probability_matrix


def main():
    classes = canonical_classes()
    assert classes.tolist() == sorted(classes.tolist())

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        LogisticRegression(
            solver="saga",
            l1_ratio=0.20,
            C=1.0,
            max_iter=25,
            class_weight="balanced",
            random_state=811,
        )

    deprecated = [
        warning for warning in captured
        if "penalty" in str(warning.message).lower()
        and "deprecated" in str(warning.message).lower()
    ]
    assert not deprecated, deprecated

    probabilities = np.asarray([
        [0.70,0.10,0.05,0.05,0.05,0.05],
        [0.05,0.70,0.05,0.05,0.10,0.05],
        [0.05,0.05,0.70,0.05,0.10,0.05],
    ])
    labels = [
        "LIQUIDITY_EXPANSION",
        "MACRO_STRESS",
        "MOMENTUM_BULL",
    ]
    validate_probability_matrix(probabilities, classes)
    loss = log_loss(
        labels,
        probabilities,
        labels=classes.tolist(),
    )
    assert 0 < loss < 1

    agreement = probability_agreement(
        np.asarray([[0.7,0.1,0.1,0.05,0.03,0.02]]),
        np.asarray([[0.6,0.2,0.1,0.05,0.03,0.02]]),
    )[0]
    assert 0 <= agreement <= 1

    print("Canonical classes:", classes.tolist())
    print(f"Canonical-order log loss: {loss:.6f}")
    print(f"Continuous agreement: {agreement:.6f}")
    print("v8.1.1 stabilization smoke tests passed.")


if __name__ == "__main__":
    main()
