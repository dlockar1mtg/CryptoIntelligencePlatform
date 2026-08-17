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
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import ASSETS, Module38Runner
from crypto_platform.module39_validation import (
    TEST_ORIGINS_PER_FOLD,
    calibration_evidence,
    exact_candidates,
    select_groups,
    split_capacity,
)

EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_IMPROVEMENT_V1"
VARIANTS = (
    "CURRENT_M38_REGRESSION_ENSEMBLE",
    "DIRECTION_FIRST_TWO_STAGE",
    "HORIZON_SPECIFIC_FEATURE_WINDOWS",
    "ROBUST_RETURN_TARGET",
)

HORIZON_FEATURES = {
    7: ["return_1d", "return_7d", "return_30d", "volatility_30d", "distance_sma50"],
    30: ["return_7d", "return_30d", "return_90d", "volatility_30d", "volatility_90d", "distance_sma50", "distance_sma200"],
    90: ["return_30d", "return_90d", "volatility_30d", "volatility_90d", "distance_sma50", "distance_sma200"],
    180: ["return_30d", "return_90d", "volatility_90d", "distance_sma50", "distance_sma200"],
    365: ["return_90d", "volatility_90d", "distance_sma200"],
}

DEVELOPMENT_ORIGINS = 20
FINAL_TEST_ORIGINS = 10


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def feature_columns(frame: pd.DataFrame, horizon: int, variant: str) -> list[str]:
    available = [c for c in frame.columns if c not in {"observation_date", "target_return"}]
    if variant != "HORIZON_SPECIFIC_FEATURE_WINDOWS":
        return available
    chosen = [c for c in HORIZON_FEATURES[int(horizon)] if c in available]
    require(bool(chosen), f"No horizon-specific features available for {horizon}d")
    return chosen


def regression_prediction(runner, train, validation, current, columns, horizon, robust_target):
    train_x = train[columns].astype(float).copy()
    val_x = validation[columns].astype(float).copy()
    current_x = current[columns].astype(float).copy()
    lo = train_x.min(axis=0)
    hi = train_x.max(axis=0)
    val_x = val_x.clip(lower=lo, upper=hi, axis=1)
    current_x = current_x.clip(lower=lo, upper=hi, axis=1)

    scaler = StandardScaler()
    x_train = scaler.fit_transform(train_x)
    x_val = scaler.transform(val_x)
    x_current = scaler.transform(current_x)
    y_train = train["target_return"].to_numpy(dtype=float)
    y_val = validation["target_return"].to_numpy(dtype=float)
    if robust_target:
        q_lo, q_hi = np.quantile(y_train, [0.025, 0.975])
        y_fit = np.clip(y_train, q_lo, q_hi)
    else:
        y_fit = y_train

    predictions, residuals, weights = [], [], []
    for model in runner.model_suite(int(runner.cfg["random_state"]) + int(horizon)).values():
        model.fit(x_train, y_fit)
        val_pred = model.predict(x_val)
        current_pred = float(model.predict(x_current)[0])
        mae = float(np.mean(np.abs(y_val - val_pred)))
        weights.append(1.0 / max(mae, 1e-6))
        predictions.append(current_pred)
        residuals.extend((y_val - val_pred).tolist())

    w = np.asarray(weights, dtype=float)
    w /= w.sum()
    prediction = float(np.dot(w, np.asarray(predictions, dtype=float)))
    residual_array = np.asarray(residuals, dtype=float)
    raw_probability = float(np.mean(prediction + residual_array > 0))
    half_width = float(np.quantile(np.abs(residual_array), 0.90)) if len(residual_array) else 0.0
    return prediction, raw_probability, prediction - half_width, prediction + half_width


def direction_probability(train, validation, current, columns, horizon, random_state):
    train_x = train[columns].astype(float).copy()
    val_x = validation[columns].astype(float).copy()
    current_x = current[columns].astype(float).copy()
    lo = train_x.min(axis=0)
    hi = train_x.max(axis=0)
    val_x = val_x.clip(lower=lo, upper=hi, axis=1)
    current_x = current_x.clip(lower=lo, upper=hi, axis=1)

    scaler = StandardScaler()
    x_train = scaler.fit_transform(train_x)
    x_val = scaler.transform(val_x)
    x_current = scaler.transform(current_x)
    y_train = (train["target_return"].to_numpy(dtype=float) > 0).astype(int)
    y_val = (validation["target_return"].to_numpy(dtype=float) > 0).astype(int)
    if len(np.unique(y_train)) < 2:
        return float(y_train.mean())

    models = [
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=random_state + horizon),
        RandomForestClassifier(
            n_estimators=220,
            max_depth=6,
            min_samples_leaf=10,
            max_features=0.8,
            class_weight="balanced_subsample",
            random_state=random_state + horizon,
            n_jobs=-1,
        ),
    ]
    probabilities, weights = [], []
    for model in models:
        model.fit(x_train, y_train)
        val_p = model.predict_proba(x_val)[:, 1]
        current_p = float(model.predict_proba(x_current)[0, 1])
        brier = float(brier_score_loss(y_val, np.clip(val_p, 1e-4, 1 - 1e-4)))
        weights.append(1.0 / max(brier, 1e-6))
        probabilities.append(current_p)
    w = np.asarray(weights, dtype=float)
    w /= w.sum()
    return float(np.dot(w, np.asarray(probabilities, dtype=float)))


def origin_prediction(runner, features, origin_idx, horizon, variant):
    origin_date = pd.Timestamp(features.iloc[origin_idx]["observation_date"])
    dates = pd.to_datetime(features["observation_date"])
    due_mask = (dates + pd.to_timedelta(horizon, unit="D") <= origin_date) & (dates < origin_date)
    available = features.loc[due_mask].copy()

    cfg = runner.cfg
    minimum_training = int(cfg.get("absolute_minimum_training_rows", 90))
    minimum_validation = int(cfg.get("minimum_validation_rows", 30))
    validation_rows, train_end = split_capacity(
        usable_rows=len(available),
        horizon=horizon,
        minimum_training_rows=minimum_training,
        minimum_validation_rows=minimum_validation,
        configured_validation=int(cfg["validation_rows"]),
        maximum_validation_share=float(cfg.get("maximum_validation_share", 0.25)),
    )
    require(validation_rows >= minimum_validation and train_end >= minimum_training, "Unsafe replay split")
    validation_start = len(available) - validation_rows
    train = available.iloc[:train_end].copy()
    validation = available.iloc[validation_start:].copy()
    current = features.iloc[[origin_idx]].copy()
    require(pd.Timestamp(train["observation_date"].iloc[-1]) < origin_date, "Replay chronology violation")

    columns = feature_columns(train, horizon, variant)
    prediction, raw_probability, lower, upper = regression_prediction(
        runner, train, validation, current, columns, horizon,
        robust_target=(variant == "ROBUST_RETURN_TARGET"),
    )
    if variant == "DIRECTION_FIRST_TWO_STAGE":
        raw_probability = direction_probability(
            train, validation, current, columns, horizon, int(cfg["random_state"])
        )
        signed_prediction = abs(prediction) if raw_probability >= 0.5 else -abs(prediction)
        shift = signed_prediction - prediction
        prediction = signed_prediction
        lower += shift
        upper += shift

    actual = float(features.iloc[origin_idx]["target_return"])
    return {
        "forecast_date": origin_date.date(),
        "training_end_date": pd.Timestamp(train["observation_date"].iloc[-1]).date(),
        "predicted_return_pct": prediction * 100,
        "actual_return_pct": actual * 100,
        "raw_probability_positive": raw_probability,
        "observed_positive": int(actual > 0),
        "lower_return_pct": lower * 100,
        "upper_return_pct": upper * 100,
        "interval_covered": bool(lower <= actual <= upper),
    }


def group_test_frame(group: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    ordered = group.sort_values("origin_number").copy()
    require(len(ordered) == DEVELOPMENT_ORIGINS + FINAL_TEST_ORIGINS, "Expected 30 replay rows per supported group")
    development = ordered.iloc[:DEVELOPMENT_ORIGINS]
    test = ordered.iloc[DEVELOPMENT_ORIGINS:]
    development_majority = 1 if float(development["observed_positive"].mean()) >= 0.5 else 0
    return test, development_majority


def summarize_test_only(frame: pd.DataFrame) -> dict:
    test_parts = []
    majority_correct = []
    for _, group in frame.groupby(["asset_id", "horizon_days"], sort=True):
        test, development_majority = group_test_frame(group)
        test_parts.append(test)
        majority_correct.extend((test["observed_positive"].to_numpy(dtype=int) == development_majority).tolist())
    test_frame = pd.concat(test_parts, ignore_index=True)
    actual = test_frame["actual_return_pct"].to_numpy(dtype=float)
    predicted = test_frame["predicted_return_pct"].to_numpy(dtype=float)
    observed = test_frame["observed_positive"].to_numpy(dtype=int)
    raw_p = np.clip(test_frame["raw_probability_positive"].to_numpy(dtype=float), 1e-4, 1 - 1e-4)
    direction = float((np.sign(actual) == np.sign(predicted)).mean() * 100)
    majority_accuracy = float(np.mean(majority_correct) * 100)
    error = actual - predicted
    return {
        "evaluation_rows": int(len(test_frame)),
        "directional_accuracy_pct": direction,
        "development_majority_baseline_accuracy_pct": majority_accuracy,
        "model_minus_majority_accuracy_pct_points": direction - majority_accuracy,
        "raw_brier_score": float(brier_score_loss(observed, raw_p)),
        "mae_pct": float(np.mean(np.abs(error))),
        "rmse_pct": float(np.sqrt(np.mean(error ** 2))),
        "interval_coverage_pct": float(test_frame["interval_covered"].mean() * 100),
    }


def economic_metrics_test_only(frame: pd.DataFrame, cost_bps: float) -> dict:
    returns = []
    turnover = []
    for _, group in frame.groupby(["asset_id", "horizon_days"], sort=True):
        test, _ = group_test_frame(group)
        ordered = test.sort_values("forecast_date")
        position = np.sign(ordered["predicted_return_pct"].to_numpy(dtype=float))
        realized = ordered["actual_return_pct"].to_numpy(dtype=float) / 100.0
        changes = np.abs(np.diff(np.concatenate([[0.0], position])))
        net = position * realized - changes * (cost_bps / 10000.0)
        returns.extend(net.tolist())
        turnover.extend(changes.tolist())
    arr = np.asarray(returns, dtype=float)
    return {
        "mean_sign_strategy_return_after_fixed_transaction_cost_pct": float(arr.mean() * 100) if len(arr) else 0.0,
        "median_sign_strategy_return_after_fixed_transaction_cost_pct": float(np.median(arr) * 100) if len(arr) else 0.0,
        "turnover_units": float(np.sum(turnover)),
        "transaction_cost_bps": float(cost_bps),
        "note": "Secondary exploratory metric over isolated final-test forecast outcomes; not a portfolio backtest.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--transaction-cost-bps", type=float, default=15.0)
    args = parser.parse_args()
    source = Path(args.database).resolve()
    require(source.is_file(), f"Database missing: {source}")
    before = sha256(source)

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_challenger_") as tmp:
        temp_db = Path(tmp) / source.name
        shutil.copy2(source, temp_db)
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.platform import load_all, connect
            settings, _ = load_all()
            conn = connect(settings)
            runner = object.__new__(Module38Runner)
            runner.cfg = settings["module38"]
            folds = int(settings["module39"]["rolling_folds"])
            required = folds * TEST_ORIGINS_PER_FOLD
            require(required == 30, "Experiment requires exactly 30 chronological origins per supported group")
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

            all_rows, gaps = [], []
            for asset in ASSETS:
                asset_frame = prices[prices.asset_id == asset].copy()
                for horizon in [int(v) for v in runner.cfg["horizons_days"]]:
                    features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                    candidates = exact_candidates(
                        features, horizon,
                        int(runner.cfg.get("absolute_minimum_training_rows", 90)),
                        int(runner.cfg.get("minimum_validation_rows", 30)),
                        int(runner.cfg["validation_rows"]),
                        float(runner.cfg.get("maximum_validation_share", 0.25)),
                    )
                    if len(candidates) < required:
                        gaps.append({
                            "asset_id": asset,
                            "horizon_days": horizon,
                            "available_candidates": len(candidates),
                            "required_candidates": required,
                        })
                        continue
                    selected = [idx for group in select_groups(candidates, folds) for idx in group]
                    for variant in VARIANTS:
                        for origin_number, idx in enumerate(selected, start=1):
                            row = origin_prediction(runner, features, idx, horizon, variant)
                            row.update({
                                "variant": variant,
                                "asset_id": asset,
                                "horizon_days": horizon,
                                "origin_number": origin_number,
                            })
                            all_rows.append(row)
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    after = sha256(source)
    require(before == after, "Source database changed during disposable challenger replay")
    evidence = pd.DataFrame(all_rows)
    require(not evidence.empty, "No challenger replay evidence produced")

    results = {}
    for variant in VARIANTS:
        vf = evidence[evidence.variant == variant].copy()
        result = summarize_test_only(vf)
        result["economic_metrics"] = economic_metrics_test_only(vf, args.transaction_cost_bps)
        by_horizon = {}
        positive_horizons = 0
        for horizon, hf in vf.groupby("horizon_days"):
            summary = summarize_test_only(hf)
            by_horizon[str(int(horizon))] = summary
            if summary["model_minus_majority_accuracy_pct_points"] > 0:
                positive_horizons += 1
        result["by_horizon"] = by_horizon
        result["supported_horizons_with_positive_baseline_adjusted_skill"] = positive_horizons

        calibration_groups = []
        for (_, _), gf in vf.groupby(["asset_id", "horizon_days"]):
            if len(gf) == required:
                calibration, _ = calibration_evidence(gf.sort_values("origin_number"))
                calibration_groups.append(calibration)
        result["mean_leakage_safe_calibrated_brier_score"] = (
            float(np.mean([r["calibrated_brier_score"] for r in calibration_groups]))
            if calibration_groups else None
        )
        result["calibration_groups"] = len(calibration_groups)
        results[variant] = result

    champion = results[VARIANTS[0]]
    exploratory = []
    for variant in VARIANTS[1:]:
        result = results[variant]
        result["delta_model_minus_majority_vs_champion_pp"] = (
            result["model_minus_majority_accuracy_pct_points"]
            - champion["model_minus_majority_accuracy_pct_points"]
        )
        result["beats_champion_aggregate_direction"] = bool(result["delta_model_minus_majority_vs_champion_pp"] > 0)
        result["majority_of_supported_horizons_positive"] = bool(
            result["supported_horizons_with_positive_baseline_adjusted_skill"] >= 3
        )
        result["eligible_for_exploratory_followup"] = bool(
            result["beats_champion_aggregate_direction"]
            and result["majority_of_supported_horizons_positive"]
        )
        if result["eligible_for_exploratory_followup"]:
            exploratory.append(variant)

    champion_rows = evidence[evidence.variant == VARIANTS[0]]
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "evidence_class": "HISTORICAL_RECONSTRUCTION_REPLAY_EXPLORATORY",
        "evaluation_partition": "FINAL_10_OF_30_PER_SUPPORTED_ASSET_HORIZON_GROUP",
        "majority_baseline_partition": "FIRST_20_OF_30_DEVELOPMENT_ROWS_PER_GROUP",
        "production_source_modified": False,
        "source_database_unchanged": True,
        "rows_per_supported_variant": int(len(champion_rows)),
        "final_test_rows_per_supported_variant": int(results[VARIANTS[0]]["evaluation_rows"]),
        "supported_asset_horizon_groups": int(champion_rows.groupby(["asset_id", "horizon_days"]).ngroups),
        "explicit_evidence_gaps": gaps,
        "results": results,
        "exploratory_followup_candidates": exploratory,
        "promotion_allowed_from_this_run": False,
        "reason_promotion_blocked": "Final replay outcomes are visible in this experiment; any selected challenger requires a newly isolated holdout before promotion.",
    }
    print(json.dumps(payload, indent=2, default=str))
    print("CRYPTO_PREDICTIVE_CHAMPION_CHALLENGER_REPLAY=COMPLETE")
    print(f"SUPPORTED_ASSET_HORIZON_GROUPS={payload['supported_asset_horizon_groups']}")
    print(f"EXPLICIT_EVIDENCE_GAPS={len(gaps)}")
    print(f"ROWS_PER_SUPPORTED_VARIANT={payload['rows_per_supported_variant']}")
    print(f"FINAL_TEST_ROWS_PER_SUPPORTED_VARIANT={payload['final_test_rows_per_supported_variant']}")
    print("MAJORITY_BASELINE_USES_FINAL_TEST_OUTCOMES=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("PRODUCTION_SOURCE_MODIFIED=FALSE")
    print("PROMOTION_ALLOWED_FROM_THIS_RUN=FALSE")
    print("NEXT_GATE=INTERPRET_EXPLORATORY_CHAMPION_CHALLENGER_RESULTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
