from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

import duckdb
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
    7: [
        "return_1d", "return_7d", "return_30d", "volatility_30d", "distance_sma50",
    ],
    30: [
        "return_7d", "return_30d", "return_90d", "volatility_30d", "volatility_90d",
        "distance_sma50", "distance_sma200",
    ],
    90: [
        "return_30d", "return_90d", "volatility_30d", "volatility_90d",
        "distance_sma50", "distance_sma200",
    ],
    180: [
        "return_30d", "return_90d", "volatility_90d", "distance_sma50", "distance_sma200",
    ],
    365: [
        "return_90d", "volatility_90d", "distance_sma200",
    ],
}


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
    available = [
        c for c in frame.columns if c not in {"observation_date", "target_return"}
    ]
    if variant != "HORIZON_SPECIFIC_FEATURE_WINDOWS":
        return available
    chosen = [c for c in HORIZON_FEATURES[int(horizon)] if c in available]
    require(bool(chosen), f"No horizon-specific features available for {horizon}d")
    return chosen


def regression_prediction(
    runner: Module38Runner,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    current: pd.DataFrame,
    columns: list[str],
    horizon: int,
    robust_target: bool,
) -> tuple[float, float, float, float]:
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
        lower_q, upper_q = np.quantile(y_train, [0.025, 0.975])
        y_fit = np.clip(y_train, lower_q, upper_q)
    else:
        y_fit = y_train

    predictions: list[float] = []
    residuals: list[float] = []
    weights: list[float] = []
    for model in runner.model_suite(int(runner.cfg["random_state"]) + int(horizon)).values():
        model.fit(x_train, y_fit)
        val_pred = model.predict(x_val)
        current_pred = float(model.predict(x_current)[0])
        mae = float(np.mean(np.abs(y_val - val_pred)))
        weights.append(1.0 / max(mae, 1e-6))
        predictions.append(current_pred)
        residuals.extend((y_val - val_pred).tolist())

    weight_array = np.asarray(weights, dtype=float)
    weight_array /= weight_array.sum()
    prediction = float(np.dot(weight_array, np.asarray(predictions, dtype=float)))
    residual_array = np.asarray(residuals, dtype=float)
    raw_probability = float(np.mean(prediction + residual_array > 0))
    half_width = float(np.quantile(np.abs(residual_array), 0.90)) if len(residual_array) else 0.0
    return prediction, raw_probability, prediction - half_width, prediction + half_width


def direction_probability(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    current: pd.DataFrame,
    columns: list[str],
    horizon: int,
    random_state: int,
) -> float:
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
    probabilities: list[float] = []
    weights: list[float] = []
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


def origin_prediction(
    runner: Module38Runner,
    features: pd.DataFrame,
    origin_idx: int,
    horizon: int,
    variant: str,
) -> dict:
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
        runner,
        train,
        validation,
        current,
        columns,
        horizon,
        robust_target=(variant == "ROBUST_RETURN_TARGET"),
    )
    if variant == "DIRECTION_FIRST_TWO_STAGE":
        raw_probability = direction_probability(
            train,
            validation,
            current,
            columns,
            horizon,
            int(cfg["random_state"]),
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


def summarize(frame: pd.DataFrame) -> dict:
    actual = frame["actual_return_pct"].to_numpy(dtype=float)
    predicted = frame["predicted_return_pct"].to_numpy(dtype=float)
    observed = frame["observed_positive"].to_numpy(dtype=int)
    raw_p = np.clip(frame["raw_probability_positive"].to_numpy(dtype=float), 1e-4, 1 - 1e-4)
    direction = float((np.sign(actual) == np.sign(predicted)).mean() * 100)
    majority_sign = 1 if observed.mean() >= 0.5 else 0
    majority_accuracy = float((observed == majority_sign).mean() * 100)
    error = actual - predicted
    return {
        "rows": int(len(frame)),
        "directional_accuracy_pct": direction,
        "majority_accuracy_pct": majority_accuracy,
        "model_minus_majority_accuracy_pct_points": direction - majority_accuracy,
        "raw_brier_score": float(brier_score_loss(observed, raw_p)),
        "mae_pct": float(np.mean(np.abs(error))),
        "rmse_pct": float(np.sqrt(np.mean(error ** 2))),
        "interval_coverage_pct": float(frame["interval_covered"].mean() * 100),
    }


def economic_metrics(frame: pd.DataFrame, cost_bps: float) -> dict:
    ordered = frame.sort_values(["forecast_date", "asset_id", "horizon_days"]).copy()
    position = np.sign(ordered["predicted_return_pct"].to_numpy(dtype=float))
    realized = ordered["actual_return_pct"].to_numpy(dtype=float) / 100.0
    gross = position * realized
    turnover = np.abs(np.diff(np.concatenate([[0.0], position])))
    costs = turnover * (cost_bps / 10000.0)
    net = gross - costs
    equity = np.cumprod(1.0 + net)
    peak = np.maximum.accumulate(equity)
    drawdown = equity / np.maximum(peak, 1e-12) - 1.0
    return {
        "sign_strategy_return_before_costs_pct": float((np.prod(1.0 + gross) - 1.0) * 100),
        "sign_strategy_return_after_fixed_transaction_cost_pct": float((np.prod(1.0 + net) - 1.0) * 100),
        "maximum_drawdown_pct": float(drawdown.min() * 100) if len(drawdown) else 0.0,
        "turnover_units": float(turnover.sum()),
        "transaction_cost_bps": float(cost_bps),
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
            m39_cfg = settings["module39"]
            folds = int(m39_cfg["rolling_folds"])
            required = folds * TEST_ORIGINS_PER_FOLD
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

            all_rows: list[dict] = []
            gaps: list[dict] = []
            for asset in ASSETS:
                asset_frame = prices[prices.asset_id == asset].copy()
                for horizon in [int(v) for v in runner.cfg["horizons_days"]]:
                    features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                    candidates = exact_candidates(
                        features,
                        horizon,
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

    results: dict[str, dict] = {}
    for variant in VARIANTS:
        vf = evidence[evidence.variant == variant].copy()
        variant_result = summarize(vf)
        variant_result["economic_metrics"] = economic_metrics(vf, args.transaction_cost_bps)
        by_horizon = {}
        positive_horizons = 0
        for horizon, hf in vf.groupby("horizon_days"):
            summary = summarize(hf)
            by_horizon[str(int(horizon))] = summary
            if summary["model_minus_majority_accuracy_pct_points"] > 0:
                positive_horizons += 1
        variant_result["by_horizon"] = by_horizon
        variant_result["supported_horizons_with_positive_baseline_adjusted_skill"] = positive_horizons
        calibration_groups = []
        for (asset, horizon), gf in vf.groupby(["asset_id", "horizon_days"]):
            if len(gf) != required:
                continue
            calibration, _ = calibration_evidence(gf)
            calibration_groups.append(calibration)
        if calibration_groups:
            variant_result["mean_leakage_safe_calibrated_brier_score"] = float(
                np.mean([row["calibrated_brier_score"] for row in calibration_groups])
            )
            variant_result["calibration_groups"] = len(calibration_groups)
        else:
            variant_result["mean_leakage_safe_calibrated_brier_score"] = None
            variant_result["calibration_groups"] = 0
        results[variant] = variant_result

    champion = results["CURRENT_M38_REGRESSION_ENSEMBLE"]
    exploratory_winners = []
    for variant in VARIANTS[1:]:
        result = results[variant]
        result["delta_model_minus_majority_vs_champion_pp"] = (
            result["model_minus_majority_accuracy_pct_points"]
            - champion["model_minus_majority_accuracy_pct_points"]
        )
        result["beats_champion_aggregate_direction"] = bool(
            result["delta_model_minus_majority_vs_champion_pp"] > 0
        )
        result["majority_of_supported_horizons_positive"] = bool(
            result["supported_horizons_with_positive_baseline_adjusted_skill"] >= 3
        )
        result["eligible_for_exploratory_followup"] = bool(
            result["beats_champion_aggregate_direction"]
            and result["majority_of_supported_horizons_positive"]
        )
        if result["eligible_for_exploratory_followup"]:
            exploratory_winners.append(variant)

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "evidence_class": "HISTORICAL_RECONSTRUCTION_REPLAY_EXPLORATORY",
        "production_source_modified": False,
        "source_database_unchanged": True,
        "rows_per_supported_variant": int(len(evidence[evidence.variant == VARIANTS[0]])),
        "supported_asset_horizon_groups": int(evidence[evidence.variant == VARIANTS[0]].groupby(["asset_id", "horizon_days"]).ngroups),
        "explicit_evidence_gaps": gaps,
        "results": results,
        "exploratory_followup_candidates": exploratory_winners,
        "promotion_allowed_from_this_run": False,
        "reason_promotion_blocked": "Final replay outcomes are visible in this experiment; any selected challenger requires a newly isolated holdout before promotion.",
    }
    print(json.dumps(payload, indent=2, default=str))
    print("CRYPTO_PREDICTIVE_CHAMPION_CHALLENGER_REPLAY=COMPLETE")
    print(f"SUPPORTED_ASSET_HORIZON_GROUPS={payload['supported_asset_horizon_groups']}")
    print(f"EXPLICIT_EVIDENCE_GAPS={len(gaps)}")
    print(f"ROWS_PER_SUPPORTED_VARIANT={payload['rows_per_supported_variant']}")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("PRODUCTION_SOURCE_MODIFIED=FALSE")
    print("PROMOTION_ALLOWED_FROM_THIS_RUN=FALSE")
    print("NEXT_GATE=INTERPRET_EXPLORATORY_CHAMPION_CHALLENGER_RESULTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
