from __future__ import annotations
from dataclasses import dataclass
from typing import Any

WEIGHT_KEYS = [
    "trend_weight", "momentum_weight", "value_weight",
    "risk_adjusted_weight", "relative_strength_weight",
    "liquidity_weight", "derivatives_weight",
]

@dataclass(frozen=True)
class ParameterSpace:
    ranges: dict[str, list[float]]

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> "ParameterSpace":
        return cls(ranges=settings["module16"]["parameter_space"])

    def sample(self, rng) -> dict[str, float]:
        raw = {}
        for key, bounds in self.ranges.items():
            low, high = float(bounds[0]), float(bounds[1])
            raw[key] = float(rng.uniform(low, high))
        total = sum(raw[key] for key in WEIGHT_KEYS)
        for key in WEIGHT_KEYS:
            raw[key] = raw[key] / total
        return raw

    @staticmethod
    def validate(parameters: dict[str, float]) -> None:
        total = sum(float(parameters[key]) for key in WEIGHT_KEYS)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Scoring weights must sum to 1.0; found {total}")
        if not 0 <= parameters["maximum_cash_weight"] <= 0.75:
            raise ValueError("maximum_cash_weight is outside the allowed range")
