from __future__ import annotations

import pandas as pd

from crypto_platform.module21 import Module21Runner


def test_make_decision_accepts_empty_probability_schema() -> None:
    runner = Module21Runner.__new__(Module21Runner)
    runner.run_id = "test-module21"
    runner.cfg = {
        "decision": {
            "stance_thresholds": {
                "strong_buy": 1.0,
                "buy": 0.4,
                "hold": -0.2,
                "reduce": -0.8,
            },
            "governed_signal_weight": 0.4,
            "regime_weight": 0.3,
            "probability_weight": 0.2,
            "risk_weight": 0.1,
            "maximum_rationales": 5,
        },
        "allocation": {
            "neutral_btc_weight": 0.5,
            "action_score_slope": 0.1,
            "weak_model_multiplier": 0.5,
            "minimum_btc_weight": 0.0,
            "maximum_btc_weight": 1.0,
        },
    }

    captured: dict[str, pd.DataFrame] = {}

    def capture_upsert(table: str, frame: pd.DataFrame) -> None:
        captured[table] = frame.copy()

    runner.upsert = capture_upsert  # type: ignore[method-assign]

    frame = pd.DataFrame(
        {
            "observation_date": [pd.Timestamp("2026-07-25")],
        }
    )

    regimes = pd.DataFrame(
        [
            {
                "dominant_regime": "NEUTRAL",
                "regime_confidence": 0.5,
                "bull_probability": 0.25,
                "recovery_probability": 0.25,
                "correction_probability": 0.25,
                "bear_probability": 0.25,
            }
        ]
    )

    risk = pd.DataFrame(
        [
            {
                "risk_score": 50.0,
                "risk_level": "MODERATE",
            }
        ]
    )

    probabilities = pd.DataFrame()

    decision, rationale, composite = runner.make_decision(
        frame=frame,
        regimes=regimes,
        probabilities=probabilities,
        risk=risk,
        features=[],
        scores={},
        directions={},
    )

    assert len(decision) == 1
    assert decision.iloc[0]["positive_return_probability_90d"] == 0.5
    assert decision.iloc[0]["drawdown_20_probability_90d"] == 0.5
    assert decision.iloc[0]["production_status"] == (
        "INSUFFICIENT_GOVERNED_FEATURES"
    )
    assert not rationale.empty
    assert len(composite) == 1
    assert "investment_decisions" in captured
