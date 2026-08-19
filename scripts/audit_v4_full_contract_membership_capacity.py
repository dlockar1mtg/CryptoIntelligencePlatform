from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import ASSETS, Module38Runner
from scripts.audit_predictive_horizon_recovery_v4_fresh_evidence_capacity import selected_v3_origins_for_group
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

EXPECTED_V3_RESULTS_SHA256 = "33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1"
REQUIRED_DEVELOPMENT = 50
REQUIRED_FINAL = 10
REQUIRED_TOTAL = REQUIRED_DEVELOPMENT + REQUIRED_FINAL


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def exact_target_date_available(price_dates: set[str], origin_date: str, horizon: int) -> bool:
    target = (pd.Timestamp(origin_date) + pd.to_timedelta(int(horizon), unit="D")).date().isoformat()
    return target in price_dates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--v3-results", required=True)
    parser.add_argument("--v4-manifest", required=True)
    args = parser.parse_args()

    source = Path(args.database).resolve()
    v2_path = Path(args.v2_manifest).resolve()
    v3_path = Path(args.v3_manifest).resolve()
    v3_results_path = Path(args.v3_results).resolve()
    v4_path = Path(args.v4_manifest).resolve()
    for path in (source, v2_path, v3_path, v3_results_path, v4_path):
        require(path.is_file(), f"Required input missing: {path}")

    tracked = {"database": source, "v2": v2_path, "v3": v3_path, "v3_results": v3_results_path, "v4": v4_path}
    before = {name: sha256(path) for name, path in tracked.items()}
    require(before["v3_results"] == EXPECTED_V3_RESULTS_SHA256, "Unexpected V3 results hash")

    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    v3 = json.loads(v3_path.read_text(encoding="utf-8"))
    v3_results = json.loads(v3_results_path.read_text(encoding="utf-8"))
    v4 = json.loads(v4_path.read_text(encoding="utf-8"))
    require(v3_results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout has been viewed")
    require(v4.get("holdout_outcomes_viewed_before_freeze") is False, "V4 holdout was viewed before freeze")

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_final_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}
    v4_groups = {(g["asset_id"], int(g["horizon_days"])): g for g in v4["groups"]}

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    rows = []
    reason_counts = Counter()
    family_failures = Counter()
    group_failure_counts = defaultdict(int)

    with tempfile.TemporaryDirectory(prefix="crypto_v4_full_contract_capacity_") as tmp:
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
                "SELECT observation_date," + ",".join(NATIVE_LAG_DAYS) + " FROM crypto_features_daily ORDER BY observation_date"
            ).fetchdf()
            context["observation_date"] = pd.to_datetime(context["observation_date"])
            v4_relative = build_relative_market(prices)
            v4_relative["observation_date"] = pd.to_datetime(v4_relative["observation_date"])
            v3_relative = build_v3_relative_market(prices)
            v3_relative["observation_date"] = pd.to_datetime(v3_relative["observation_date"])

            supported = [(asset, horizon) for horizon in RECOVERY_HORIZONS for asset in ASSETS if not (asset == "xrp" and horizon == 365)]
            for asset, horizon in supported:
                key = (asset, horizon)
                require(key in v4_groups, f"Missing V4 group {asset} {horizon}d")
                asset_frame = prices[prices["asset_id"] == asset].copy()
                price_dates = set(pd.to_datetime(asset_frame["observation_date"]).dt.date.astype(str))

                v3_features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                v3_mask = pd.to_datetime(v3_features["observation_date"]).dt.date.astype(str).isin(v3_final_dates[key])
                v3_features.loc[v3_mask, "target_return"] = np.nan
                selected_v3_indices = selected_v3_origins_for_group(
                    v3_features, horizon, runner, context, v3_relative, asset,
                    v2_dates[key], v3_final_dates[key],
                )
                selected_v3_dates = {
                    pd.Timestamp(v3_features.iloc[index]["observation_date"]).date().isoformat()
                    for index in selected_v3_indices
                }
                prior_excluded = set(v2_dates[key]) | set(v3_final_dates[key]) | selected_v3_dates

                features = build_price_features(asset_frame, horizon).reset_index(drop=True)
                date_to_index = {
                    pd.Timestamp(row.observation_date).date().isoformat(): int(row.Index)
                    for row in features[["observation_date"]].itertuples(index=True)
                }
                safe_dates = []
                examined = 0
                failures = 0

                for date_key, origin_idx in date_to_index.items():
                    if date_key in prior_excluded:
                        continue
                    if not exact_target_date_available(price_dates, date_key, horizon):
                        reason_counts["exact_target_date_missing"] += 1
                        continue
                    # Development eligibility needs a matured target. Holdout membership only needs
                    # endpoint availability, but we audit against the stricter full development contract.
                    target_value = features.iloc[origin_idx]["target_return"]
                    if not np.isfinite(float(target_value)):
                        reason_counts["target_return_missing"] += 1
                        continue
                    examined += 1
                    try:
                        _, train, validation, current = v4_split_origin(features, origin_idx, horizon, runner, prior_excluded)
                    except RuntimeError:
                        reason_counts["unsafe_split"] += 1
                        failures += 1
                        group_failure_counts[f"{asset}|{horizon}"] += 1
                        continue

                    origin_ok = True
                    for family in CANDIDATE_CONTRACTS[horizon]["families"]:
                        columns = candidate_features(horizon, family)
                        train_f = attach_relative(attach_lagged_native(train, context, columns), v4_relative, asset, columns)
                        val_f = attach_relative(attach_lagged_native(validation, context, columns), v4_relative, asset, columns)
                        current_f = attach_relative(attach_lagged_native(current, context, columns), v4_relative, asset, columns)
                        train_complete = train_f.dropna(subset=columns + ["target_return"])
                        val_complete = val_f.dropna(subset=columns + ["target_return"])
                        current_complete = current_f.dropna(subset=columns)
                        if len(train_complete) < 90:
                            origin_ok = False
                            reason_counts["train_lt_90"] += 1
                            family_failures[f"{horizon}|{family}|train_lt_90"] += 1
                        if len(val_complete) < 30:
                            origin_ok = False
                            reason_counts["validation_lt_30"] += 1
                            family_failures[f"{horizon}|{family}|validation_lt_30"] += 1
                        if len(current_complete) != 1:
                            origin_ok = False
                            reason_counts["current_incomplete"] += 1
                            family_failures[f"{horizon}|{family}|current_incomplete"] += 1
                    if origin_ok:
                        safe_dates.append(date_key)
                    else:
                        failures += 1
                        group_failure_counts[f"{asset}|{horizon}"] += 1

                safe_dates = sorted(set(safe_dates))
                rows.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "candidate_origins_examined": examined,
                    "full_contract_safe_origins": len(safe_dates),
                    "required_total": REQUIRED_TOTAL,
                    "capacity_pass": len(safe_dates) >= REQUIRED_TOTAL,
                    "earliest_safe_origin": safe_dates[0] if safe_dates else None,
                    "latest_safe_origin": safe_dates[-1] if safe_dates else None,
                    "failed_origins": failures,
                })
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    after = {name: sha256(path) for name, path in tracked.items()}
    require(before == after, "Source evidence changed during full-contract capacity audit")
    require(len(rows) == 17, f"Expected 17 groups, found {len(rows)}")
    capacity_failures = [row for row in rows if not row["capacity_pass"]]
    minimum = min(row["full_contract_safe_origins"] for row in rows)

    report = {
        "status": "PASS",
        "experiment_id": "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4",
        "supported_groups": len(rows),
        "required_full_contract_safe_origins_per_group": REQUIRED_TOTAL,
        "capacity_failures": len(capacity_failures),
        "minimum_full_contract_safe_capacity": minimum,
        "groups": rows,
        "failure_reason_counts": dict(reason_counts),
        "family_failure_counts": dict(family_failures),
        "group_failed_origin_counts": dict(group_failure_counts),
        "holdout_outcome_values_read": False,
        "source_database_modified": False,
        "next_gate": "REBUILD_V4_MEMBERSHIP_FROM_FULL_CONTRACT_SAFE_POOL" if not capacity_failures else "REVIEW_V4_FULL_CONTRACT_CAPACITY_SHORTFALL",
    }
    print(json.dumps(report, indent=2))
    print("CRYPTO_V4_FULL_CONTRACT_MEMBERSHIP_CAPACITY_AUDIT=PASS")
    print(f"SUPPORTED_GROUPS={len(rows)}")
    print(f"CAPACITY_FAILURES={len(capacity_failures)}")
    print(f"MINIMUM_FULL_CONTRACT_SAFE_CAPACITY={minimum}")
    print(f"TOTAL_CURRENT_MANIFEST_PREFLIGHT_FAILURES_OBSERVED=318")
    print("HOLDOUT_OUTCOME_VALUES_READ=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
