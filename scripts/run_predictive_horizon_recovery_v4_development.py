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
from sklearn.metrics import brier_score_loss, mean_absolute_error
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import ASSETS, Module38Runner
from scripts.audit_predictive_horizon_recovery_v4_fresh_evidence_capacity import selected_v3_origins_for_group
from scripts.preflight_predictive_horizon_recovery_v4_development import v4_split_origin
from scripts.run_v3_per_horizon_development_tournament import build_relative_market as build_v3_relative_market
from scripts.v4_horizon_recovery_model_spec import (
    CANDIDATE_CONTRACTS,
    EVIDENCE_CLASS,
    EXPERIMENT_ID,
    NATIVE_LAG_DAYS,
    RECOVERY_HORIZONS,
    TRANSACTION_COST_BPS,
    attach_lagged_native,
    attach_relative,
    build_price_features,
    build_relative_market,
    candidate_features,
    candidate_kind,
    model_list,
)

EXPECTED_V3_RESULTS_SHA256 = "33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1"
EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2"
EXPECTED_GROUPS = 17
EXPECTED_DEV_ORIGINS = 50
DEFAULT_FINAL_HOLDOUT_ORIGINS = 10
AVALANCHE365_FINAL_HOLDOUT_ORIGINS = 9

CANDIDATE_SIMPLICITY_ORDER = {
    "V4_7D_SHORT_TREND_REVERSAL_LOGIT": 0,
    "V4_7D_RELATIVE_STRENGTH_GB": 1,
    "V4_7D_VOLATILITY_STATE_EXTRA_TREES": 2,
    "V4_30D_TREND_REVERSAL_LOGIT": 0,
    "V4_30D_RELATIVE_CONTEXT_GB": 1,
    "V4_30D_VOLATILITY_STATE_EXTRA_TREES": 2,
    "V4_365D_LONG_TREND_LOGIT": 0,
    "V4_365D_LONG_REGIME_GB": 1,
    "V4_365D_RETURN_MAGNITUDE_ENSEMBLE": 2,
}


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


def expected_holdout_count(asset: str, horizon: int) -> int:
    if asset == "avalanche" and int(horizon) == 365:
        return AVALANCHE365_FINAL_HOLDOUT_ORIGINS
    return DEFAULT_FINAL_HOLDOUT_ORIGINS


def fit_predict(
    horizon: int,
    family: str,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    current: pd.DataFrame,
    columns: list[str],
    random_state: int,
) -> tuple[float, float | None]:
    train = train.dropna(subset=columns + ["target_return"]).copy()
    validation = validation.dropna(subset=columns + ["target_return"]).copy()
    current = current.dropna(subset=columns).copy()
    require(len(train) >= 90, f"Insufficient V4 complete training rows for {family}")
    require(len(validation) >= 30, f"Insufficient V4 complete validation rows for {family}")
    require(len(current) == 1, f"Missing V4 current features for {family}")

    x_train = train[columns].astype(float)
    x_val = validation[columns].astype(float)
    x_current = current[columns].astype(float)
    lo = x_train.min(axis=0)
    hi = x_train.max(axis=0)
    x_val = x_val.clip(lower=lo, upper=hi, axis=1)
    x_current = x_current.clip(lower=lo, upper=hi, axis=1)
    scaler = StandardScaler()
    tx = scaler.fit_transform(x_train)
    vx = scaler.transform(x_val)
    cx = scaler.transform(x_current)

    models = model_list(horizon, family, random_state)
    kind = candidate_kind(horizon, family)
    if kind == "classifier":
        y_train = (train["target_return"].to_numpy(dtype=float) > 0).astype(int)
        y_val = (validation["target_return"].to_numpy(dtype=float) > 0).astype(int)
        if len(np.unique(y_train)) < 2:
            p = float(y_train.mean())
            return p, None
        probs = []
        weights = []
        for model in models:
            model.fit(tx, y_train)
            val_prob = np.clip(model.predict_proba(vx)[:, 1], 1e-4, 1 - 1e-4)
            score = float(brier_score_loss(y_val, val_prob))
            probs.append(float(model.predict_proba(cx)[0, 1]))
            weights.append(1.0 / max(score, 1e-6))
        w = np.asarray(weights, dtype=float)
        w /= w.sum()
        return float(np.dot(w, np.asarray(probs, dtype=float))), None

    y_train = train["target_return"].to_numpy(dtype=float)
    y_val = validation["target_return"].to_numpy(dtype=float)
    preds = []
    weights = []
    for model in models:
        model.fit(tx, y_train)
        val_pred = model.predict(vx)
        score = float(mean_absolute_error(y_val, val_pred))
        preds.append(float(model.predict(cx)[0]))
        weights.append(1.0 / max(score, 1e-8))
    w = np.asarray(weights, dtype=float)
    w /= w.sum()
    predicted_return = float(np.dot(w, np.asarray(preds, dtype=float)))
    return float(1.0 if predicted_return > 0 else 0.0), predicted_return


def summarize(frame: pd.DataFrame, assets_required_nonnegative: int) -> dict:
    observed = frame["observed_positive"].astype(int)
    predicted = frame["predicted_positive"].astype(int)
    baseline = frame["baseline_positive"].astype(int)
    model_correct = (predicted == observed).astype(int)
    baseline_correct = (baseline == observed).astype(int)
    direction = float(model_correct.mean() * 100.0)
    baseline_acc = float(baseline_correct.mean() * 100.0)
    delta = direction - baseline_acc

    by_asset = {}
    positive_asset_gains = []
    for asset, group in frame.groupby("asset_id"):
        mc = (group["predicted_positive"].astype(int) == group["observed_positive"].astype(int)).astype(int)
        bc = (group["baseline_positive"].astype(int) == group["observed_positive"].astype(int)).astype(int)
        net_gain = int(mc.sum() - bc.sum())
        asset_delta = float((mc.mean() - bc.mean()) * 100.0)
        by_asset[str(asset)] = {
            "rows": int(len(group)),
            "directional_accuracy_pct": float(mc.mean() * 100.0),
            "baseline_accuracy_pct": float(bc.mean() * 100.0),
            "baseline_adjusted_skill_pp": asset_delta,
            "net_correct_gain_vs_baseline": net_gain,
        }
        positive_asset_gains.append(max(0, net_gain))
    nonnegative_assets = sum(1 for row in by_asset.values() if float(row["baseline_adjusted_skill_pp"]) >= 0)
    total_positive_asset_gain = int(sum(positive_asset_gains))
    max_positive_asset_gain = int(max(positive_asset_gains)) if positive_asset_gains else 0
    single_asset_majority = bool(total_positive_asset_gain > 0 and max_positive_asset_gain > total_positive_asset_gain / 2)

    by_fold = {}
    positive_fold_gains = []
    fold_skill_values = []
    for fold, group in frame.groupby("fold"):
        mc = (group["predicted_positive"].astype(int) == group["observed_positive"].astype(int)).astype(int)
        bc = (group["baseline_positive"].astype(int) == group["observed_positive"].astype(int)).astype(int)
        net_gain = int(mc.sum() - bc.sum())
        fold_skill = float((mc.mean() - bc.mean()) * 100.0)
        by_fold[str(int(fold))] = {
            "rows": int(len(group)),
            "baseline_adjusted_skill_pp": fold_skill,
            "net_correct_gain_vs_baseline": net_gain,
        }
        fold_skill_values.append(fold_skill)
        positive_fold_gains.append(max(0, net_gain))
    total_positive_fold_gain = int(sum(positive_fold_gains))
    max_positive_fold_gain = int(max(positive_fold_gains)) if positive_fold_gains else 0
    single_fold_majority = bool(total_positive_fold_gain > 0 and max_positive_fold_gain > total_positive_fold_gain / 2)
    fold_skill_std = float(np.std(np.asarray(fold_skill_values, dtype=float), ddof=0)) if fold_skill_values else None

    ordered = frame.sort_values(["asset_id", "forecast_date"]).copy()
    ordered["position"] = np.where(ordered["predicted_positive"].astype(int) == 1, 1.0, -1.0)
    ordered["previous_position"] = ordered.groupby("asset_id")["position"].shift(1).fillna(0.0)
    ordered["turnover"] = (ordered["position"] - ordered["previous_position"]).abs()
    ordered["strategy_return_pct_after_cost"] = (
        ordered["position"] * ordered["actual_return_pct"]
        - ordered["turnover"] * (TRANSACTION_COST_BPS / 100.0)
    )
    mean_economic = float(ordered["strategy_return_pct_after_cost"].mean())

    prob_rows = frame["raw_probability_positive"].notna()
    raw_brier = None
    if bool(prob_rows.any()):
        raw_brier = float(brier_score_loss(
            frame.loc[prob_rows, "observed_positive"].astype(int),
            np.clip(frame.loc[prob_rows, "raw_probability_positive"].astype(float), 1e-4, 1 - 1e-4),
        ))

    qualifies = bool(
        delta > 0
        and nonnegative_assets >= int(assets_required_nonnegative)
        and not single_asset_majority
        and not single_fold_majority
        and mean_economic > 0
        and len(frame) > 0
    )
    return {
        "development_rows": int(len(frame)),
        "directional_accuracy_pct": direction,
        "development_majority_baseline_accuracy_pct": baseline_acc,
        "model_minus_development_majority_accuracy_pct_points": delta,
        "raw_brier_score": raw_brier,
        "calibrated_brier_score": None,
        "assets_nonnegative_baseline_adjusted_skill": int(nonnegative_assets),
        "single_asset_explains_majority_of_positive_gain": single_asset_majority,
        "single_fold_explains_majority_of_positive_gain": single_fold_majority,
        "fold_baseline_adjusted_skill_std_pp": fold_skill_std,
        "mean_sign_strategy_return_pct_after_15bps_cost": mean_economic,
        "turnover_units": float(ordered["turnover"].sum()),
        "by_asset": by_asset,
        "by_fold": by_fold,
        "development_selection_gate_pass": qualifies,
    }


def choose_winner(candidate_results: dict) -> str | None:
    eligible = [(name, metrics) for name, metrics in candidate_results.items() if metrics["development_selection_gate_pass"]]
    if not eligible:
        return None

    def key(item):
        name, m = item
        calibrated = m.get("calibrated_brier_score")
        raw = m.get("raw_brier_score")
        fold_std = m.get("fold_baseline_adjusted_skill_std_pp")
        return (
            float(m["model_minus_development_majority_accuracy_pct_points"]),
            float(m["directional_accuracy_pct"]),
            int(m["assets_nonnegative_baseline_adjusted_skill"]),
            -(float(calibrated) if calibrated is not None else 999.0),
            -(float(raw) if raw is not None else 999.0),
            -(float(fold_std) if fold_std is not None else 999.0),
            -int(CANDIDATE_SIMPLICITY_ORDER[name]),
            name,
        )

    return max(eligible, key=key)[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--v3-results", required=True)
    parser.add_argument("--v4-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.database).resolve()
    v2_path = Path(args.v2_manifest).resolve()
    v3_path = Path(args.v3_manifest).resolve()
    v3_results_path = Path(args.v3_results).resolve()
    v4_path = Path(args.v4_manifest).resolve()
    output = Path(args.output).resolve()
    for path in (source, v2_path, v3_path, v3_results_path, v4_path):
        require(path.is_file(), f"Required V4 development input missing: {path}")
    require(not output.exists(), "V4 development output already exists; refusing overwrite")
    before = {name: sha256(path) for name, path in {
        "database": source, "v2": v2_path, "v3": v3_path, "v3_results": v3_results_path, "v4": v4_path,
    }.items()}
    require(before["v3_results"] == EXPECTED_V3_RESULTS_SHA256, "Unexpected V3 development-results hash")

    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    v3 = json.loads(v3_path.read_text(encoding="utf-8"))
    v3_results = json.loads(v3_results_path.read_text(encoding="utf-8"))
    v4 = json.loads(v4_path.read_text(encoding="utf-8"))
    require(v3_results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout has been viewed")
    require(v4.get("experiment_id") == EXPERIMENT_ID, "Unexpected V4 experiment id")
    require(v4.get("manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Unexpected candidate-safe V4 manifest hash")
    require(manifest_content_hash(v4) == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "V4 manifest canonical content hash mismatch")
    require(v4.get("candidate_safe_membership_required") is True, "V4 candidate-safe membership control missing")
    require(v4.get("avalanche365_exception_governed") is True, "Governed Avalanche365 allocation exception missing")
    require(v4.get("exact_calendar_target_date_required") is True, "V4 exact-calendar target control missing")
    require(v4.get("holdout_outcomes_viewed_before_freeze") is False, "V4 holdout not frozen before outcomes")
    require(v4.get("holdout_outcome_values_read_during_membership_selection") is False, "V4 holdout outcomes were read during membership selection")
    require(v4.get("v3_final_holdout_reused") is False, "V3 final holdout was reused by V4")

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_final_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}
    v4_groups = {(g["asset_id"], int(g["horizon_days"])): g for g in v4["groups"]}
    require(len(v4_groups) == EXPECTED_GROUPS, "Unexpected V4 group count")

    for (asset, horizon), group in v4_groups.items():
        dev_dates = list(group["v4_development_origin_dates"])
        holdout_dates = list(group["v4_final_holdout_origin_dates"])
        required_holdout = expected_holdout_count(asset, horizon)
        require(len(dev_dates) == EXPECTED_DEV_ORIGINS, f"Unexpected V4 development count for {asset} {horizon}d")
        require(len(holdout_dates) == required_holdout, f"Unexpected V4 holdout count for {asset} {horizon}d")
        require(int(group.get("development_origin_count", len(dev_dates))) == EXPECTED_DEV_ORIGINS, f"V4 development count metadata mismatch for {asset} {horizon}d")
        require(int(group.get("final_holdout_origin_count", len(holdout_dates))) == required_holdout, f"V4 holdout count metadata mismatch for {asset} {horizon}d")
        require(set(dev_dates).isdisjoint(holdout_dates), f"V4 development/final overlap for {asset} {horizon}d")
        require(max(dev_dates) < min(holdout_dates), f"V4 final holdout is not later than development for {asset} {horizon}d")

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    horizon_rows: dict[int, dict[str, list[dict]]] = {h: {family: [] for family in CANDIDATE_CONTRACTS[h]["families"]} for h in RECOVERY_HORIZONS}

    with tempfile.TemporaryDirectory(prefix="crypto_v4_development_") as tmp:
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
                "SELECT asset_id, observation_date, price_usd, market_cap_usd, volume_24h_usd FROM canonical_market_daily "
                "WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche') AND price_usd IS NOT NULL ORDER BY observation_date, asset_id"
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
                holdout_dates = set(group["v4_final_holdout_origin_dates"])
                asset_frame = prices[prices["asset_id"] == asset].copy()
                v3_features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                v3_mask = pd.to_datetime(v3_features["observation_date"]).dt.date.astype(str).isin(v3_final_dates[(asset, horizon)])
                v3_features.loc[v3_mask, "target_return"] = np.nan
                selected_v3_indices = selected_v3_origins_for_group(
                    v3_features, horizon, runner, context, v3_relative, asset,
                    v2_dates[(asset, horizon)], v3_final_dates[(asset, horizon)],
                )
                selected_v3_dates = {pd.Timestamp(v3_features.iloc[index]["observation_date"]).date().isoformat() for index in selected_v3_indices}
                excluded = set(v2_dates[(asset, horizon)]) | set(v3_final_dates[(asset, horizon)]) | selected_v3_dates | holdout_dates

                features = build_price_features(asset_frame, horizon).reset_index(drop=True)
                holdout_mask = pd.to_datetime(features["observation_date"]).dt.date.astype(str).isin(holdout_dates)
                features.loc[holdout_mask, ["target_return", "target_positive", "target_exceeds_15pct"]] = np.nan
                date_to_index = {pd.Timestamp(row.observation_date).date().isoformat(): int(row.Index) for row in features[["observation_date"]].itertuples(index=True)}

                for origin_number, date_key in enumerate(dev_dates):
                    require(date_key in date_to_index, f"V4 development origin missing from feature frame: {asset} {horizon}d {date_key}")
                    origin_idx = date_to_index[date_key]
                    origin_date, train, validation, current = v4_split_origin(features, origin_idx, horizon, runner, excluded)
                    actual_return = float(features.iloc[origin_idx]["target_return"])
                    require(np.isfinite(actual_return), f"Missing V4 development outcome for {asset} {horizon}d {date_key}")
                    train_majority = int((train["target_return"].astype(float) > 0).mean() >= 0.5)
                    fold = int(origin_number // 10) + 1

                    for family in CANDIDATE_CONTRACTS[horizon]["families"]:
                        columns = candidate_features(horizon, family)
                        train_f = attach_relative(attach_lagged_native(train, context, columns), v4_relative, asset, columns)
                        val_f = attach_relative(attach_lagged_native(validation, context, columns), v4_relative, asset, columns)
                        current_f = attach_relative(attach_lagged_native(current, context, columns), v4_relative, asset, columns)
                        probability, predicted_return = fit_predict(horizon, family, train_f, val_f, current_f, columns, random_state)
                        if candidate_kind(horizon, family) == "classifier":
                            predicted_positive = int(probability >= 0.5)
                            raw_probability = probability
                        else:
                            require(predicted_return is not None, f"Missing regression prediction for {family}")
                            predicted_positive = int(predicted_return > 0)
                            raw_probability = None
                        horizon_rows[horizon][family].append({
                            "asset_id": asset,
                            "horizon_days": int(horizon),
                            "forecast_date": origin_date.date().isoformat(),
                            "fold": fold,
                            "family": family,
                            "predicted_positive": predicted_positive,
                            "raw_probability_positive": raw_probability,
                            "predicted_return": predicted_return,
                            "observed_positive": int(actual_return > 0),
                            "observed_exceeds_15pct": int(actual_return > 0.15),
                            "actual_return_pct": actual_return * 100.0,
                            "baseline_positive": train_majority,
                        })
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    after = {name: sha256(path) for name, path in {
        "database": source, "v2": v2_path, "v3": v3_path, "v3_results": v3_results_path, "v4": v4_path,
    }.items()}
    require(before == after, "Source evidence changed during V4 development scoring")

    horizon_results = {}
    selected_winners = {}
    for horizon in RECOVERY_HORIZONS:
        candidate_results = {}
        expected_rows = 300 if horizon in (7, 30) else 250
        for family, rows in horizon_rows[horizon].items():
            frame = pd.DataFrame(rows)
            require(len(frame) == expected_rows, f"Unexpected V4 development row count for {horizon}d {family}")
            candidate_results[family] = summarize(frame, int(CANDIDATE_CONTRACTS[horizon]["assets_required_nonnegative"]))
            if horizon == 365:
                candidate_results[family]["aux_observed_forward_return_exceeds_15pct_rate"] = float(frame["observed_exceeds_15pct"].mean())
                if candidate_kind(horizon, family) == "regressor":
                    predicted_exceeds = (frame["predicted_return"].astype(float) > 0.15).astype(int)
                    candidate_results[family]["aux_predicted_exceeds_15pct_accuracy"] = float((predicted_exceeds == frame["observed_exceeds_15pct"].astype(int)).mean())
                else:
                    candidate_results[family]["aux_predicted_exceeds_15pct_accuracy"] = None
        winner = choose_winner(candidate_results)
        horizon_results[str(horizon)] = {
            "candidate_results": candidate_results,
            "selected_development_winner": winner,
            "qualified_winner_exists": winner is not None,
        }
        selected_winners[str(horizon)] = winner

    report = {
        "experiment_id": EXPERIMENT_ID,
        "evidence_class": EVIDENCE_CLASS,
        "strict_point_in_time_claim_allowed": False,
        "recovery_horizons": list(RECOVERY_HORIZONS),
        "v4_manifest_content_sha256": EXPECTED_V4_MANIFEST_CONTENT_SHA256,
        "candidate_safe_membership_required": True,
        "avalanche365_exception_governed": True,
        "v2_consumed_origins_excluded": True,
        "v3_development_origins_excluded": True,
        "v3_final_holdout_origins_excluded": True,
        "v4_final_holdout_origins_excluded": True,
        "v3_final_holdout_outcomes_viewed": False,
        "v4_final_holdout_outcomes_viewed": False,
        "recommendation_policy_changed": False,
        "production_promotion_allowed": False,
        "horizon_results": horizon_results,
        "selected_winners": selected_winners,
        "all_recovery_horizons_have_qualified_winners": all(selected_winners[str(h)] is not None for h in RECOVERY_HORIZONS),
        "next_gate": "VALIDATE_AND_REVIEW_V4_DEVELOPMENT_RESULTS_BEFORE_ANY_FINAL_HOLDOUT_EXPOSURE",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("CRYPTO_V4_DEVELOPMENT_SCORING=PASS")
    for horizon in RECOVERY_HORIZONS:
        winner = selected_winners[str(horizon)] or "NO_QUALIFIED_WINNER"
        print(f"WINNER_{horizon}D={winner}")
    print("V4_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
