"""Focused v8.1.0 sklearn API compatibility smoke test."""

import inspect

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from crypto_platform.ml.models import build_clean_models


def main():
    gradient, elastic = build_clean_models(random_state=810)

    logistic_parameters = inspect.signature(
        LogisticRegression
    ).parameters
    gradient_parameters = inspect.signature(
        HistGradientBoostingClassifier
    ).parameters

    assert "multi_class" not in elastic.get_params(), (
        "The removed sklearn multi_class argument is still configured."
    )
    assert elastic.get_params()["solver"] == "saga"
    assert elastic.get_params()["penalty"] == "elasticnet"
    assert "max_iter" in logistic_parameters
    assert "max_iter" in gradient_parameters
    assert gradient.get_params()["max_iter"] > 0

    print("v8.1.0 sklearn API compatibility smoke test passed.")


if __name__ == "__main__":
    main()
