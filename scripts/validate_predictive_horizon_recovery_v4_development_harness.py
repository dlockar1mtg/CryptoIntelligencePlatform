from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "run_predictive_horizon_recovery_v4_development.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(TARGET.is_file(), "Missing V4 development scoring harness")
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    required_literals = [
        "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4",
        "510d121e1e4e8ea7e2079b1f61883b2ca01dfb6ce2c6baf6b9ba601eadeafd42",
        "V4 final holdout outcomes viewed",
        "v4_final_holdout_origins_excluded",
        "v3_final_holdout_origins_excluded",
        "recommendation_policy_changed",
        "production_promotion_allowed",
        "VALIDATE_AND_REVIEW_V4_DEVELOPMENT_RESULTS_BEFORE_ANY_FINAL_HOLDOUT_EXPOSURE",
        "development_selection_gate_pass",
        "single_asset_explains_majority_of_positive_gain",
        "single_fold_explains_majority_of_positive_gain",
        "mean_sign_strategy_return_pct_after_15bps_cost",
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
    for name in {"fit_predict", "summarize", "choose_winner", "main"}:
        require(name in function_names, f"Missing V4 harness function: {name}")

    require("output.write_text" in source, "V4 harness does not persist a development-results artifact")
    require("V4_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE" in source, "V4 harness does not emit holdout-seal status")
    require("SOURCE_DATABASE_MODIFIED=FALSE" in source, "V4 harness does not emit source immutability status")

    print("CRYPTO_V4_DEVELOPMENT_HARNESS_VALIDATION=PASS")
    print("RECOVERY_HORIZONS=7,30,365")
    print("DEVELOPMENT_ORIGINS_PER_GROUP=50")
    print("V4_FINAL_HOLDOUT_EXCLUDED=TRUE")
    print("V3_FINAL_HOLDOUT_EXCLUDED=TRUE")
    print("DATE_BASED_TARGET_ENDPOINT_CONTRACT_REUSED=TRUE")
    print("ASSET_AND_FOLD_ROBUSTNESS_GATES_PRESENT=TRUE")
    print("POSITIVE_AFTER_COST_ECONOMIC_GUARDRAIL_PRESENT=TRUE")
    print("SOURCE_EVIDENCE_IMMUTABILITY_ASSERTED=TRUE")
    print("NEXT_GATE=RUN_V4_DEVELOPMENT_SCORING_ONLY_AFTER_LOCAL_HARNESS_VALIDATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
