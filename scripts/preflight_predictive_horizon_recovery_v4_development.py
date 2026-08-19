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
from crypto_platform.module39_validation import split_capacity
from scripts.audit_predictive_horizon_recovery_v4_fresh_evidence_capacity import selected_v3_origins_for_group
from scripts.run_v3_per_horizon_development_tournament import build_relative_market as build_v3_relative_market
from scripts.v4_horizon_recovery_model_spec import (
    CANDIDATE_CONTRACTS,
    EXPERIMENT_ID,
    NATIVE_LAG_DAYS,
    RECOVERY_HORIZONS,
    all_candidate_families,
    attach_lagged_native,
    attach_relative,
    build_price_features,
    build_relative_market,
    candidate_features,
    model_list,
)

EXPECTED_V3_RESULTS_SHA256 = "33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1"
EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "4b42d66a6cea1949b956fc5fe57545cb21abfe6b8cdddb0fe7f933b75734ca02"
EXPECTED_V4_GROUPS = 17
EXPECTED_DEVELOPMENT_ORIGINS = 50
EXPECTED_FINAL_HOLDOUT_ORIGINS = 10


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_content_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("manifest_content_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def v4_split_origin(features: pd.DataFrame, origin_idx: int, horizon: int, runner: Module38Runner, excluded_dates: set[str]):
    origin_date = pd.Timestamp(features.iloc[origin_idx]["observation_date"])
    dates = pd.to_datetime(features["observation_date"])
    target_matured = dates + pd.to_timedelta(int(horizon), unit="D") <= origin_date
    excluded_mask = dates.dt.date.astype(str).isin(excluded_dates)
    available = features.loc[target_matured & ~excluded_mask].dropna(subset=["target_return"]).copy()
    cfg = runner.cfg
    validation_rows, train_end = split_capacity(
        usable_rows=len(available),
        horizon=int(horizon),
        minimum_training_rows=int(cfg.get("absolute_minimum_training_rows", 90)),
        minimum_validation_rows=int(cfg.get("minimum_validation_rows", 30)),
        configured_validation=int(cfg["validation_rows"]),
        maximum_validation_share=float(cfg.get("maximum_validation_share", 0.25)),
    )
    require(validation_rows >= int(cfg.get("minimum_validation_rows", 30)), "Unsafe V4 internal validation split")
    require(train_end >= int(cfg.get("absolute_minimum_training_rows", 90)), "Unsafe V4 purged training split")
    validation_start = len(available) - validation_rows
    train = available.iloc[:train_end].copy()
    validation = available.iloc[validation_start:].copy()
    current = features.iloc[[origin_idx]].copy()
    require(pd.Timestamp(train["observation_date"].iloc[-1]) < origin_date, "V4 chronology violation")
    return origin_date, train, validation, current


def finite_matrix(frame: pd.DataFrame, columns: list[str]) -> bool:
    if frame.empty:
        return False
    values = frame[columns].astype(float).to_numpy()
    return bool(np.isfinite(values).all())


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
        require(path.is_file(), f"Required V4 preflight input missing: {path}")

    tracked = {"database": source, "v2": v2_path, "v3": v3_path, "v3_results": v3_results_path, "v4": v4_path}
    before = {name: sha256(path) for name, path in tracked.items()}
    require(before["v3_results"] == EXPECTED_V3_RESULTS_SHA256, "Unexpected preserved V3 development-results hash")

    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    v3 = json.loads(v3_path.read_text(encoding="utf-8"))
    v3_results = json.loads(v3_results_path.read_text(encoding="utf-8"))
    v4 = json.loads(v4_path.read_text(encoding="utf-8"))
    require(v3_results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout has been viewed")
    require(v4.get("experiment_id") == EXPERIMENT_ID, "Unexpected V4 experiment id")
    require(v4.get("holdout_outcomes_viewed_before_freeze") is False, "V4 holdout was not frozen before outcomes")
    require(v4.get("v3_final_holdout_reused") is False, "V3 final holdout was reused by V4")
    require(v4.get("manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Unexpected V4 manifest content hash")
    require(manifest_content_hash(v4) == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "V4 manifest canonical content hash mismatch")
    require(int(v4.get("supported_groups", 0)) == EXPECTED_V4_GROUPS, "Unexpected V4 supported-group count")

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_final_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}
    v4_groups = {(g["asset_id"], int(g["horizon_days"])): g for g in v4["groups"]}
    require(len(v4_groups) == EXPECTED_V4_GROUPS, "V4 manifest group duplication detected")
    supported_expected = {(asset, horizon) for asset in ASSETS for horizon in RECOVERY_HORIZONS if not (asset == "xrp" and horizon == 365)}
    require(set(v4_groups) == supported_expected, "Unexpected V4 supported group set")

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    selected_origins_checked = 0
    family_origin_preconditions_checked = 0
    model_constructors_checked = 0
    min_complete_train = None
    min_complete_validation = None
    failures: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="crypto_v4_preflight_") as tmp:
        temp_db = Path(tmp) / source.name
        shutil.copy2(source, temp_db)
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.platform import load_all, connect
            settings, _ = load_all()
            conn = connect(settings)
            runner = object.__new__(Module38Runner)
            runner.cfg = settings["module38"]
            random_state = int(runner.cfg["random_state"])
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

            for (asset, horizon), group in sorted(v4_groups.items(), key=lambda item: (item[0][1], item[0][0])):
                dev_dates = list(group["v4_development_origin_dates"])
                holdout_dates = list(group["v4_final_holdout_origin_dates"])
                require(len(dev_dates) == EXPECTED_DEVELOPMENT_ORIGINS, f"Unexpected V4 development-origin count for {asset} {horizon}d")
                require(len(holdout_dates) == EXPECTED_FINAL_HOLDOUT_ORIGINS, f"Unexpected V4 holdout-origin count for {asset} {horizon}d")
                require(len(set(dev_dates)) == len(dev_dates), f"Duplicate V4 development origin for {asset} {horizon}d")
                require(len(set(holdout_dates)) == len(holdout_dates), f"Duplicate V4 holdout origin for {asset} {horizon}d")
                require(set(dev_dates).isdisjoint(holdout_dates), f"V4 development/holdout overlap for {asset} {horizon}d")

                asset_frame = prices[prices["asset_id"] == asset].copy()
                v3_features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                v3_mask = pd.to_datetime(v3_features["observation_date"]).dt.date.astype(str).isin(v3_final_dates[(asset, horizon)])
                v3_features.loc[v3_mask, "target_return"] = np.nan
                selected_v3_indices = selected_v3_origins_for_group(
                    v3_features, horizon, runner, context, v3_relative, asset,
                    v2_dates[(asset, horizon)], v3_final_dates[(asset, horizon)],
                )
                selected_v3_dates = {pd.Timestamp(v3_features.iloc[index]["observation_date"]).date().isoformat() for index in selected_v3_indices}
                excluded = set(v2_dates[(asset, horizon)]) | set(v3_final_dates[(asset, horizon)]) | selected_v3_dates | set(holdout_dates)

                features = build_price_features(asset_frame, horizon).reset_index(drop=True)
                holdout_mask = pd.to_datetime(features["observation_date"]).dt.date.astype(str).isin(holdout_dates)
                features.loc[holdout_mask, ["target_return", "target_positive", "target_exceeds_15pct"]] = np.nan
                date_to_index = {
                    pd.Timestamp(row.observation_date).date().isoformat(): int(row.Index)
                    for row in features[["observation_date"]].itertuples(index=True)
                }

                for date_key in dev_dates:
                    require(date_key in date_to_index, f"V4 development origin missing from feature frame: {asset} {horizon}d {date_key}")
                    origin_idx = date_to_index[date_key]
                    origin_date, train, validation, current = v4_split_origin(features, origin_idx, horizon, runner, excluded)
                    require(origin_date.date().isoformat() == date_key, "V4 development-origin mapping mismatch")
                    require(np.isfinite(float(features.iloc[origin_idx]["target_return"])), f"V4 development target missing: {asset} {horizon}d {date_key}")
                    selected_origins_checked += 1

                    for family in CANDIDATE_CONTRACTS[horizon]["families"]:
                        columns = candidate_features(horizon, family)
                        train_f = attach_relative(attach_lagged_native(train, context, columns), v4_relative, asset, columns)
                        val_f = attach_relative(attach_lagged_native(validation, context, columns), v4_relative, asset, columns)
                        current_f = attach_relative(attach_lagged_native(current, context, columns), v4_relative, asset, columns)
                        train_complete = train_f.dropna(subset=columns + ["target_return"]).copy()
                        val_complete = val_f.dropna(subset=columns + ["target_return"]).copy()
                        current_complete = current_f.dropna(subset=columns).copy()
                        min_complete_train = len(train_complete) if min_complete_train is None else min(min_complete_train, len(train_complete))
                        min_complete_validation = len(val_complete) if min_complete_validation is None else min(min_complete_validation, len(val_complete))
                        family_origin_preconditions_checked += 1
                        if len(train_complete) < 90 or len(val_complete) < 30 or len(current_complete) != 1:
                            failures.append({
                                "asset_id": asset, "horizon_days": horizon, "forecast_date": date_key, "family": family,
                                "train_complete_rows": len(train_complete), "validation_complete_rows": len(val_complete),
                                "current_complete_rows": len(current_complete),
                            })
                            continue
                        require(finite_matrix(train_complete, columns), f"Non-finite V4 training matrix for {asset} {horizon}d {family}")
                        require(finite_matrix(val_complete, columns), f"Non-finite V4 validation matrix for {asset} {horizon}d {family}")
                        require(finite_matrix(current_complete, columns), f"Non-finite V4 current matrix for {asset} {horizon}d {family}")

            for horizon in RECOVERY_HORIZONS:
                for family, family_contract in CANDIDATE_CONTRACTS[horizon]["families"].items():
                    models = model_list(horizon, family, random_state)
                    require(models, f"No V4 estimators for {family}")
                    for model in models:
                        require(callable(getattr(model, "fit", None)), f"Estimator missing fit: {family}")
                        if family_contract["kind"] == "classifier":
                            require(callable(getattr(model, "predict_proba", None)), f"Classifier missing predict_proba: {family}")
                        else:
                            require(callable(getattr(model, "predict", None)), f"Regressor missing predict: {family}")
                        model_constructors_checked += 1
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    after = {name: sha256(path) for name, path in tracked.items()}
    require(before == after, "Source evidence changed during V4 development preflight")
    require(selected_origins_checked == EXPECTED_V4_GROUPS * EXPECTED_DEVELOPMENT_ORIGINS, "Unexpected V4 development-origin preflight count")
    require(family_origin_preconditions_checked == EXPECTED_V4_GROUPS * EXPECTED_DEVELOPMENT_ORIGINS * 3, "Unexpected V4 family-origin precondition count")

    report = {
        "status": "PASS" if not failures else "FAIL",
        "experiment_id": EXPERIMENT_ID,
        "supported_groups_checked": EXPECTED_V4_GROUPS,
        "selected_origins_checked": selected_origins_checked,
        "family_origin_preconditions_checked": family_origin_preconditions_checked,
        "candidate_families": all_candidate_families(),
        "model_constructors_checked": model_constructors_checked,
        "minimum_complete_training_rows": min_complete_train,
        "minimum_complete_validation_rows": min_complete_validation,
        "precondition_failures": len(failures),
        "first_failures": failures[:20],
        "date_based_target_endpoint_enforced": True,
        "v4_final_holdout_outcomes_viewed": False,
        "v3_final_holdout_outcomes_viewed": False,
        "source_database_modified": False,
        "next_gate": "BUILD_V4_DEVELOPMENT_SCORING_HARNESS" if not failures else "REMEDIATE_V4_PREFLIGHT_FAILURES_BEFORE_MODEL_FITTING",
    }
    print(json.dumps(report, indent=2))
    require(not failures, f"V4 development preflight found {len(failures)} family-origin failures")
    print("CRYPTO_V4_DEVELOPMENT_PREFLIGHT=PASS")
    print(f"SUPPORTED_GROUPS_CHECKED={EXPECTED_V4_GROUPS}")
    print(f"SELECTED_ORIGINS_CHECKED={selected_origins_checked}")
    print(f"FAMILY_ORIGIN_PRECONDITIONS_CHECKED={family_origin_preconditions_checked}")
    print(f"MODEL_CONSTRUCTORS_CHECKED={model_constructors_checked}")
    print(f"MINIMUM_COMPLETE_TRAINING_ROWS={min_complete_train}")
    print(f"MINIMUM_COMPLETE_VALIDATION_ROWS={min_complete_validation}")
    print("DATE_BASED_TARGET_ENDPOINT_ENFORCED=TRUE")
    print("V4_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=BUILD_V4_DEVELOPMENT_SCORING_HARNESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
