from __future__ import annotations

import pandas as pd

from crypto_platform.module30 import Module30Runner


class FakeConnection:
    def execute(self, query: str, parameters=None):
        normalized = " ".join(query.split())

        if "FROM m25_regime_features" in normalized:
            return FakeResult(
                pd.DataFrame(
                    {
                        "observation_date": [
                            pd.Timestamp("2026-01-01"),
                            pd.Timestamp("2026-01-02"),
                        ],
                        "trend_score": [0.1, 0.2],
                    }
                )
            )

        if "FROM m27_representation_features" in normalized:
            return FakeResult(
                pd.DataFrame(
                    {
                        "observation_date": [
                            pd.Timestamp("2026-01-01"),
                            pd.Timestamp("2026-01-02"),
                        ],
                        "volatility_term_ratio": [0.8, 0.9],
                    }
                )
            )

        if "FROM m25_regime_probabilities" in normalized:
            return FakeResult(
                pd.DataFrame(
                    {
                        "observation_date": [
                            pd.Timestamp("2026-01-01"),
                            pd.Timestamp("2026-01-02"),
                        ],
                        "dominant_regime": ["BULL", "BULL"],
                    }
                )
            )

        raise AssertionError(f"Unexpected query: {normalized}")


class FakeResult:
    def __init__(self, frame: pd.DataFrame):
        self.frame = frame

    def fetchdf(self) -> pd.DataFrame:
        return self.frame.copy()


def test_module30_data_joins_module27_representation_features() -> None:
    runner = Module30Runner.__new__(Module30Runner)
    runner.conn = FakeConnection()
    runner.source_m29 = "module29-test-run"
    runner.source_m27 = "module27-test-run"
    runner.features = [
        "trend_score",
        "volatility_term_ratio",
    ]

    frame = runner.data()

    assert "trend_score" in frame.columns
    assert "volatility_term_ratio" in frame.columns
    assert "dominant_regime" in frame.columns
    assert len(frame) == 2
    assert frame["volatility_term_ratio"].tolist() == [0.8, 0.9]
