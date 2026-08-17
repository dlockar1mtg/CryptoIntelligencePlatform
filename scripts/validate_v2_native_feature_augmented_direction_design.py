from __future__ import annotations

import json


DESIGN = {
    "experiment_id": "CRYPTO_NATIVE_PREDICTIVE_MODEL_IMPROVEMENT_V2",
    "starting_status": "V1_NO_CHALLENGER_PROMOTED",
    "v2_holdout_status": "AVAILABLE_AND_UNVIEWED",
    "objective": (
        "Test whether adding already-governed native Crypto macro, sentiment, market-structure, "
        "and liquidity context to the direction-first classifier improves genuinely isolated "
        "out-of-sample directional skill without changing recommendation policy or weakening "
        "point-in-time controls."
    ),
    "champion": "CURRENT_M38_REGRESSION_ENSEMBLE",
    "challenger": "NATIVE_CONTEXT_AUGMENTED_DIRECTION_FIRST",
    "direction_model_family": [
        "LOGISTIC_REGRESSION_BALANCED",
        "RANDOM_FOREST_CLASSIFIER_BALANCED_SUBSAMPLE",
    ],
    "magnitude_model": "CURRENT_M38_REGRESSION_ENSEMBLE_UNCHANGED",
    "price_features": [
        "return_1d",
        "return_7d",
        "return_30d",
        "return_90d",
        "volatility_30d",
        "volatility_90d",
        "distance_sma50",
        "distance_sma200",
    ],
    "native_context_features": [
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
    ],
    "excluded_candidate_features": {
        "high_yield_spread": "Shorter governed history than the fixed V2 long-history context set.",
        "btc_dominance_proxy_pct": "Only 379 active days in the pre-outcome capacity audit.",
        "total2_market_cap_proxy_usd": "Only 379 active days in the pre-outcome capacity audit.",
        "total3_market_cap_proxy_usd": "Only 379 active days in the pre-outcome capacity audit.",
    },
    "feature_selection_basis": (
        "Governed production eligibility plus long-history coverage observed before any V2 holdout "
        "outcome was viewed; no feature was selected using V2 outcome performance."
    ),
    "frozen_controls": [
        "same six-asset universe",
        "same governed 7d, 30d, 90d, 180d, and 365d horizons",
        "XRP 365d remains unsupported unless governed history genuinely becomes sufficient",
        "all labels must mature before each forecast origin",
        "purged internal train-validation boundary remains in force",
        "feature scaling and support bounds are fit from training data only",
        "no V2 holdout outcome may be used for feature selection, tuning, weighting, or threshold choice",
        "magnitude regression ensemble remains unchanged during V2",
        "recommendation BUY/HOLD/WAIT/REDUCE/SELL policy remains unchanged during V2",
        "missing native context remains missing; do not synthesize zero or neutral values",
    ],
    "development_policy": (
        "All design decisions are frozen before the V2 holdout is evaluated. Development may use "
        "V1 development evidence and non-outcome capacity/coverage metadata only."
    ),
    "v2_holdout_policy": {
        "rows_per_supported_asset_horizon_group": 10,
        "supported_groups_expected": 29,
        "selection_rule": (
            "Use valid point-in-time candidate origins not used in the 30-row V1 replay set; freeze "
            "the selected origin dates before loading realized target outcomes."
        ),
        "outcomes_viewed_before_design": False,
    },
    "primary_promotion_metrics": [
        "directional_accuracy_pct",
        "model_minus_development_majority_accuracy_pct_points",
        "raw_brier_score",
        "leakage_safe_calibrated_brier_score",
    ],
    "guardrail_metrics": [
        "mae_pct",
        "rmse_pct",
        "interval_coverage_pct",
        "supported_horizons_with_positive_baseline_adjusted_skill",
        "supported_assets_with_positive_baseline_adjusted_skill",
    ],
    "promotion_rules": [
        "The V2 challenger must beat the current champion on aggregate baseline-adjusted directional accuracy.",
        "The V2 challenger must have positive baseline-adjusted directional skill in a majority of supported horizons.",
        "Aggregate improvement may not be driven solely by one asset or one horizon.",
        "The V2 challenger may not materially worsen magnitude-error guardrails without explicit review.",
        "Calibration improvement alone cannot establish investment-timing skill.",
        "No recommendation-policy promotion occurs in this gate even if forecast promotion succeeds.",
    ],
    "prohibited_shortcuts": [
        "view V2 holdout outcomes before origin dates and model design are frozen",
        "drop losing assets or horizons after seeing V2 outcomes",
        "add or remove native context features after seeing V2 outcomes",
        "change classifier thresholds after seeing V2 outcomes",
        "backfill missing native features with synthetic neutral values",
        "claim investment-timing certification from V2 if robustness rules fail",
    ],
    "next_gate": "IMPLEMENT_FROZEN_V2_HOLDOUT_AND_NATIVE_CONTEXT_REPLAY_HARNESS",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(DESIGN["v2_holdout_status"] == "AVAILABLE_AND_UNVIEWED", "V2 holdout must remain unviewed at design time")
    require(DESIGN["v2_holdout_policy"]["outcomes_viewed_before_design"] is False, "V2 outcome isolation violated")
    require(len(DESIGN["native_context_features"]) == 10, "Expected fixed ten-feature long-history native context set")
    require(len(DESIGN["excluded_candidate_features"]) == 4, "Expected four coverage-based exclusions")
    require("high_yield_spread" in DESIGN["excluded_candidate_features"], "Shorter-history macro exclusion must be explicit")
    require("btc_dominance_proxy_pct" in DESIGN["excluded_candidate_features"], "Short-history proxy exclusion must be explicit")
    require(DESIGN["v2_holdout_policy"]["rows_per_supported_asset_horizon_group"] == 10, "V2 holdout must remain ten rows per supported group")
    require(DESIGN["v2_holdout_policy"]["supported_groups_expected"] == 29, "Expected 29 supported groups")
    require(any("majority of supported horizons" in rule for rule in DESIGN["promotion_rules"]), "Cross-horizon robustness rule missing")
    require(any("recommendation-policy" in rule for rule in DESIGN["promotion_rules"]), "Recommendation separation rule missing")
    require(any("synthetic neutral" in rule for rule in DESIGN["prohibited_shortcuts"]), "Missing-data safeguard missing")

    print(json.dumps(DESIGN, indent=2))
    print("CRYPTO_V2_NATIVE_FEATURE_AUGMENTED_DIRECTION_DESIGN=PASS")
    print("V2_HOLDOUT_OUTCOMES_VIEWED_BEFORE_DESIGN=FALSE")
    print("NATIVE_CONTEXT_FEATURES=10")
    print("COVERAGE_BASED_EXCLUSIONS=4")
    print("RECOMMENDATION_POLICY_CHANGES_ALLOWED=FALSE")
    print("NEXT_GATE=IMPLEMENT_FROZEN_V2_HOLDOUT_AND_NATIVE_CONTEXT_REPLAY_HARNESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
