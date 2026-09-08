"""Deterministic normalization for universal crypto contracts."""

from __future__ import annotations

import math
import re
from typing import Any


_ASSET_ID_PATTERN = re.compile(
    r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$"
)

_ASSET_SUBCLASS_MAP = {
    "core": "large_cap_crypto",
    "satellite": "satellite_crypto",
}

_LIQUIDITY_TIER_MAP = {
    "core": "high",
    "satellite": "medium",
}

_RECOMMENDATION_MAP = {
    "STRONG_BUY": "buy",
    "BUY": "buy",
    "SCALE_IN": "accumulate",
    "ACCUMULATE": "accumulate",
    "HOLD": "hold",
    "WAIT": "watch",
    "REDUCE": "reduce",
    "SELL": "sell",
    "AVOID": "sell",
}

_RISK_LEVEL_MAP = {
    "LOW": "low",
    "MODERATE": "medium",
    "MEDIUM": "medium",
    "ELEVATED": "high",
    "HIGH": "high",
    "SEVERE": "extreme",
    "EXTREME": "extreme",
}

_RISK_SCORE_MAP = {
    "LOW": 25.0,
    "MODERATE": 50.0,
    "MEDIUM": 50.0,
    "ELEVATED": 75.0,
    "HIGH": 75.0,
    "SEVERE": 95.0,
    "EXTREME": 95.0,
}


def normalize_platform_asset_id(
    value: str,
) -> str:
    normalized = value.strip().lower()

    if not normalized:
        raise ValueError(
            "Platform asset ID must not be empty."
        )

    if not _ASSET_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Platform asset ID contains unsupported "
            f"characters: {value!r}"
        )

    return normalized


def universal_crypto_asset_id(
    platform_asset_id: str,
) -> str:
    return (
        "crypto:"
        + normalize_platform_asset_id(
            platform_asset_id
        )
    )


def normalize_asset_subclass(
    asset_tier: str | None,
) -> str:
    if asset_tier is None:
        return "crypto_asset"

    normalized = asset_tier.strip().lower()

    return _ASSET_SUBCLASS_MAP.get(
        normalized,
        "crypto_asset",
    )


def normalize_liquidity_tier(
    asset_tier: str | None,
) -> str:
    if asset_tier is None:
        return "medium"

    normalized = asset_tier.strip().lower()

    return _LIQUIDITY_TIER_MAP.get(
        normalized,
        "medium",
    )


def normalize_recommendation(
    value: str,
) -> str:
    normalized = value.strip().upper()

    try:
        return _RECOMMENDATION_MAP[
            normalized
        ]

    except KeyError as exc:
        raise ValueError(
            "Unsupported recommendation label: "
            f"{value!r}"
        ) from exc


def normalize_risk_level(
    value: str,
) -> str:
    normalized = value.strip().upper()

    try:
        return _RISK_LEVEL_MAP[
            normalized
        ]

    except KeyError as exc:
        raise ValueError(
            f"Unsupported risk level: {value!r}"
        ) from exc


def risk_status_to_score(
    value: str,
) -> float:
    normalized = value.strip().upper()

    try:
        return _RISK_SCORE_MAP[normalized]

    except KeyError as exc:
        raise ValueError(
            "Unsupported risk status for score: "
            f"{value!r}"
        ) from exc


def percentage_points_to_decimal(
    value: Any,
) -> float | None:
    if value is None:
        return None

    number = float(value)

    if not math.isfinite(number):
        return None

    return number / 100.0


def normalize_score_100(
    value: Any,
) -> float:
    number = float(value)

    if not math.isfinite(number):
        raise ValueError(
            "Score must be finite."
        )

    if number < 0.0 or number > 100.0:
        raise ValueError(
            "Score must be between 0 and 100."
        )

    return number


def normalize_probability(
    value: Any,
) -> float:
    number = float(value)

    if not math.isfinite(number):
        raise ValueError(
            "Probability must be finite."
        )

    if number < 0.0 or number > 1.0:
        raise ValueError(
            "Probability must be between 0 and 1."
        )

    return number


def horizon_days_to_months(
    horizon_days: int,
) -> int:
    if horizon_days <= 0:
        raise ValueError(
            "Forecast horizon must be positive."
        )

    fixed_mapping = {
        7: 1,
        30: 1,
        90: 3,
        180: 6,
    }

    if horizon_days in fixed_mapping:
        return fixed_mapping[horizon_days]

    return max(
        1,
        round(horizon_days / 30.4375),
    )
