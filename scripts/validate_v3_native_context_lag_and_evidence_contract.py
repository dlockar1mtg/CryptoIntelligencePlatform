from __future__ import annotations

import json

EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_TOURNAMENT_V3"
EVIDENCE_CLASS = "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME"

LAG_DAYS = {
    # Price-derived context uses the prior completed daily observation so an
    # origin never consumes same-day close information.
    "btc_return_30d_pct": 1,
    "core_breadth_above_sma50_pct": 1,
    "core_median_return_30d_pct": 1,
    # External daily sentiment/liquidity series were historically backfilled
    # into the repository. A lag is applied for conservative temporal ordering,
    # but this does not convert reconstructed history into vintage evidence.
    "fear_greed_index": 1,
    "stablecoin_supply_usd": 1,
    "stablecoin_growth_30d_pct": 1,
    # FRED-derived daily macro series are conservatively delayed by two calendar
    # days because the repository does not retain vintage/realtime metadata.
    "dollar_index": 2,
    "vix": 2,
    # Composite features inherit the most conservative lag of their components.
    "macro_liquidity_score": 2,
    "risk_appetite_score": 2,
}

CONTRACT = {
    "experiment_id": EXPERIMENT_ID,
    "audit_finding": "STRICT_HISTORICAL_AS_KNOWN_POINT_IN_TIME_CERTIFIED_FALSE",
    "evidence_class": EVIDENCE_CLASS,
    "strict_point_in_time_claim_allowed": False,
    "historical_reconstruction_allowed_for_development_tournament": True,
    "production_promotion_allowed_from_tournament": False,
    "v3_final_holdout_outcomes_may_be_viewed_before_winners_frozen": False,
    "v2_consumed_holdout_may_be_used_for_tuning": False,
    "recommendation_policy_changed": False,
    "lag_application_rule": (
        "For each feature at each forecast origin, use only a source observation "
        "whose observation_date is on or before origin_date minus the governed "
        "calendar-day lag. Never shift values forward to fill a missing eligible "
        "observation and never synthesize zero or neutral values."
    ),
    "native_context_lag_days": LAG_DAYS,
    "horizon_policy": {
        "7": {
            "native_context_allowed": False,
            "reason": "7d tournament remains price/relative-market only.",
        },
        "30": {
            "native_context_allowed": True,
            "allowed_features": [
                "core_breadth_above_sma50_pct",
                "core_median_return_30d_pct",
                "fear_greed_index",
            ],
        },
        "90": {
            "native_context_allowed": True,
            "allowed_features": list(LAG_DAYS),
        },
        "180": {
            "native_context_allowed": True,
            "allowed_features": list(LAG_DAYS),
        },
        "365": {
            "native_context_allowed": True,
            "allowed_features": list(LAG_DAYS),
        },
    },
    "provenance_controls": {
        "macro_vintage_metadata_available": False,
        "same_day_macro_usage_allowed": False,
        "same_day_external_context_usage_allowed": False,
        "reconstructed_feature_values_may_be_described_as_strict_vintage": False,
        "composite_features_inherit_component_lag": True,
        "missing_lagged_features_remain_missing": True,
    },
    "interpretation_controls": [
        "A tournament winner may establish comparative research skill within reconstructed historical evidence only.",
        "A winner does not establish strict real-time historical skill until future genuinely timestamped observations mature.",
        "The fresh V3 final holdout remains valid as a frozen reconstructed-history test boundary, but its evidence class remains historical reconstruction.",
        "Recommendation timing certification remains separate and blocked until forecast and recommendation evidence gates are satisfied.",
    ],
    "next_gate": "IMPLEMENT_PER_HORIZON_DEVELOPMENT_TOURNAMENT_HARNESS_WITH_GOVERNED_LAGS",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(CONTRACT["experiment_id"] == EXPERIMENT_ID, "Experiment id mismatch")
    require(CONTRACT["evidence_class"] == EVIDENCE_CLASS, "Evidence class mismatch")
    require(CONTRACT["strict_point_in_time_claim_allowed"] is False, "Strict PIT claim must remain blocked")
    require(CONTRACT["historical_reconstruction_allowed_for_development_tournament"] is True, "Research tournament should remain allowed")
    require(CONTRACT["production_promotion_allowed_from_tournament"] is False, "Tournament cannot directly production-promote")
    require(CONTRACT["v3_final_holdout_outcomes_may_be_viewed_before_winners_frozen"] is False, "V3 holdout outcome gate weakened")
    require(CONTRACT["v2_consumed_holdout_may_be_used_for_tuning"] is False, "V2 holdout reuse prohibited")
    require(CONTRACT["recommendation_policy_changed"] is False, "Recommendation policy must remain unchanged")
    require(CONTRACT["horizon_policy"]["7"]["native_context_allowed"] is False, "7d native context must remain disabled")
    require(CONTRACT["provenance_controls"]["macro_vintage_metadata_available"] is False, "Macro vintage metadata must not be invented")
    require(CONTRACT["provenance_controls"]["same_day_macro_usage_allowed"] is False, "Same-day macro use must remain blocked")
    require(CONTRACT["provenance_controls"]["same_day_external_context_usage_allowed"] is False, "Same-day external context use must remain blocked")
    require(CONTRACT["provenance_controls"]["missing_lagged_features_remain_missing"] is True, "Missing lagged features must remain missing")
    require(all(int(v) >= 1 for v in LAG_DAYS.values()), "Every governed native feature needs a positive lag")
    require(LAG_DAYS["dollar_index"] >= 2 and LAG_DAYS["vix"] >= 2, "Macro lags are too weak")
    require(LAG_DAYS["macro_liquidity_score"] >= 2 and LAG_DAYS["risk_appetite_score"] >= 2, "Composite lag inheritance is too weak")

    print(json.dumps(CONTRACT, indent=2))
    print("CRYPTO_V3_NATIVE_CONTEXT_LAG_AND_EVIDENCE_CONTRACT=PASS")
    print("STRICT_POINT_IN_TIME_CLAIM_ALLOWED=FALSE")
    print("EVIDENCE_CLASS=HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME")
    print("SEVEN_DAY_NATIVE_CONTEXT_ALLOWED=FALSE")
    print("SAME_DAY_MACRO_USAGE_ALLOWED=FALSE")
    print("MISSING_LAGGED_FEATURES_SYNTHESIZED=FALSE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWABLE_BEFORE_WINNERS_FROZEN=FALSE")
    print("PRODUCTION_PROMOTION_ALLOWED_FROM_TOURNAMENT=FALSE")
    print("RECOMMENDATION_POLICY_CHANGED=FALSE")
    print("NEXT_GATE=IMPLEMENT_PER_HORIZON_DEVELOPMENT_TOURNAMENT_HARNESS_WITH_GOVERNED_LAGS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
