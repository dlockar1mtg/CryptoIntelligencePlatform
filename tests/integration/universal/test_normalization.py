from __future__ import annotations

import pytest

from crypto_platform.integration.universal.normalization import (
    horizon_days_to_months,
    normalize_probability,
    normalize_recommendation,
    normalize_risk_level,
    normalize_score_100,
    percentage_points_to_decimal,
    universal_crypto_asset_id,
)


def test_universal_crypto_asset_id() -> None:
    assert (
        universal_crypto_asset_id("Bitcoin")
        == "crypto:bitcoin"
    )


def test_universal_crypto_asset_id_rejects_spaces() -> None:
    with pytest.raises(ValueError):
        universal_crypto_asset_id(
            "bitcoin asset"
        )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("BUY", "buy"),
        ("ACCUMULATE", "accumulate"),
        ("HOLD", "hold"),
        ("WAIT", "wait"),
        ("REDUCE", "reduce"),
        ("SELL", "sell"),
    ],
)
def test_normalize_recommendation(
    source: str,
    expected: str,
) -> None:
    assert (
        normalize_recommendation(source)
        == expected
    )


def test_unknown_recommendation_fails() -> None:
    with pytest.raises(ValueError):
        normalize_recommendation(
            "MAYBE"
        )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("LOW", "low"),
        ("MODERATE", "medium"),
        ("MEDIUM", "medium"),
        ("ELEVATED", "high"),
        ("HIGH", "high"),
        ("SEVERE", "extreme"),
        ("EXTREME", "extreme"),
    ],
)
def test_normalize_risk_level(
    source: str,
    expected: str,
) -> None:
    assert (
        normalize_risk_level(source)
        == expected
    )


def test_unknown_risk_level_fails() -> None:
    with pytest.raises(ValueError):
        normalize_risk_level(
            "UNKNOWN"
        )


def test_percentage_points_to_decimal() -> None:
    assert (
        percentage_points_to_decimal(
            62.5
        )
        == 0.625
    )

    assert (
        percentage_points_to_decimal(
            None
        )
        is None
    )


def test_nonfinite_percentage_becomes_none() -> None:
    assert (
        percentage_points_to_decimal(
            float("nan")
        )
        is None
    )


def test_probability_validation() -> None:
    assert normalize_probability(0.75) == 0.75

    with pytest.raises(ValueError):
        normalize_probability(1.01)

    with pytest.raises(ValueError):
        normalize_probability(-0.01)


def test_score_validation() -> None:
    assert normalize_score_100(82.5) == 82.5

    with pytest.raises(ValueError):
        normalize_score_100(100.01)

    with pytest.raises(ValueError):
        normalize_score_100(-0.01)


@pytest.mark.parametrize(
    ("days", "months"),
    [
        (7, 1),
        (30, 1),
        (90, 3),
        (180, 6),
        (365, 12),
    ],
)
def test_horizon_days_to_months(
    days: int,
    months: int,
) -> None:
    assert (
        horizon_days_to_months(days)
        == months
    )


def test_invalid_horizon_fails() -> None:
    with pytest.raises(ValueError):
        horizon_days_to_months(0)