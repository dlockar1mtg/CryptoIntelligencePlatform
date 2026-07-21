from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module14 import Module14Runner, MODULE14_SCHEMA

def main():
    settings, assets = load_all()
    with tempfile.TemporaryDirectory() as temp:
        settings["platform"]["database_path"] = str(
            Path(temp) / "test.duckdb"
        )
        settings["module14"]["backtest"]["start_date"] = "2023-01-01"
        settings["module14"]["validation"][
            "minimum_rebalance_periods"
        ] = 6

        conn = connect(settings)
        conn.execute(MODULE6_SCHEMA)
        conn.execute(MODULE14_SCHEMA)

        rng = np.random.default_rng(100)
        dates = pd.date_range(
            "2022-01-01", periods=1000, freq="D"
        )
        rows = []
        for index, asset_id in enumerate([
            "bitcoin","ethereum","solana",
            "chainlink","xrp","avalanche"
        ]):
            drift = 0.0004 + index * 0.00003
            volatility = 0.018 + index * 0.001
            returns = rng.normal(drift, volatility, len(dates))
            prices = 100 * np.exp(np.cumsum(returns))
            for date, price in zip(dates, prices):
                rows.append({
                    "asset_id": asset_id,
                    "observation_date": date.date(),
                    "price_usd": float(price),
                    "market_cap_usd": 1e10,
                    "volume_24h_usd": 1e8,
                    "price_source": "test",
                    "market_cap_source": "test",
                    "volume_source": "test",
                    "source_rows": 1,
                    "collected_at_utc": pd.Timestamp.now(tz="UTC"),
                })
        frame = pd.DataFrame(rows)
        conn.register("stage", frame)
        conn.execute(
            "INSERT INTO canonical_market_daily SELECT * FROM stage"
        )
        conn.unregister("stage")
        conn.close()

        runner = Module14Runner()
        runner.conn.close()
        runner.settings = settings
        runner.assets = assets
        runner.config = settings["module14"]
        runner.conn = connect(settings)
        runner.conn.execute(MODULE14_SCHEMA)
        result = runner.run()

        assert result["status"] == "SUCCESS"
        assert result["rebalance_periods"] >= 6
        assert result["validation_rows"] > 0

        check = connect(settings)
        assert check.execute(
            "SELECT COUNT(*) FROM latest_portfolio_backtest_summary"
        ).fetchone()[0] == 1
        assert check.execute(
            "SELECT COUNT(*) FROM latest_score_validation_summary"
        ).fetchone()[0] == 3
        assert check.execute(
            "SELECT COUNT(*) FROM latest_portfolio_backtest_periods"
        ).fetchone()[0] > 0
        check.close()

    print("Crypto v3.3.4 validation smoke test passed.")

if __name__ == "__main__":
    main()
