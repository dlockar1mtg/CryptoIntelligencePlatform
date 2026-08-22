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
from scripts.audit_predictive_horizon_recovery_v4_fresh_evidence_capacity import (
    EXPECTED_V3_RESULTS_SHA256,
    V4_DEVELOPMENT_ORIGINS_PER_GROUP,
    V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP,
    selected_v3_origins_for_group,
)
from scripts.preflight_predictive_horizon_recovery_v4_development import v4_split_origin
from scripts.run_v3_per_horizon_development_tournament import build_relative_market as build_v3_relative_market
from scripts.v4_horizon_recovery_model_spec import (
    CANDIDATE_CONTRACTS,
    NATIVE_LAG_DAYS,
    RECOVERY_HORIZONS,
    attach_lagged_native,
    attach_relative,
    build_price_features,
    build_relative_market,
    candidate_features,
)

EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_GROUPS = 17


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def exact_target_date_available(asset_dates: set[pd.Timestamp], origin_date: pd.Timestamp, horizon: int) -> bool:
    target = (pd.Timestamp(origin_date).normalize() + pd.to_timedelta(int(horizon), unit="D")).normalize()
    return target in asset_dates


def family_safe_at_origin(
    features: pd.DataFrame,
    origin_idx: int,
    horizon: int,
    runner: Module38Runner,
    excluded_dates: set[str],
    context: pd.DataFrame,
    relative: pd.DataFrame,
    asset: str,
    family: str,
) -> bool:
    try:
        _, train, validation, current = v4_split_origin(features, origin_idx, horizon, runner, excluded_dates)
    except RuntimeError:
        return False

    columns = candidate_features(horizon, family)
    train_f = attach_relative(attach_lagged_native(train, context, columns), relative, asset, columns)
    val_f = attach_relative(attach_lagged_native(validation, context, columns), relative, asset, columns)
    current_f = attach_relative(attach_lagged_native(current, context, columns), relative, asset, columns)

    train_complete = train_f.dropna(subset=columns + ["target_return"])
    val_complete = val_f.dropna(subset=columns + ["target_return"])
    current_complete = current_f.dropna(subset=columns)

    return len(train_complete) >= 90 and len(val_complete) >= 30 and len(current_complete) == 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--v3-results", required=True)
    args = parser.parse_args()

    source = Path(args.database).resolve()
    v2_path = Path(args.v2_manifest).resolve()
    v3_path = Path(args.v3_manifest).resolve()
    v3_results_path = Path(args.v3_results).resolve()

    for path in (source, v2_path, v3_path, v3_results_path):
        require(path.is_file(), f"Required V4 capacity input missing: {path}")
    require(sha256(v3_results_path) == EXPECTED_V3_RESULTS_SHA256, "Unexpected preserved V3 development-results hash")

    before = {
        "database": sha256(source),
        "v2": sha256(v2_path),
        "v3": sha256(v3_path),
        "v3_results": sha256(v3_results_path),
    }

    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    v3 = json.loads(v3_path.read_text(encoding="utf-8"))
    v3_results = json.loads(v3_results_path.read_text(encoding="utf-8"))
    require(v3_results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout has been viewed")

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_final_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}
    require(set(v2_dates) == set(v3_final_dates), "V2/V3 supported-group mismatch")

    rows: list[dict] = []
    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_v4_candidate_capacity_") as tmp:
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
                "SELECT observation_date," + ",".join(NATIVE_LAG_DAYS) + " FROM crypto_features_daily ORDER BY observation_date"
            ).fetchdf()
            context["observation_date"] = pd.to_datetime(context["observation_date"])

            v4_relative = build_relative_market(prices)
            v4_relative["observation_date"] = pd.to_datetime(v4_relative["observation_date"])
            v3_relative = build_v3_relative_market(prices)
            v3_relative["observation_date"] = pd.to_datetime(v3_relative["observation_date"])

            for asset in ASSETS:
                asset_frame = prices[prices["asset_id"] == asset].copy()
                asset_dates = {pd.Timestamp(value).normalize() for value in asset_frame["observation_date"]}

                for horizon in RECOVERY_HORIZONS:
                    key = (asset, int(horizon))
                    if key not in v3_final_dates:
                        continue

                    v3_features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                    v3_mask = pd.to_datetime(v3_features["observation_date"]).dt.date.astype(str).isin(v3_final_dates[key])
                    v3_features.loc[v3_mask, "target_return"] = pd.NA
                    selected_v3 = selected_v3_origins_for_group(
                        v3_features,
                        horizon,
                        runner,
                        context,
                        v3_relative,
                        asset,
                        v2_dates[key],
                        v3_final_dates[key],
                    )
                    selected_v3_dates = {
                        pd.Timestamp(v3_features.iloc[idx]["observation_date"]).date().isoformat()
                        for idx in selected_v3
                    }
                    prior_exclusions = set(v2_dates[key]) | set(v3_final_dates[key]) | selected_v3_dates

                    features = build_price_features(asset_frame, horizon).reset_index(drop=True)
                    families = list(CANDIDATE_CONTRACTS[horizon]["families"])
                    family_safe_dates = {family: [] for family in families}
                    common_safe_dates: list[str] = []
                    exact_target_candidate_dates = 0

                    for origin_idx, row in features[["observation_date"]].iterrows():
                        origin_date = pd.Timestamp(row["observation_date"])
                        date_key = origin_date.date().isoformat()
                        if date_key in prior_exclusions:
                            continue
                        if not exact_target_date_available(asset_dates, origin_date, horizon):
                            continue
                        exact_target_candidate_dates += 1

                        all_safe = True
                        for family in families:
                            safe = family_safe_at_origin(
                                features,
                                int(origin_idx),
                                horizon,
                                runner,
                                prior_exclusions,
                                context,
                                v4_relative,
                                asset,
                                family,
                            )
                            if safe:
                                family_safe_dates[family].append(date_key)
                            else:
                                all_safe = False
                        if all_safe:
                            common_safe_dates.append(date_key)

                    required = V4_DEVELOPMENT_ORIGINS_PER_GROUP + V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP
                    rows.append({
                        "asset_id": asset,
                        "horizon_days": int(horizon),
                        "exact_target_candidate_origins": exact_target_candidate_dates,
                        "family_safe_origin_counts": {family: len(dates) for family, dates in family_safe_dates.items()},
                        "common_all_v4_family_safe_origins": len(common_safe_dates),
                        "required_for_50_dev_plus_10_final": required,
                        "capacity_pass": len(common_safe_dates) >= required,
                        "earliest_common_safe_origin": common_safe_dates[0] if common_safe_dates else None,
                        "latest_common_safe_origin": common_safe_dates[-1] if common_safe_dates else None,
                    })

            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    after = {
        "database": sha256(source),
        "v2": sha256(v2_path),
        "v3": sha256(v3_path),
        "v3_results": sha256(v3_results_path),
    }
    require(before == after, "Source evidence changed during V4 candidate-safe capacity audit")
    require(len(rows) == EXPECTED_GROUPS, f"Expected {EXPECTED_GROUPS} V4 groups, found {len(rows)}")

    failures = [row for row in rows if not row["capacity_pass"]]
    minimum_capacity = min(int(row["common_all_v4_family_safe_origins"]) for row in rows)
    report = {
        "status": "PASS" if not failures else "CAPACITY_SHORTFALL",
        "experiment_id": EXPERIMENT_ID,
        "supported_groups": len(rows),
        "required_common_safe_origins_per_group": V4_DEVELOPMENT_ORIGINS_PER_GROUP + V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP,
        "capacity_failures": len(failures),
        "minimum_common_all_v4_family_safe_capacity": minimum_capacity,
        "groups": rows,
        "v3_final_holdout_outcomes_viewed": False,
        "v4_final_holdout_outcomes_viewed": False,
        "source_database_modified": False,
        "next_gate": (
            "CORRECT_V4_MEMBERSHIP_SELECTION_TO_V4_CANDIDATE_SAFE_ORIGINS"
            if not failures
            else "REVIEW_V4_CANDIDATE_CAPACITY_SHORTFALL_BEFORE_MEMBERSHIP_CHANGE"
        ),
    }
    print(json.dumps(report, indent=2))
    print("CRYPTO_V4_CANDIDATE_SAFE_CAPACITY_AUDIT=PASS")
    print(f"SUPPORTED_GROUPS={len(rows)}")
    print(f"CAPACITY_FAILURES={len(failures)}")
    print(f"MINIMUM_COMMON_V4_CANDIDATE_SAFE_CAPACITY={minimum_capacity}")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V4_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
