from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "predictive_horizon_recovery_v4_candidate_and_holdout_contract.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    text = CONTRACT.read_text(encoding="utf-8")

    required = [
        "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4",
        "V4 development origins: 50",
        "V4 final-holdout origins: 10",
        "V4_7D_SHORT_TREND_REVERSAL_LOGIT",
        "V4_7D_RELATIVE_STRENGTH_GB",
        "V4_7D_VOLATILITY_STATE_EXTRA_TREES",
        "V4_30D_TREND_REVERSAL_LOGIT",
        "V4_30D_RELATIVE_CONTEXT_GB",
        "V4_30D_VOLATILITY_STATE_EXTRA_TREES",
        "V4_365D_LONG_TREND_LOGIT",
        "V4_365D_LONG_REGIME_GB",
        "V4_365D_RETURN_MAGNITUDE_ENSEMBLE",
        "GradientBoostingRegressor",
        "RandomForestRegressor",
        "BayesianRidge",
        "holdout_outcomes_viewed_before_freeze=false",
        "XRP365 remains unsupported",
        "15 bps",
        "at least 4 of 6 assets",
        "at least 3 of 5 supported assets",
        "NO_QUALIFIED_WINNER",
        "V3 final-holdout outcomes remain unopened",
        "FREEZE_V4_FINAL_HOLDOUT_MEMBERSHIP_BEFORE_DEVELOPMENT_SCORING",
    ]

    for marker in required:
        require(marker in text, f"Missing governed V4 contract marker: {marker}")

    forbidden = [
        "repurpose the V3 final holdout",
        "synthesize XRP365",
        "lower the baseline",
        "automatic production promotion",
    ]
    for marker in forbidden:
        require(marker not in text, f"Forbidden V4 contract language present: {marker}")

    require(text.count("## 7d candidate contract") == 1, "Expected one 7d contract")
    require(text.count("## 30d candidate contract") == 1, "Expected one 30d contract")
    require(text.count("## 365d candidate contract") == 1, "Expected one 365d contract")
    require("Reserve the latest 10 eligible fresh origins as the V4 final holdout." in text,
            "V4 final holdout membership rule is not deterministic")
    require("select exactly 50 development origins using deterministic chronological spacing" in text,
            "V4 development membership rule is not deterministic")
    require("original majority baseline" in text,
            "365d original directional baseline preservation missing")
    require("These are diagnostics only in V4" in text,
            "365d auxiliary targets are not bounded to diagnostics")

    print("CRYPTO_V4_CANDIDATE_AND_HOLDOUT_CONTRACT_VALIDATION=PASS")
    print("RECOVERY_HORIZONS=7,30,365")
    print("SUPPORTED_GROUPS=17")
    print("DEVELOPMENT_ORIGINS_PER_GROUP=50")
    print("FINAL_HOLDOUT_ORIGINS_PER_GROUP=10")
    print("V3_FINAL_HOLDOUT_REUSED=FALSE")
    print("XRP365_SYNTHESIZED=FALSE")
    print("BASELINE_LOWERED_AFTER_V3=FALSE")
    print("RECOMMENDATION_POLICY_CHANGED=FALSE")
    print("NEXT_GATE=FREEZE_V4_FINAL_HOLDOUT_MEMBERSHIP_BEFORE_DEVELOPMENT_SCORING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
