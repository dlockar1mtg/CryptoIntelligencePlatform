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
from crypto_platform.module39_validation import exact_candidates
from scripts.run_v3_per_horizon_development_tournament import (
    DEVELOPMENT_FOLDS,
    ORIGINS_PER_FOLD,
    HORIZON_CONTRACTS,
    attach_lagged_native,
    attach_relative,
    build_relative_market,
    family_columns,
    split_origin,
)

V4_HORIZONS = (7, 30, 365)
V4_DEVELOPMENT_ORIGINS_PER_GROUP = 50
V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP = 10
EXPECTED_V3_RESULTS_SHA256 = "33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def selected_v3_origins_for_group(
    features: pd.DataFrame,
    horizon: int,
    runner: Module38Runner,
    context: pd.DataFrame,
    relative: pd.DataFrame,
    asset: str,
    v2_dates: set[str],
    v3_final_dates: set[str],
) -> list[int]:
    contract = HORIZON_CONTRACTS[horizon]
    candidate_frame = features.dropna(subset=["target_return"]).reset_index(drop=False).rename(columns={"index": "_original_index"})
    candidates = exact_candidates(
        candidate_frame,
        horizon,
        int(runner.cfg.get("absolute_minimum_training_rows", 90)),
        int(runner.cfg.get("minimum_validation_rows", 30)),
        int(runner.cfg["validation_rows"]),
        float(runner.cfg.get("maximum_validation_share", 0.25)),
    )
    excluded = set(v2_dates) | set(v3_final_dates)
    selection_columns = sorted({
        column
        for family in contract["families"]
        for column in family_columns(family, contract)
    })
    minimum_training_rows = int(runner.cfg.get("absolute_minimum_training_rows", 90))
    minimum_validation_rows = int(runner.cfg.get("minimum_validation_rows", 30))
    safe_indices: list[int] = []

    for candidate_pos in candidates:
        original_idx = int(candidate_frame.iloc[candidate_pos]["_original_index"])
        date_key = pd.Timestamp(features.iloc[original_idx]["observation_date"]).date().isoformat()
        if date_key in excluded:
            continue
        try:
            _, train_probe, validation_probe, current_probe = split_origin(
                features, original_idx, horizon, runner, excluded
            )
        except RuntimeError:
            continue
        train_probe = attach_lagged_native(train_probe, context, contract["native"])
        validation_probe = attach_lagged_native(validation_probe, context, contract["native"])
        current_probe = attach_lagged_native(current_probe, context, contract["native"])
        train_probe = attach_relative(train_probe, relative, asset, contract["relative"])
        validation_probe = attach_relative(validation_probe, relative, asset, contract["relative"])
        current_probe = attach_relative(current_probe, relative, asset, contract["relative"])
        if current_probe[selection_columns].isna().any(axis=1).iloc[0]:
            continue
        if len(train_probe.dropna(subset=selection_columns + ["target_return"])) < minimum_training_rows:
            continue
        if len(validation_probe.dropna(subset=selection_columns + ["target_return"])) < minimum_validation_rows:
            continue
        safe_indices.append(original_idx)

    required = DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD
    require(len(safe_indices) >= required, f"Could not reconstruct V3 development origins for {asset} {horizon}d")
    positions = np.linspace(0, len(safe_indices) - 1, required, dtype=int)
    selected = [safe_indices[int(pos)] for pos in positions]
    require(len(selected) == required, f"Unexpected V3 selected-origin count for {asset} {horizon}d")
    require(len(set(selected)) == required, f"Duplicate reconstructed V3 development origin for {asset} {horizon}d")
    return selected


def fresh_capacity_for_group(
    features: pd.DataFrame,
    horizon: int,
    runner: Module38Runner,
    context: pd.DataFrame,
    relative: pd.DataFrame,
    asset: str,
    excluded_dates: set[str],
) -> tuple[list[int], list[int]]:
    contract = HORIZON_CONTRACTS[horizon]
    candidate_frame = features.dropna(subset=["target_return"]).reset_index(drop=False).rename(columns={"index": "_original_index"})
    candidates = exact_candidates(
        candidate_frame,
        horizon,
        int(runner.cfg.get("absolute_minimum_training_rows", 90)),
        int(runner.cfg.get("minimum_validation_rows", 30)),
        int(runner.cfg["validation_rows"]),
        float(runner.cfg.get("maximum_validation_share", 0.25)),
    )
    chronology_safe: list[int] = []
    v3_contract_feature_safe: list[int] = []
    selection_columns = sorted({
        column
        for family in contract["families"]
        for column in family_columns(family, contract)
    })
    minimum_training_rows = int(runner.cfg.get("absolute_minimum_training_rows", 90))
    minimum_validation_rows = int(runner.cfg.get("minimum_validation_rows", 30))

    for candidate_pos in candidates:
        original_idx = int(candidate_frame.iloc[candidate_pos]["_original_index"])
        date_key = pd.Timestamp(features.iloc[original_idx]["observation_date"]).date().isoformat()
        if date_key in excluded_dates:
            continue
        try:
            _, train_probe, validation_probe, current_probe = split_origin(
                features, original_idx, horizon, runner, excluded_dates
            )
        except RuntimeError:
            continue
        chronology_safe.append(original_idx)
        train_probe = attach_lagged_native(train_probe, context, contract["native"])
        validation_probe = attach_lagged_native(validation_probe, context, contract["native"])
        current_probe = attach_lagged_native(current_probe, context, contract["native"])
        train_probe = attach_relative(train_probe, relative, asset, contract["relative"])
        validation_probe = attach_relative(validation_probe, relative, asset, contract["relative"])
        current_probe = attach_relative(current_probe, relative, asset, contract["relative"])
        if current_probe[selection_columns].isna().any(axis=1).iloc[0]:
            continue
        if len(train_probe.dropna(subset=selection_columns + ["target_return"])) < minimum_training_rows:
            continue
        if len(validation_probe.dropna(subset=selection_columns + ["target_return"])) < minimum_validation_rows:
            continue
        v3_contract_feature_safe.append(original_idx)

    return chronology_safe, v3_contract_feature_safe


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
        require(path.is_file(), f"Required input missing: {path}")
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

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    report_rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="crypto_v4_capacity_") as tmp:
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
                    require(len(selected_v3_dates) == DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD, f"V3 development-date reconstruction mismatch for {asset} {horizon}d")
                    excluded = set(v2_dates[key]) | set(v3_final_dates[key]) | selected_v3_dates
                    chronology_safe, feature_safe = fresh_capacity_for_group(
                        features,
                        horizon,
                        runner,
                        context,
                        relative,
                        asset,
                        excluded,
                    )
                    required_total = V4_DEVELOPMENT_ORIGINS_PER_GROUP + V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP
                    report_rows.append({
                        "asset_id": asset,
                        "horizon_days": horizon,
                        "v2_consumed_origins": len(v2_dates[key]),
                        "v3_development_origins": len(selected_v3_dates),
                        "v3_final_holdout_origins": len(v3_final_dates[key]),
                        "fresh_chronology_safe_origins": len(chronology_safe),
                        "fresh_v3_contract_feature_safe_origins": len(feature_safe),
                        "required_for_v4_50_dev_plus_10_final": required_total,
                        "capacity_pass_under_v3_feature_contract": len(feature_safe) >= required_total,
                        "earliest_fresh_feature_safe_origin": (
                            pd.Timestamp(features.iloc[feature_safe[0]]["observation_date"]).date().isoformat()
                            if feature_safe else None
                        ),
                        "latest_fresh_feature_safe_origin": (
                            pd.Timestamp(features.iloc[feature_safe[-1]]["observation_date"]).date().isoformat()
                            if feature_safe else None
                        ),
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
    require(before == after, "Source evidence changed during V4 capacity audit")

    expected_groups = 17  # 6 assets x 7d + 6 assets x 30d + 5 assets x 365d; XRP365 unsupported.
    require(len(report_rows) == expected_groups, f"Expected {expected_groups} V4 supported groups, found {len(report_rows)}")
    failures = [row for row in report_rows if not row["capacity_pass_under_v3_feature_contract"]]
    min_capacity = min(int(row["fresh_v3_contract_feature_safe_origins"]) for row in report_rows)
    min_rows = [row for row in report_rows if int(row["fresh_v3_contract_feature_safe_origins"]) == min_capacity]

    report = {
        "status": "COMPLETE",
        "experiment_id": "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4",
        "recovery_horizons": list(V4_HORIZONS),
        "supported_groups": len(report_rows),
        "v4_development_origins_per_group_planning_assumption": V4_DEVELOPMENT_ORIGINS_PER_GROUP,
        "v4_final_holdout_origins_per_group_planning_assumption": V4_FINAL_HOLDOUT_ORIGINS_PER_GROUP,
        "capacity_failures_under_v3_feature_contract": len(failures),
        "minimum_fresh_v3_contract_feature_safe_capacity": min_capacity,
        "minimum_capacity_groups": min_rows,
        "groups": report_rows,
        "v3_final_holdout_outcomes_viewed": False,
        "source_database_modified": False,
        "next_gate": (
            "FREEZE_V4_HORIZON_SPECIFIC_CANDIDATE_AND_HOLDOUT_CONTRACTS"
            if not failures
            else "REVIEW_V4_CAPACITY_SHORTFALL_WITHOUT_VIEWING_ANY_FINAL_HOLDOUT"
        ),
    }
    print(json.dumps(report, indent=2))
    print("CRYPTO_V4_FRESH_EVIDENCE_CAPACITY_AUDIT=PASS")
    print(f"SUPPORTED_GROUPS={len(report_rows)}")
    print(f"CAPACITY_FAILURES_UNDER_V3_FEATURE_CONTRACT={len(failures)}")
    print(f"MINIMUM_FRESH_FEATURE_SAFE_CAPACITY={min_capacity}")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
