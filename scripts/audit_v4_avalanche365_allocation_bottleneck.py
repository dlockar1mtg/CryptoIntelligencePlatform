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

from crypto_platform.module38 import Module38Runner
from scripts.audit_predictive_horizon_recovery_v4_fresh_evidence_capacity import selected_v3_origins_for_group
from scripts.preflight_predictive_horizon_recovery_v4_development import v4_split_origin
from scripts.run_v3_per_horizon_development_tournament import build_relative_market as build_v3_relative_market
from scripts.v4_horizon_recovery_model_spec import (
    CANDIDATE_CONTRACTS,
    NATIVE_LAG_DAYS,
    attach_lagged_native,
    attach_relative,
    build_price_features,
    build_relative_market,
    candidate_features,
)

EXPECTED_V3_RESULTS_SHA256 = "33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1"
ASSET = "avalanche"
HORIZON = 365


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def exact_target_date_available(price_dates: set[str], origin_date: str) -> bool:
    target = (pd.Timestamp(origin_date) + pd.to_timedelta(HORIZON, unit="D")).date().isoformat()
    return target in price_dates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--v3-results", required=True)
    parser.add_argument("--v4-manifest", required=True)
    args = parser.parse_args()

    paths = {
        "database": Path(args.database).resolve(),
        "v2": Path(args.v2_manifest).resolve(),
        "v3": Path(args.v3_manifest).resolve(),
        "v3_results": Path(args.v3_results).resolve(),
        "v4": Path(args.v4_manifest).resolve(),
    }
    for path in paths.values():
        require(path.is_file(), f"Required input missing: {path}")
    before = {name: sha256(path) for name, path in paths.items()}
    require(before["v3_results"] == EXPECTED_V3_RESULTS_SHA256, "Unexpected V3 results hash")

    v2 = json.loads(paths["v2"].read_text(encoding="utf-8"))
    v3 = json.loads(paths["v3"].read_text(encoding="utf-8"))
    v3_results = json.loads(paths["v3_results"].read_text(encoding="utf-8"))
    v4 = json.loads(paths["v4"].read_text(encoding="utf-8"))
    require(v3_results.get("v3_final_holdout_outcomes_viewed") is False, "V3 holdout viewed")
    require(v4.get("holdout_outcomes_viewed_before_freeze") is False, "V4 holdout viewed before freeze")

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}
    key = (ASSET, HORIZON)

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_v4_avax365_bottleneck_") as tmp:
        temp_db = Path(tmp) / paths["database"].name
        shutil.copy2(paths["database"], temp_db)
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
            relative = build_relative_market(prices)
            relative["observation_date"] = pd.to_datetime(relative["observation_date"])
            v3_relative = build_v3_relative_market(prices)
            v3_relative["observation_date"] = pd.to_datetime(v3_relative["observation_date"])

            asset_frame = prices[prices["asset_id"] == ASSET].copy()
            price_dates = set(pd.to_datetime(asset_frame["observation_date"]).dt.date.astype(str))
            v3_features = runner.build_features(asset_frame, HORIZON).reset_index(drop=True)
            v3_mask = pd.to_datetime(v3_features["observation_date"]).dt.date.astype(str).isin(v3_dates[key])
            v3_features.loc[v3_mask, "target_return"] = float("nan")
            selected_v3_indices = selected_v3_origins_for_group(
                v3_features, HORIZON, runner, context, v3_relative, ASSET,
                v2_dates[key], v3_dates[key],
            )
            selected_v3_dates = {
                pd.Timestamp(v3_features.iloc[index]["observation_date"]).date().isoformat()
                for index in selected_v3_indices
            }
            excluded = set(v2_dates[key]) | set(v3_dates[key]) | selected_v3_dates

            features = build_price_features(asset_frame, HORIZON).reset_index(drop=True)
            date_to_index = {
                pd.Timestamp(row.observation_date).date().isoformat(): int(row.Index)
                for row in features[["observation_date"]].itertuples(index=True)
            }

            holdout_safe = []
            family_safe = {family: [] for family in CANDIDATE_CONTRACTS[HORIZON]["families"]}
            common_development_safe = []
            family_failure_counts = {family: {"current": 0, "split": 0, "train": 0, "validation": 0} for family in family_safe}

            for date_key, origin_idx in date_to_index.items():
                if date_key in excluded or not exact_target_date_available(price_dates, date_key):
                    continue
                current = features.iloc[[origin_idx]].copy()
                current_ok_all = True
                for family in family_safe:
                    cols = candidate_features(HORIZON, family)
                    current_f = attach_relative(attach_lagged_native(current, context, cols), relative, ASSET, cols)
                    if len(current_f.dropna(subset=cols)) != 1:
                        family_failure_counts[family]["current"] += 1
                        current_ok_all = False
                if current_ok_all:
                    holdout_safe.append(date_key)
                try:
                    _, train, validation, _ = v4_split_origin(features, origin_idx, HORIZON, runner, excluded)
                except RuntimeError:
                    for family in family_safe:
                        family_failure_counts[family]["split"] += 1
                    continue

                all_families_ok = True
                for family in family_safe:
                    cols = candidate_features(HORIZON, family)
                    train_f = attach_relative(attach_lagged_native(train, context, cols), relative, ASSET, cols)
                    val_f = attach_relative(attach_lagged_native(validation, context, cols), relative, ASSET, cols)
                    current_f = attach_relative(attach_lagged_native(current, context, cols), relative, ASSET, cols)
                    ok = True
                    if len(current_f.dropna(subset=cols)) != 1:
                        ok = False
                    train_rows = len(train_f.dropna(subset=cols + ["target_return"]))
                    val_rows = len(val_f.dropna(subset=cols + ["target_return"]))
                    if train_rows < 90:
                        family_failure_counts[family]["train"] += 1
                        ok = False
                    if val_rows < 30:
                        family_failure_counts[family]["validation"] += 1
                        ok = False
                    if ok:
                        family_safe[family].append(date_key)
                    else:
                        all_families_ok = False
                if all_families_ok:
                    common_development_safe.append(date_key)

            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    holdout_safe = sorted(set(holdout_safe))
    common_development_safe = sorted(set(common_development_safe))
    family_safe = {family: sorted(set(values)) for family, values in family_safe.items()}

    def summary(values: list[str]) -> dict:
        return {
            "count": len(values),
            "earliest": values[0] if values else None,
            "fiftieth": values[49] if len(values) >= 50 else None,
            "latest": values[-1] if values else None,
        }

    common = summary(common_development_safe)
    holdout = summary(holdout_safe)
    after_50th_common = 0
    if common["fiftieth"] is not None:
        after_50th_common = sum(1 for d in holdout_safe if d > common["fiftieth"])

    report = {
        "status": "PASS",
        "asset_id": ASSET,
        "horizon_days": HORIZON,
        "holdout_safe": holdout,
        "common_development_safe": common,
        "holdout_safe_dates_after_50th_common_development": after_50th_common,
        "family_development_safe": {family: summary(values) for family, values in family_safe.items()},
        "family_failure_counts": family_failure_counts,
        "holdout_outcome_values_read": False,
        "holdout_outcome_signs_read": False,
        "holdout_outcome_magnitudes_read": False,
        "source_database_modified": False,
        "next_gate": "GOVERN_AVALANCHE365_V4_EVIDENCE_ALLOCATION_BASED_ON_BOTTLENECK",
    }
    print(json.dumps(report, indent=2))
    print("CRYPTO_V4_AVALANCHE365_ALLOCATION_BOTTLENECK_AUDIT=PASS")
    print(f"COMMON_DEVELOPMENT_SAFE={common['count']}")
    print(f"COMMON_DEVELOPMENT_50TH={common['fiftieth']}")
    print(f"COMMON_DEVELOPMENT_LATEST={common['latest']}")
    print(f"HOLDOUT_SAFE={holdout['count']}")
    print(f"HOLDOUT_SAFE_AFTER_50TH_COMMON={after_50th_common}")
    for family, values in family_safe.items():
        s = summary(values)
        print(f"FAMILY={family}|SAFE={s['count']}|EARLIEST={s['earliest']}|50TH={s['fiftieth']}|LATEST={s['latest']}")
    print("HOLDOUT_OUTCOME_VALUES_READ=FALSE")
    print("HOLDOUT_OUTCOME_SIGNS_READ=FALSE")
    print("HOLDOUT_OUTCOME_MAGNITUDES_READ=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=GOVERN_AVALANCHE365_V4_EVIDENCE_ALLOCATION_BASED_ON_BOTTLENECK")

    after = {name: sha256(path) for name, path in paths.items()}
    require(before == after, "Source evidence changed during Avalanche365 bottleneck audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
