from pathlib import Path
import tempfile

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import (
    Module10Runner, MODULE10_SCHEMA,
)

def main():
    settings, core_assets = load_all()
    with tempfile.TemporaryDirectory() as temp:
        settings["platform"]["database_path"] = str(
            Path(temp) / "test.duckdb"
        )
        conn = connect(settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
            MODULE9_SCHEMA, MODULE10_SCHEMA,
        ]:
            conn.execute(schema)

        now = pd.Timestamp.now(tz="UTC")
        universe = pd.DataFrame([
            {
                "asset_id": f"asset-{i}",
                "symbol": f"A{i}",
                "name": f"Asset {i}",
                "market_cap_rank": i + 1,
                "market_cap_usd": 1e11 / (i + 1),
                "volume_24h_usd": 1e9 / (i + 1),
                "current_price_usd": 100 + i,
                "price_change_24h_pct": 1.0,
                "price_change_7d_pct": 3.0,
                "price_change_30d_pct": 5.0,
                "circulating_supply": 1e8,
                "total_supply": 1e8,
                "max_supply": 2e8,
                "ath_change_pct": -20.0,
                "inclusion_status": "INCLUDED",
                "inclusion_reason": "test",
                "is_core": i < 6,
                "discovered_at_utc": now,
                "updated_at_utc": now,
            }
            for i in range(50)
        ])
        conn.register("u", universe)
        conn.execute("INSERT INTO research_universe SELECT * FROM u")
        conn.unregister("u")

        dates = pd.date_range("2023-01-01", periods=400, freq="D")
        history = []
        for i in range(50):
            prices = 100 * np.exp(
                np.cumsum(np.full(len(dates), 0.0004 + i * 0.000002))
            )
            for date, price in zip(dates, prices):
                history.append({
                    "asset_id": f"asset-{i}",
                    "observation_date": date.date(),
                    "price_usd": float(price),
                    "market_cap_usd": None,
                    "volume_24h_usd": 1e7,
                    "source": "test",
                    "source_symbol": f"A{i}USDT",
                    "collected_at_utc": now,
                })
        history_frame = pd.DataFrame(history)
        conn.register("h", history_frame)
        conn.execute("INSERT INTO research_market_daily SELECT * FROM h")
        conn.unregister("h")

        calibration_rows = []
        for target in ["OUTPERFORM_BTC", "POSITIVE_RETURN"]:
            for index in range(10):
                low = index / 10
                calibration_rows.append({
                    "run_id": "test",
                    "target_name": target,
                    "probability_bin_low": low,
                    "probability_bin_high": low + 0.1,
                    "sample_count": 100,
                    "average_predicted_probability": low + 0.05,
                    "observed_rate": min(0.95, 0.10 + index * 0.075),
                    "calibration_error": 0.05,
                    "calculated_at_utc": now,
                })
        calibration = pd.DataFrame(calibration_rows)
        conn.register("c", calibration)
        conn.execute("INSERT INTO probability_calibration_bins SELECT * FROM c")
        conn.unregister("c")

        predictions = []
        for index, asset in enumerate(core_assets):
            predictions.append({
                "run_id": "module9",
                "asset_id": asset["asset_id"],
                "observation_date": dates[-1].date(),
                "cycle_phase": "RECOVERY",
                "calibrated_excess_return_pct": 20.0,
                "probability_outperform_btc": 0.55 + index * 0.05,
                "probability_positive_return": 0.60 + index * 0.04,
                "global_probability_outperform": 0.55,
                "regime_probability_outperform": 0.60,
                "global_probability_positive": 0.60,
                "regime_probability_positive": 0.65,
                "predictive_score": 60.0,
                "predictive_signal": "HOLD",
                "predictive_confidence": 70.0,
                "rules_score": 50.0 + index,
                "rules_signal": "HOLD",
                "final_ensemble_score": 55.0,
                "final_ensemble_signal": "HOLD",
                "final_ensemble_confidence": 75.0,
                "predictive_weight": 0.426,
                "promotion_status": "PROMOTED",
                "calculated_at_utc": now,
            })
        pred = pd.DataFrame(predictions)
        conn.register("p", pred)
        conn.execute("INSERT INTO predictive_classification_current SELECT * FROM p")
        conn.unregister("p")
        conn.execute(
            "INSERT INTO module9_runs VALUES "
            "('module9', ?, ?, 'SUCCESS', 180, 1000, 6, TRUE, 0.426, 'test', '3.0.0')",
            [now, now],
        )
        conn.close()

        runner = Module10Runner()
        runner.conn.close()
        runner.settings = settings
        runner.core_assets = core_assets
        runner.config = settings["module10"]
        runner.conn = connect(settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
            MODULE9_SCHEMA, MODULE10_SCHEMA,
        ]:
            runner.conn.execute(schema)
        runner.conn.execute(
            """
            INSERT INTO module10_runs(
                run_id,started_at_utc,completed_at_utc,status,
                discovered_assets,selected_assets,history_rows,
                derivative_rows,sentiment_rows,notes,platform_version
            ) VALUES (?,?,?,'RUNNING',50,50,0,0,0,'smoke test','3.0.0')
            """,
            [runner.run_id, now, now],
        )

        breadth = runner.calculate_breadth()
        calibrated = runner.calibrate_current_probabilities()
        assert breadth == 1
        assert calibrated == 6

        check = connect(settings)
        latest_breadth = check.execute(
            "SELECT universe_size FROM latest_research_breadth"
        ).fetchone()[0]
        assert latest_breadth == 50
        weight = check.execute(
            "SELECT MAX(capped_predictive_weight) "
            "FROM latest_calibrated_predictive"
        ).fetchone()[0]
        assert weight <= 0.20 + 1e-9
        assert check.execute(
            "SELECT COUNT(*) FROM latest_calibrated_predictive"
        ).fetchone()[0] == 6
        check.close()

    print("Crypto v3.0 institutional expansion smoke test passed.")

if __name__ == "__main__":
    main()
