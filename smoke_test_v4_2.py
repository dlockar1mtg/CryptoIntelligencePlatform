from pathlib import Path
import tempfile
import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module17 import Module17Runner, MODULE17_SCHEMA

def main():
    settings, assets = load_all()
    with tempfile.TemporaryDirectory() as temp:
        settings["platform"]["database_path"] = str(Path(temp) / "test.duckdb")
        settings["module17"]["feature_collection"]["fear_greed_enabled"] = False
        settings["module17"]["manual_inputs"]["etf_flows_csv"] = str(
            Path(temp) / "missing.csv"
        )
        c = connect(settings)
        c.execute(MODULE6_SCHEMA)
        c.execute(MODULE17_SCHEMA)
        dates = pd.date_range("2023-01-01", periods=500, freq="D")
        rng = np.random.default_rng(42)
        rows = []
        for i, asset in enumerate([
            "bitcoin","ethereum","solana","chainlink","xrp","avalanche"
        ]):
            prices = 100 * np.exp(np.cumsum(rng.normal(.0004, .02, len(dates))))
            for d, p in zip(dates, prices):
                rows.append({
                    "asset_id": asset,
                    "observation_date": d.date(),
                    "price_usd": float(p),
                    "market_cap_usd": float(p * (1e8 / (i + 1))),
                    "volume_24h_usd": 1e8,
                    "price_source": "test",
                    "market_cap_source": "test",
                    "volume_source": "test",
                    "source_priority": 1,
                    "collected_at_utc": pd.Timestamp.now(tz="UTC"),
                })
        frame = pd.DataFrame(rows)
        c.register("stage", frame)
        c.execute("INSERT INTO canonical_market_daily SELECT * FROM stage")
        c.unregister("stage")
        c.close()

        runner = Module17Runner()
        runner.conn.close()
        runner.settings = settings
        runner.cfg = settings["module17"]
        runner.conn = connect(settings)
        runner.conn.execute(MODULE17_SCHEMA)
        result = runner.run()
        assert result["status"] == "SUCCESS"
        assert result["feature_rows"] == 500
        assert result["validation_rows"] > 0
        check = connect(settings)
        assert check.execute(
            "SELECT COUNT(*) FROM crypto_features_daily"
        ).fetchone()[0] == 500
        assert check.execute(
            "SELECT COUNT(*) FROM latest_feature_readiness"
        ).fetchone()[0] > 0
        check.close()
    print("Crypto v4.2 feature expansion smoke test passed.")

if __name__ == "__main__":
    main()
