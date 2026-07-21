from __future__ import annotations

import numpy as np

# Canonical lexicographic order required by sklearn multiclass metrics.
CANONICAL_REGIME_CLASSES = np.asarray([
    "LIQUIDITY_EXPANSION",
    "MACRO_STRESS",
    "MOMENTUM_BULL",
    "RANGE_BOUND",
    "RECOVERY",
    "VOLATILITY_SHOCK",
])


def canonical_classes() -> np.ndarray:
    """Return a defensive copy of the platform-wide probability class order."""
    return CANONICAL_REGIME_CLASSES.copy()
