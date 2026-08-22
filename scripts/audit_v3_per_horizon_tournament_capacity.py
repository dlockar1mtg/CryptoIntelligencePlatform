from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import ASSETS, Module38Runner
from crypto_platform.module39_validation import exact_candidates

HORIZONS = [7, 30, 90, 180, 365]
PRICE_FEATURES = [
    "return_1d",
    "return_7d",
    "return_30d",
    "return_90d",
    "volatility_30d",
    "volatility_90d",
    "distance_sma50",
    "distance_sma200",
]
NATIVE_CONTEXT_FEATURES = [
    "btc_return_30d_pct",
    "core_breadth_above_sma50_pct",
    "core_median_return_30d_pct",
    "dollar_index",
    "fear_greed_index",
    "macro_liquidity_score",
    "risk_appetite_score",
    "stablecoin_growth_30d_pct",
    "stablecoin_supply_usd",
    "vix",
]
RELATIVE_FEATURE_REQUIREMENTS = [
    "BTC_RELATIVE_RETURN_7D",
    "BTC_RELATIVE_RETURN_30D",
    "CROSS_ASSET_BREADTH_7D",
    "CROSS_ASSET_BREADTH_30D",
    "CROSS_ASSET_RETURN_DISPERSION_7D",
    "CROSS_ASSET_RETURN_DISPERSION_30D",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_relative_market(prices: pd.DataFrame) -> pd.DataFrame:
    pivot = prices.pivot(index="observation_date", columns="asset_id", values="price_usd").sort_index()
    ret7 = pivot.pct_change(7, fill_method=None)
    ret30 = pivot.pct_change(30, fill_method=None)
    btc7 = ret7.get("bitcoin")
    btc30 = ret30.get("bitcoin")
    rows = []
    for asset in [c for c in pivot.columns if c in ASSETS]:
        frame = pd.DataFrame(index=pivot.index)
        frame["asset_id"] = asset
        frame["BTC_RELATIVE_RETURN_7D"] = ret7[asset] - btc7
        frame["BTC_RELATIVE_RETURN_30D"] = ret30[asset] - btc30
        frame["CROSS_ASSET_BREADTH_7D"] = (ret7 > 0).mean(axis=1)
        frame["CROSS_ASSET_BREADTH_30D"] = (ret30 > 0).mean(axis=1)
        frame["CROSS_ASSET_RETURN_DISPERSION_7D"] = ret7.std(axis=1)
        frame["CROSS_ASSET_RETURN_DISPERSION_30D"] = ret30.std(axis=1)
        frame = frame.reset_index()
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--minimum-development-origins-per-group", type=int, default=60)
    parser.add_argument("--minimum-final-holdout-origins-per-group", type=int, default=10)
    args = parser.parse_args()

    source = Path(args.database).resolve()
    manifest_path = Path(args.v2_manifest).resolve()
    require(source.is_file(), f"Database missing: {source}")
    require(manifest_path.is_file(), f"V2 manifest missing: {manifest_path}")
    before_db = sha256(source)
    before_manifest = sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    v2_dates = {
        (g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"])
        for g in manifest["groups"]
    }

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_v3_capacity_") as tmp:
        temp_db = Path(tmp) / source.name
        shutil.copy2(source, temp_db)
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.platform import load_all, connect
            settings, _ = load_all()
            conn = connect(settings)
            runner = object.__new__(Module38Runner)
            runner.cfg = settings["module38"]

            prices = conn.execute(
                """
                SELECT asset_id, observation_date, price_usd, market_cap_usd, volume_24h_usd
                FROM canonical_market_daily
                WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
                  AND price_usd IS NOT NULL
                ORDER BY observation_date, asset_id
                """
            ).fetchdf()
            prices["observation_date"] = pd.to_datetime(prices["observation_date"])
            context = conn.execute(
                "SELECT observation_date," + ",".join(NATIVE_CONTEXT_FEATURES) + " FROM crypto_features_daily ORDER BY observation_date"
            ).fetchdf()
            context["observation_date"] = pd.to_datetime(context["observation_date"])
            relative = build_relative_market(prices)
            relative["observation_date"] = pd.to_datetime(relative["observation_date"])

            per_group = []
            horizon_summary = {str(h): {"supported_groups": 0, "groups_with_development_capacity": 0, "groups_with_fresh_holdout_capacity": 0} for h in HORIZONS}
            for asset in ASSETS:
                asset_frame = prices[prices.asset_id == asset].copy()
                for horizon in HORIZONS:
                    key = (asset, horizon)
                    features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                    candidates = exact_candidates(
                        features,
                        horizon,
                        int(runner.cfg.get("absolute_minimum_training_rows", 90)),
                        int(runner.cfg.get("minimum_validation_rows", 30)),
                        int(runner.cfg["validation_rows"]),
                        float(runner.cfg.get("maximum_validation_share", 0.25)),
                    )
                    candidate_dates = [pd.Timestamp(features.iloc[i]["observation_date"]).date().isoformat() for i in candidates]
                    if not candidate_dates:
                        per_group.append({"asset_id": asset, "horizon_days": horizon, "supported": False, "reason": "NO_SAFE_POINT_IN_TIME_CANDIDATES"})
                        continue
                    if key not in v2_dates:
                        per_group.append({"asset_id": asset, "horizon_days": horizon, "supported": False, "reason": "PRESERVED_UNSUPPORTED_GROUP"})
                        continue

                    consumed = set(v2_dates[key])
                    unused_dates = [d for d in candidate_dates if d not in consumed]
                    dev_capacity = max(0, len(unused_dates) - int(args.minimum_final_holdout_origins_per_group))
                    fresh_holdout_capacity = len(unused_dates) >= int(args.minimum_final_holdout_origins_per_group)
                    development_capacity = dev_capacity >= int(args.minimum_development_origins_per_group)

                    feature_dates = pd.to_datetime(features["observation_date"])
                    joined = features[["observation_date"]].merge(context, on="observation_date", how="left")
                    rel_join = features[["observation_date"]].merge(
                        relative[relative.asset_id == asset].drop(columns=["asset_id"]),
                        on="observation_date",
                        how="left",
                    )
                    native_complete_rows = int(joined[NATIVE_CONTEXT_FEATURES].notna().all(axis=1).sum())
                    relative_complete_rows = int(rel_join[RELATIVE_FEATURE_REQUIREMENTS].notna().all(axis=1).sum())
                    price_complete_rows = int(features[PRICE_FEATURES].notna().all(axis=1).sum())

                    row = {
                        "asset_id": asset,
                        "horizon_days": horizon,
                        "supported": True,
                        "safe_candidate_origins": len(candidate_dates),
                        "v2_consumed_origins": len(consumed),
                        "unused_safe_origins": len(unused_dates),
                        "development_capacity_after_reserving_fresh_holdout": dev_capacity,
                        "minimum_development_required": int(args.minimum_development_origins_per_group),
                        "fresh_final_holdout_reserved": int(args.minimum_final_holdout_origins_per_group),
                        "development_capacity_ok": development_capacity,
                        "fresh_holdout_capacity_ok": fresh_holdout_capacity,
                        "price_feature_complete_rows": price_complete_rows,
                        "native_context_complete_rows": native_complete_rows,
                        "relative_market_complete_rows": relative_complete_rows,
                        "first_safe_origin": candidate_dates[0],
                        "latest_safe_origin": candidate_dates[-1],
                    }
                    per_group.append(row)
                    hs = horizon_summary[str(horizon)]
                    hs["supported_groups"] += 1
                    hs["groups_with_development_capacity"] += int(development_capacity)
                    hs["groups_with_fresh_holdout_capacity"] += int(fresh_holdout_capacity)

            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    require(sha256(source) == before_db, "Source database changed during V3 capacity audit")
    require(sha256(manifest_path) == before_manifest, "V2 manifest changed during V3 capacity audit")

    supported = [r for r in per_group if r.get("supported")]
    all_dev = all(bool(r["development_capacity_ok"]) for r in supported)
    all_holdout = all(bool(r["fresh_holdout_capacity_ok"]) for r in supported)
    report = {
        "status": "COMPLETE",
        "audit_scope": "V3_PER_HORIZON_TOURNAMENT_CAPACITY_AND_FEATURE_AVAILABILITY",
        "v2_holdout_outcomes_used": False,
        "source_database_unchanged": True,
        "v2_manifest_unchanged": True,
        "supported_groups": len(supported),
        "unsupported_groups": len(per_group) - len(supported),
        "minimum_development_origins_per_group": int(args.minimum_development_origins_per_group),
        "minimum_fresh_final_holdout_origins_per_group": int(args.minimum_final_holdout_origins_per_group),
        "all_supported_groups_have_development_capacity": all_dev,
        "all_supported_groups_have_fresh_v3_holdout_capacity": all_holdout,
        "horizon_summary": horizon_summary,
        "groups": per_group,
        "next_gate": "DEFINE_V3_HORIZON_SPECIFIC_FEATURE_SETS_AND_TOURNAMENT_HARNESS" if all_dev and all_holdout else "GOVERN_V3_CAPACITY_GAPS_BEFORE_TOURNAMENT",
    }
    print(json.dumps(report, indent=2))
    print("CRYPTO_V3_PER_HORIZON_TOURNAMENT_CAPACITY_AUDIT=PASS")
    print("V2_HOLDOUT_OUTCOMES_USED=FALSE")
    print(f"SUPPORTED_GROUPS={len(supported)}")
    print(f"ALL_SUPPORTED_GROUPS_HAVE_DEVELOPMENT_CAPACITY={str(all_dev).upper()}")
    print(f"ALL_SUPPORTED_GROUPS_HAVE_FRESH_V3_HOLDOUT_CAPACITY={str(all_holdout).upper()}")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
