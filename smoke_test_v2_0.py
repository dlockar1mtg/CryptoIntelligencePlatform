from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import Module8Runner, MODULE8_SCHEMA, FEATURES

def main():
    settings, assets = load_all()
    with tempfile.TemporaryDirectory() as temp:
        settings["platform"]["database_path"] = str(
            Path(temp) / "test.duckdb"
        )
        settings["module8"]["predictive_engine"][
            "minimum_training_rows"
        ] = 100
        settings["module8"]["validation"][
            "minimum_training_rows"
        ] = 200
        settings["module8"]["validation"][
            "minimum_test_rows"
        ] = 20
        settings["module8"]["regimes"][
            "minimum_rows_per_regime"
        ] = 10
        settings["module8"]["predictive_engine"]["max_iter"] = 20
        settings["module8"]["validation"]["training_days"] = 180
        settings["module8"]["validation"]["test_days"] = 30
        settings["module8"]["validation"]["step_days"] = 90
        settings["module8"]["explainability"][
            "shap_permutations"
        ] = 2
        settings["module8"]["explainability"][
            "global_permutation_repeats"
        ] = 1

        conn = connect(settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
        ]:
            conn.execute(schema)

        rng = np.random.default_rng(123)
        dates = pd.date_range(
            "2021-01-01", periods=500, freq="D"
        )
        phases = [
            "ACCUMULATION",
            "RECOVERY",
            "EXPANSION",
            "DISTRIBUTION",
            "CONTRACTION",
        ]
        snapshot_rows = []
        performance_rows = []

        for asset_index, asset in enumerate(assets):
            latent = rng.normal(0, 1, len(dates))
            for index, date in enumerate(dates):
                return_30 = latent[index] * 10
                return_90 = (
                    latent[index] * 16
                    + rng.normal(0, 8)
                )
                return_365 = (
                    latent[index] * 24
                    + rng.normal(0, 15)
                )
                vs50 = latent[index] * 9
                vs200 = latent[index] * 14
                rsi = np.clip(
                    50 + latent[index] * 11,
                    10,
                    90,
                )
                volatility = np.clip(
                    70 - latent[index] * 7
                    + rng.normal(0, 5),
                    25,
                    150,
                )
                drawdown = -np.clip(
                    40 - latent[index] * 12
                    + rng.normal(0, 8),
                    0,
                    90,
                )
                momentum = np.clip(
                    50 + latent[index] * 18,
                    0,
                    100,
                )
                trend = np.clip(
                    50 + latent[index] * 15,
                    0,
                    100,
                )
                risk = np.clip(
                    60 + latent[index] * 9,
                    0,
                    100,
                )
                overall = np.clip(
                    momentum * 0.30
                    + trend * 0.25
                    + risk * 0.20
                    + (100 + drawdown) * 0.25,
                    0,
                    100,
                )
                expected_proxy = (
                    -momentum * 0.25
                    + risk * 0.35
                    - drawdown * 0.30
                    + rng.normal(0, 4)
                )
                phase = phases[
                    (index // 120 + asset_index) % len(phases)
                ]
                snapshot_rows.append({
                    "asset_id": asset["asset_id"],
                    "observation_date": date.date(),
                    "price_usd": 100 + index * 0.05,
                    "return_30d_pct": return_30,
                    "return_90d_pct": return_90,
                    "return_365d_pct": return_365,
                    "sma_50": 100.0,
                    "sma_200": 95.0,
                    "price_vs_sma50_pct": vs50,
                    "price_vs_sma200_pct": vs200,
                    "rsi_14": rsi,
                    "volatility_30d_pct": volatility,
                    "max_drawdown_365d_pct": drawdown,
                    "momentum_score": momentum,
                    "trend_score": trend,
                    "risk_score": risk,
                    "historical_overall_score": overall,
                    "historical_signal": "HOLD",
                    "cycle_phase": phase,
                    "valuation_label": "FAIR_RANGE",
                    "expected_return_proxy_pct": expected_proxy,
                    "calculation_version": "test",
                    "calculated_at_utc": pd.Timestamp.now(tz="UTC"),
                })
                target = (
                    risk * 0.30
                    - momentum * 0.35
                    + trend * 0.18
                    - drawdown * 0.20
                    + (8 if phase == "ACCUMULATION" else 0)
                    + rng.normal(0, 12)
                )
                performance_rows.append({
                    "asset_id": asset["asset_id"],
                    "signal_date": date.date(),
                    "historical_signal": "HOLD",
                    "historical_score": overall,
                    "horizon_days": 180,
                    "target_date": (
                        date + pd.Timedelta(days=180)
                    ).date(),
                    "actual_target_date": (
                        date + pd.Timedelta(days=180)
                    ).date(),
                    "signal_price_usd": 100.0,
                    "future_price_usd": 100.0 * (
                        1 + target / 100
                    ),
                    "forward_return_pct": target + 5,
                    "benchmark_btc_return_pct": 5.0,
                    "excess_vs_btc_pct": target,
                    "positive_return": bool(target + 5 > 0),
                    "outperformed_btc": bool(target > 0),
                    "completed": True,
                    "calculated_at_utc": pd.Timestamp.now(tz="UTC"),
                })

        snapshots = pd.DataFrame(snapshot_rows)
        performance = pd.DataFrame(performance_rows)
        conn.register("snapshots_stage", snapshots)
        conn.execute(
            "INSERT INTO model_snapshots_daily "
            "SELECT * FROM snapshots_stage"
        )
        conn.unregister("snapshots_stage")
        conn.register("performance_stage", performance)
        conn.execute(
            "INSERT INTO signal_forward_performance "
            "SELECT * FROM performance_stage"
        )
        conn.unregister("performance_stage")

        latest = (
            snapshots.sort_values("observation_date")
            .groupby("asset_id")
            .tail(1)
        )
        signals = pd.DataFrame([{
            "asset_id": row["asset_id"],
            "observation_date": row["observation_date"],
            "price_usd": row["price_usd"],
            "market_cap_usd": 1e10,
            "volume_24h_usd": 1e9,
            "return_7d_pct": 1.0,
            "return_30d_pct": row["return_30d_pct"],
            "return_90d_pct": row["return_90d_pct"],
            "return_365d_pct": row["return_365d_pct"],
            "sma_20": 100.0,
            "sma_50": row["sma_50"],
            "sma_200": row["sma_200"],
            "price_vs_sma50_pct": row[
                "price_vs_sma50_pct"
            ],
            "price_vs_sma200_pct": row[
                "price_vs_sma200_pct"
            ],
            "rsi_14": row["rsi_14"],
            "volatility_30d_annualized_pct": row[
                "volatility_30d_pct"
            ],
            "max_drawdown_365d_pct": row[
                "max_drawdown_365d_pct"
            ],
            "ath_drawdown_pct": -30.0,
            "turnover_pct": 2.0,
            "volume_30d_change_pct": 5.0,
            "momentum_score": row["momentum_score"],
            "trend_score": row["trend_score"],
            "liquidity_score": 70.0,
            "macro_score": 60.0,
            "risk_score": row["risk_score"],
            "relative_value_score": 60.0,
            "overall_score": row[
                "historical_overall_score"
            ],
            "confidence": 80.0,
            "signal": "HOLD",
            "risk_level": "HIGH",
            "calculation_version": "test",
            "calculated_at_utc": pd.Timestamp.now(tz="UTC"),
        } for _, row in latest.iterrows()])
        conn.register("signals_stage", signals)
        conn.execute(
            "INSERT INTO asset_signals_daily "
            "SELECT * FROM signals_stage"
        )
        conn.unregister("signals_stage")
        conn.close()

        runner = Module8Runner()
        runner.conn.close()
        runner.settings = settings
        runner.assets = assets
        runner.config = settings["module8"]
        runner.conn = connect(settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
        ]:
            runner.conn.execute(schema)
        runner.model_directory = Path(temp) / "models"
        runner.model_directory.mkdir(parents=True)
        result = runner.run()

        assert result["status"] == "SUCCESS"
        assert result["training_rows"] >= 200
        assert result["validation_folds"] >= 2
        assert result["prediction_count"] == 6
        assert result["explanation_count"] == 36

        check = connect(settings)
        assert check.execute(
            "SELECT COUNT(*) FROM latest_ml_predictions"
        ).fetchone()[0] == 6
        assert check.execute(
            "SELECT COUNT(*) FROM latest_ml_feature_importance"
        ).fetchone()[0] == len(FEATURES)
        assert check.execute(
            "SELECT COUNT(*) FROM latest_ml_shap_explanations"
        ).fetchone()[0] == 36
        assert check.execute(
            "SELECT COUNT(*) FROM latest_ml_walk_forward_results"
        ).fetchone()[0] >= 2
        check.close()

    print("Crypto v2.0 predictive intelligence smoke test passed.")

if __name__ == "__main__":
    main()
