from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    require(args.source_commit == EXPECTED_SOURCE_COMMIT, "Unexpected certified source commit")

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from crypto_platform.platform import load_all
    from crypto_platform.module38 import Module38Runner, ASSETS

    source_db = Path(args.database).resolve()
    require(source_db.is_file(), f"Crypto database missing: {source_db}")
    before = sha256(source_db)

    settings, _ = load_all()
    cfg38 = settings["module38"]
    cfg39 = settings["module39"]
    horizons = [int(v) for v in cfg38["horizons_days"]]
    folds = int(cfg39["rolling_folds"])
    minimum_training_rows = int(cfg39["minimum_training_rows"])
    minimum_calibration_rows = int(cfg39.get("minimum_calibration_rows", 30))

    con = duckdb.connect(str(source_db), read_only=True)
    try:
        prices = con.execute(
            """
            SELECT asset_id, observation_date, price_usd, market_cap_usd, volume_24h_usd
            FROM canonical_market_daily
            WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
              AND price_usd IS NOT NULL
            ORDER BY observation_date, asset_id
            """
        ).fetchdf()
        prices["observation_date"] = pd.to_datetime(prices["observation_date"])

        capacity = []
        for asset in ASSETS:
            asset_frame = prices[prices.asset_id == asset].copy()
            for horizon in horizons:
                features = Module38Runner.build_features(None, asset_frame, horizon)
                usable = int(len(features))
                # A true fold must have training origins whose labels mature before
                # the first test origin. This reserves one full horizon as the purge.
                post_training_rows = usable - minimum_training_rows - horizon
                possible_test_origins = max(post_training_rows, 0)
                capacity.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "usable_feature_rows": usable,
                    "minimum_training_rows": minimum_training_rows,
                    "purge_rows": horizon,
                    "possible_test_origins_after_minimum_train_and_purge": possible_test_origins,
                    "configured_rolling_folds": folds,
                    "can_form_configured_nonempty_folds": possible_test_origins >= folds,
                    "first_feature_date": str(pd.Timestamp(features.observation_date.min()).date()) if usable else None,
                    "last_feature_date": str(pd.Timestamp(features.observation_date.max()).date()) if usable else None,
                })

        realized = con.execute(
            """
            WITH latest_current AS (
                SELECT run_id
                FROM module38_runs
                WHERE status='SUCCESS'
                ORDER BY started_at_utc DESC
                LIMIT 1
            )
            SELECT f.asset_id,
                   f.horizon_days,
                   COUNT(*) AS historical_forecasts,
                   COUNT(r.price_usd) AS realized_forecasts,
                   COUNT(DISTINCT f.forecast_date) AS distinct_forecast_dates,
                   MIN(f.forecast_date) AS first_forecast_date,
                   MAX(f.forecast_date) AS last_forecast_date
            FROM m38_asset_forecasts f
            LEFT JOIN canonical_market_daily r
              ON r.asset_id=f.asset_id
             AND r.observation_date=CAST(f.forecast_date AS DATE)+f.horizon_days
            WHERE f.run_id<>(SELECT run_id FROM latest_current)
            GROUP BY f.asset_id,f.horizon_days
            ORDER BY f.asset_id,f.horizon_days
            """
        ).fetchall()
        realized_rows = [
            {
                "asset_id": str(r[0]),
                "horizon_days": int(r[1]),
                "historical_forecasts": int(r[2]),
                "realized_forecasts": int(r[3]),
                "distinct_forecast_dates": int(r[4]),
                "first_forecast_date": str(r[5]) if r[5] is not None else None,
                "last_forecast_date": str(r[6]) if r[6] is not None else None,
                "meets_direct_calibration_minimum": int(r[3]) >= minimum_calibration_rows,
            }
            for r in realized
        ]
    finally:
        con.close()

    after = sha256(source_db)
    require(before == after, "Read-only Module 39 capacity audit changed the database")

    insufficient_folds = [r for r in capacity if not r["can_form_configured_nonempty_folds"]]
    calibration_ready = [r for r in realized_rows if r["meets_direct_calibration_minimum"]]

    if insufficient_folds:
        route = "MODULE39_REPLAY_REQUIRES_CAPACITY_REVIEW"
    elif calibration_ready:
        route = "MODULE39_TRUE_ROLLING_ORIGIN_PLUS_DIRECT_REALIZED_CALIBRATION"
    else:
        route = "MODULE39_TRUE_ROLLING_ORIGIN_REPLAY_MUST_SUPPLY_REALIZED_CALIBRATION_EVIDENCE"

    payload = {
        "status": "CRYPTO_MODULE39_TRUE_VALIDATION_CAPACITY_AUDIT_COMPLETE",
        "source_commit": args.source_commit,
        "source_database_unchanged": True,
        "module39_config": {
            "rolling_folds": folds,
            "minimum_training_rows": minimum_training_rows,
            "minimum_calibration_rows": minimum_calibration_rows,
        },
        "rolling_origin_capacity": capacity,
        "insufficient_rolling_origin_groups": insufficient_folds,
        "historical_module38_realized_forecast_capacity": realized_rows,
        "direct_calibration_ready_groups": calibration_ready,
        "implementation_route": route,
        "interpretation_guard": "Existing Module 39 pseudo-rolling rows are not certification evidence. This audit only selects a leakage-safe implementation route.",
        "next_gate": "IMPLEMENT_MODULE39_TRUE_ROLLING_ORIGIN_AND_REALIZED_OUTCOME_CALIBRATION",
    }
    print(json.dumps(payload, indent=2, default=str))
    print("CRYPTO_MODULE39_TRUE_VALIDATION_CAPACITY_AUDIT=COMPLETE")
    print(f"INSUFFICIENT_ROLLING_ORIGIN_GROUPS={len(insufficient_folds)}")
    print(f"DIRECT_CALIBRATION_READY_GROUPS={len(calibration_ready)}")
    print(f"IMPLEMENTATION_ROUTE={route}")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=IMPLEMENT_MODULE39_TRUE_ROLLING_ORIGIN_AND_REALIZED_OUTCOME_CALIBRATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
