from pathlib import Path
import tempfile
import pandas as pd
from crypto_platform.platform import (
    load_all, connect, upsert, TABLE_KEYS, ProviderHealth
)

def main():
    settings, assets = load_all()
    with tempfile.TemporaryDirectory() as directory:
        settings["platform"]["database_path"] = str(Path(directory) / "smoke.duckdb")
        conn = connect(settings)
        asset_frame = pd.DataFrame(assets)
        asset_frame["active"] = True
        asset_frame["created_at_utc"] = pd.Timestamp.now(tz="UTC")
        inserted, updated = upsert(conn, "assets", asset_frame, ["asset_id"])
        assert inserted == 6
        sample = pd.DataFrame([{
            "asset_id": "bitcoin", "exchange": "coinbase",
            "symbol": "BTC-USD", "interval": "1d",
            "open_time_utc": pd.Timestamp("2026-01-01", tz="UTC"),
            "close_time_utc": pd.Timestamp("2026-01-01 23:59:59", tz="UTC"),
            "open": 100000.0, "high": 101000.0, "low": 99000.0,
            "close": 100500.0, "base_volume": 1000.0,
            "quote_volume": 100500000.0, "trade_count": None,
            "taker_buy_base_volume": None, "taker_buy_quote_volume": None,
            "collected_at_utc": pd.Timestamp.now(tz="UTC"),
        }])
        inserted, updated = upsert(
            conn, "asset_ohlcv", sample, TABLE_KEYS["asset_ohlcv"]
        )
        assert (inserted, updated) == (1, 0)
        inserted, updated = upsert(
            conn, "asset_ohlcv", sample, TABLE_KEYS["asset_ohlcv"]
        )
        assert (inserted, updated) == (0, 1)
        conn.close()
    print("Crypto v1.1 smoke test passed.")

if __name__ == "__main__":
    main()
