from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

EXPECTED_RESULTS_SHA256 = "a44e237112bf6521c8a770de120d4a0104731c280d7009568e6618cca1c1fbfb"
EXPECTED_MANIFEST_CONTENT_SHA256 = "6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2"
WINNER = "V4_7D_VOLATILITY_STATE_EXTRA_TREES"
EXPECTED_ASSETS = ["avalanche", "bitcoin", "chainlink", "ethereum", "solana", "xrp"]


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--v4-manifest", required=True)
    parser.add_argument("--development-results", required=True)
    parser.add_argument("--decision-freeze", required=True)
    parser.add_argument("--evaluation-contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    runner_path = Path(args.runner).resolve()
    manifest_path = Path(args.v4_manifest).resolve()
    results_path = Path(args.development_results).resolve()
    freeze_path = Path(args.decision_freeze).resolve()
    contract_path = Path(args.evaluation_contract).resolve()
    output_path = Path(args.output).resolve()

    for path in (runner_path, manifest_path, results_path, freeze_path, contract_path):
        require(path.is_file(), f"Missing V4 7d final-holdout validation input: {path}")
    require(not output_path.exists(), "V4 7d final-holdout output already exists before runner authorization")
    require(sha256(results_path) == EXPECTED_RESULTS_SHA256, "Unexpected authoritative V4 development-results hash")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    require(manifest.get("manifest_content_sha256") == EXPECTED_MANIFEST_CONTENT_SHA256, "Unexpected V4 manifest content hash")
    require(manifest_content_hash(manifest) == EXPECTED_MANIFEST_CONTENT_SHA256, "V4 manifest canonical hash mismatch")
    require(results.get("v4_final_holdout_outcomes_viewed") is False, "V4 final holdout already viewed in development results")
    require(results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout already viewed")
    require(results.get("selected_winners", {}).get("7") == WINNER, "Development results do not freeze expected 7d winner")
    require(results.get("selected_winners", {}).get("30") is None, "30d unexpectedly qualified")
    require(results.get("selected_winners", {}).get("365") is None, "365d unexpectedly qualified")

    require(freeze.get("development_decisions_frozen") is True, "V4 development decisions are not frozen")
    require(freeze["v4_final_holdout_policy"].get("eligible_horizons") == [7], "Unexpected final-holdout eligible horizons")
    require(freeze["v4_final_holdout_policy"].get("ineligible_horizons") == [30, 365], "Unexpected final-holdout ineligible horizons")
    require(freeze["v4_final_holdout_policy"].get("post_holdout_tuning_allowed") is False, "Post-holdout tuning is allowed")

    require(contract.get("evaluation_scope") == "7D_FINAL_HOLDOUT_ONLY", "Final-holdout contract is not 7d-only")
    require(contract.get("development_results_sha256") == EXPECTED_RESULTS_SHA256, "Final-holdout contract not pinned to V4 development results")
    require(contract.get("v4_manifest_content_sha256") == EXPECTED_MANIFEST_CONTENT_SHA256, "Final-holdout contract not pinned to V4 manifest")
    require(contract.get("frozen_winner") == WINNER, "Final-holdout contract winner changed")
    require(contract.get("eligible_horizon_days") == 7, "Final-holdout contract horizon changed")
    require(contract.get("ineligible_horizons_days") == [30, 365], "Final-holdout contract ineligible horizons changed")
    require(contract.get("expected_assets") == EXPECTED_ASSETS, "Final-holdout contract asset set changed")
    require(contract.get("expected_holdout_origins_per_asset") == 10, "Final-holdout contract per-asset count changed")
    require(contract.get("expected_total_holdout_predictions") == 60, "Final-holdout contract total coverage changed")
    require(contract["training_policy"].get("all_v4_7d_final_holdout_targets_masked_from_training_and_validation") is True, "7d holdout target masking not required")
    require(contract["training_policy"].get("post_holdout_tuning_allowed") is False, "Contract permits post-holdout tuning")
    require(contract["confirmation_gate"].get("aggregate_baseline_adjusted_directional_skill_gt_zero") is True, "Aggregate directional confirmation gate missing")
    require(contract["confirmation_gate"].get("assets_nonnegative_baseline_adjusted_skill_minimum") == 4, "Asset breadth confirmation gate changed")
    require(contract["confirmation_gate"].get("single_asset_majority_positive_gain_allowed") is False, "Asset concentration guardrail changed")
    require(contract["confirmation_gate"].get("mean_sign_strategy_return_after_15bps_cost_gt_zero") is True, "Economic confirmation gate missing")
    require(contract["confirmation_gate"].get("complete_prediction_coverage_required") is True, "Coverage confirmation gate missing")
    require(contract["confirmation_gate"].get("fold_concentration_gate_applies") is False, "Development fold rule incorrectly applied to final holdout")
    require(contract.get("v4_final_holdout_outcomes_viewed_before_contract") is False, "V4 holdout was viewed before confirmation contract")

    source = runner_path.read_text(encoding="utf-8")
    ast.parse(source)
    required_literals = [
        'WINNER = "V4_7D_VOLATILITY_STATE_EXTRA_TREES"',
        "ELIGIBLE_HORIZON = 7",
        "INELIGIBLE_HORIZONS = (30, 365)",
        "EXPECTED_TOTAL_HOLDOUT_PREDICTIONS = 60",
        "EXPECTED_HOLDOUT_ORIGINS_PER_ASSET = 10",
        "evaluation_features = build_price_features(asset_frame, ELIGIBLE_HORIZON)",
        "model_features = evaluation_features.copy()",
        'model_features.loc[holdout_mask, ["target_return", "target_positive", "target_exceeds_15pct"]] = np.nan',
        "selected_v3_origins_for_group",
        "v4_split_origin",
        "candidate_features(ELIGIBLE_HORIZON, WINNER)",
        "fit_predict(",
        "set(holdout_dates)",
        "single_asset_explains_majority_of_positive_gain",
        "mean_sign_strategy_return_pct_after_15bps_cost",
        "brier_score_loss",
        '"opened_v4_final_holdout_horizons": [ELIGIBLE_HORIZON]',
        '"unopened_v4_final_holdout_horizons": list(INELIGIBLE_HORIZONS)',
        '"v4_30d_final_holdout_outcomes_viewed": False',
        '"v4_365d_final_holdout_outcomes_viewed": False',
        '"v3_final_holdout_outcomes_viewed": False',
        '"post_holdout_tuning_allowed": False',
        '"recommendation_policy_changed": False',
        '"production_promotion_allowed": False',
        '"PRESERVE_AND_REVIEW_V4_7D_FINAL_HOLDOUT_RESULT_NO_TUNING"',
        "TemporaryDirectory",
        "shutil.copy2",
        "require(before == after",
        "refusing overwrite",
    ]
    for literal in required_literals:
        require(literal in source, f"Missing governed V4 7d runner marker: {literal}")

    require('build_price_features(asset_frame, 30)' not in source, "Runner derives prohibited 30d final-holdout targets")
    require('build_price_features(asset_frame, 365)' not in source, "Runner derives prohibited 365d final-holdout targets")
    require('candidate_features(30' not in source, "Runner scores prohibited 30d candidate")
    require('candidate_features(365' not in source, "Runner scores prohibited 365d candidate")

    seven_day_groups = [g for g in manifest["groups"] if int(g["horizon_days"]) == 7]
    require(len(seven_day_groups) == 6, "Unexpected number of V4 7d groups")
    require(sorted(g["asset_id"] for g in seven_day_groups) == EXPECTED_ASSETS, "Unexpected 7d asset membership")
    require(all(len(g["v4_final_holdout_origin_dates"]) == 10 for g in seven_day_groups), "Unexpected 7d final-holdout count")

    print("CRYPTO_V4_7D_FINAL_HOLDOUT_RUNNER_VALIDATION=PASS")
    print("ELIGIBLE_HORIZON=7")
    print(f"FROZEN_WINNER={WINNER}")
    print("EXPECTED_ASSETS=6")
    print("EXPECTED_FINAL_HOLDOUT_ROWS=60")
    print("ALL_7D_HOLDOUT_TARGETS_MASKED_FROM_MODEL_FIT=TRUE")
    print("V4_30D_FINAL_HOLDOUT_DERIVATION_ALLOWED=FALSE")
    print("V4_365D_FINAL_HOLDOUT_DERIVATION_ALLOWED=FALSE")
    print("POST_HOLDOUT_TUNING_ALLOWED=FALSE")
    print("MODEL_FITTING_EXECUTED=FALSE")
    print("V4_7D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V4_30D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V4_365D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("NEXT_GATE=AUTHORIZE_ONE_TIME_V4_7D_FINAL_HOLDOUT_EVALUATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
