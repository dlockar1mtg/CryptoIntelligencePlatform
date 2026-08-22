from __future__ import annotations

import json


EXPERIMENT = {
    "experiment_id": "CRYPTO_NATIVE_PREDICTIVE_MODEL_IMPROVEMENT_V1",
    "champion_generation": "M38_PURGED_FEATURE_STABLE_V1",
    "predictive_skill_status_at_start": "NOT_CERTIFIED_FOR_INVESTMENT_TIMING",
    "objective": (
        "Test whether predeclared challenger predictive designs improve true point-in-time "
        "out-of-sample investment-timing evidence without weakening leakage, calibration, "
        "history, or evidence-gap controls."
    ),
    "frozen_controls": [
        "true chronological point-in-time replay",
        "labels must mature before each forecast origin",
        "purged train/validation boundary",
        "training-only feature support bounds",
        "realized-outcome probability calibration with untouched final test",
        "explicit unsupported asset/horizon evidence gaps",
        "generation-aware stability and drift monitoring",
        "no lowering minimum history solely to make an unsupported group pass",
        "no production recommendation-policy changes during forecast experiment",
    ],
    "evaluation_horizons_days": [7, 30, 90, 180, 365],
    "evaluation_assets": [
        "bitcoin",
        "ethereum",
        "solana",
        "chainlink",
        "xrp",
        "avalanche",
    ],
    "champion": {
        "name": "CURRENT_M38_REGRESSION_ENSEMBLE",
        "models": ["GRADIENT_BOOSTING", "RANDOM_FOREST", "BAYESIAN_RIDGE"],
        "feature_family": "CURRENT_PRICE_DERIVED_WITH_OPTIONAL_PROVIDER_FEATURES",
        "ensemble_weighting": "INVERSE_VALIDATION_MAE",
    },
    "challengers": [
        {
            "name": "DIRECTION_FIRST_TWO_STAGE",
            "design": (
                "Train a point-in-time binary direction classifier separately from the return "
                "magnitude regressor; use the classifier only for sign/probability evidence and "
                "retain the regression ensemble for magnitude."
            ),
            "reason": "Current failure is primarily directional skill versus trivial baselines.",
        },
        {
            "name": "HORIZON_SPECIFIC_FEATURE_WINDOWS",
            "design": (
                "Use predeclared horizon-specific subsets of existing point-in-time price-derived "
                "features, with no new external data and no test-driven feature selection."
            ),
            "reason": (
                "The same feature family is currently applied across 7d through 365d despite "
                "materially different prediction horizons."
            ),
        },
        {
            "name": "ROBUST_RETURN_TARGET",
            "design": (
                "Train the magnitude model on a training-window-derived winsorized forward-return "
                "target while evaluating predictions against untouched realized returns."
            ),
            "reason": "Long-horizon return errors remain very large and heavy-tailed.",
        },
    ],
    "primary_metrics": [
        "directional_accuracy_pct",
        "model_minus_majority_accuracy_pct_points",
        "raw_brier_score",
        "leakage_safe_calibrated_brier_score",
        "mae_pct",
        "rmse_pct",
    ],
    "secondary_economic_metrics": [
        "sign_strategy_return_before_costs",
        "sign_strategy_return_after_fixed_transaction_cost",
        "maximum_drawdown",
        "turnover",
    ],
    "required_breakdowns": [
        "asset",
        "horizon",
        "chronological_fold",
        "aggregate_with_asset_and_horizon_counts",
    ],
    "promotion_rules": [
        "A challenger must beat the champion on model-minus-majority directional accuracy in aggregate.",
        "A challenger must not obtain aggregate improvement solely from one asset or one horizon.",
        "No challenger may be promoted if a majority of supported horizons have non-positive model-minus-majority directional accuracy.",
        "Calibration improvement alone cannot establish predictive timing skill.",
        "Long-horizon directional improvement cannot compensate for pathological magnitude error without an explicit bounded-error review.",
        "Any challenger selected after viewing final-test outcomes is exploratory only and must be re-evaluated on a newly isolated holdout before promotion.",
        "Recommendation BUY/HOLD/REDUCE/SELL policy remains outside this forecast-model promotion gate.",
    ],
    "prohibited_shortcuts": [
        "tune features, models, or thresholds directly against the final replay test rows",
        "choose a challenger because it wins only on 365d aggregate accuracy",
        "pool unsupported XRP 365d as if it had valid replay evidence",
        "replace missing evidence with zero, worst case, or synthetic labels",
        "change recommendation action thresholds to improve forecast metrics",
        "claim investment timing skill from in-sample or validation-set metrics",
    ],
    "next_gate": "IMPLEMENT_DISPOSABLE_CHAMPION_CHALLENGER_REPLAY_HARNESS",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(EXPERIMENT["predictive_skill_status_at_start"] == "NOT_CERTIFIED_FOR_INVESTMENT_TIMING", "Start status must remain fail-closed")
    require(EXPERIMENT["evaluation_horizons_days"] == [7, 30, 90, 180, 365], "All governed horizons must be retained")
    require(len(EXPERIMENT["evaluation_assets"]) == 6, "Expected governed six-asset universe")
    require(len(EXPERIMENT["challengers"]) == 3, "Expected three predeclared challenger families")
    require("model_minus_majority_accuracy_pct_points" in EXPERIMENT["primary_metrics"], "Baseline-adjusted directional skill must be primary")
    require("leakage_safe_calibrated_brier_score" in EXPERIMENT["primary_metrics"], "Leakage-safe calibration must be measured")
    require(any("majority of supported horizons" in rule for rule in EXPERIMENT["promotion_rules"]), "Cross-horizon robustness rule missing")
    require(any("newly isolated holdout" in rule for rule in EXPERIMENT["promotion_rules"]), "Selection-bias safeguard missing")
    require(any("XRP 365d" in rule for rule in EXPERIMENT["prohibited_shortcuts"]), "XRP 365d evidence-gap safeguard missing")

    print(json.dumps(EXPERIMENT, indent=2))
    print("CRYPTO_PREDICTIVE_MODEL_IMPROVEMENT_EXPERIMENT_DESIGN=PASS")
    print("STARTING_SKILL_STATUS=NOT_CERTIFIED_FOR_INVESTMENT_TIMING")
    print("CHALLENGER_FAMILIES=3")
    print("FINAL_TEST_SELECTION_ALLOWED=FALSE")
    print("RECOMMENDATION_POLICY_CHANGES_ALLOWED=FALSE")
    print("NEXT_GATE=IMPLEMENT_DISPOSABLE_CHAMPION_CHALLENGER_REPLAY_HARNESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
