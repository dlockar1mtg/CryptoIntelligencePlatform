from __future__ import annotations

import json

DESIGN = {
    "experiment_id": "CRYPTO_NATIVE_PREDICTIVE_MODEL_TOURNAMENT_V3",
    "starting_status": "V2_NATIVE_CONTEXT_RESEARCH_CHAMPION_PROMOTED_BUT_INVESTMENT_TIMING_NOT_CERTIFIED",
    "objective": (
        "Run a bounded, leakage-safe model tournament separately for each forecast horizon so that "
        "7d, 30d, 90d, 180d, and 365d are treated as distinct prediction problems rather than forcing "
        "one architecture across all horizons."
    ),
    "horizons_days": [7, 30, 90, 180, 365],
    "assets": ["bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche"],
    "unsupported_groups_preserved": ["xrp:365"],
    "tournament_unit": "ONE_INDEPENDENT_TOURNAMENT_PER_HORIZON",
    "development_evidence_policy": (
        "Use only chronological/purged walk-forward development evidence that excludes consumed V2 holdout origins."
    ),
    "v2_holdout_policy": "CONSUMED_DO_NOT_TUNE_OR_SELECT_MODELS_ON_V2_HOLDOUT",
    "future_final_holdout_policy": (
        "After selecting one winner per horizon from development evidence, freeze a newly isolated V3 final holdout "
        "before evaluating any selected horizon winner."
    ),
    "candidate_families": {
        "PRICE_ONLY_DIRECTION_FIRST": {
            "purpose": "Short-horizon reference architecture using governed point-in-time price features.",
            "classifiers": [
                "LOGISTIC_REGRESSION_BALANCED",
                "RANDOM_FOREST_CLASSIFIER_BALANCED_SUBSAMPLE",
            ],
        },
        "NATIVE_CONTEXT_DIRECTION_FIRST": {
            "purpose": "V2 research champion reference using price plus governed native context.",
            "classifiers": [
                "LOGISTIC_REGRESSION_BALANCED",
                "RANDOM_FOREST_CLASSIFIER_BALANCED_SUBSAMPLE",
            ],
        },
        "GRADIENT_BOOSTED_DIRECTION": {
            "purpose": "Capture nonlinear interactions between price, macro, sentiment, market-structure, and liquidity context.",
            "classifiers": ["GRADIENT_BOOSTING_CLASSIFIER"],
        },
        "HIST_GRADIENT_BOOSTED_DIRECTION": {
            "purpose": "Alternative nonlinear boosted classifier with different bias/variance behavior.",
            "classifiers": ["HIST_GRADIENT_BOOSTING_CLASSIFIER"],
        },
        "EXTRA_TREES_DIRECTION": {
            "purpose": "High-randomization tree ensemble candidate already native to repository research architecture.",
            "classifiers": ["EXTRA_TREES_CLASSIFIER_BALANCED"],
        },
        "RELATIVE_MARKET_DIRECTION": {
            "purpose": "Direction-first architecture augmented with point-in-time cross-asset relative momentum, breadth, dispersion, and BTC-relative features.",
            "classifiers": [
                "LOGISTIC_REGRESSION_BALANCED",
                "RANDOM_FOREST_CLASSIFIER_BALANCED_SUBSAMPLE",
                "GRADIENT_BOOSTING_CLASSIFIER",
            ],
        },
    },
    "horizon_feature_policy": {
        "7": {
            "priority": "SHORT_HORIZON_PRICE_AND_MARKET_STRUCTURE",
            "allowed_context": [
                "price_momentum",
                "volatility",
                "reversal",
                "relative_market",
                "breadth",
                "provider_volume_or_liquidity_only_when_point_in_time_complete",
            ],
        },
        "30": {
            "priority": "SHORT_TO_MEDIUM_PRICE_PLUS_MARKET_STRUCTURE",
            "allowed_context": [
                "price_momentum",
                "volatility",
                "relative_market",
                "breadth",
                "selected_native_context_if_point_in_time_available",
            ],
        },
        "90": {
            "priority": "MEDIUM_HORIZON_NATIVE_CONTEXT",
            "allowed_context": [
                "price",
                "macro",
                "sentiment",
                "market_structure",
                "liquidity",
                "relative_market",
            ],
        },
        "180": {
            "priority": "LONG_HORIZON_NATIVE_CONTEXT",
            "allowed_context": [
                "price",
                "macro",
                "sentiment",
                "market_structure",
                "liquidity",
                "relative_market",
            ],
        },
        "365": {
            "priority": "LONG_HORIZON_NATIVE_CONTEXT",
            "allowed_context": [
                "price",
                "macro",
                "sentiment",
                "market_structure",
                "liquidity",
                "relative_market",
            ],
        },
    },
    "primary_metrics": [
        "directional_accuracy_pct",
        "model_minus_development_majority_accuracy_pct_points",
        "raw_brier_score",
        "leakage_safe_calibrated_brier_score",
    ],
    "guardrail_metrics": [
        "mae_pct",
        "rmse_pct",
        "interval_coverage_pct",
        "asset_level_baseline_adjusted_directional_skill",
        "turnover_and_transaction_cost_secondary_metrics",
    ],
    "selection_rules": [
        "Choose one development winner independently for each horizon.",
        "A winner must beat the horizon-specific majority baseline on baseline-adjusted directional accuracy.",
        "Do not select a model based on aggregate all-horizon performance.",
        "Do not select a model that wins only because one asset dominates the horizon aggregate.",
        "Calibration improvement alone is insufficient for selection.",
        "Magnitude-error guardrails may not materially deteriorate without explicit review.",
        "No model may be tuned using V2 holdout outcomes.",
        "No recommendation-policy thresholds may change during the tournament.",
    ],
    "regime_conditioning_policy": (
        "REGIME_CONDITIONED_CANDIDATES_ARE_BLOCKED_UNTIL_HISTORICAL_POINT_IN_TIME_REGIME_AVAILABILITY_IS_PROVEN"
    ),
    "missing_data_policy": "MISSING_FEATURES_REMAIN_MISSING_NO_ZERO_OR_NEUTRAL_SYNTHESIS",
    "recommendation_policy_changed": False,
    "production_promotion_allowed_from_development_tournament": False,
    "next_gate": "AUDIT_V3_PER_HORIZON_TOURNAMENT_CAPACITY_AND_FEATURE_AVAILABILITY",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(DESIGN["horizons_days"] == [7, 30, 90, 180, 365], "Unexpected governed horizons")
    require(DESIGN["tournament_unit"] == "ONE_INDEPENDENT_TOURNAMENT_PER_HORIZON", "Tournament is not horizon-specific")
    require(len(DESIGN["candidate_families"]) == 6, "Expected six bounded candidate families")
    require("CONSUMED_DO_NOT_TUNE" in DESIGN["v2_holdout_policy"], "Consumed V2 holdout is not protected")
    require("newly isolated V3 final holdout" in DESIGN["future_final_holdout_policy"], "Fresh V3 holdout is not required")
    require(DESIGN["recommendation_policy_changed"] is False, "Recommendation policy may not change")
    require(DESIGN["production_promotion_allowed_from_development_tournament"] is False, "Development tournament cannot directly promote production")
    require(DESIGN["unsupported_groups_preserved"] == ["xrp:365"], "Governed XRP 365d gap was not preserved")
    require("BLOCKED" in DESIGN["regime_conditioning_policy"], "Regime-conditioned models must remain blocked pending PIT proof")

    print(json.dumps(DESIGN, indent=2, sort_keys=False))
    print("CRYPTO_V3_PER_HORIZON_MODEL_TOURNAMENT_DESIGN=PASS")
    print("INDEPENDENT_HORIZON_TOURNAMENTS=5")
    print("BOUNDED_CANDIDATE_FAMILIES=6")
    print("V2_HOLDOUT_REUSE_FOR_TUNING=FALSE")
    print("FRESH_V3_FINAL_HOLDOUT_REQUIRED=TRUE")
    print("RECOMMENDATION_POLICY_CHANGED=FALSE")
    print("NEXT_GATE=AUDIT_V3_PER_HORIZON_TOURNAMENT_CAPACITY_AND_FEATURE_AVAILABILITY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
