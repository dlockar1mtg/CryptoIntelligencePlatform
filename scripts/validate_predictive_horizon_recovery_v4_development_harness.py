from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "run_predictive_horizon_recovery_v4_development.py"
EXPECTED_EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2"
EXPECTED_GROUPS = 17
EXPECTED_DEV_ORIGINS = 50
DEFAULT_FINAL_HOLDOUT_ORIGINS = 10
AVALANCHE365_FINAL_HOLDOUT_ORIGINS = 9


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v4-manifest", required=True)
    parser.add_argument("--superseded-results", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.v4_manifest).resolve()
    superseded_path = Path(args.superseded_results).resolve()
    output_path = Path(args.output).resolve()

    require(TARGET.is_file(), "Missing V4 development scoring harness")
    require(manifest_path.is_file(), "Missing candidate-safe V4 manifest")
    require(superseded_path.is_file(), "Missing preserved superseded V4 development results")
    require(not output_path.exists(), "Current V4 development-results path must be absent before rescoring")
    require(superseded_path != output_path, "Superseded and current V4 result paths must differ")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("experiment_id") == EXPECTED_EXPERIMENT_ID, "Unexpected V4 experiment id")
    require(manifest.get("manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Unexpected V4 manifest content hash")
    require(manifest_content_hash(manifest) == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "V4 manifest canonical hash mismatch")
    require(manifest.get("candidate_safe_membership_required") is True, "Candidate-safe membership control missing")
    require(manifest.get("avalanche365_exception_governed") is True, "Avalanche365 governed exception missing")
    require(manifest.get("exact_calendar_target_date_required") is True, "Exact-calendar target control missing")
    require(manifest.get("holdout_outcomes_viewed_before_freeze") is False, "V4 final holdout has been viewed")
    require(manifest.get("holdout_outcome_values_read_during_membership_selection") is False, "V4 holdout outcomes were read during membership selection")
    require(manifest.get("v3_final_holdout_reused") is False, "V3 final holdout was reused")

    groups = manifest.get("groups")
    require(isinstance(groups, list) and len(groups) == EXPECTED_GROUPS, "Unexpected V4 group manifest")
    for group in groups:
        asset = str(group["asset_id"])
        horizon = int(group["horizon_days"])
        dev = list(group["v4_development_origin_dates"])
        holdout = list(group["v4_final_holdout_origin_dates"])
        required_holdout = expected_holdout_count(asset, horizon)
        require(len(dev) == EXPECTED_DEV_ORIGINS, f"Unexpected development count for {asset} {horizon}d")
        require(len(holdout) == required_holdout, f"Unexpected holdout count for {asset} {horizon}d")
        require(set(dev).isdisjoint(holdout), f"Development/final overlap for {asset} {horizon}d")
        require(max(dev) < min(holdout), f"Final holdout is not later than development for {asset} {horizon}d")

    superseded = json.loads(superseded_path.read_text(encoding="utf-8"))
    require(superseded.get("experiment_id") == EXPECTED_EXPERIMENT_ID, "Superseded V4 results have unexpected experiment id")
    require(superseded.get("v4_final_holdout_outcomes_viewed") is False, "Superseded V4 results indicate V4 final-holdout exposure")
    require(superseded.get("v3_final_holdout_outcomes_viewed") is False, "Superseded V4 results indicate V3 final-holdout exposure")

    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_experiment_id = False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "scripts.v4_horizon_recovery_model_spec":
            if any(alias.name == "EXPERIMENT_ID" for alias in node.names):
                imported_experiment_id = True
                break
    require(imported_experiment_id, "V4 harness does not import governed EXPERIMENT_ID")

    required_literals = [
        EXPECTED_V4_MANIFEST_CONTENT_SHA256,
        "candidate_safe_membership_required",
        "avalanche365_exception_governed",
        "exact_calendar_target_date_required",
        "holdout_outcomes_viewed_before_freeze",
        "holdout_outcome_values_read_during_membership_selection",
        "v4_final_holdout_origins_excluded",
        "v3_final_holdout_origins_excluded",
        "recommendation_policy_changed",
        "production_promotion_allowed",
        "VALIDATE_AND_REVIEW_V4_DEVELOPMENT_RESULTS_BEFORE_ANY_FINAL_HOLDOUT_EXPOSURE",
        "development_selection_gate_pass",
        "single_asset_explains_majority_of_positive_gain",
        "single_fold_explains_majority_of_positive_gain",
        "mean_sign_strategy_return_pct_after_15bps_cost",
        "fold_baseline_adjusted_skill_std_pp",
        "CANDIDATE_SIMPLICITY_ORDER",
        "AVALANCHE365_FINAL_HOLDOUT_ORIGINS = 9",
    ]
    for literal in required_literals:
        require(literal in source, f"Missing governed V4 harness marker: {literal}")

    require("v4_split_origin" in source, "V4 harness does not reuse validated chronological split contract")
    require("build_price_features" in source, "V4 harness does not use exact-date price feature builder")
    require("attach_lagged_native" in source, "V4 harness missing governed native-context lag attachment")
    require("attach_relative" in source, "V4 harness missing relative-market feature attachment")
    require("holdout_mask" in source and "target_return" in source, "V4 harness does not mask final-holdout labels")
    require("refusing overwrite" in source, "V4 harness does not refuse output overwrite")
    require("TemporaryDirectory" in source and "copy2" in source, "V4 harness does not isolate database use")
    require("before == after" in source, "V4 harness does not assert source-evidence immutability")
    require("EXPECTED_DEV_ORIGINS = 50" in source, "V4 harness development-origin count is not frozen")

    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    require(any(isinstance(call.func, ast.Name) and call.func.id == "fit_predict" for call in calls), "V4 harness never calls fit_predict")
    require(any(isinstance(call.func, ast.Name) and call.func.id == "summarize" for call in calls), "V4 harness never summarizes candidate results")
    require(any(isinstance(call.func, ast.Name) and call.func.id == "choose_winner" for call in calls), "V4 harness never selects development winners")

    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    for name in {"fit_predict", "summarize", "choose_winner", "main", "manifest_content_hash", "expected_holdout_count"}:
        require(name in function_names, f"Missing V4 harness function: {name}")

    require("output.write_text" in source, "V4 harness does not persist a development-results artifact")
    require("V4_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE" in source, "V4 harness does not emit V4 holdout-seal status")
    require("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE" in source, "V4 harness does not emit V3 holdout-seal status")
    require("SOURCE_DATABASE_MODIFIED=FALSE" in source, "V4 harness does not emit source immutability status")

    print("CRYPTO_V4_DEVELOPMENT_HARNESS_VALIDATION=PASS")
    print(f"V4_MANIFEST_CONTENT_SHA256={EXPECTED_V4_MANIFEST_CONTENT_SHA256}")
    print("RECOVERY_HORIZONS=7,30,365")
    print(f"SUPPORTED_GROUPS={EXPECTED_GROUPS}")
    print(f"DEVELOPMENT_ORIGINS_PER_GROUP={EXPECTED_DEV_ORIGINS}")
    print(f"DEFAULT_FINAL_HOLDOUT_ORIGINS={DEFAULT_FINAL_HOLDOUT_ORIGINS}")
    print(f"AVALANCHE365_FINAL_HOLDOUT_ORIGINS={AVALANCHE365_FINAL_HOLDOUT_ORIGINS}")
    print(f"SUPERSEDED_RESULTS_SHA256={sha256(superseded_path)}")
    print("CURRENT_RESULTS_PATH_ABSENT=TRUE")
    print("V4_FINAL_HOLDOUT_EXCLUDED=TRUE")
    print("V3_FINAL_HOLDOUT_EXCLUDED=TRUE")
    print("DATE_BASED_TARGET_ENDPOINT_CONTRACT_REUSED=TRUE")
    print("ASSET_AND_FOLD_ROBUSTNESS_GATES_PRESENT=TRUE")
    print("POSITIVE_AFTER_COST_ECONOMIC_GUARDRAIL_PRESENT=TRUE")
    print("SOURCE_EVIDENCE_IMMUTABILITY_ASSERTED=TRUE")
    print("MODEL_FITTING_EXECUTED=FALSE")
    print("NEXT_GATE=AUTHORIZE_CANDIDATE_SAFE_V4_DEVELOPMENT_SCORING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
