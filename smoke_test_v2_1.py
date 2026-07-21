from pathlib import Path
import tempfile
import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA, FEATURES
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import Module9Runner, MODULE9_SCHEMA

def main():
    settings, assets = load_all()
    with tempfile.TemporaryDirectory() as temp:
        settings["platform"]["database_path"] = str(
            Path(temp) / "test.duckdb"
        )
        settings["module9"]["calibrated_prediction"][
            "minimum_training_rows"
        ] = 300
        settings["module9"]["walk_forward"][
            "minimum_training_rows"
        ] = 180
        settings["module9"]["walk_forward"][
            "minimum_test_rows"
        ] = 30
        settings["module9"]["regimes"][
            "minimum_training_rows"
        ] = 80
        settings["module9"]["walk_forward"]["training_days"] = 300
        settings["module9"]["walk_forward"]["test_days"] = 50
        settings["module9"]["walk_forward"]["step_days"] = 50
        settings["module9"]["classification"]["max_iter"] = 35
        settings["module9"]["classification"]["min_samples_leaf"] = 20

        conn = connect(settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
            MODULE9_SCHEMA,
        ]:
            conn.execute(schema)

        rng = np.random.default_rng(321)
        dates = pd.date_range("2023-01-01", periods=620, freq="D")
        snapshots, performance = [], []
        phases = ["ACCUMULATION", "RECOVERY", "EXPANSION", "CONTRACTION"]

        for ai, asset in enumerate(assets):
            latent = rng.normal(0, 1, len(dates))
            for i, date in enumerate(dates):
                values = {
                    "return_30d_pct": latent[i] * 10,
                    "return_90d_pct": latent[i] * 16 + rng.normal(0, 5),
                    "return_365d_pct": latent[i] * 25 + rng.normal(0, 10),
                    "price_vs_sma50_pct": latent[i] * 8,
                    "price_vs_sma200_pct": latent[i] * 14,
                    "rsi_14": np.clip(50 + latent[i] * 10, 10, 90),
                    "volatility_30d_pct": np.clip(70-latent[i]*6, 25, 150),
                    "max_drawdown_365d_pct": -np.clip(45-latent[i]*12, 0, 90),
                    "momentum_score": np.clip(50+latent[i]*16, 0, 100),
                    "trend_score": np.clip(50+latent[i]*13, 0, 100),
                    "risk_score": np.clip(60+latent[i]*8, 0, 100),
                    "historical_overall_score": np.clip(48+latent[i]*10, 0, 100),
                    "expected_return_proxy_pct": -latent[i]*8,
                }
                phase = phases[(i // 130 + ai) % len(phases)]
                snapshots.append({
                    "asset_id": asset["asset_id"],
                    "observation_date": date.date(),
                    "price_usd": 100.0,
                    **values,
                    "sma_50": 100.0, "sma_200": 95.0,
                    "historical_signal": "HOLD",
                    "cycle_phase": phase,
                    "valuation_label": "FAIR_RANGE",
                    "calculation_version": "test",
                    "calculated_at_utc": pd.Timestamp.now(tz="UTC"),
                })
                excess = (
                    -values["momentum_score"] * 0.30
                    + values["risk_score"] * 0.35
                    - values["max_drawdown_365d_pct"] * 0.25
                    + (10 if phase == "ACCUMULATION" else 0)
                    + rng.normal(0, 10)
                )
                performance.append({
                    "asset_id": asset["asset_id"],
                    "signal_date": date.date(),
                    "historical_signal": "HOLD",
                    "historical_score": values["historical_overall_score"],
                    "horizon_days": 180,
                    "target_date": (date+pd.Timedelta(days=180)).date(),
                    "actual_target_date": (date+pd.Timedelta(days=180)).date(),
                    "signal_price_usd": 100.0,
                    "future_price_usd": 100.0*(1+(excess+5)/100),
                    "forward_return_pct": excess+5,
                    "benchmark_btc_return_pct": 5.0,
                    "excess_vs_btc_pct": excess,
                    "positive_return": bool(excess+5 > 0),
                    "outperformed_btc": bool(excess > 0),
                    "completed": True,
                    "calculated_at_utc": pd.Timestamp.now(tz="UTC"),
                })

        s = pd.DataFrame(snapshots)
        p = pd.DataFrame(performance)
        conn.register("s", s)
        conn.execute("""
            INSERT INTO model_snapshots_daily(
                asset_id,observation_date,price_usd,return_30d_pct,
                return_90d_pct,return_365d_pct,sma_50,sma_200,
                price_vs_sma50_pct,price_vs_sma200_pct,rsi_14,
                volatility_30d_pct,max_drawdown_365d_pct,momentum_score,
                trend_score,risk_score,historical_overall_score,
                historical_signal,cycle_phase,valuation_label,
                expected_return_proxy_pct,calculation_version,
                calculated_at_utc
            ) SELECT
                asset_id,observation_date,price_usd,return_30d_pct,
                return_90d_pct,return_365d_pct,sma_50,sma_200,
                price_vs_sma50_pct,price_vs_sma200_pct,rsi_14,
                volatility_30d_pct,max_drawdown_365d_pct,momentum_score,
                trend_score,risk_score,historical_overall_score,
                historical_signal,cycle_phase,valuation_label,
                expected_return_proxy_pct,calculation_version,
                calculated_at_utc FROM s
        """)
        conn.unregister("s")
        conn.register("p", p)
        conn.execute("INSERT INTO signal_forward_performance SELECT * FROM p")
        conn.unregister("p")

        latest = s.sort_values("observation_date").groupby("asset_id").tail(1)
        signals = []
        for _, row in latest.iterrows():
            signals.append({
                "asset_id": row["asset_id"],
                "observation_date": row["observation_date"],
                "price_usd": 100.0, "market_cap_usd": 1e10,
                "volume_24h_usd": 1e9, "return_7d_pct": 1.0,
                "return_30d_pct": row["return_30d_pct"],
                "return_90d_pct": row["return_90d_pct"],
                "return_365d_pct": row["return_365d_pct"],
                "sma_20": 100.0, "sma_50": 100.0, "sma_200": 95.0,
                "price_vs_sma50_pct": row["price_vs_sma50_pct"],
                "price_vs_sma200_pct": row["price_vs_sma200_pct"],
                "rsi_14": row["rsi_14"],
                "volatility_30d_annualized_pct": row["volatility_30d_pct"],
                "max_drawdown_365d_pct": row["max_drawdown_365d_pct"],
                "ath_drawdown_pct": -30.0, "turnover_pct": 2.0,
                "volume_30d_change_pct": 5.0,
                "momentum_score": row["momentum_score"],
                "trend_score": row["trend_score"],
                "liquidity_score": 70.0, "macro_score": 60.0,
                "risk_score": row["risk_score"],
                "relative_value_score": 60.0,
                "overall_score": row["historical_overall_score"],
                "confidence": 80.0, "signal": "HOLD",
                "risk_level": "HIGH", "calculation_version": "test",
                "calculated_at_utc": pd.Timestamp.now(tz="UTC"),
            })
        sf = pd.DataFrame(signals)
        conn.register("sf", sf)
        conn.execute("INSERT INTO asset_signals_daily SELECT * FROM sf")
        conn.unregister("sf")
        conn.close()

        runner = Module9Runner()
        runner.conn.close()
        runner.settings = settings
        runner.assets = assets
        runner.config = settings["module9"]
        runner.conn = connect(settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
            MODULE9_SCHEMA,
        ]:
            runner.conn.execute(schema)
        result = runner.run()
        assert result["status"] == "SUCCESS"
        assert result["validation_folds"] >= 3
        assert result["prediction_count"] == 6

        check = connect(settings)
        assert check.execute(
            "SELECT COUNT(*) FROM latest_predictive_classifications"
        ).fetchone()[0] == 6
        assert check.execute(
            "SELECT COUNT(*) FROM latest_calibrated_walk_forward"
        ).fetchone()[0] >= 3
        assert check.execute(
            "SELECT COUNT(*) FROM latest_probability_calibration"
        ).fetchone()[0] > 0
        check.close()

    print("Crypto v2.1 calibrated predictive smoke test passed.")

if __name__ == "__main__":
    main()
