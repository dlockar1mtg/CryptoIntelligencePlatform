from pathlib import Path
import tempfile
import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect, upsert
from crypto_platform.module2 import Module2Runner, MODULE2_SCHEMA

def main():
    settings, assets = load_all()
    with tempfile.TemporaryDirectory() as temp:
        settings["platform"]["database_path"] = str(Path(temp) / "test.duckdb")
        conn = connect(settings)
        conn.execute(MODULE2_SCHEMA)

        asset_frame = pd.DataFrame(assets)
        asset_frame["active"] = True
        asset_frame["created_at_utc"] = pd.Timestamp.now(tz="UTC")
        upsert(conn, "assets", asset_frame, ["asset_id"])

        dates = pd.date_range("2024-01-01", periods=600, freq="D")
        market_rows = []
        for i, asset in enumerate(assets):
            prices = 100 * (1 + 0.0008 + i * 0.00005) ** np.arange(len(dates))
            for date, price in zip(dates, prices):
                market_rows.append({
                    "asset_id": asset["asset_id"],
                    "observation_date": date.date(),
                    "price_usd": float(price),
                    "market_cap_usd": float(price * (2e7 + i * 1e8)),
                    "volume_24h_usd": float(price * 1e6),
                    "circulating_supply": None, "total_supply": None,
                    "max_supply": None, "fully_diluted_value_usd": None,
                    "market_cap_rank": i + 1, "ath_usd": float(prices[-1] * 1.1),
                    "ath_change_pct": -9.09, "source": "coingecko",
                    "collected_at_utc": pd.Timestamp.now(tz="UTC"),
                })
        upsert(
            conn, "asset_market_daily", pd.DataFrame(market_rows),
            ["asset_id", "observation_date", "source"]
        )

        global_rows = pd.DataFrame([{
            "observation_date": d.date(),
            "total_market_cap_usd": 2e12 * (1.0005 ** n),
            "total_volume_usd": 8e10 * (1.0003 ** n),
            "btc_dominance_pct": 50.0,
            "eth_dominance_pct": 18.0,
            "stablecoin_dominance_pct": 6.0,
            "active_asset_count": 10000, "markets_count": 800,
            "source": "coingecko",
            "collected_at_utc": pd.Timestamp.now(tz="UTC"),
        } for n, d in enumerate(dates)])
        upsert(conn, "crypto_global_daily", global_rows, ["observation_date", "source"])

        macro_specs = {
            "FRED::DFF": 4.0, "FRED::DGS10": 4.2, "FRED::DFII10": 1.8,
            "FRED::T10YIE": 2.4, "FRED::M2SL": 21000,
            "FRED::DTWEXBGS": 120, "FRED::VIXCLS": 18,
            "FRED::BAMLH0A0HYM2": 3.5, "FRED::UNRATE": 4.1,
        }
        macro_rows = []
        for key, base in macro_specs.items():
            freq = "MS" if key in {"FRED::M2SL", "FRED::UNRATE"} else "D"
            md = pd.date_range("2023-01-01", periods=36 if freq == "MS" else 1000, freq=freq)
            for n, d in enumerate(md):
                macro_rows.append({
                    "series_key": key, "observation_date": d.date(),
                    "value": float(base + n * 0.001),
                    "source": "fred_api",
                    "collected_at_utc": pd.Timestamp.now(tz="UTC"),
                })
        upsert(
            conn, "macro_observations", pd.DataFrame(macro_rows),
            ["series_key", "observation_date", "source"]
        )
        conn.close()

        # Temporarily point the real loader's config through an environment-neutral
        # runner instance by creating it then replacing its connection/settings.
        runner = Module2Runner()
        runner.conn.close()
        runner.settings = settings
        runner.assets = assets
        runner.conn = connect(settings)
        runner.conn.execute(MODULE2_SCHEMA)
        result = runner.run()
        assert result["status"] == "SUCCESS"
        assert result["assets_scored"] == 6
        check = connect(settings)
        assert check.execute("SELECT COUNT(*) FROM latest_asset_signals").fetchone()[0] == 6
        check.close()
    print("Crypto v1.2 Module 1/2 smoke test passed.")

if __name__ == "__main__":
    main()
