from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "run_v3_per_horizon_development_tournament.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(text)

    required_literals = [
        'EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_TOURNAMENT_V3"',
        'EVIDENCE_CLASS = "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME"',
        'EXPECTED_V3_MANIFEST_CONTENT_SHA256 = "69a848d935509ac692d6af50f6e95d72fb3c0a22925a39d2434e678e1e5c628d"',
        "DEVELOPMENT_FOLDS = 5",
        "ORIGINS_PER_FOLD = 10",
        '"PRICE_ONLY_DIRECTION_FIRST"',
        '"NATIVE_CONTEXT_DIRECTION_FIRST"',
        '"GRADIENT_BOOSTED_DIRECTION"',
        '"HIST_GRADIENT_BOOSTED_DIRECTION"',
        '"EXTRA_TREES_DIRECTION"',
        '"RELATIVE_MARKET_DIRECTION"',
        'features.loc[v3_mask, "target_return"] = np.nan',
        'excluded = set(v2_dates[key]) | set(v3_dates[key])',
        'attach_lagged_native(train, context, contract["native"])',
        'attach_lagged_native(validation, context, contract["native"])',
        'attach_lagged_native(current, context, contract["native"])',
        '"v3_final_holdout_outcomes_viewed": False',
        '"recommendation_policy_changed": False',
        '"production_promotion_allowed": False',
    ]
    for literal in required_literals:
        require(literal in text, f"Required tournament control missing: {literal}")

    require("NATIVE_LAG_DAYS" in text, "Governed lag map missing")
    for feature, lag in {
        "btc_return_30d_pct": 1,
        "core_breadth_above_sma50_pct": 1,
        "core_median_return_30d_pct": 1,
        "fear_greed_index": 1,
        "stablecoin_supply_usd": 1,
        "stablecoin_growth_30d_pct": 1,
        "dollar_index": 2,
        "vix": 2,
        "macro_liquidity_score": 2,
        "risk_appetite_score": 2,
    }.items():
        require(f'"{feature}": {lag}' in text, f"Governed lag missing for {feature}")

    require("7: {" in text and '"native": []' in text, "7d native-context exclusion missing")
    require(all(f"{h}: {{" in text for h in [7, 30, 90, 180, 365]), "Five horizon contracts missing")
    require("np.linspace(0, len(safe_indices) - 1, required, dtype=int)" in text, "Deterministic chronological development sampling missing")
    require("development_selection_gate_pass" in text, "Per-horizon development gate missing")
    require("assets_nonnegative_baseline_adjusted_skill" in text, "Asset robustness metric missing")
    require("single_asset_explains_majority_of_positive_gain" in text, "Asset dominance guardrail missing")
    require("choose_winner" in text, "Independent winner selection missing")

    # The tournament may read V3 membership, but must never contain a path that
    # explicitly evaluates a V3 holdout outcome before winners are frozen.
    prohibited = [
        "evaluate_v3_holdout",
        "v3_holdout_actual_return",
        "recommendation_threshold",
        "production_promote",
    ]
    for token in prohibited:
        require(token not in text, f"Prohibited pre-winner behavior present: {token}")

    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    for required_function in {
        "attach_lagged_native",
        "split_origin",
        "fit_probability",
        "summarize_family",
        "choose_winner",
        "main",
    }:
        require(required_function in function_names, f"Required function missing: {required_function}")

    print("CRYPTO_V3_PER_HORIZON_DEVELOPMENT_TOURNAMENT_HARNESS_VALIDATION=PASS")
    print("INDEPENDENT_HORIZON_TOURNAMENTS=5")
    print("DEVELOPMENT_FOLDS=5")
    print("ORIGINS_PER_FOLD_PER_SUPPORTED_ASSET=10")
    print("V2_CONSUMED_ORIGINS_EXCLUDED_FROM_DEVELOPMENT=TRUE")
    print("V3_FINAL_HOLDOUT_ORIGINS_EXCLUDED_FROM_DEVELOPMENT=TRUE")
    print("V3_FINAL_HOLDOUT_LABELS_MASKED_BEFORE_DEVELOPMENT_SELECTION=TRUE")
    print("GOVERNED_NATIVE_CONTEXT_LAGS_ENFORCED=TRUE")
    print("SEVEN_DAY_NATIVE_CONTEXT_ALLOWED=FALSE")
    print("STRICT_POINT_IN_TIME_CLAIM_ALLOWED=FALSE")
    print("RECOMMENDATION_POLICY_CHANGED=FALSE")
    print("PRODUCTION_PROMOTION_ALLOWED=FALSE")
    print("NEXT_GATE=RUN_V3_PER_HORIZON_DEVELOPMENT_TOURNAMENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
