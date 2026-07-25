from __future__ import annotations

import pandas as pd

from crypto_platform.module11 import Module11Runner


def test_collect_derivatives_records_unmapped_symbol_without_null() -> None:
    runner = Module11Runner.__new__(Module11Runner)
    runner.config = {"derivatives": {"enabled": True}}

    captured: dict[str, pd.DataFrame] = {}

    def capture_upsert(table: str, frame: pd.DataFrame) -> None:
        captured[table] = frame.copy()

    runner.upsert = capture_upsert  # type: ignore[method-assign]

    universe = pd.DataFrame(
        [
            {
                "asset_id": "crypto:test-asset",
                "symbol": "TEST",
            }
        ]
    )

    mappings = pd.DataFrame(
        columns=[
            "asset_id",
            "provider",
            "market_type",
            "provider_symbol",
        ]
    )

    result = runner.collect_derivatives(universe, mappings)

    assert result == 0

    status = captured["derivatives_collection_status"]

    assert len(status) == 1
    assert status.iloc[0]["asset_id"] == "crypto:test-asset"
    assert status.iloc[0]["provider"] == "binance"
    assert status.iloc[0]["provider_symbol"] == "UNMAPPED"
    assert bool(status.iloc[0]["supported"]) is False
    assert status.iloc[0]["status"] == "NO_MAPPING"
    assert pd.notna(status.iloc[0]["provider_symbol"])
