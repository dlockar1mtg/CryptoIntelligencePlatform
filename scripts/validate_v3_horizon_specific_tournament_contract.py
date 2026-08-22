from __future__ import annotations

import json

EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_TOURNAMENT_V3"

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

RELATIVE_MARKET_FEATURES = [
    "asset_minus_btc_return_7d",
    "asset_minus_btc_return_30d",
    "asset_minus_core_median_return_7d",
    "asset_minus_core_median_return_30d",
    "core_return_dispersion_7d",
    "core_return_dispersion_30d",
    "core_breadth_positive_7d_pct",
    "core_breadth_positive_30d_pct",
]

CONTRACT = {
    "experiment_id": EXPERIMENT_ID,
    "tournament_unit": "ONE_INDEPENDENT_TOURNAMENT_PER_HORIZON",
    "horizons_days": [7, 30, 90, 180, 365],
    "supported_groups": 29,
    "unsupported_groups_preserved": ["xrp:365"],
    "development_policy": {
        "minimum_origins_per_supported_group": 60,
        "chronological_only": True,
        "purged_target_endpoint_boundary_required": True,
        "training_only_scaling_and_feature_bounds": True,
        "v2_consumed_origins_excluded": True,
        "v3_final_holdout_origins_excluded": True,
        "missing_features_synthesized": False,
    },
    "future_v3_holdout_policy": {
        "rows_per_supported_group": 10,
        "outcomes_must_remain_unviewed_until_winners_frozen": True,
        "membership_must_be_frozen_before_tournament_execution": True,
        "selection_rule": "chronologically latest 10 safe unused origins after excluding consumed V2 origins",
    },
    "candidate_families": [
        "PRICE_ONLY_DIRECTION_FIRST",
        "NATIVE_CONTEXT_DIRECTION_FIRST",
        "GRADIENT_BOOSTED_DIRECTION",
        "HIST_GRADIENT_BOOSTED_DIRECTION",
        "EXTRA_TREES_DIRECTION",
        "RELATIVE_MARKET_DIRECTION",
    ],
    "horizon_contracts": {
        "7": {
            "objective": "short_horizon_direction",
            "base_feature_set": [
                "return_1d", "return_7d", "return_30d",
                "volatility_30d", "distance_sma50",
            ],
            "native_context_features": [],
            "relative_market_features": [
                "asset_minus_btc_return_7d",
                "asset_minus_core_median_return_7d",
                "core_return_dispersion_7d",
                "core_breadth_positive_7d_pct",
            ],
            "eligible_families": [
                "PRICE_ONLY_DIRECTION_FIRST",
                "GRADIENT_BOOSTED_DIRECTION",
                "HIST_GRADIENT_BOOSTED_DIRECTION",
                "EXTRA_TREES_DIRECTION",
                "RELATIVE_MARKET_DIRECTION",
            ],
        },
        "30": {
            "objective": "short_to_medium_horizon_direction",
            "base_feature_set": [
                "return_7d", "return_30d", "return_90d",
                "volatility_30d", "volatility_90d",
                "distance_sma50", "distance_sma200",
            ],
            "native_context_features": [
                "core_breadth_above_sma50_pct",
                "core_median_return_30d_pct",
                "fear_greed_index",
            ],
            "relative_market_features": [
                "asset_minus_btc_return_7d",
                "asset_minus_btc_return_30d",
                "asset_minus_core_median_return_30d",
                "core_return_dispersion_30d",
                "core_breadth_positive_30d_pct",
            ],
            "eligible_families": [
                "PRICE_ONLY_DIRECTION_FIRST",
                "NATIVE_CONTEXT_DIRECTION_FIRST",
                "GRADIENT_BOOSTED_DIRECTION",
                "HIST_GRADIENT_BOOSTED_DIRECTION",
                "EXTRA_TREES_DIRECTION",
                "RELATIVE_MARKET_DIRECTION",
            ],
        },
        "90": {
            "objective": "medium_horizon_direction",
            "base_feature_set": [
                "return_30d", "return_90d",
                "volatility_30d", "volatility_90d",
                "distance_sma50", "distance_sma200",
            ],
            "native_context_features": NATIVE_CONTEXT_FEATURES,
            "relative_market_features": RELATIVE_MARKET_FEATURES,
            "eligible_families": [
                "PRICE_ONLY_DIRECTION_FIRST",
                "NATIVE_CONTEXT_DIRECTION_FIRST",
                "GRADIENT_BOOSTED_DIRECTION",
                "HIST_GRADIENT_BOOSTED_DIRECTION",
                "EXTRA_TREES_DIRECTION",
                "RELATIVE_MARKET_DIRECTION",
            ],
        },
        "180": {
            "objective": "long_horizon_direction",
            "base_feature_set": [
                "return_30d", "return_90d",
                "volatility_90d", "distance_sma50", "distance_sma200",
            ],
            "native_context_features": NATIVE_CONTEXT_FEATURES,
            "relative_market_features": RELATIVE_MARKET_FEATURES,
            "eligible_families": [
                "PRICE_ONLY_DIRECTION_FIRST",
                "NATIVE_CONTEXT_DIRECTION_FIRST",
                "GRADIENT_BOOSTED_DIRECTION",
                "HIST_GRADIENT_BOOSTED_DIRECTION",
                "EXTRA_TREES_DIRECTION",
                "RELATIVE_MARKET_DIRECTION",
            ],
        },
        "365": {
            "objective": "long_horizon_direction",
            "base_feature_set": [
                "return_90d", "volatility_90d", "distance_sma200",
            ],
            "native_context_features": NATIVE_CONTEXT_FEATURES,
            "relative_market_features": RELATIVE_MARKET_FEATURES,
            "eligible_families": [
                "PRICE_ONLY_DIRECTION_FIRST",
                "NATIVE_CONTEXT_DIRECTION_FIRST",
                "GRADIENT_BOOSTED_DIRECTION",
                "HIST_GRADIENT_BOOSTED_DIRECTION",
                "EXTRA_TREES_DIRECTION",
                "RELATIVE_MARKET_DIRECTION",
            ],
        },
    },
    "classifier_contracts": {
        "PRICE_ONLY_DIRECTION_FIRST": [
            "LOGISTIC_REGRESSION_BALANCED",
            "RANDOM_FOREST_CLASSIFIER_BALANCED_SUBSAMPLE",
        ],
        "NATIVE_CONTEXT_DIRECTION_FIRST": [
            "LOGISTIC_REGRESSION_BALANCED",
            "RANDOM_FOREST_CLASSIFIER_BALANCED_SUBSAMPLE",
        ],
        "GRADIENT_BOOSTED_DIRECTION": ["GRADIENT_BOOSTING_CLASSIFIER"],
        "HIST_GRADIENT_BOOSTED_DIRECTION": ["HIST_GRADIENT_BOOSTING_CLASSIFIER"],
        "EXTRA_TREES_DIRECTION": ["EXTRA_TREES_CLASSIFIER_BALANCED"],
        "RELATIVE_MARKET_DIRECTION": [
            "LOGISTIC_REGRESSION_BALANCED",
            "RANDOM_FOREST_CLASSIFIER_BALANCED_SUBSAMPLE",
            "GRADIENT_BOOSTING_CLASSIFIER",
        ],
    },
    "primary_scoring": {
        "metric_1": "model_minus_development_majority_accuracy_pct_points",
        "metric_2": "directional_accuracy_pct",
        "metric_3": "leakage_safe_calibrated_brier_score",
        "metric_4": "raw_brier_score",
        "selection_order": "baseline_adjusted_direction_first_then_direction_then_calibration",
    },
    "robustness_requirements": {
        "positive_horizon_baseline_adjusted_skill_required": True,
        "asset_dominance_prohibited": True,
        "minimum_assets_nonnegative_baseline_adjusted_skill": 3,
        "single_asset_may_not_explain_majority_of_gain": True,
        "calibration_alone_cannot_win": True,
        "transaction_cost_metrics_secondary_only": True,
    },
    "tie_breakers": [
        "more_assets_with_positive_baseline_adjusted_skill",
        "lower_calibrated_brier_score",
        "lower_variance_across_chronological_folds",
        "simpler_model_family_if_effectively_tied",
    ],
    "prohibited": [
        "aggregate_all_horizon_winner",
        "tuning_on_consumed_v2_holdout",
        "viewing_v3_final_holdout_outcomes_before_winners_frozen",
        "post_hoc_feature_add_remove_after_tournament_results",
        "dropping_losing_assets_after_results",
        "synthetic_zero_or_neutral_missing_features",
        "recommendation_threshold_changes",
        "production_auto_promotion",
        "regime_conditioning_before_point_in_time_regime_audit",
    ],
    "production_promotion_allowed": False,
    "recommendation_policy_changed": False,
    "next_gate": "FREEZE_FRESH_V3_FINAL_HOLDOUT_MEMBERSHIP_BEFORE_TOURNAMENT_EXECUTION",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(CONTRACT["experiment_id"] == EXPERIMENT_ID, "Experiment id mismatch")
    require(CONTRACT["horizons_days"] == [7, 30, 90, 180, 365], "Unexpected horizons")
    require(CONTRACT["supported_groups"] == 29, "Expected 29 supported groups")
    require(len(CONTRACT["candidate_families"]) == 6, "Expected six candidate families")
    require(len(CONTRACT["horizon_contracts"]) == 5, "Expected five horizon contracts")
    require(CONTRACT["development_policy"]["v2_consumed_origins_excluded"] is True, "V2 exclusion missing")
    require(CONTRACT["development_policy"]["v3_final_holdout_origins_excluded"] is True, "V3 holdout exclusion missing")
    require(CONTRACT["future_v3_holdout_policy"]["membership_must_be_frozen_before_tournament_execution"] is True, "V3 holdout must freeze before tournament")
    require(CONTRACT["future_v3_holdout_policy"]["outcomes_must_remain_unviewed_until_winners_frozen"] is True, "V3 outcomes must remain unviewed")
    require(CONTRACT["robustness_requirements"]["minimum_assets_nonnegative_baseline_adjusted_skill"] >= 3, "Asset robustness threshold too weak")
    require(CONTRACT["production_promotion_allowed"] is False, "Development tournament cannot production-promote")
    require(CONTRACT["recommendation_policy_changed"] is False, "Recommendation policy must remain unchanged")

    seven = CONTRACT["horizon_contracts"]["7"]
    thirty = CONTRACT["horizon_contracts"]["30"]
    ninety = CONTRACT["horizon_contracts"]["90"]
    require(seven["native_context_features"] == [], "7d must not inherit long-horizon native context")
    require(0 < len(thirty["native_context_features"]) < len(NATIVE_CONTEXT_FEATURES), "30d should use selective native context")
    require(ninety["native_context_features"] == NATIVE_CONTEXT_FEATURES, "90d native context mismatch")
    require(CONTRACT["horizon_contracts"]["180"]["native_context_features"] == NATIVE_CONTEXT_FEATURES, "180d native context mismatch")
    require(CONTRACT["horizon_contracts"]["365"]["native_context_features"] == NATIVE_CONTEXT_FEATURES, "365d native context mismatch")

    print(json.dumps(CONTRACT, indent=2))
    print("CRYPTO_V3_HORIZON_SPECIFIC_TOURNAMENT_CONTRACT=PASS")
    print("INDEPENDENT_HORIZON_CONTRACTS=5")
    print("CANDIDATE_FAMILIES=6")
    print("SEVEN_DAY_LONG_HORIZON_CONTEXT_INHERITED=FALSE")
    print("THIRTY_DAY_NATIVE_CONTEXT=SELECTIVE")
    print("NINETY_TO_365_NATIVE_CONTEXT=FULL_GOVERNED_SET")
    print("V2_CONSUMED_ORIGINS_EXCLUDED=TRUE")
    print("V3_FINAL_HOLDOUT_MUST_FREEZE_BEFORE_TOURNAMENT=TRUE")
    print("RECOMMENDATION_POLICY_CHANGED=FALSE")
    print("NEXT_GATE=FREEZE_FRESH_V3_FINAL_HOLDOUT_MEMBERSHIP_BEFORE_TOURNAMENT_EXECUTION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
