from __future__ import annotations

from pathlib import Path

EXPECTED_EXPERIMENT = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_V3_HASH = "33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1"
EXPECTED_NEXT_GATE = "AUDIT_V4_FRESH_EVIDENCE_CAPACITY_AND_FREEZE_HORIZON_SPECIFIC_CANDIDATE_CONTRACTS"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "docs" / "predictive_horizon_recovery_v4_design.md"
    require(path.is_file(), f"Missing V4 design: {path}")
    text = path.read_text(encoding="utf-8")

    required_literals = [
        EXPECTED_EXPERIMENT,
        EXPECTED_V3_HASH,
        "7d: `NO_QUALIFIED_WINNER`",
        "30d: `NO_QUALIFIED_WINNER`",
        "90d: `RELATIVE_MARKET_DIRECTION`",
        "180d: `NATIVE_CONTEXT_DIRECTION_FIRST`",
        "365d: `NO_QUALIFIED_WINNER`",
        "V3 final holdout outcomes remain unopened",
        "The sealed V3 final holdout must not be repurposed",
        "A V4 horizon may close with `NO_QUALIFIED_WINNER`",
        "Missing values remain missing",
        "Calibration improvement alone cannot create a winner",
        "No tuning is allowed after V4 final-holdout outcomes are viewed",
        "Recommendation-policy validation remains a separate task",
        EXPECTED_NEXT_GATE,
    ]
    for literal in required_literals:
        require(literal in text, f"Missing governed V4 design literal: {literal}")

    require("### 7d" in text and "### 30d" in text and "### 365d" in text, "Missing horizon-specific V4 hypotheses")
    require("73.6% majority baseline" in text, "365d V3 baseline must remain explicit")
    require("positive modeled after-cost economic value" in text, "7d economic guardrail missing")
    require("demonstrate positive baseline-adjusted skill before any promotion discussion" in text, "30d signal-first gate missing")
    require("excess return versus Bitcoin" in text, "365d auxiliary-target option missing")
    require("fresh V4 final holdout" in text, "Fresh V4 holdout requirement missing")
    require("majority of supported assets" in text, "Asset-robustness gate missing")
    require("one development fold" in text, "Fold-robustness gate missing")

    print("CRYPTO_V4_PREDICTIVE_HORIZON_RECOVERY_DESIGN_VALIDATION=PASS")
    print(f"EXPERIMENT_ID={EXPECTED_EXPERIMENT}")
    print("RECOVERY_HORIZONS=7,30,365")
    print("V3_90D_AND_180D_REOPENED=FALSE")
    print("V3_FINAL_HOLDOUT_REPURPOSED=FALSE")
    print("MISSING_VALUES_SYNTHESIZED=FALSE")
    print("RECOMMENDATION_POLICY_CHANGED=FALSE")
    print(f"NEXT_GATE={EXPECTED_NEXT_GATE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
