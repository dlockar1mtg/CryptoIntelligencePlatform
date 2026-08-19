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


def attach_candidate_features(frame, context, relative, asset, horizon):
    by_family = {}
    for family in CANDIDATE_CONTRACTS[horizon]["families"]:
        columns = candidate_features(horizon, family)
        enriched = attach_relative(attach_lagged_native(frame, context, columns), relative, asset, columns)
        by_family[family] = (enriched, columns)
    return by_family


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

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    rows = []
    with tempfile.TemporaryDirectory(prefix="crypto_v4_split_capacity_") as tmp:
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

                holdout_safe = []
                development_safe = []
                for date_key, origin_idx in date_to_index.items():
                    if date_key in prior_excluded:
                        continue
                    if not exact_target_date_available(price_dates, date_key, horizon):
                        continue

                    # Holdout eligibility uses only origin-time feature completeness and endpoint existence.
                    # It deliberately does not inspect the target value, target sign, or target magnitude.
                    current = features.iloc[[origin_idx]].copy()
                    current_by_family = attach_candidate_features(current, context, v4_relative, asset, horizon)
                    current_ok = True
                    for enriched, columns in current_by_family.values():
                        if len(enriched.dropna(subset=columns)) != 1:
                            current_ok = False
                            break
                    if not current_ok:
                        continue
                    holdout_safe.append(date_key)

                    # Development eligibility additionally requires a leakage-safe split and complete
                    # training/validation matrices. The origin's target is not used for membership ranking.
                    try:
                        _, train, validation, _ = v4_split_origin(features, origin_idx, horizon, runner, prior_excluded)
                    except RuntimeError:
                        continue
                    development_ok = True
                    train_by_family = attach_candidate_features(train, context, v4_relative, asset, horizon)
                    validation_by_family = attach_candidate_features(validation, context, v4_relative, asset, horizon)
                    for family in CANDIDATE_CONTRACTS[horizon]["families"]:
                        train_f, columns = train_by_family[family]
                        val_f, _ = validation_by_family[family]
                        if len(train_f.dropna(subset=columns + ["target_return"])) < 90:
                            development_ok = False
                            break
                        if len(val_f.dropna(subset=columns + ["target_return"])) < 30:
                            development_ok = False
                            break
                    if development_ok:
                        development_safe.append(date_key)

                holdout_safe = sorted(set(holdout_safe))
                development_safe = sorted(set(development_safe))
                require(len(holdout_safe) >= REQUIRED_FINAL, f"Insufficient holdout-safe origins for {asset} {horizon}d")
                reserved_holdout = holdout_safe[-REQUIRED_FINAL:]
                residual_development = [d for d in development_safe if d not in set(reserved_holdout)]
                rows.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "holdout_safe_origins": len(holdout_safe),
                    "development_safe_origins": len(development_safe),
                    "reserved_latest_holdout_origins": len(reserved_holdout),
                    "residual_development_safe_after_holdout_reservation": len(residual_development),
                    "development_capacity_pass": len(residual_development) >= REQUIRED_DEVELOPMENT,
                    "earliest_residual_development_safe_origin": residual_development[0] if residual_development else None,
                    "latest_residual_development_safe_origin": residual_development[-1] if residual_development else None,
                    "earliest_reserved_holdout_origin": reserved_holdout[0],
                    "latest_reserved_holdout_origin": reserved_holdout[-1],
                })
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    after = {name: sha256(path) for name, path in tracked.items()}
    require(before == after, "Source evidence changed during separate-capacity audit")
    require(len(rows) == 17, f"Expected 17 groups, found {len(rows)}")
    failures = [row for row in rows if not row["development_capacity_pass"]]
    minimum_residual = min(int(row["residual_development_safe_after_holdout_reservation"]) for row in rows)

    report = {
        "status": "PASS",
        "experiment_id": "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4",
        "supported_groups": len(rows),
        "required_development_origins_per_group": REQUIRED_DEVELOPMENT,
        "required_final_holdout_origins_per_group": REQUIRED_FINAL,
        "capacity_failures_after_separate_eligibility": len(failures),
        "minimum_residual_development_capacity": minimum_residual,
        "groups": rows,
        "holdout_outcome_values_read": False,
        "holdout_outcome_signs_read": False,
        "holdout_outcome_magnitudes_read": False,
        "source_database_modified": False,
        "next_gate": "REBUILD_V4_MEMBERSHIP_WITH_SEPARATE_DEVELOPMENT_AND_HOLDOUT_ELIGIBILITY" if not failures else "REVIEW_V4_DEVELOPMENT_CAPACITY_SHORTFALL_AFTER_SEPARATE_ELIGIBILITY",
    }
    print(json.dumps(report, indent=2))
    print("CRYPTO_V4_SEPARATE_DEVELOPMENT_AND_HOLDOUT_CAPACITY_AUDIT=PASS")
    print(f"SUPPORTED_GROUPS={len(rows)}")
    print(f"CAPACITY_FAILURES_AFTER_SEPARATE_ELIGIBILITY={len(failures)}")
    print(f"MINIMUM_RESIDUAL_DEVELOPMENT_CAPACITY={minimum_residual}")
    print("HOLDOUT_OUTCOME_VALUES_READ=FALSE")
    print("HOLDOUT_OUTCOME_SIGNS_READ=FALSE")
    print("HOLDOUT_OUTCOME_MAGNITUDES_READ=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
