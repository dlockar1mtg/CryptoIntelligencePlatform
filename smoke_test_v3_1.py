from pathlib import Path
import tempfile
import pandas as pd
import numpy as np

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import Module11Runner, MODULE11_SCHEMA

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
            MODULE9_SCHEMA, MODULE10_SCHEMA, MODULE11_SCHEMA,
        ]:
            conn.execute(schema)

        now = pd.Timestamp.now(tz="UTC")
        universe = pd.DataFrame([
            {
                "asset_id": asset["asset_id"],
                "symbol": asset["symbol"],
                "name": asset.get("name", asset["asset_id"].replace("-", " ").title()),
                "market_cap_rank": i + 1,
                "market_cap_usd": 1e11 / (i + 1),
                "volume_24h_usd": 1e9,
                "current_price_usd": 100.0,
                "price_change_24h_pct": 1.0,
                "price_change_7d_pct": i - 2.0,
                "price_change_30d_pct": i * 3.0 - 5.0,
                "circulating_supply": 1e8,
                "total_supply": 1e8,
                "max_supply": 2e8,
                "ath_change_pct": -20.0,
                "inclusion_status": "INCLUDED",
                "inclusion_reason": "test",
                "is_core": True,
                "discovered_at_utc": now,
                "updated_at_utc": now,
            }
            for i, asset in enumerate(core_assets)
        ])
        conn.register("u", universe)
        conn.execute("INSERT INTO research_universe SELECT * FROM u")
        conn.unregister("u")

        dates = pd.date_range("2024-01-01", periods=400, freq="D")
        history = []
        for asset in core_assets:
            for i, date in enumerate(dates):
                history.append({
                    "asset_id": asset["asset_id"],
                    "observation_date": date.date(),
                    "price_usd": 100 + i * 0.05,
                    "market_cap_usd": None,
                    "volume_24h_usd": 1e7,
                    "source": "coinbase",
                    "source_symbol": asset["coinbase_product"],
                    "collected_at_utc": now,
                })
        hf = pd.DataFrame(history)
        conn.register("h", hf)
        conn.execute("INSERT INTO research_market_daily SELECT * FROM h")
        conn.unregister("h")

        calibration_rows = []
        for target in ["OUTPERFORM_BTC", "POSITIVE_RETURN"]:
            for index in range(10):
                calibration_rows.append({
                    "run_id": "calibration",
                    "target_name": target,
                    "probability_bin_low": index / 10,
                    "probability_bin_high": (index + 1) / 10,
                    "sample_count": 100,
                    "average_predicted_probability": index / 10 + 0.05,
                    "observed_rate": 0.15 + index * 0.07,
                    "calibration_error": 0.05,
                    "calculated_at_utc": now,
                })
        cf = pd.DataFrame(calibration_rows)
        conn.register("c", cf)
        conn.execute("INSERT INTO probability_calibration_bins SELECT * FROM c")
        conn.unregister("c")

        predictions = []
        for i, asset in enumerate(core_assets):
            predictions.append({
                "run_id": "m9",
                "asset_id": asset["asset_id"],
                "observation_date": dates[-1].date(),
                "cycle_phase": "RECOVERY",
                "calibrated_excess_return_pct": 10 + i,
                "probability_outperform_btc": 0.55 + i * 0.04,
                "probability_positive_return": 0.60 + i * 0.03,
                "global_probability_outperform": 0.55,
                "regime_probability_outperform": 0.60,
                "global_probability_positive": 0.60,
                "regime_probability_positive": 0.65,
                "predictive_score": 60.0,
                "predictive_signal": "HOLD",
                "predictive_confidence": 70.0,
                "rules_score": 50.0 + i,
                "rules_signal": "HOLD",
                "final_ensemble_score": 55.0,
                "final_ensemble_signal": "HOLD",
                "final_ensemble_confidence": 75.0,
                "predictive_weight": 0.189,
                "promotion_status": "PROMOTED",
                "calculated_at_utc": now,
            })
        pf = pd.DataFrame(predictions)
        conn.register("p", pf)
        conn.execute(
            "INSERT INTO predictive_classification_current SELECT * FROM p"
        )
        conn.unregister("p")
        conn.execute(
            "INSERT INTO module9_runs VALUES "
            "('m9', ?, ?, 'SUCCESS', 180, 1000, 6, TRUE, 0.189, 'test', '3.1.0')",
            [now, now],
        )
        conn.close()

        runner = Module11Runner()
        runner.conn.close()
        runner.settings = settings
        runner.core_assets = core_assets
        runner.config = settings["module11"]
        runner.conn = connect(settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
            MODULE9_SCHEMA, MODULE10_SCHEMA, MODULE11_SCHEMA,
        ]:
            runner.conn.execute(schema)
        runner.conn.execute(
            """
            INSERT INTO module11_runs(
                run_id,started_at_utc,status,mapped_assets,
                history_rows,derivatives_rows,taxonomy_rows,
                calibrated_predictions,notes,platform_version
            ) VALUES (?,?,'RUNNING',0,0,0,0,0,'test','3.1.0')
            """,
            [runner.run_id, now],
        )

        quality = runner.calculate_quality(universe)
        taxonomy = runner.classify_taxonomy(universe)
        sectors = runner.sector_snapshot(universe, taxonomy)
        calibrated = runner.robust_calibration()

        assert quality == 6
        assert len(taxonomy) == 6
        assert sectors > 0
        assert calibrated == 6

        check = connect(settings)
        assert check.execute(
            "SELECT COUNT(*) FROM latest_history_quality"
        ).fetchone()[0] == 6
        assert check.execute(
            "SELECT COUNT(*) FROM latest_sector_snapshot"
        ).fetchone()[0] > 0
        assert check.execute(
            "SELECT COUNT(*) FROM latest_robust_calibrated_predictive"
        ).fetchone()[0] == 6
        max_weight = check.execute(
            "SELECT MAX(predictive_weight_capped) "
            "FROM latest_robust_calibrated_predictive"
        ).fetchone()[0]
        assert max_weight <= 0.20 + 1e-9
        check.close()

    print("Crypto v3.1 reliability smoke test passed.")

if __name__ == "__main__":
    main()
