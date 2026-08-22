from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections import defaultdict
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    args = parser.parse_args()

    source = Path(args.database).resolve()
    v2_path = Path(args.v2_manifest).resolve()
    v3_path = Path(args.v3_manifest).resolve()
    require(source.is_file(), f"Database missing: {source}")
    require(v2_path.is_file(), f"V2 manifest missing: {v2_path}")
    require(v3_path.is_file(), f"V3 manifest missing: {v3_path}")

    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    v3 = json.loads(v3_path.read_text(encoding="utf-8"))
    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    failures: list[dict] = []
    counts = defaultdict(int)
    with tempfile.TemporaryDirectory(prefix="crypto_v3_split_feature_audit_") as tmp:
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
            native_features = sorted({f for c in HORIZON_CONTRACTS.values() for f in c["native"]})
            context = conn.execute(
                "SELECT observation_date," + ",".join(native_features) + " FROM crypto_features_daily ORDER BY observation_date"
            ).fetchdf() if native_features else pd.DataFrame({"observation_date": []})
            context["observation_date"] = pd.to_datetime(context["observation_date"])
            relative = build_relative_market(prices)
            relative["observation_date"] = pd.to_datetime(relative["observation_date"])

            for asset in ASSETS:
                asset_frame = prices[prices["asset_id"] == asset].copy()
                for horizon, contract in HORIZON_CONTRACTS.items():
                    key = (asset, horizon)
                    if key not in v3_dates:
                        continue
                    features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                    v3_mask = pd.to_datetime(features["observation_date"]).dt.date.astype(str).isin(v3_dates[key])
                    features.loc[v3_mask, "target_return"] = np.nan
                    candidate_frame = features.dropna(subset=["target_return"]).reset_index(drop=False).rename(columns={"index": "_original_index"})
                    candidates = exact_candidates(
                        candidate_frame,
                        horizon,
                        int(runner.cfg.get("absolute_minimum_training_rows", 90)),
                        int(runner.cfg.get("minimum_validation_rows", 30)),
                        int(runner.cfg["validation_rows"]),
                        float(runner.cfg.get("maximum_validation_share", 0.25)),
                    )
                    selection_columns = sorted({
                        column
                        for family in contract["families"]
                        for column in family_columns(family, contract)
                    })
                    safe_indices = []
                    for candidate_pos in candidates:
                        original_idx = int(candidate_frame.iloc[candidate_pos]["_original_index"])
                        date_key = pd.Timestamp(features.iloc[original_idx]["observation_date"]).date().isoformat()
                        if date_key in v2_dates[key] or date_key in v3_dates[key]:
                            continue
                        current_probe = features.iloc[[original_idx]].copy()
                        current_probe = attach_lagged_native(current_probe, context, contract["native"])
                        current_probe = attach_relative(current_probe, relative, asset, contract["relative"])
                        if current_probe[selection_columns].isna().any(axis=1).iloc[0]:
                            continue
                        safe_indices.append(original_idx)
                    required = DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD
                    require(len(safe_indices) >= required, f"Insufficient selected-origin capacity for {asset} {horizon}d")
                    positions = np.linspace(0, len(safe_indices) - 1, required, dtype=int)
                    selected = [safe_indices[int(pos)] for pos in positions]
                    excluded = set(v2_dates[key]) | set(v3_dates[key])

                    for origin_idx in selected:
                        origin_date, train, validation, current = split_origin(features, origin_idx, horizon, runner, excluded)
                        train = attach_lagged_native(train, context, contract["native"])
                        validation = attach_lagged_native(validation, context, contract["native"])
                        current = attach_lagged_native(current, context, contract["native"])
                        train = attach_relative(train, relative, asset, contract["relative"])
                        validation = attach_relative(validation, relative, asset, contract["relative"])
                        current = attach_relative(current, relative, asset, contract["relative"])
                        for family in contract["families"]:
                            columns = family_columns(family, contract)
                            train_complete = int(train.dropna(subset=columns + ["target_return"]).shape[0])
                            validation_complete = int(validation.dropna(subset=columns + ["target_return"]).shape[0])
                            current_complete = int(current.dropna(subset=columns).shape[0])
                            if train_complete < 90 or validation_complete < 30 or current_complete != 1:
                                counts[f"{asset}:{horizon}:{family}"] += 1
                                failures.append({
                                    "asset_id": asset,
                                    "horizon_days": horizon,
                                    "forecast_date": origin_date.date().isoformat(),
                                    "family": family,
                                    "train_complete_rows": train_complete,
                                    "validation_complete_rows": validation_complete,
                                    "current_complete_rows": current_complete,
                                })
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    report = {
        "status": "COMPLETE",
        "selected_origin_split_feature_failures": len(failures),
        "summary": dict(sorted(counts.items())),
        "first_failures": failures[:50],
        "v3_holdout_outcomes_viewed": False,
        "next_gate": "GOVERN_COMMON_SPLIT_FEATURE_ELIGIBLE_DEVELOPMENT_ORIGINS" if failures else "RERUN_V3_PER_HORIZON_DEVELOPMENT_TOURNAMENT",
    }
    print(json.dumps(report, indent=2))
    print("CRYPTO_V3_TOURNAMENT_SPLIT_FEATURE_ELIGIBILITY_AUDIT=PASS")
    print(f"SELECTED_ORIGIN_SPLIT_FEATURE_FAILURES={len(failures)}")
    print("V3_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
