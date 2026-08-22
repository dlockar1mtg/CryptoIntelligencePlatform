from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import ASSETS, Module38Runner
from scripts.audit_predictive_horizon_recovery_v4_fresh_evidence_capacity import (
    EXPECTED_V3_RESULTS_SHA256,
    V4_DEVELOPMENT_ORIGINS_PER_GROUP,
    V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP,
    V4_HORIZONS,
    fresh_capacity_for_group,
    selected_v3_origins_for_group,
)
from scripts.run_v3_per_horizon_development_tournament import (
    DEVELOPMENT_FOLDS,
    ORIGINS_PER_FOLD,
    build_relative_market,
)

EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EVIDENCE_CLASS = "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("manifest_content_sha256", None)
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def exact_target_available_indices(features: pd.DataFrame, indices: list[int], asset_frame: pd.DataFrame, horizon: int) -> list[int]:
    """Filter origin indices by exact calendar target-date availability only.

    This intentionally checks date membership, not future price values or outcomes.
    """
    available_dates = {
        pd.Timestamp(value).date()
        for value in pd.to_datetime(asset_frame["observation_date"])
    }
    exact_safe: list[int] = []
    for idx in indices:
        origin_date = pd.Timestamp(features.iloc[int(idx)]["observation_date"]).date()
        target_date = (pd.Timestamp(origin_date) + pd.to_timedelta(int(horizon), unit="D")).date()
        if target_date in available_dates:
            exact_safe.append(int(idx))
    return exact_safe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--v3-results", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.database).resolve()
    v2_path = Path(args.v2_manifest).resolve()
    v3_path = Path(args.v3_manifest).resolve()
    v3_results_path = Path(args.v3_results).resolve()
    output = Path(args.output).resolve()

    for path in (source, v2_path, v3_path, v3_results_path):
        require(path.is_file(), f"Required input missing: {path}")
    require(not output.exists(), f"V4 final-holdout manifest already exists: {output}")
    require(sha256(v3_results_path) == EXPECTED_V3_RESULTS_SHA256, "Unexpected preserved V3 development-results hash")

    before = {
        "database": sha256(source),
        "v2_manifest": sha256(v2_path),
        "v3_manifest": sha256(v3_path),
        "v3_results": sha256(v3_results_path),
    }

    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    v3 = json.loads(v3_path.read_text(encoding="utf-8"))
    v3_results = json.loads(v3_results_path.read_text(encoding="utf-8"))
    require(v3_results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout has been viewed")

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_final_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}
    require(set(v2_dates) == set(v3_final_dates), "V2/V3 supported-group mismatch")

    groups: list[dict] = []
    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_v4_holdout_freeze_") as tmp:
        temp_db = Path(tmp) / source.name
        shutil.copy2(source, temp_db)
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.platform import connect, load_all

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
                "SELECT observation_date,btc_return_30d_pct,core_breadth_above_sma50_pct,core_median_return_30d_pct,fear_greed_index,stablecoin_supply_usd,stablecoin_growth_30d_pct,dollar_index,vix,macro_liquidity_score,risk_appetite_score FROM crypto_features_daily ORDER BY observation_date"
            ).fetchdf()
            context["observation_date"] = pd.to_datetime(context["observation_date"])
            relative = build_relative_market(prices)
            relative["observation_date"] = pd.to_datetime(relative["observation_date"])

            for asset in ASSETS:
                asset_frame = prices[prices["asset_id"] == asset].copy()
                for horizon in V4_HORIZONS:
                    key = (asset, horizon)
                    if key not in v3_final_dates:
                        continue

                    features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                    v3_mask = pd.to_datetime(features["observation_date"]).dt.date.astype(str).isin(v3_final_dates[key])
                    features.loc[v3_mask, "target_return"] = np.nan

                    selected_v3 = selected_v3_origins_for_group(
                        features,
                        horizon,
                        runner,
                        context,
                        relative,
                        asset,
                        v2_dates[key],
                        v3_final_dates[key],
                    )
                    selected_v3_dates = {
                        pd.Timestamp(features.iloc[idx]["observation_date"]).date().isoformat()
                        for idx in selected_v3
                    }
                    require(
                        len(selected_v3_dates) == DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD,
                        f"V3 development reconstruction mismatch for {asset} {horizon}d",
                    )

                    prior_exclusions = set(v2_dates[key]) | set(v3_final_dates[key]) | selected_v3_dates
                    _, feature_safe = fresh_capacity_for_group(
                        features,
                        horizon,
                        runner,
                        context,
                        relative,
                        asset,
                        prior_exclusions,
                    )
                    exact_safe = exact_target_available_indices(features, feature_safe, asset_frame, horizon)
                    required = V4_DEVELOPMENT_ORIGINS_PER_GROUP + V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP
                    require(len(exact_safe) >= required, f"Insufficient exact-target-safe V4 capacity for {asset} {horizon}d")

                    final_indices = exact_safe[-V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP:]
                    development_pool = exact_safe[:-V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP]
                    require(len(development_pool) >= V4_DEVELOPMENT_ORIGINS_PER_GROUP, f"Insufficient V4 development pool for {asset} {horizon}d")
                    positions = np.linspace(0, len(development_pool) - 1, V4_DEVELOPMENT_ORIGINS_PER_GROUP, dtype=int)
                    development_indices = [development_pool[int(pos)] for pos in positions]
                    require(len(set(development_indices)) == V4_DEVELOPMENT_ORIGINS_PER_GROUP, f"Duplicate V4 development origin for {asset} {horizon}d")

                    final_dates = [pd.Timestamp(features.iloc[idx]["observation_date"]).date().isoformat() for idx in final_indices]
                    development_dates = [pd.Timestamp(features.iloc[idx]["observation_date"]).date().isoformat() for idx in development_indices]
                    require(len(set(final_dates)) == V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP, f"Duplicate V4 final-holdout origin for {asset} {horizon}d")
                    require(set(final_dates).isdisjoint(development_dates), f"V4 development/final overlap for {asset} {horizon}d")
                    require(set(final_dates).isdisjoint(prior_exclusions), f"V4 final holdout overlaps prior evidence for {asset} {horizon}d")
                    require(set(development_dates).isdisjoint(prior_exclusions), f"V4 development overlaps prior evidence for {asset} {horizon}d")

                    groups.append({
                        "asset_id": asset,
                        "horizon_days": horizon,
                        "v4_development_origin_dates": development_dates,
                        "v4_final_holdout_origin_dates": final_dates,
                    })
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    after = {
        "database": sha256(source),
        "v2_manifest": sha256(v2_path),
        "v3_manifest": sha256(v3_path),
        "v3_results": sha256(v3_results_path),
    }
    require(before == after, "Source evidence changed during V4 final-holdout freeze")
    require(len(groups) == 17, f"Expected 17 supported V4 groups, found {len(groups)}")

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "evidence_class": EVIDENCE_CLASS,
        "recovery_horizons": list(V4_HORIZONS),
        "supported_groups": 17,
        "development_origins_per_group": V4_DEVELOPMENT_ORIGINS_PER_GROUP,
        "final_holdout_origins_per_group": V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP,
        "v2_consumed_origins_excluded": True,
        "v3_development_origins_excluded": True,
        "v3_final_holdout_origins_excluded": True,
        "v3_final_holdout_reused": False,
        "holdout_outcomes_viewed_before_freeze": False,
        "exact_calendar_target_date_required": True,
        "holdout_outcome_values_read_during_membership_selection": False,
        "groups": sorted(groups, key=lambda row: (int(row["horizon_days"]), str(row["asset_id"]))),
    }
    payload["manifest_content_sha256"] = canonical_hash(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("CRYPTO_V4_FINAL_HOLDOUT_MEMBERSHIP_FREEZE=PASS")
    print(f"SUPPORTED_GROUPS={payload['supported_groups']}")
    print(f"DEVELOPMENT_ORIGINS_PER_GROUP={payload['development_origins_per_group']}")
    print(f"FINAL_HOLDOUT_ORIGINS_PER_GROUP={payload['final_holdout_origins_per_group']}")
    print(f"MANIFEST_CONTENT_SHA256={payload['manifest_content_sha256']}")
    print("EXACT_CALENDAR_TARGET_DATE_REQUIRED=TRUE")
    print("HOLDOUT_OUTCOME_VALUES_READ_DURING_MEMBERSHIP_SELECTION=FALSE")
    print("HOLDOUT_OUTCOMES_VIEWED_BEFORE_FREEZE=FALSE")
    print("V3_FINAL_HOLDOUT_REUSED=FALSE")
    print("SOURCE_EVIDENCE_MODIFIED=FALSE")
    print("NEXT_GATE=VALIDATE_AND_PRESERVE_V4_FINAL_HOLDOUT_MANIFEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())