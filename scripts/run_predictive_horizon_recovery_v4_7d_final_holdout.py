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
from sklearn.metrics import brier_score_loss

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import Module38Runner
from scripts.audit_predictive_horizon_recovery_v4_fresh_evidence_capacity import selected_v3_origins_for_group
from scripts.preflight_predictive_horizon_recovery_v4_development import v4_split_origin
from scripts.run_predictive_horizon_recovery_v4_development import fit_predict, manifest_content_hash
from scripts.run_v3_per_horizon_development_tournament import build_relative_market as build_v3_relative_market
from scripts.v4_horizon_recovery_model_spec import (
    EVIDENCE_CLASS,
    EXPERIMENT_ID,
    NATIVE_LAG_DAYS,
    TRANSACTION_COST_BPS,
    attach_lagged_native,
    attach_relative,
    build_price_features,
    build_relative_market,
    candidate_features,
)

WINNER = "V4_7D_VOLATILITY_STATE_EXTRA_TREES"
ELIGIBLE_HORIZON = 7
INELIGIBLE_HORIZONS = (30, 365)
EXPECTED_ASSETS = ("avalanche", "bitcoin", "chainlink", "ethereum", "solana", "xrp")
EXPECTED_HOLDOUT_ORIGINS_PER_ASSET = 10
EXPECTED_TOTAL_HOLDOUT_PREDICTIONS = 60
EXPECTED_V3_RESULTS_SHA256 = "33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1"
EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2"
EXPECTED_DEVELOPMENT_RESULTS_SHA256 = "a44e237112bf6521c8a770de120d4a0104731c280d7009568e6618cca1c1fbfb"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def summarize(frame: pd.DataFrame) -> dict:
    require(len(frame) == EXPECTED_TOTAL_HOLDOUT_PREDICTIONS, "Incomplete V4 7d final-holdout prediction coverage")
    observed = frame["observed_positive"].astype(int)
    predicted = frame["predicted_positive"].astype(int)
    baseline = frame["baseline_positive"].astype(int)
    model_correct = (predicted == observed).astype(int)
    baseline_correct = (baseline == observed).astype(int)
    direction = float(model_correct.mean() * 100.0)
    baseline_accuracy = float(baseline_correct.mean() * 100.0)
    delta = direction - baseline_accuracy

    by_asset = {}
    positive_asset_gains = []
    for asset, group in frame.groupby("asset_id"):
        require(len(group) == EXPECTED_HOLDOUT_ORIGINS_PER_ASSET, f"Incomplete 7d holdout coverage for {asset}")
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

    require(tuple(sorted(by_asset)) == EXPECTED_ASSETS, "Unexpected asset coverage in V4 7d final holdout")
    nonnegative_assets = sum(1 for row in by_asset.values() if float(row["baseline_adjusted_skill_pp"]) >= 0)
    total_positive_asset_gain = int(sum(positive_asset_gains))
    max_positive_asset_gain = int(max(positive_asset_gains)) if positive_asset_gains else 0
    single_asset_majority = bool(total_positive_asset_gain > 0 and max_positive_asset_gain > total_positive_asset_gain / 2)

    ordered = frame.sort_values(["asset_id", "forecast_date"]).copy()
    ordered["position"] = np.where(ordered["predicted_positive"].astype(int) == 1, 1.0, -1.0)
    ordered["previous_position"] = ordered.groupby("asset_id")["position"].shift(1).fillna(0.0)
    ordered["turnover"] = (ordered["position"] - ordered["previous_position"]).abs()
    ordered["strategy_return_pct_after_cost"] = (
        ordered["position"] * ordered["actual_return_pct"]
        - ordered["turnover"] * (TRANSACTION_COST_BPS / 100.0)
    )
    mean_economic = float(ordered["strategy_return_pct_after_cost"].mean())
    raw_brier = float(brier_score_loss(
        observed,
        np.clip(frame["raw_probability_positive"].astype(float), 1e-4, 1 - 1e-4),
    ))

    confirmation = bool(
        delta > 0
        and nonnegative_assets >= 4
        and not single_asset_majority
        and mean_economic > 0
        and len(frame) == EXPECTED_TOTAL_HOLDOUT_PREDICTIONS
    )
    return {
        "final_holdout_rows": int(len(frame)),
        "directional_accuracy_pct": direction,
        "training_window_majority_baseline_accuracy_pct": baseline_accuracy,
        "model_minus_baseline_accuracy_pct_points": delta,
        "raw_brier_score": raw_brier,
        "assets_nonnegative_baseline_adjusted_skill": int(nonnegative_assets),
        "single_asset_explains_majority_of_positive_gain": single_asset_majority,
        "mean_sign_strategy_return_pct_after_15bps_cost": mean_economic,
        "turnover_units": float(ordered["turnover"].sum()),
        "by_asset": by_asset,
        "complete_prediction_coverage": True,
        "final_holdout_confirmation_pass": confirmation,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--v3-results", required=True)
    parser.add_argument("--v4-manifest", required=True)
    parser.add_argument("--development-results", required=True)
    parser.add_argument("--decision-freeze", required=True)
    parser.add_argument("--evaluation-contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    paths = {
        "database": Path(args.database).resolve(),
        "v2": Path(args.v2_manifest).resolve(),
        "v3": Path(args.v3_manifest).resolve(),
        "v3_results": Path(args.v3_results).resolve(),
        "v4": Path(args.v4_manifest).resolve(),
        "development_results": Path(args.development_results).resolve(),
        "decision_freeze": Path(args.decision_freeze).resolve(),
        "evaluation_contract": Path(args.evaluation_contract).resolve(),
    }
    output = Path(args.output).resolve()
    for path in paths.values():
        require(path.is_file(), f"Required V4 7d final-holdout input missing: {path}")
    require(not output.exists(), "V4 7d final-holdout output already exists; refusing overwrite")

    before = {name: sha256(path) for name, path in paths.items()}
    require(before["v3_results"] == EXPECTED_V3_RESULTS_SHA256, "Unexpected V3 development-results hash")
    require(before["development_results"] == EXPECTED_DEVELOPMENT_RESULTS_SHA256, "Unexpected V4 development-results hash")

    v2 = json.loads(paths["v2"].read_text(encoding="utf-8"))
    v3 = json.loads(paths["v3"].read_text(encoding="utf-8"))
    v3_results = json.loads(paths["v3_results"].read_text(encoding="utf-8"))
    v4 = json.loads(paths["v4"].read_text(encoding="utf-8"))
    development_results = json.loads(paths["development_results"].read_text(encoding="utf-8"))
    freeze = json.loads(paths["decision_freeze"].read_text(encoding="utf-8"))
    contract = json.loads(paths["evaluation_contract"].read_text(encoding="utf-8"))

    require(v3_results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout has already been viewed")
    require(v4.get("manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Unexpected V4 manifest hash")
    require(manifest_content_hash(v4) == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "V4 manifest canonical content hash mismatch")
    require(development_results.get("v4_final_holdout_outcomes_viewed") is False, "V4 final holdout already viewed in development evidence")
    require(development_results.get("selected_winners", {}).get("7") == WINNER, "Frozen 7d winner does not match development results")
    require(development_results.get("selected_winners", {}).get("30") is None, "30d unexpectedly has a qualified winner")
    require(development_results.get("selected_winners", {}).get("365") is None, "365d unexpectedly has a qualified winner")

    require(freeze.get("development_results_sha256") == EXPECTED_DEVELOPMENT_RESULTS_SHA256, "Decision freeze is not pinned to V4 development results")
    require(freeze.get("development_decisions_frozen") is True, "V4 development decisions are not frozen")
    require(freeze["decisions"]["7"].get("decision") == WINNER, "Unexpected frozen 7d winner")
    require(freeze["decisions"]["7"].get("eligible_for_v4_final_holdout") is True, "7d final holdout not authorized")
    require(freeze["decisions"]["30"].get("eligible_for_v4_final_holdout") is False, "30d final holdout incorrectly authorized")
    require(freeze["decisions"]["365"].get("eligible_for_v4_final_holdout") is False, "365d final holdout incorrectly authorized")
    require(freeze["v4_final_holdout_policy"].get("eligible_horizons") == [7], "Unexpected final-holdout eligible horizons")
    require(freeze["v4_final_holdout_policy"].get("ineligible_horizons") == [30, 365], "Unexpected final-holdout ineligible horizons")
    require(freeze["v4_final_holdout_policy"].get("post_holdout_tuning_allowed") is False, "Post-holdout tuning was enabled")

    require(contract.get("evaluation_scope") == "7D_FINAL_HOLDOUT_ONLY", "Unexpected V4 final-holdout evaluation scope")
    require(contract.get("development_results_sha256") == EXPECTED_DEVELOPMENT_RESULTS_SHA256, "Evaluation contract not pinned to development results")
    require(contract.get("v4_manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Evaluation contract not pinned to V4 manifest")
    require(contract.get("frozen_winner") == WINNER, "Evaluation contract winner changed")
    require(contract.get("eligible_horizon_days") == ELIGIBLE_HORIZON, "Evaluation contract horizon changed")
    require(contract.get("ineligible_horizons_days") == list(INELIGIBLE_HORIZONS), "Evaluation contract ineligible horizons changed")
    require(contract.get("expected_assets") == list(EXPECTED_ASSETS), "Evaluation contract assets changed")
    require(contract.get("expected_holdout_origins_per_asset") == EXPECTED_HOLDOUT_ORIGINS_PER_ASSET, "Evaluation contract per-asset holdout count changed")
    require(contract.get("expected_total_holdout_predictions") == EXPECTED_TOTAL_HOLDOUT_PREDICTIONS, "Evaluation contract coverage changed")
    require(contract["training_policy"].get("post_holdout_tuning_allowed") is False, "Evaluation contract permits post-holdout tuning")
    require(contract["confirmation_gate"].get("fold_concentration_gate_applies") is False, "Unexpected fold concentration rule in final holdout")
    require(contract.get("v4_final_holdout_outcomes_viewed_before_contract") is False, "Evaluation contract was frozen after V4 holdout exposure")
    require(contract.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout was exposed before V4 evaluation")

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_final_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}
    all_v4_groups = {(g["asset_id"], int(g["horizon_days"])): g for g in v4["groups"]}
    seven_day_groups = {
        asset: group
        for (asset, horizon), group in all_v4_groups.items()
        if int(horizon) == ELIGIBLE_HORIZON
    }
    require(tuple(sorted(seven_day_groups)) == EXPECTED_ASSETS, "Unexpected V4 7d group membership")
    for horizon in INELIGIBLE_HORIZONS:
        require(any(int(g["horizon_days"]) == horizon for g in v4["groups"]), f"Missing governed {horizon}d manifest groups")

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    rows = []
    with tempfile.TemporaryDirectory(prefix="crypto_v4_7d_final_holdout_") as tmp:
        temp_db = Path(tmp) / paths["database"].name
        shutil.copy2(paths["database"], temp_db)
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.platform import connect, load_all

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

            for asset in EXPECTED_ASSETS:
                group = seven_day_groups[asset]
                dev_dates = list(group["v4_development_origin_dates"])
                holdout_dates = list(group["v4_final_holdout_origin_dates"])
                require(len(dev_dates) == 50, f"Unexpected V4 development count for {asset} 7d")
                require(len(holdout_dates) == EXPECTED_HOLDOUT_ORIGINS_PER_ASSET, f"Unexpected V4 final holdout count for {asset} 7d")
                require(max(dev_dates) < min(holdout_dates), f"V4 7d holdout does not follow development for {asset}")

                asset_frame = prices[prices["asset_id"] == asset].copy()
                v3_features = runner.build_features(asset_frame, ELIGIBLE_HORIZON).reset_index(drop=True)
                v3_mask = pd.to_datetime(v3_features["observation_date"]).dt.date.astype(str).isin(v3_final_dates[(asset, ELIGIBLE_HORIZON)])
                v3_features.loc[v3_mask, "target_return"] = np.nan
                selected_v3_indices = selected_v3_origins_for_group(
                    v3_features,
                    ELIGIBLE_HORIZON,
                    runner,
                    context,
                    v3_relative,
                    asset,
                    v2_dates[(asset, ELIGIBLE_HORIZON)],
                    v3_final_dates[(asset, ELIGIBLE_HORIZON)],
                )
                selected_v3_dates = {
                    pd.Timestamp(v3_features.iloc[index]["observation_date"]).date().isoformat()
                    for index in selected_v3_indices
                }
                excluded = (
                    set(v2_dates[(asset, ELIGIBLE_HORIZON)])
                    | set(v3_final_dates[(asset, ELIGIBLE_HORIZON)])
                    | selected_v3_dates
                    | set(holdout_dates)
                )

                evaluation_features = build_price_features(asset_frame, ELIGIBLE_HORIZON).reset_index(drop=True)
                model_features = evaluation_features.copy()
                holdout_mask = pd.to_datetime(model_features["observation_date"]).dt.date.astype(str).isin(holdout_dates)
                model_features.loc[holdout_mask, ["target_return", "target_positive", "target_exceeds_15pct"]] = np.nan
                date_to_index = {
                    pd.Timestamp(row.observation_date).date().isoformat(): int(row.Index)
                    for row in model_features[["observation_date"]].itertuples(index=True)
                }
                columns = candidate_features(ELIGIBLE_HORIZON, WINNER)

                for date_key in holdout_dates:
                    require(date_key in date_to_index, f"V4 7d final-holdout origin missing from feature frame: {asset} {date_key}")
                    origin_idx = date_to_index[date_key]
                    actual_return = float(evaluation_features.iloc[origin_idx]["target_return"])
                    require(np.isfinite(actual_return), f"Missing exact V4 7d final-holdout outcome for {asset} {date_key}")
                    origin_date, train, validation, current = v4_split_origin(
                        model_features,
                        origin_idx,
                        ELIGIBLE_HORIZON,
                        runner,
                        excluded,
                    )
                    train_majority = int((train["target_return"].astype(float) > 0).mean() >= 0.5)
                    train_f = attach_relative(attach_lagged_native(train, context, columns), v4_relative, asset, columns)
                    val_f = attach_relative(attach_lagged_native(validation, context, columns), v4_relative, asset, columns)
                    current_f = attach_relative(attach_lagged_native(current, context, columns), v4_relative, asset, columns)
                    probability, predicted_return = fit_predict(
                        ELIGIBLE_HORIZON,
                        WINNER,
                        train_f,
                        val_f,
                        current_f,
                        columns,
                        random_state,
                    )
                    require(predicted_return is None, "7d frozen classifier unexpectedly returned regression prediction")
                    rows.append({
                        "asset_id": asset,
                        "horizon_days": ELIGIBLE_HORIZON,
                        "forecast_date": origin_date.date().isoformat(),
                        "family": WINNER,
                        "predicted_positive": int(probability >= 0.5),
                        "raw_probability_positive": float(probability),
                        "observed_positive": int(actual_return > 0),
                        "actual_return_pct": actual_return * 100.0,
                        "baseline_positive": train_majority,
                    })
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    after = {name: sha256(path) for name, path in paths.items()}
    require(before == after, "Source evidence changed during V4 7d final-holdout evaluation")

    frame = pd.DataFrame(rows)
    metrics = summarize(frame)
    report = {
        "experiment_id": EXPERIMENT_ID,
        "evidence_class": EVIDENCE_CLASS,
        "strict_point_in_time_claim_allowed": False,
        "evaluation_scope": "7D_FINAL_HOLDOUT_ONLY",
        "frozen_winner": WINNER,
        "development_results_sha256": EXPECTED_DEVELOPMENT_RESULTS_SHA256,
        "v4_manifest_content_sha256": EXPECTED_V4_MANIFEST_CONTENT_SHA256,
        "final_holdout_metrics": metrics,
        "opened_v4_final_holdout_horizons": [ELIGIBLE_HORIZON],
        "unopened_v4_final_holdout_horizons": list(INELIGIBLE_HORIZONS),
        "v4_7d_final_holdout_outcomes_viewed": True,
        "v4_30d_final_holdout_outcomes_viewed": False,
        "v4_365d_final_holdout_outcomes_viewed": False,
        "v3_final_holdout_outcomes_viewed": False,
        "post_holdout_tuning_allowed": False,
        "recommendation_policy_changed": False,
        "production_promotion_allowed": False,
        "next_gate": "PRESERVE_AND_REVIEW_V4_7D_FINAL_HOLDOUT_RESULT_NO_TUNING",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("CRYPTO_V4_7D_FINAL_HOLDOUT_EVALUATION=PASS")
    print(f"V4_7D_FINAL_HOLDOUT_CONFIRMATION={'PASS' if metrics['final_holdout_confirmation_pass'] else 'FAIL'}")
    print(f"V4_7D_FINAL_HOLDOUT_ROWS={metrics['final_holdout_rows']}")
    print(f"V4_7D_DIRECTIONAL_ACCURACY_PCT={metrics['directional_accuracy_pct']}")
    print(f"V4_7D_BASELINE_ACCURACY_PCT={metrics['training_window_majority_baseline_accuracy_pct']}")
    print(f"V4_7D_BASELINE_ADJUSTED_SKILL_PP={metrics['model_minus_baseline_accuracy_pct_points']}")
    print(f"V4_7D_NONNEGATIVE_ASSETS={metrics['assets_nonnegative_baseline_adjusted_skill']}")
    print(f"V4_7D_SINGLE_ASSET_MAJORITY={str(metrics['single_asset_explains_majority_of_positive_gain']).upper()}")
    print(f"V4_7D_MEAN_SIGN_RETURN_AFTER_15BPS_PCT={metrics['mean_sign_strategy_return_pct_after_15bps_cost']}")
    print("V4_30D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V4_365D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("POST_HOLDOUT_TUNING_ALLOWED=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
