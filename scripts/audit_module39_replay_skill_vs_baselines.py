from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for path in (ROOT, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_module39_true_replay_rehearsal as base
import run_module39_true_replay_rehearsal_v2 as replay_v2
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


def fit_calibrator(train: pd.DataFrame, method: str):
    x = train[["raw_probability_positive"]].to_numpy(dtype=float)
    y = train["observed_positive"].astype(int).to_numpy()
    if method == "PLATT":
        model = LogisticRegression().fit(x, y)
        return lambda values: model.predict_proba(np.asarray(values, dtype=float).reshape(-1, 1))[:, 1]
    if method == "ISOTONIC":
        model = IsotonicRegression(out_of_bounds="clip").fit(x.ravel(), y)
        return lambda values: model.predict(np.asarray(values, dtype=float))
    raise RuntimeError(f"Unsupported calibrator: {method}")


def leakage_safe_calibration(rows: pd.DataFrame) -> dict:
    rows = rows.sort_values("forecast_date").reset_index(drop=True)
    require(len(rows) == 30, f"Expected 30 replay rows, found {len(rows)}")
    development = rows.iloc[:20].copy()
    final_test = rows.iloc[20:].copy()
    inner_train = development.iloc[:15].copy()
    inner_validation = development.iloc[15:].copy()

    raw_final = base.clip_probability(final_test["raw_probability_positive"].to_numpy())
    observed_final = final_test["observed_positive"].astype(int).to_numpy()
    raw_brier = float(brier_score_loss(observed_final, raw_final))
    raw_ll = float(log_loss(observed_final, raw_final, labels=[0, 1]))

    candidate_scores = []
    if (
        inner_train["observed_positive"].nunique() >= 2
        and inner_train["raw_probability_positive"].nunique() >= 2
    ):
        for method in ("PLATT", "ISOTONIC"):
            predict = fit_calibrator(inner_train, method)
            probs = base.clip_probability(
                predict(inner_validation["raw_probability_positive"].to_numpy())
            )
            score = float(
                brier_score_loss(
                    inner_validation["observed_positive"].astype(int).to_numpy(),
                    probs,
                )
            )
            candidate_scores.append((method, score))

    if candidate_scores:
        selected_method = min(candidate_scores, key=lambda item: item[1])[0]
        if (
            development["observed_positive"].nunique() >= 2
            and development["raw_probability_positive"].nunique() >= 2
        ):
            predict = fit_calibrator(development, selected_method)
            calibrated_final = base.clip_probability(
                predict(final_test["raw_probability_positive"].to_numpy())
            )
        else:
            selected_method = "BETA_SHRINKAGE"
            positives = int(development["observed_positive"].sum())
            calibrated_final = np.repeat((positives + 1) / (len(development) + 2), len(final_test))
    else:
        selected_method = "BETA_SHRINKAGE"
        positives = int(development["observed_positive"].sum())
        calibrated_final = np.repeat((positives + 1) / (len(development) + 2), len(final_test))

    calibrated_final = base.clip_probability(calibrated_final)
    calibrated_brier = float(brier_score_loss(observed_final, calibrated_final))
    calibrated_ll = float(log_loss(observed_final, calibrated_final, labels=[0, 1]))
    return {
        "selected_method_without_test_peeking": selected_method,
        "development_rows": 20,
        "inner_train_rows": 15,
        "inner_validation_rows": 5,
        "final_test_rows": 10,
        "raw_brier_score": raw_brier,
        "calibrated_brier_score": calibrated_brier,
        "raw_log_loss": raw_ll,
        "calibrated_log_loss": calibrated_ll,
        "calibration_improved_brier": bool(calibrated_brier < raw_brier),
    }


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
    unavailable: list[dict] = []
    calibration: list[dict] = []

    for asset in ASSETS:
        asset_frame = prices[prices.asset_id == asset].copy()
        for horizon in horizons:
            features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
            candidates = replay_v2.exact_candidates(
                features=features,
                horizon=horizon,
                minimum_training_rows=minimum_training_rows,
                minimum_validation_rows=minimum_validation_rows,
                configured_validation=configured_validation,
                maximum_validation_share=maximum_validation_share,
            )
            if len(candidates) < required_candidates:
                unavailable.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "exact_replay_candidates": len(candidates),
                    "required_replay_candidates": required_candidates,
                    "evidence_gap": "INSUFFICIENT_POINT_IN_TIME_REPLAY_HISTORY",
                })
                continue

            groups = replay_v2.select_groups(candidates, folds)
            group_rows: list[dict] = []
            for fold_number, indices in enumerate(groups, start=1):
                for idx in indices:
                    row = base.point_in_time_prediction(runner, features, idx, horizon)
                    row.update({
                        "asset_id": asset,
                        "horizon_days": horizon,
                        "fold_number": fold_number,
                    })
                    all_rows.append(row)
                    group_rows.append(row)

            cal = leakage_safe_calibration(pd.DataFrame(group_rows))
            cal.update({"asset_id": asset, "horizon_days": horizon})
            calibration.append(cal)

    frame = pd.DataFrame(all_rows)
    require(not frame.empty, "No replay rows produced")
    after = sha256(db)
    require(before == after, "Source database changed during skill audit")

    horizon_results = []
    for horizon, group in frame.groupby("horizon_days"):
        actual_positive = group["observed_positive"].astype(int)
        model_correct = (
            np.sign(group["predicted_return_pct"])
            == np.sign(group["actual_return_pct"])
        )
        positive_rate = float(actual_positive.mean() * 100)
        always_positive_accuracy = positive_rate
        always_negative_accuracy = 100.0 - positive_rate
        majority_accuracy = max(always_positive_accuracy, always_negative_accuracy)
        model_accuracy = float(model_correct.mean() * 100)
        horizon_results.append({
            "horizon_days": int(horizon),
            "replay_rows": int(len(group)),
            "asset_groups": int(group["asset_id"].nunique()),
            "observed_positive_rate_pct": positive_rate,
            "always_positive_directional_accuracy_pct": always_positive_accuracy,
            "always_negative_directional_accuracy_pct": always_negative_accuracy,
            "majority_class_directional_accuracy_pct": majority_accuracy,
            "model_directional_accuracy_pct": model_accuracy,
            "model_minus_majority_accuracy_pct_points": model_accuracy - majority_accuracy,
            "model_mae_pct": float(
                (group["actual_return_pct"] - group["predicted_return_pct"]).abs().mean()
            ),
            "raw_brier_score": float(
                brier_score_loss(
                    actual_positive,
                    base.clip_probability(group["raw_probability_positive"]),
                )
            ),
        })

    cal_frame = pd.DataFrame(calibration)
    calibration_summary = {
        "groups_evaluated": int(len(cal_frame)),
        "groups_with_brier_improvement": int(cal_frame["calibration_improved_brier"].sum()),
        "mean_raw_brier": float(cal_frame["raw_brier_score"].mean()),
        "mean_leakage_safe_calibrated_brier": float(cal_frame["calibrated_brier_score"].mean()),
        "mean_raw_log_loss": float(cal_frame["raw_log_loss"].mean()),
        "mean_leakage_safe_calibrated_log_loss": float(cal_frame["calibrated_log_loss"].mean()),
    }

    payload = {
        "status": "CRYPTO_MODULE39_REPLAY_SKILL_VS_BASELINES_AUDIT_COMPLETE",
        "source_commit": args.source_commit,
        "source_database_unchanged": True,
        "replay_rows": int(len(frame)),
        "supported_asset_horizon_groups": int(frame.groupby(["asset_id", "horizon_days"]).ngroups),
        "unavailable_groups": unavailable,
        "directional_skill_vs_naive_baselines": horizon_results,
        "leakage_safe_calibration_summary": calibration_summary,
        "leakage_safe_calibration_by_group": calibration,
        "interpretation_guard": (
            "The prior rehearsal selected PLATT versus ISOTONIC using final-test Brier and therefore its "
            "calibration holdout was not independent. This audit selects the calibration method only on an "
            "inner development split and reserves the final 10 rows for evaluation. Directional skill is also "
            "compared with trivial majority-sign baselines so bullish outcome prevalence cannot be mistaken for skill."
        ),
        "next_gate": "DECIDE_MODULE39_REMEDIATION_AND_MODEL_SKILL_STATUS_FROM_LEAKAGE_SAFE_BASELINE_ADJUSTED_EVIDENCE",
    }
    print(json.dumps(payload, indent=2))
    print("CRYPTO_MODULE39_REPLAY_SKILL_VS_BASELINES_AUDIT=COMPLETE")
    print(f"REPLAY_ROWS={len(frame)}")
    print(f"SUPPORTED_GROUPS={payload['supported_asset_horizon_groups']}")
    print(f"UNAVAILABLE_GROUPS={len(unavailable)}")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=DECIDE_MODULE39_REMEDIATION_AND_MODEL_SKILL_STATUS_FROM_LEAKAGE_SAFE_BASELINE_ADJUSTED_EVIDENCE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
