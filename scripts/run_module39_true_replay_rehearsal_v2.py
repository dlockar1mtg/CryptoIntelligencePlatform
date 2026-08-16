from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for path in (ROOT, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_module39_true_replay_rehearsal as base
from crypto_platform.module38 import Module38Runner, ASSETS
from crypto_platform.platform import load_all

EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def exact_candidates(
    features: pd.DataFrame,
    horizon: int,
    minimum_training_rows: int,
    minimum_validation_rows: int,
    configured_validation: int,
    maximum_validation_share: float,
) -> list[int]:
    dates = pd.to_datetime(features["observation_date"])
    candidates: list[int] = []
    for idx in range(len(features)):
        origin = dates.iloc[idx]
        due_mask = (
            dates + pd.to_timedelta(horizon, unit="D") <= origin
        ) & (dates < origin)
        usable_rows = int(due_mask.sum())
        adaptive_validation, train_end = base.split_capacity(
            usable_rows=usable_rows,
            horizon=horizon,
            minimum_training_rows=minimum_training_rows,
            minimum_validation_rows=minimum_validation_rows,
            configured_validation=configured_validation,
            maximum_validation_share=maximum_validation_share,
        )
        if (
            adaptive_validation >= minimum_validation_rows
            and train_end >= minimum_training_rows
        ):
            candidates.append(idx)
    return candidates


def select_groups(candidates: list[int], folds: int) -> list[list[int]]:
    required = folds * base.TEST_ORIGINS_PER_FOLD
    require(len(candidates) >= required, "Candidate selection called without sufficient evidence")
    positions = np.linspace(0, len(candidates) - 1, required, dtype=int)
    chosen = [candidates[int(pos)] for pos in positions]
    return [
        chosen[i * base.TEST_ORIGINS_PER_FOLD:(i + 1) * base.TEST_ORIGINS_PER_FOLD]
        for i in range(folds)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    require(args.source_commit == EXPECTED_SOURCE_COMMIT, "Unexpected certified source commit")

    db = Path(args.database).resolve()
    require(db.is_file(), f"Database missing: {db}")
    before = sha256(db)

    settings, _ = load_all()
    runner = object.__new__(Module38Runner)
    runner.cfg = settings["module38"]
    folds = int(settings["module39"]["rolling_folds"])
    minimum_training_rows = int(settings["module39"]["minimum_training_rows"])
    minimum_validation_rows = int(settings["module38"].get("minimum_validation_rows", 30))
    configured_validation = int(settings["module38"]["validation_rows"])
    maximum_validation_share = float(settings["module38"].get("maximum_validation_share", 0.25))
    horizons = [int(v) for v in settings["module38"]["horizons_days"]]
    required_candidates = folds * base.TEST_ORIGINS_PER_FOLD

    with duckdb.connect(str(db), read_only=True) as con:
        prices = con.execute(
            """
            SELECT asset_id, observation_date, price_usd, market_cap_usd, volume_24h_usd
            FROM canonical_market_daily
            WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
              AND price_usd IS NOT NULL
            ORDER BY observation_date, asset_id
            """
        ).fetchdf()

    prices["observation_date"] = pd.to_datetime(prices["observation_date"])
    all_rows: list[dict] = []
    fold_rows: list[dict] = []
    calibration_rows: list[dict] = []
    unavailable_groups: list[dict] = []
    capacity_rows: list[dict] = []

    for asset in ASSETS:
        asset_frame = prices[prices.asset_id == asset].copy()
        for horizon in horizons:
            features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
            candidates = exact_candidates(
                features=features,
                horizon=horizon,
                minimum_training_rows=minimum_training_rows,
                minimum_validation_rows=minimum_validation_rows,
                configured_validation=configured_validation,
                maximum_validation_share=maximum_validation_share,
            )
            capacity_record = {
                "asset_id": asset,
                "horizon_days": horizon,
                "feature_rows": int(len(features)),
                "exact_replay_candidates": int(len(candidates)),
                "required_replay_candidates": int(required_candidates),
                "replay_supported": bool(len(candidates) >= required_candidates),
            }
            capacity_rows.append(capacity_record)
            if len(candidates) < required_candidates:
                unavailable_groups.append({
                    **capacity_record,
                    "evidence_gap": "INSUFFICIENT_POINT_IN_TIME_REPLAY_HISTORY",
                    "predictive_skill_certified": False,
                })
                continue

            groups = select_groups(candidates, folds)
            group_predictions: list[dict] = []
            for fold_number, indices in enumerate(groups, start=1):
                fold_predictions = [
                    base.point_in_time_prediction(runner, features, idx, horizon)
                    for idx in indices
                ]
                frame = pd.DataFrame(fold_predictions)
                frame["asset_id"] = asset
                frame["horizon_days"] = horizon
                frame["fold_number"] = fold_number
                all_rows.extend(frame.to_dict("records"))
                group_predictions.extend(fold_predictions)

                errors = frame["actual_return_pct"] - frame["predicted_return_pct"]
                direction = float(
                    (
                        np.sign(frame["actual_return_pct"])
                        == np.sign(frame["predicted_return_pct"])
                    ).mean() * 100
                )
                brier = float(
                    brier_score_loss(
                        frame["observed_positive"],
                        base.clip_probability(frame["raw_probability_positive"]),
                    )
                )
                fold_rows.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "fold_number": fold_number,
                    "training_rows_min": int(frame["training_rows"].min()),
                    "training_rows_max": int(frame["training_rows"].max()),
                    "testing_rows": int(len(frame)),
                    "training_end_before_testing": True,
                    "testing_start_date": frame["forecast_date"].min(),
                    "testing_end_date": frame["forecast_date"].max(),
                    "mae_pct": float(errors.abs().mean()),
                    "rmse_pct": float(np.sqrt(np.mean(errors ** 2))),
                    "directional_accuracy_pct": direction,
                    "brier_score": brier,
                })

            calibration = base.calibration_holdout(pd.DataFrame(group_predictions))
            calibration.update({
                "asset_id": asset,
                "horizon_days": horizon,
                "replay_rows": len(group_predictions),
            })
            calibration_rows.append(calibration)

    all_frame = pd.DataFrame(all_rows)
    fold_frame = pd.DataFrame(fold_rows)
    cal_frame = pd.DataFrame(calibration_rows)
    after = sha256(db)
    require(before == after, "Source database changed during Module 39 replay rehearsal")
    require(not all_frame.empty, "No supported replay groups were produced")

    horizon_summary = []
    for horizon, group in all_frame.groupby("horizon_days"):
        errors = group["actual_return_pct"] - group["predicted_return_pct"]
        horizon_summary.append({
            "horizon_days": int(horizon),
            "replay_rows": int(len(group)),
            "asset_groups": int(group["asset_id"].nunique()),
            "mae_pct": float(errors.abs().mean()),
            "rmse_pct": float(np.sqrt(np.mean(errors ** 2))),
            "directional_accuracy_pct": float(
                (
                    np.sign(group["actual_return_pct"])
                    == np.sign(group["predicted_return_pct"])
                ).mean() * 100
            ),
            "raw_brier_score": float(
                brier_score_loss(
                    group["observed_positive"],
                    base.clip_probability(group["raw_probability_positive"]),
                )
            ),
        })

    payload = {
        "status": "CRYPTO_MODULE39_TRUE_REPLAY_REHEARSAL_COMPLETE",
        "source_commit": args.source_commit,
        "source_database_unchanged": True,
        "replay_rows": int(len(all_frame)),
        "asset_horizon_groups": int(all_frame.groupby(["asset_id", "horizon_days"]).ngroups),
        "configured_asset_horizon_groups": int(len(ASSETS) * len(horizons)),
        "unavailable_group_count": int(len(unavailable_groups)),
        "unavailable_groups": unavailable_groups,
        "capacity_by_group": capacity_rows,
        "fold_rows": int(len(fold_frame)),
        "folds_per_supported_group": folds,
        "test_origins_per_fold": base.TEST_ORIGINS_PER_FOLD,
        "directional_accuracy_by_horizon": horizon_summary,
        "fold_detail": fold_frame.to_dict("records"),
        "calibration_holdout": cal_frame.to_dict("records"),
        "interpretation_guard": "Unsupported groups remain explicit evidence gaps. No minimum was lowered and no unsupported horizon was synthesized or silently dropped.",
        "next_gate": "INTERPRET_TRUE_REPLAY_SKILL_AND_REMEDIATE_MODULE39_WITH_EXPLICIT_EVIDENCE_GAPS",
    }
    print(json.dumps(payload, indent=2))
    print("CRYPTO_MODULE39_TRUE_REPLAY_REHEARSAL=COMPLETE")
    print(f"REPLAY_ROWS={len(all_frame)}")
    print(f"ASSET_HORIZON_GROUPS={payload['asset_horizon_groups']}")
    print(f"UNAVAILABLE_GROUPS={len(unavailable_groups)}")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=INTERPRET_TRUE_REPLAY_SKILL_AND_REMEDIATE_MODULE39_WITH_EXPLICIT_EVIDENCE_GAPS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
