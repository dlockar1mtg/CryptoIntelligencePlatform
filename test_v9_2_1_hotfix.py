import warnings
import numpy as np

from crypto_platform.module37 import portfolio_metrics


def main():
    weights = np.asarray([
        0.02,
        0.01,
        0.005,
        0.0,
        0.0,
        0.0,
    ])
    expected = np.asarray([
        0.10,
        0.08,
        0.06,
        0.04,
        0.02,
        0.01,
    ])
    covariance = np.eye(6) * 0.20

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        metrics = portfolio_metrics(
            weights,
            expected,
            covariance,
        )

    entropy_warnings = [
        warning
        for warning in caught
        if "divide by zero" in str(
            warning.message
        ).lower()
        or "invalid value" in str(
            warning.message
        ).lower()
    ]
    assert not entropy_warnings, entropy_warnings
    assert np.isfinite(metrics["entropy"])
    print("v9.2.1 entropy hotfix test passed.")
    print(f"Entropy: {metrics['entropy']:.6f}")


if __name__ == "__main__":
    main()
