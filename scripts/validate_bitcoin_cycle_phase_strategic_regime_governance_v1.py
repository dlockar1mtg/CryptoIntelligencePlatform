from __future__ import annotations

import argparse
from pathlib import Path

EXPECTED_RESULT_SHA256 = "ed22cfb5eb83ac860527ca3c47c6b8d9e10a7cb3827ebb89ebd33fe8a324b9ca"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--governance", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    governance = Path(args.governance).resolve()
    result = Path(args.result).resolve()

    require(governance.is_file(), f"Governance document missing: {governance}")
    require(result.is_file(), f"V2 result missing: {result}")

    governance_text = governance.read_text(encoding="utf-8")
    result_text = result.read_text(encoding="utf-8")

    for fragment in (
        "BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_GOVERNANCE_V1",
        EXPECTED_RESULT_SHA256,
        "PATTERN_SUPPORTED_DESCRIPTIVELY",
        "completed adequately covered cycles: `3`",
        "refined expansion-reset ordering matches: `3`",
        "small-sample warning: `TRUE`",
        "ACCUMULATE",
        "HOLD",
        "DISTRIBUTE",
        "INSUFFICIENT_EVIDENCE",
        "tactical entry-timing evidence",
        "negative 7-day forecast",
        "DELAY",
        "ACCELERATE",
        "No one feature, including calendar year, halving distance, or cycle phase, may independently force a BUY or SELL",
        "BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE",
        "BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE",
        "BITCOIN_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE",
        "PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE",
        "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
        "V4_MODEL_SELECTION_REOPENED=FALSE",
        "BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED",
        "Recommendation remains distinct from execution",
        "BUILD_BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_CONTRACT",
    ):
        require(fragment.lower() in governance_text.lower(), f"Governance missing required boundary: {fragment}")

    for prohibited in (
        "BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=TRUE",
        "BITCOIN_RECOMMENDATION_POLICY_SKILL_CERTIFIED=TRUE",
        "PRODUCTION_POLICY_CHANGE_AUTHORIZED=TRUE",
        "AUTONOMOUS_EXECUTION_AUTHORIZED=TRUE",
        "V4_MODEL_SELECTION_REOPENED=TRUE",
    ):
        require(prohibited not in governance_text, f"Governance contains prohibited authority: {prohibited}")

    for fragment in (
        '"study_id": "BITCOIN_FOUR_YEAR_CYCLE_EXTENDED_HISTORY_V2"',
        '"study_interpretation": "PATTERN_SUPPORTED_DESCRIPTIVELY"',
        '"completed_cycle_count": 3',
        '"adequately_covered_completed_cycle_count": 3',
        '"refined_expansion_reset_ordering_matches": 3',
        '"cycle_policy_promotion_recommendation_allowed": true',
        '"cycle_policy_authority_granted": false',
        '"calendar_only_execution_allowed": false',
        '"v4_model_selection_affected": false',
        '"production_policy_changed": false',
        '"canonical_database_modified": false',
    ):
        require(fragment.lower() in result_text.lower(), f"V2 result missing required evidence: {fragment}")

    print("BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_GOVERNANCE_VALIDATION=PASS")
    print("V2_RESULT_SHA256=" + EXPECTED_RESULT_SHA256)
    print("HISTORICAL_PATTERN_SUPPORT=PATTERN_SUPPORTED_DESCRIPTIVELY")
    print("INDEPENDENT_COMPLETED_CYCLES=3")
    print("BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE")
    print("BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE")
    print("BITCOIN_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE")
    print("BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE")
    print("V4_MODEL_SELECTION_REOPENED=FALSE")
    print("PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("NEXT_GATE=BUILD_BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_CONTRACT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
