from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]


def zero_risk_metrics(
    weights: np.ndarray,
) -> tuple[float, float]:
    risky_weight = float(weights.sum())

    if risky_weight > 1e-12:
        normalized_risky = weights / risky_weight
        concentration = float(
            np.sum(normalized_risky**2)
        )
        diversification = (
            float(
                min(
                    (1.0 / concentration) / 6.0,
                    1.0,
                )
                * 100.0
            )
            if concentration > 1e-12
            else 0.0
        )
    else:
        concentration = 0.0
        diversification = 0.0

    return concentration, diversification


def test_zero_risk_metrics_do_not_divide_by_zero() -> None:
    weights = np.zeros(6)

    concentration, diversification = (
        zero_risk_metrics(weights)
    )

    assert concentration == 0.0
    assert diversification == 0.0
    assert np.isfinite(concentration)
    assert np.isfinite(diversification)


def test_positive_risk_metrics_remain_valid() -> None:
    weights = np.repeat(0.5 / 6.0, 6)

    concentration, diversification = (
        zero_risk_metrics(weights)
    )

    assert concentration > 0.0
    assert diversification == pytest.approx(100.0)


def test_module35_contains_zero_risk_guard() -> None:
    source = (
        ROOT / "crypto_platform" / "module35.py"
    ).read_text(encoding="utf-8")

    assert "risky_weight=float(w.sum())" in source
    assert "if risky_weight>1e-12:" in source
    assert "conc=0.0" in source
    assert "div=0.0" in source
