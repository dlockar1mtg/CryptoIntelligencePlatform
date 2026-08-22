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
    apply_calibration,
    calibration_evidence,
    exact_candidates,
    select_groups,
    split_capacity,
)

EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_IMPROVEMENT_V2"
CHAMPION = "CURRENT_M38_REGRESSION_ENSEMBLE"
CHALLENGER = "NATIVE_CONTEXT_AUGMENTED_DIRECTION_FIRST"
EXPECTED_MANIFEST_CONTENT_SHA256 = "7ae0e4f84896097c32ebae0f7a6a514686f07e065db23fa4e04d205752729a76"
NATIVE_CONTEXT_FEATURES = [
    "btc_return_30d_pct",
    "core_breadth_above_sma50_pct",
    "core_median_return_30d_pct",
    "dollar_index",
    "fear_greed_index",
    "macro_liquidity_score",
    "risk_appetite_score",
    "stablecoin_growth_30d_pct",
    "stablecoin_supply_usd",
    "vix",
]
PRICE_FEATURES = [
    "return_1d",
    "return_7d",
    "return_30d",
    "return_90d",
    "volatility_30d",
    "volatility_90d",
    "distance_sma50",
    "distance_sma200",
]


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


def regression_prediction(runner, train, validation, current, columns, horizon):
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

    predictions, residuals, weights = [], [], []
    for model in runner.model_suite(int(runner.cfg["random_state"]) + int(horizon)).values():
        model.fit(x_train, y_train)
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
    probability = float(np.mean(prediction + residual_array > 0))
    half_width = float(np.quantile(np.abs(residual_array), 0.90)) if len(residual_array) else 0.0
    return prediction, probability, prediction - half_width, prediction + half_width


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
    probs, weights = [], []
    for model in models:
        model.fit(x_train, y_train)
        val_p = model.predict_proba(x_val)[:, 1]
        current_p = float(model.predict_proba(x_current)[0, 1])
        brier = float(brier_score_loss(y_val, np.clip(val_p, 1e-4, 1 - 1e-4)))
        weights.append(1.0 / max(brier, 1e-6))
        probs.append(current_p)
    w = np.asarray(weights, dtype=float)
    w /= w.sum()
    return float(np.dot(w, np.asarray(probs, dtype=float)))


def split_origin(features, origin_idx, horizon, runner):
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
    return origin_date, train, validation, current


def predict_origin(runner, features, origin_idx, horizon, context_frame):
    origin_date, train, validation, current = split_origin(features, origin_idx, horizon, runner)
    price_columns = [c for c in PRICE_FEATURES if c in train.columns]
    require(len(price_columns) == len(PRICE_FEATURES), "Required price feature missing")
    prediction, champion_probability, lower, upper = regression_prediction(
        runner, train, validation, current, price_columns, horizon
    )

    context = context_frame.copy()
    context["observation_date"] = pd.to_datetime(context["observation_date"])
    train_aug = train.merge(context, on="observation_date", how="left")
    val_aug = validation.merge(context, on="observation_date", how="left")
    cur_aug = current.merge(context, on="observation_date", how="left")
    augmented_columns = price_columns + NATIVE_CONTEXT_FEATURES
    train_aug = train_aug.dropna(subset=augmented_columns + ["target_return"]).copy()
    val_aug = val_aug.dropna(subset=augmented_columns + ["target_return"]).copy()
    cur_aug = cur_aug.dropna(subset=augmented_columns).copy()
    require(len(train_aug) >= int(runner.cfg.get("absolute_minimum_training_rows", 90)), "Insufficient complete native-context training history")
    require(len(val_aug) >= int(runner.cfg.get("minimum_validation_rows", 30)), "Insufficient complete native-context validation history")
    require(len(cur_aug) == 1, f"Missing native context at frozen origin {origin_date.date()}")

    challenger_probability = direction_probability(
        train_aug,
        val_aug,
        cur_aug,
        augmented_columns,
        horizon,
        int(runner.cfg["random_state"]),
    )
    challenger_prediction = abs(prediction) if challenger_probability >= 0.5 else -abs(prediction)
    shift = challenger_prediction - prediction
    actual = float(features.iloc[origin_idx]["target_return"])
    return {
        "forecast_date": origin_date.date(),
        "actual_return_pct": actual * 100,
        "observed_positive": int(actual > 0),
        CHAMPION: {
            "predicted_return_pct": prediction * 100,
            "raw_probability_positive": champion_probability,
            "lower_return_pct": lower * 100,
            "upper_return_pct": upper * 100,
            "interval_covered": bool(lower <= actual <= upper),
        },
        CHALLENGER: {
            "predicted_return_pct": challenger_prediction * 100,
            "raw_probability_positive": challenger_probability,
            "lower_return_pct": (lower + shift) * 100,
            "upper_return_pct": (upper + shift) * 100,
            "interval_covered": bool((lower + shift) <= actual <= (upper + shift)),
        },
    }


def summarize(frame: pd.DataFrame, baseline_sign_by_group: dict) -> dict:
    actual = frame["actual_return_pct"].to_numpy(dtype=float)
    predicted = frame["predicted_return_pct"].to_numpy(dtype=float)
    observed = frame["observed_positive"].to_numpy(dtype=int)
    raw_p = np.clip(frame["raw_probability_positive"].to_numpy(dtype=float), 1e-4, 1 - 1e-4)
    baseline_correct = []
    for row in frame.itertuples(index=False):
        baseline = baseline_sign_by_group[(row.asset_id, int(row.horizon_days))]
        baseline_correct.append(int(row.observed_positive) == int(baseline))
    direction = float((np.sign(actual) == np.sign(predicted)).mean() * 100)
    baseline_accuracy = float(np.mean(baseline_correct) * 100)
    error = actual - predicted
    return {
        "evaluation_rows": int(len(frame)),
        "directional_accuracy_pct": direction,
        "development_majority_baseline_accuracy_pct": baseline_accuracy,
        "model_minus_development_majority_accuracy_pct_points": direction - baseline_accuracy,
        "raw_brier_score": float(brier_score_loss(observed, raw_p)),
        "leakage_safe_calibrated_brier_score": float(brier_score_loss(observed, np.clip(frame["calibrated_probability_positive"].to_numpy(dtype=float), 1e-4, 1 - 1e-4))),
        "mae_pct": float(np.mean(np.abs(error))),
        "rmse_pct": float(np.sqrt(np.mean(error ** 2))),
        "interval_coverage_pct": float(frame["interval_covered"].mean() * 100),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    source = Path(args.database).resolve()
    manifest_path = Path(args.manifest).resolve()
    require(source.is_file(), f"Database missing: {source}")
    require(manifest_path.is_file(), f"Manifest missing: {manifest_path}")
    before_db = sha256(source)
    before_manifest = sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["experiment_id"] == EXPERIMENT_ID, "Unexpected V2 manifest experiment id")
    require(manifest["holdout_outcomes_viewed_before_freeze"] is False, "Manifest is not pre-outcome frozen")
    require(manifest["manifest_content_sha256"] == EXPECTED_MANIFEST_CONTENT_SHA256, "Unexpected frozen manifest content hash")
    require(manifest_content_hash(manifest) == EXPECTED_MANIFEST_CONTENT_SHA256, "Frozen manifest content no longer matches its canonical hash")
    require(int(manifest["supported_groups"]) == 29, "Expected 29 supported V2 groups")
    require(int(manifest["rows_per_supported_group"]) == 10, "Expected 10 V2 rows per supported group")

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_v2_holdout_") as tmp:
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
            require(folds * TEST_ORIGINS_PER_FOLD == 30, "Expected 30 V1 origins per supported group")

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
                "SELECT observation_date," + ",".join(NATIVE_CONTEXT_FEATURES) + " FROM crypto_features_daily ORDER BY observation_date"
            ).fetchdf()
            context["observation_date"] = pd.to_datetime(context["observation_date"])
            require(all(c in context.columns for c in NATIVE_CONTEXT_FEATURES), "Native context warehouse columns missing")

            manifest_groups = {(g["asset_id"], int(g["horizon_days"])): g for g in manifest["groups"]}
            all_rows = {CHAMPION: [], CHALLENGER: []}
            calibration_specs = {CHAMPION: {}, CHALLENGER: {}}
            baseline_sign_by_group = {}

            for asset in ASSETS:
                asset_frame = prices[prices.asset_id == asset].copy()
                for horizon in [int(v) for v in runner.cfg["horizons_days"]]:
                    key = (asset, horizon)
                    if key not in manifest_groups:
                        continue
                    features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                    candidates = exact_candidates(
                        features, horizon,
                        int(runner.cfg.get("absolute_minimum_training_rows", 90)),
                        int(runner.cfg.get("minimum_validation_rows", 30)),
                        int(runner.cfg["validation_rows"]),
                        float(runner.cfg.get("maximum_validation_share", 0.25)),
                    )
                    require(len(candidates) >= 30, f"V1 evidence disappeared for {asset} {horizon}d")
                    v1_selected = [idx for group in select_groups(candidates, folds) for idx in group]
                    v1_rows = {CHAMPION: [], CHALLENGER: []}
                    for idx in v1_selected:
                        result = predict_origin(runner, features, idx, horizon, context)
                        for variant in (CHAMPION, CHALLENGER):
                            row = {
                                "forecast_date": result["forecast_date"],
                                "observed_positive": result["observed_positive"],
                                "raw_probability_positive": result[variant]["raw_probability_positive"],
                            }
                            v1_rows[variant].append(row)
                    development = pd.DataFrame(v1_rows[CHAMPION][:20])
                    baseline_sign_by_group[key] = 1 if float(development["observed_positive"].mean()) >= 0.5 else 0
                    for variant in (CHAMPION, CHALLENGER):
                        _, spec = calibration_evidence(pd.DataFrame(v1_rows[variant]))
                        calibration_specs[variant][key] = spec

                    date_to_idx = {pd.Timestamp(d).date(): i for i, d in enumerate(pd.to_datetime(features["observation_date"]))}
                    frozen_dates = [pd.Timestamp(d).date() for d in manifest_groups[key]["v2_holdout_origin_dates"]]
                    require(len(frozen_dates) == 10 and len(set(frozen_dates)) == 10, f"Invalid frozen dates for {asset} {horizon}d")
                    require(not set(frozen_dates).intersection({pd.Timestamp(features.iloc[i]["observation_date"]).date() for i in v1_selected}), f"V2/V1 overlap for {asset} {horizon}d")
                    for origin_date in frozen_dates:
                        require(origin_date in date_to_idx, f"Frozen origin missing from features for {asset} {horizon}d: {origin_date}")
                        result = predict_origin(runner, features, date_to_idx[origin_date], horizon, context)
                        for variant in (CHAMPION, CHALLENGER):
                            spec = calibration_specs[variant][key]
                            raw_p = float(result[variant]["raw_probability_positive"])
                            all_rows[variant].append({
                                "variant": variant,
                                "asset_id": asset,
                                "horizon_days": horizon,
                                "forecast_date": result["forecast_date"],
                                "actual_return_pct": result["actual_return_pct"],
                                "observed_positive": result["observed_positive"],
                                "predicted_return_pct": result[variant]["predicted_return_pct"],
                                "raw_probability_positive": raw_p,
                                "calibrated_probability_positive": apply_calibration(spec, raw_p),
                                "interval_covered": result[variant]["interval_covered"],
                            })
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    require(sha256(source) == before_db, "Source database changed during V2 holdout evaluation")
    require(sha256(manifest_path) == before_manifest, "Frozen V2 manifest changed during evaluation")

    results = {}
    for variant in (CHAMPION, CHALLENGER):
        frame = pd.DataFrame(all_rows[variant])
        require(len(frame) == 290, f"Expected 290 V2 evaluation rows for {variant}, got {len(frame)}")
        result = summarize(frame, baseline_sign_by_group)
        by_horizon = {}
        positive_horizons = 0
        for horizon, hframe in frame.groupby("horizon_days"):
            summary = summarize(hframe, baseline_sign_by_group)
            by_horizon[str(int(horizon))] = summary
            if summary["model_minus_development_majority_accuracy_pct_points"] > 0:
                positive_horizons += 1
        by_asset = {}
        positive_assets = 0
        for asset, aframe in frame.groupby("asset_id"):
            summary = summarize(aframe, baseline_sign_by_group)
            by_asset[str(asset)] = summary
            if summary["model_minus_development_majority_accuracy_pct_points"] > 0:
                positive_assets += 1
        result["by_horizon"] = by_horizon
        result["by_asset"] = by_asset
        result["supported_horizons_with_positive_baseline_adjusted_skill"] = positive_horizons
        result["supported_assets_with_positive_baseline_adjusted_skill"] = positive_assets
        results[variant] = result

    champion = results[CHAMPION]
    challenger = results[CHALLENGER]
    challenger["delta_baseline_adjusted_direction_vs_champion_pp"] = (
        challenger["model_minus_development_majority_accuracy_pct_points"]
        - champion["model_minus_development_majority_accuracy_pct_points"]
    )
    challenger["beats_champion_aggregate_baseline_adjusted_direction"] = (
        challenger["model_minus_development_majority_accuracy_pct_points"]
        > champion["model_minus_development_majority_accuracy_pct_points"]
    )
    challenger["majority_of_supported_horizons_positive"] = (
        challenger["supported_horizons_with_positive_baseline_adjusted_skill"] >= 3
    )
    challenger["aggregate_improvement_not_single_horizon_only"] = sum(
        1 for h in challenger["by_horizon"]
        if challenger["by_horizon"][h]["directional_accuracy_pct"]
        > champion["by_horizon"][h]["directional_accuracy_pct"]
    ) >= 2
    challenger["forecast_promotion_gate_pass"] = bool(
        challenger["beats_champion_aggregate_baseline_adjusted_direction"]
        and challenger["majority_of_supported_horizons_positive"]
        and challenger["aggregate_improvement_not_single_horizon_only"]
    )

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "evidence_class": "FROZEN_PREDECLARED_V2_HOLDOUT",
        "manifest_content_sha256": EXPECTED_MANIFEST_CONTENT_SHA256,
        "supported_asset_horizon_groups": 29,
        "evaluation_rows_per_variant": 290,
        "v2_holdout_outcomes_were_frozen_before_evaluation": True,
        "recommendation_policy_changed": False,
        "source_database_unchanged": True,
        "frozen_manifest_unchanged": True,
        "results": results,
        "forecast_promotion_gate_pass": challenger["forecast_promotion_gate_pass"],
        "recommendation_policy_promotion_allowed": False,
    }
    print(json.dumps(payload, indent=2))
    print("CRYPTO_V2_NATIVE_CONTEXT_HOLDOUT_EVALUATION=COMPLETE")
    print("EVIDENCE_CLASS=FROZEN_PREDECLARED_V2_HOLDOUT")
    print("SUPPORTED_GROUPS=29")
    print("EVALUATION_ROWS_PER_VARIANT=290")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("FROZEN_MANIFEST_MODIFIED=FALSE")
    print("RECOMMENDATION_POLICY_CHANGED=FALSE")
    print(f"FORECAST_PROMOTION_GATE_PASS={'TRUE' if challenger['forecast_promotion_gate_pass'] else 'FALSE'}")
    print("NEXT_GATE=INTERPRET_V2_NATIVE_CONTEXT_HOLDOUT_RESULTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
