from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module15 import Module15Runner, MODULE15_SCHEMA

def main():
    settings, assets = load_all()
    with tempfile.TemporaryDirectory() as temp:
        settings["platform"]["database_path"] = str(
            Path(temp) / "test.duckdb"
        )
        settings["module15"]["research"]["start_date"] = "2022-01-01"
        settings["module15"]["walk_forward"]["training_months"] = 12
        settings["module15"]["walk_forward"]["testing_months"] = 6
        settings["module15"]["walk_forward"]["step_months"] = 6
        settings["module15"]["walk_forward"]["minimum_folds"] = 2

        conn = connect(settings)
        conn.execute(MODULE6_SCHEMA)
        conn.execute(MODULE15_SCHEMA)

        rng = np.random.default_rng(1234)
        dates = pd.date_range(
            "2020-01-01", periods=1700, freq="D"
        )
        rows = []
        common = rng.normal(0.00045, 0.018, len(dates))
        for index, asset_id in enumerate([
            "bitcoin", "ethereum", "solana",
            "chainlink", "xrp", "avalanche",
        ]):
            idiosyncratic = rng.normal(
                0.00005 * index,
                0.006 + 0.001 * index,
                len(dates),
            )
            prices = 100 * np.exp(
                np.cumsum(common + idiosyncratic)
            )
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

        runner = Module15Runner()
        runner.conn.close()
        runner.settings = settings
        runner.assets = assets
        runner.config = settings["module15"]
        runner.conn = connect(settings)
        runner.conn.execute(MODULE15_SCHEMA)
        result = runner.run()

        assert result["status"] == "SUCCESS"
        assert result["variants_tested"] == 5
        assert result["walk_forward_folds"] >= 2

        check = connect(settings)
        assert check.execute(
            "SELECT COUNT(*) FROM latest_calibrated_strategy_recommendation"
        ).fetchone()[0] == 1
        assert check.execute(
            "SELECT COUNT(*) FROM latest_walk_forward_selection"
        ).fetchone()[0] >= 2
        assert check.execute(
            """
            SELECT COUNT(*) FROM latest_strategy_variant_results
            WHERE evaluation_scope='FULL_SAMPLE'
            """
        ).fetchone()[0] == 5
        assert check.execute(
            "SELECT COUNT(*) FROM latest_benchmark_comparison"
        ).fetchone()[0] == 3
        check.close()

    print("Crypto v4.0 research and calibration smoke test passed.")

if __name__ == "__main__":
    main()
