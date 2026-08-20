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
    EXPERIMENT_ID,
    NATIVE_LAG_DAYS,
    RECOVERY_HORIZONS,
    attach_lagged_native,
    attach_relative,
    build_price_features,
    build_relative_market,
    candidate_features,
)

EXPECTED_V3_RESULTS_SHA256 = "33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1"
EXPECTED_SUPERSEDED_V4_FILE_SHA256 = "dcaf32dccb8ab1031f7a6bea884e676deb0732466dc73a499d75e7d792f61b57"
DEVELOPMENT_ORIGINS = 50
STANDARD_HOLDOUT_ORIGINS = 10
AVALANCHE365_HOLDOUT_ORIGINS = 9


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


def exact_target_date_available(price_dates: set[str], origin_date: str, horizon: int) -> bool:
    endpoint = (pd.Timestamp(origin_date) + pd.to_timedelta(int(horizon), unit="D")).date().isoformat()
    return endpoint in price_dates


def deterministic_spaced(values: list[str], count: int) -> list[str]:
    require(len(values) >= count, "Insufficient values for deterministic spacing")
    positions = np.linspace(0, len(values) - 1, count, dtype=int)
    selected = [values[int(position)] for position in positions]
    require(len(selected) == count and len(set(selected)) == count, "Deterministic spacing produced duplicates")
    return selected


def enrich(frame: pd.DataFrame, context: pd.DataFrame, relative: pd.DataFrame, asset: str, horizon: int, family: str):
    columns = candidate_features(horizon, family)
    out = attach_lagged_native(frame, context, columns)
    out = attach_relative(out, relative, asset, columns)
    return out, columns


def choose_allocation(holdout_safe: list[str], development_safe: list[str], holdout_count: int) -> tuple[list[str], list[str]]:
    holdout_safe = sorted(set(holdout_safe))
    development_safe = sorted(set(development_safe))
    for start in range(len(holdout_safe) - holdout_count, -1, -1):
        holdout = holdout_safe[start : start + holdout_count]
        if len(holdout) != holdout_count:
            continue
        cutoff = holdout[0]
        prior_dev = [date for date in development_safe if date < cutoff]
        if len(prior_dev) >= DEVELOPMENT_ORIGINS:
            return deterministic_spaced(prior_dev, DEVELOPMENT_ORIGINS), holdout
    raise RuntimeError(f"No chronological {DEVELOPMENT_ORIGINS}+{holdout_count} allocation exists")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--v3-results", required=True)
    parser.add_argument("--superseded-v4-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    paths = {
        "database": Path(args.database).resolve(),
        "v2": Path(args.v2_manifest).resolve(),
        "v3": Path(args.v3_manifest).resolve(),
        "v3_results": Path(args.v3_results).resolve(),
        "superseded_v4": Path(args.superseded_v4_manifest).resolve(),
    }
    output = Path(args.output).resolve()
    for path in paths.values():
        require(path.is_file(), f"Required input missing: {path}")
    require(not output.exists(), f"Corrected V4 manifest already exists: {output}")
    require(sha256(paths["v3_results"]) == EXPECTED_V3_RESULTS_SHA256, "Unexpected preserved V3 results hash")
    require(sha256(paths["superseded_v4"]) == EXPECTED_SUPERSEDED_V4_FILE_SHA256, "Unexpected superseded V4 manifest hash")

    before = {name: sha256(path) for name, path in paths.items()}
    v2 = json.loads(paths["v2"].read_text(encoding="utf-8"))
    v3 = json.loads(paths["v3"].read_text(encoding="utf-8"))
    v3_results = json.loads(paths["v3_results"].read_text(encoding="utf-8"))
    old_v4 = json.loads(paths["superseded_v4"].read_text(encoding="utf-8"))
    require(v3_results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout was viewed")
    require(old_v4.get("holdout_outcomes_viewed_before_freeze") is False, "Superseded V4 manifest says holdout was viewed before freeze")

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}

    groups = []
    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_v4_rebuild_") as tmp:
        temp_db = Path(tmp) / paths["database"].name
        shutil.copy2(paths["database"], temp_db)
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
            relative = build_relative_market(prices)
            relative["observation_date"] = pd.to_datetime(relative["observation_date"])
            v3_relative = build_v3_relative_market(prices)
            v3_relative["observation_date"] = pd.to_datetime(v3_relative["observation_date"])

            supported = [(asset, horizon) for horizon in RECOVERY_HORIZONS for asset in ASSETS if not (asset == "xrp" and horizon == 365)]
            for asset, horizon in supported:
                key = (asset, horizon)
                asset_frame = prices[prices["asset_id"] == asset].copy()
                price_dates = set(pd.to_datetime(asset_frame["observation_date"]).dt.date.astype(str))

                v3_features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                v3_mask = pd.to_datetime(v3_features["observation_date"]).dt.date.astype(str).isin(v3_dates[key])
                v3_features.loc[v3_mask, "target_return"] = np.nan
                v3_indices = selected_v3_origins_for_group(
                    v3_features, horizon, runner, context, v3_relative, asset, v2_dates[key], v3_dates[key]
                )
                v3_dev_dates = {
                    pd.Timestamp(v3_features.iloc[index]["observation_date"]).date().isoformat()
                    for index in v3_indices
                }
                prior_excluded = set(v2_dates[key]) | set(v3_dates[key]) | v3_dev_dates

                features = build_price_features(asset_frame, horizon).reset_index(drop=True)
                date_to_index = {
                    pd.Timestamp(row.observation_date).date().isoformat(): int(row.Index)
                    for row in features[["observation_date"]].itertuples(index=True)
                }
                holdout_safe = []
                development_safe = []

                for date_key, origin_idx in date_to_index.items():
                    if date_key in prior_excluded or not exact_target_date_available(price_dates, date_key, horizon):
                        continue
                    current = features.iloc[[origin_idx]].copy()
                    current_ok = True
                    for family in CANDIDATE_CONTRACTS[horizon]["families"]:
                        current_f, columns = enrich(current, context, relative, asset, horizon, family)
                        if len(current_f.dropna(subset=columns)) != 1:
                            current_ok = False
                            break
                    if not current_ok:
                        continue
                    holdout_safe.append(date_key)

                    try:
                        _, train, validation, _ = v4_split_origin(features, origin_idx, horizon, runner, prior_excluded)
                    except RuntimeError:
                        continue
                    development_ok = True
                    for family in CANDIDATE_CONTRACTS[horizon]["families"]:
                        train_f, columns = enrich(train, context, relative, asset, horizon, family)
                        validation_f, _ = enrich(validation, context, relative, asset, horizon, family)
                        if len(train_f.dropna(subset=columns + ["target_return"])) < 90:
                            development_ok = False
                            break
                        if len(validation_f.dropna(subset=columns + ["target_return"])) < 30:
                            development_ok = False
                            break
                    if development_ok:
                        development_safe.append(date_key)

                holdout_count = AVALANCHE365_HOLDOUT_ORIGINS if key == ("avalanche", 365) else STANDARD_HOLDOUT_ORIGINS
                development_dates, holdout_dates = choose_allocation(holdout_safe, development_safe, holdout_count)
                require(max(development_dates) < min(holdout_dates), f"Final holdout is not strictly later than development for {asset} {horizon}d")
                require(set(development_dates).isdisjoint(holdout_dates), f"Development/final overlap for {asset} {horizon}d")
                require(set(development_dates).isdisjoint(prior_excluded), f"Development overlaps prior evidence for {asset} {horizon}d")
                require(set(holdout_dates).isdisjoint(prior_excluded), f"Final holdout overlaps prior evidence for {asset} {horizon}d")

                groups.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "v4_development_origin_dates": development_dates,
                    "v4_final_holdout_origin_dates": holdout_dates,
                    "development_origin_count": len(development_dates),
                    "final_holdout_origin_count": len(holdout_dates),
                    "allocation_exception": "AVALANCHE365_FINAL_HOLDOUT_9" if key == ("avalanche", 365) else None,
                })
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    require(len(groups) == 17, f"Expected 17 supported groups, found {len(groups)}")
    after = {name: sha256(path) for name, path in paths.items()}
    require(before == after, "Source evidence changed during V4 membership rebuild")

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "manifest_revision": 2,
        "evidence_class": "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME",
        "recovery_horizons": list(RECOVERY_HORIZONS),
        "supported_groups": 17,
        "standard_development_origins_per_group": DEVELOPMENT_ORIGINS,
        "standard_final_holdout_origins_per_group": STANDARD_HOLDOUT_ORIGINS,
        "avalanche365_final_holdout_origins": AVALANCHE365_HOLDOUT_ORIGINS,
        "avalanche365_exception_governed": True,
        "supersedes_manifest_file_sha256": EXPECTED_SUPERSEDED_V4_FILE_SHA256,
        "v2_consumed_origins_excluded": True,
        "v3_development_origins_excluded": True,
        "v3_final_holdout_origins_excluded": True,
        "v3_final_holdout_reused": False,
        "exact_calendar_target_availability_required": True,
        "strict_final_holdout_after_development_required": True,
        "holdout_outcomes_viewed_before_freeze": False,
        "holdout_outcome_values_read_during_rebuild": False,
        "holdout_outcome_signs_read_during_rebuild": False,
        "holdout_outcome_magnitudes_read_during_rebuild": False,
        "groups": sorted(groups, key=lambda row: (int(row["horizon_days"]), str(row["asset_id"]))),
    }
    payload["manifest_content_sha256"] = canonical_hash(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("CRYPTO_V4_CORRECTED_MEMBERSHIP_REBUILD=PASS")
    print("SUPPORTED_GROUPS=17")
    print("STANDARD_DEVELOPMENT_ORIGINS_PER_GROUP=50")
    print("STANDARD_FINAL_HOLDOUT_ORIGINS_PER_GROUP=10")
    print("AVALANCHE365_DEVELOPMENT_ORIGINS=50")
    print("AVALANCHE365_FINAL_HOLDOUT_ORIGINS=9")
    print("STRICT_FINAL_HOLDOUT_AFTER_DEVELOPMENT=TRUE")
    print("EXACT_CALENDAR_TARGET_AVAILABILITY_REQUIRED=TRUE")
    print("HOLDOUT_OUTCOME_VALUES_READ=FALSE")
    print("HOLDOUT_OUTCOME_SIGNS_READ=FALSE")
    print("HOLDOUT_OUTCOME_MAGNITUDES_READ=FALSE")
    print(f"MANIFEST_CONTENT_SHA256={payload['manifest_content_sha256']}")
    print("SOURCE_EVIDENCE_MODIFIED=FALSE")
    print("NEXT_GATE=VALIDATE_AND_PRESERVE_CORRECTED_V4_MEMBERSHIP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
