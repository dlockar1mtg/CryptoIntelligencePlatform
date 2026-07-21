from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parent


def main() -> None:
    signature = inspect.signature(LogisticRegression)
    if "multi_class" in signature.parameters:
        print(
            "Compatibility note: this sklearn version still exposes "
            "multi_class, but v7.3.1 no longer depends on it."
        )

    # Verify the exact estimator family used by Module 28 can perform a
    # multiclass fit without the removed argument.
    rng = np.random.default_rng(731)
    x = rng.normal(size=(120, 8))
    y = np.repeat(np.array([0, 1, 2]), 40)
    x[y == 1, 0] += 1.0
    x[y == 2, 1] -= 1.0

    model = LogisticRegression(
        max_iter=1500,
        class_weight="balanced",
        random_state=731,
    )
    model.fit(x, y)
    probabilities = model.predict_proba(x[:5])

    if probabilities.shape != (5, 3):
        raise RuntimeError(
            f"Unexpected multiclass probability shape: {probabilities.shape}"
        )
    if not np.allclose(probabilities.sum(axis=1), 1.0):
        raise RuntimeError("Multiclass probabilities do not sum to one.")

    # Import Module 28 only after the patch is applied. In the packaged
    # development container, DuckDB may be unavailable; the user's installed
    # platform has it through requirements.txt, so only that specific missing
    # dependency is deferred during artifact validation.
    module_import_status = "PASS"
    try:
        from crypto_platform.module28 import MODULE28_SCHEMA, Module28Runner
        if "m28_research_summary" not in MODULE28_SCHEMA:
            raise RuntimeError("Module 28 schema import validation failed.")
    except ModuleNotFoundError as exc:
        if exc.name != "duckdb":
            raise
        module_import_status = "DEFERRED (DuckDB unavailable in build runtime)"

    print(f"scikit-learn version: {sklearn.__version__}")
    print("LogisticRegression multiclass fit: PASS")
    print(f"Module 28 import and schema validation: {module_import_status}")


if __name__ == "__main__":
    main()
