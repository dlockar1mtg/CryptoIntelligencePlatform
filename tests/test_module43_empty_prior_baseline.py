from __future__ import annotations

import pandas as pd

from crypto_platform.module43 import Module43Runner


def test_changes_accepts_columnless_empty_prior_frame() -> None:
    runner = Module43Runner.__new__(Module43Runner)
    runner.run_id = "test-module43-run"

    current = pd.DataFrame(
        [
            {
                "asset_id": "bitcoin",
                "recommendation_date": pd.Timestamp(
                    "2026-07-26"
                ),
                "best_action": "HOLD",
                "investment_score": 47.0,
                "best_current_portfolio_pct": 4.0,
                "forecast_confidence": 0.60,
                "reliability_score": 22.0,
            }
        ]
    )

    changes = runner.changes(
        current=current,
        current_projection=pd.DataFrame(),
        prior=pd.DataFrame(),
        prior_projection=pd.DataFrame(),
    )

    assert len(changes) == 1
    assert changes.iloc[0]["asset_id"] == "bitcoin"
    assert (
        changes.iloc[0]["prior_action"]
        == "NO_BASELINE"
    )
    assert (
        changes.iloc[0]["change_classification"]
        == "BASELINE_CREATED"
    )
    assert bool(changes.iloc[0]["action_changed"]) is False


def test_changes_accepts_empty_prior_with_expected_columns() -> None:
    runner = Module43Runner.__new__(Module43Runner)
    runner.run_id = "test-module43-run"

    current = pd.DataFrame(
        [
            {
                "asset_id": "ethereum",
                "recommendation_date": pd.Timestamp(
                    "2026-07-26"
                ),
                "best_action": "WAIT",
                "investment_score": 42.0,
                "best_current_portfolio_pct": 0.0,
                "forecast_confidence": 0.50,
                "reliability_score": 20.0,
            }
        ]
    )

    prior = pd.DataFrame(
        columns=[
            "asset_id",
            "recommendation_date",
        ]
    )

    changes = runner.changes(
        current=current,
        current_projection=pd.DataFrame(),
        prior=prior,
        prior_projection=pd.DataFrame(),
    )

    assert len(changes) == 1
    assert (
        changes.iloc[0]["change_classification"]
        == "BASELINE_CREATED"
    )
