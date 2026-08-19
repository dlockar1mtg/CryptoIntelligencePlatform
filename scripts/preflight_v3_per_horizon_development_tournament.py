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
    EXPERIMENT_ID,
    HORIZON_CONTRACTS,
    ORIGINS_PER_FOLD,
    EXPECTED_V3_MANIFEST_CONTENT_SHA256,
    attach_lagged_native,
    attach_relative,
    build_relative_market,
    family_columns,
    manifest_content_hash,
    model_list,
    sha256,
    split_origin,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def finite_frame(frame: pd.DataFrame, columns: list[str]) -> bool:
    values = frame[columns].astype(float).to_numpy()
    return bool(np.isfinite(values).all())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.database).resolve()
    v2_path = Path(args.v2_manifest).resolve()
    v3_path = Path(args.v3_manifest).resolve()
    output = Path(args.output).resolve()

    require(source.is_file(), f"Database missing: {source}")
    require(v2_path.is_file(), f"V2 manifest missing: {v2_path}")
    require(v3_path.is_file(), f"V3 manifest missing: {v3_path}")
    require(not output.exists(), f"Tournament output already exists: {output}")

    before_db = sha256(source)
    before_v2 = sha256(v2_path)
    before_v3 = sha256(v3_path)

    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    v3 = json.loads(v3_path.read_text(encoding="utf-8"))
    require(v3["experiment_id"] == EXPERIMENT_ID, "Unexpected V3 manifest experiment id")
    require(v3["holdout_outcomes_viewed_before_freeze"] is False, "V3 holdout was not pre-outcome frozen")
    require(v3["manifest_content_sha256"] == EXPECTED_V3_MANIFEST_CONTENT_SHA256, "Unexpected V3 manifest content hash")
    require(manifest_content_hash(v3) == EXPECTED_V3_MANIFEST_CONTENT_SHA256, "V3 manifest canonical hash mismatch")
    require(int(v3["supported_groups"]) == 29, "Expected 29 V3 supported groups")
    require(int(v3["rows_per_supported_group"]) == 10, "Expected 10 V3 holdout rows per group")

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}
    require(set(v2_dates) == set(v3_dates), "V2/V3 supported group mismatch")
    require(all(v2_dates[k].isdisjoint(v3_dates[k]) for k in v2_dates), "V2/V3 holdout overlap detected")

    selected_groups = 0
    selected_origins = 0
    family_preconditions_checked = 0
    model_constructors_checked = 0
    minimum_safe_origin_capacity = None
    per_group_capacity: dict[str, int] = {}

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_v3_preflight_") as tmp:
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

            from scripts.run_v3_per_horizon_development_tournament import NATIVE_LAG_DAYS
            context = conn.execute(
                "SELECT observation_date," + ",".join(NATIVE_LAG_DAYS) + " FROM crypto_features_daily ORDER BY observation_date"
            ).fetchdf()
            context["observation_date"] = pd.to_datetime(context["observation_date"])
            relative = build_relative_market(prices)
            relative["observation_date"] = pd.to_datetime(relative["observation_date"])

            random_state = int(runner.cfg["random_state"])
            required = DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD

            for horizon, contract in HORIZON_CONTRACTS.items():
                for family in contract["families"]:
                    constructors = model_list(family, random_state, horizon)
                    require(len(constructors) >= 1, f"No models constructed for {family} {horizon}d")
                    for model in constructors:
                        require(hasattr(model, "fit"), f"Model lacks fit: {type(model).__name__}")
                        require(hasattr(model, "predict_proba"), f"Model lacks predict_proba: {type(model).__name__}")
                        model_constructors_checked += 1

            for asset in ASSETS:
                asset_frame = prices[prices["asset_id"] == asset].copy()
                for horizon, contract in HORIZON_CONTRACTS.items():
                    key = (asset, horizon)
                    if key not in v3_dates:
                        continue

                    features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                    v3_mask = pd.to_datetime(features["observation_date"]).dt.date.astype(str).isin(v3_dates[key])
                    features.loc[v3_mask, "target_return"] = np.nan
                    require(int(features.loc[v3_mask, "target_return"].notna().sum()) == 0, f"V3 labels not masked for {asset} {horizon}d")

                    candidate_frame = features.dropna(subset=["target_return"]).reset_index(drop=False).rename(columns={"index": "_original_index"})
                    candidates = exact_candidates(
                        candidate_frame,
                        horizon,
                        int(runner.cfg.get("absolute_minimum_training_rows", 90)),
                        int(runner.cfg.get("minimum_validation_rows", 30)),
                        int(runner.cfg["validation_rows"]),
                        float(runner.cfg.get("maximum_validation_share", 0.25)),
                    )

                    excluded = set(v2_dates[key]) | set(v3_dates[key])
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

                    group_name = f"{asset}:{horizon}"
                    per_group_capacity[group_name] = len(safe_indices)
                    minimum_safe_origin_capacity = len(safe_indices) if minimum_safe_origin_capacity is None else min(minimum_safe_origin_capacity, len(safe_indices))
                    require(len(safe_indices) >= required, f"Insufficient safe development origins for {group_name}: {len(safe_indices)} < {required}")

                    positions = np.linspace(0, len(safe_indices) - 1, required, dtype=int)
                    selected = [safe_indices[int(pos)] for pos in positions]
                    require(len(selected) == required, f"Unexpected selected origin count for {group_name}")
                    require(len(set(selected)) == required, f"Duplicate selected origins for {group_name}")

                    for origin_idx in selected:
                        origin_date, train, validation, current = split_origin(features, origin_idx, horizon, runner, excluded)
                        date_key = origin_date.date().isoformat()
                        require(date_key not in excluded, f"Excluded holdout origin selected: {group_name} {date_key}")

                        train = attach_lagged_native(train, context, contract["native"])
                        validation = attach_lagged_native(validation, context, contract["native"])
                        current = attach_lagged_native(current, context, contract["native"])
                        train = attach_relative(train, relative, asset, contract["relative"])
                        validation = attach_relative(validation, relative, asset, contract["relative"])
                        current = attach_relative(current, relative, asset, contract["relative"])

                        require(np.isfinite(float(features.iloc[origin_idx]["target_return"])), f"Non-finite target at {group_name} {date_key}")

                        for family in contract["families"]:
                            columns = family_columns(family, contract)
                            t = train.dropna(subset=columns + ["target_return"]).copy()
                            v = validation.dropna(subset=columns + ["target_return"]).copy()
                            c = current.dropna(subset=columns).copy()
                            require(len(t) >= 90, f"Training precondition failed: {group_name} {date_key} {family} rows={len(t)}")
                            require(len(v) >= 30, f"Validation precondition failed: {group_name} {date_key} {family} rows={len(v)}")
                            require(len(c) == 1, f"Current precondition failed: {group_name} {date_key} {family}")
                            require(finite_frame(t, columns), f"Non-finite training matrix: {group_name} {date_key} {family}")
                            require(finite_frame(v, columns), f"Non-finite validation matrix: {group_name} {date_key} {family}")
                            require(finite_frame(c, columns), f"Non-finite current matrix: {group_name} {date_key} {family}")
                            y_train = (t["target_return"].to_numpy(dtype=float) > 0).astype(int)
                            require(len(y_train) >= 90, f"Unexpected y_train length: {group_name} {date_key} {family}")
                            family_preconditions_checked += 1

                    selected_groups += 1
                    selected_origins += len(selected)

            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    require(sha256(source) == before_db, "Source database changed during preflight")
    require(sha256(v2_path) == before_v2, "V2 manifest changed during preflight")
    require(sha256(v3_path) == before_v3, "V3 manifest changed during preflight")
    require(selected_groups == 29, f"Expected 29 supported groups, got {selected_groups}")
    require(selected_origins == 29 * DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD, f"Unexpected total selected origins: {selected_origins}")

    payload = {
        "status": "PASS",
        "supported_groups_checked": selected_groups,
        "selected_origins_checked": selected_origins,
        "family_origin_preconditions_checked": family_preconditions_checked,
        "model_constructors_checked": model_constructors_checked,
        "minimum_safe_origin_capacity": int(minimum_safe_origin_capacity or 0),
        "required_safe_origins_per_group": int(DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD),
        "v2_holdout_excluded": True,
        "v3_holdout_excluded": True,
        "v3_holdout_outcomes_viewed": False,
        "finite_feature_matrices": True,
        "source_database_unchanged": True,
        "manifests_unchanged": True,
        "output_absent_before_run": True,
        "note": "This preflight exhaustively validates tournament selection/split/data/model-constructor preconditions without fitting the expensive tournament models. It materially reduces runtime-failure risk but cannot mathematically guarantee that every estimator fit will succeed on the local sklearn runtime.",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    print("CRYPTO_V3_DEVELOPMENT_TOURNAMENT_PREFLIGHT=PASS")
    print(f"SUPPORTED_GROUPS_CHECKED={selected_groups}")
    print(f"SELECTED_ORIGINS_CHECKED={selected_origins}")
    print(f"FAMILY_ORIGIN_PRECONDITIONS_CHECKED={family_preconditions_checked}")
    print(f"MODEL_CONSTRUCTORS_CHECKED={model_constructors_checked}")
    print(f"MINIMUM_SAFE_ORIGIN_CAPACITY={int(minimum_safe_origin_capacity or 0)}")
    print("V3_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=RUN_V3_PER_HORIZON_DEVELOPMENT_TOURNAMENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
