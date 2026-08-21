from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED_FRAGMENTS = (
    "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_CONTRACT_V1",
    "BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE",
    "BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE",
    "BITCOIN_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE",
    "BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE",
    "V4_MODEL_SELECTION_REOPENED=FALSE",
    "PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE",
    "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
    "ACCUMULATE",
    "HOLD",
    "DISTRIBUTE",
    "INSUFFICIENT_EVIDENCE",
    "ACCELERATE",
    "NORMAL",
    "DELAY",
    "NO_NEW_CAPITAL",
    "HOLD_EXISTING",
    "STAGED_DISTRIBUTION",
    "RISK_REDUCTION",
    "existing holdings must be evaluated separately from undeployed new capital",
    "7 calendar days",
    "30 calendar days",
    "90 calendar days",
    "180 calendar days",
    "approximately three-year outcomes",
    "No nearest-date substitution",
    "Missing endpoint outcomes remain missing",
    "IMMEDIATE_DEPLOYMENT",
    "FIXED_DCA",
    "BTC_BUY_AND_HOLD",
    "BTC_ETH_BUY_AND_HOLD",
    "BTC_DOMINANT_BTC_ETH",
    "UIP_TACTICAL_ACCUMULATION",
    "CASH_WHILE_WAITING",
    "records created before outcomes are known",
    "sufficient action diversity",
    "explicit transaction costs",
    "no post-hoc threshold tuning",
    "No fixed minimum sample size is invented in this contract",
    "Module42 remains the semantic authority",
    "Module44 remains diagnostic only",
    "The configured Crypto allocation is a ceiling, not an automatic deployment target",
    "No autonomous purchase or sale execution is authorized",
    "ed22cfb5eb83ac860527ca3c47c6b8d9e10a7cb3827ebb89ebd33fe8a324b9ca",
    "PATTERN_SUPPORTED_DESCRIPTIVELY",
    "BUILD_AND_VALIDATE_BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER",
)

REQUIRED_LEDGER_FIELDS = (
    "observation timestamp and operating date",
    "source run identifiers and hashes",
    "observed Bitcoin price",
    "current Bitcoin portfolio weight",
    "undeployed capital available to Bitcoin",
    "current strategic-regime state",
    "current tactical new-capital state",
    "current existing-position state",
    "original Module42 action",
    "V4 7-day forecast output and confidence",
    "cycle phase and numeric cycle-position features",
    "drawdown-from-high features",
    "medium/long trend features",
    "volatility/drawdown-state features",
    "macro/liquidity evidence references",
    "explicit uncertainty notes",
    "transaction-cost assumptions",
)

PROHIBITED_FRAGMENTS = (
    "BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=TRUE",
    "BITCOIN_RECOMMENDATION_POLICY_SKILL_CERTIFIED=TRUE",
    "V4_MODEL_SELECTION_REOPENED=TRUE",
    "PRODUCTION_POLICY_CHANGE_AUTHORIZED=TRUE",
    "AUTONOMOUS_EXECUTION_AUTHORIZED=TRUE",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--governance", required=True)
    parser.add_argument("--v2-result", required=True)
    args = parser.parse_args()

    contract = Path(args.contract).resolve()
    governance = Path(args.governance).resolve()
    result = Path(args.v2_result).resolve()

    for name, path in {
        "contract": contract,
        "governance": governance,
        "v2_result": result,
    }.items():
        require(path.is_file(), f"Required file missing: {name}={path}")

    contract_text = contract.read_text(encoding="utf-8")
    governance_text = governance.read_text(encoding="utf-8")
    result_text = result.read_text(encoding="utf-8")

    for fragment in REQUIRED_FRAGMENTS:
        require(fragment.lower() in contract_text.lower(), f"Forward evidence contract missing required boundary: {fragment}")

    for fragment in REQUIRED_LEDGER_FIELDS:
        require(fragment.lower() in contract_text.lower(), f"Forward evidence contract missing ledger field: {fragment}")

    for fragment in PROHIBITED_FRAGMENTS:
        require(fragment.lower() not in contract_text.lower(), f"Forward evidence contract contains prohibited authority: {fragment}")

    for fragment in (
        "BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE",
        "BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE",
        "BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED",
        "PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE",
        "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
    ):
        require(fragment.lower() in governance_text.lower(), f"Strategic governance missing required boundary: {fragment}")

    for fragment in (
        '\"study_interpretation\": \"PATTERN_SUPPORTED_DESCRIPTIVELY\"',
        '\"completed_cycle_count\": 3',
        '\"adequately_covered_completed_cycle_count\": 3',
        '\"refined_expansion_reset_ordering_matches\": 3',
        '\"cycle_policy_promotion_recommendation_allowed\": true',
        '\"cycle_policy_authority_granted\": false',
    ):
        require(fragment.lower() in result_text.lower(), f"Preserved V2 result missing required evidence: {fragment}")

    print("BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_CONTRACT_VALIDATION=PASS")
    print("BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE")
    print("BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE")
    print("STRATEGIC_STATES=ACCUMULATE,HOLD,DISTRIBUTE,INSUFFICIENT_EVIDENCE")
    print("TACTICAL_STATES=ACCELERATE,NORMAL,DELAY,NO_NEW_CAPITAL,INSUFFICIENT_EVIDENCE")
    print("EXISTING_POSITION_STATES=HOLD_EXISTING,STAGED_DISTRIBUTION,RISK_REDUCTION,INSUFFICIENT_EVIDENCE")
    print("EXACT_OUTCOME_HORIZONS=7,30,90,180")
    print("THREE_YEAR_STRATEGIC_OUTCOME_WHEN_MATURED=REQUIRED")
    print("NEAREST_DATE_SUBSTITUTION_ALLOWED=FALSE")
    print("MISSING_OUTCOMES_SYNTHESIZED=FALSE")
    print("MODULE42_SEMANTIC_AUTHORITY=PRESERVED")
    print("MODULE44_CERTIFICATION_AUTHORITY=FALSE")
    print("BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE")
    print("V4_MODEL_SELECTION_REOPENED=FALSE")
    print("PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("NEXT_GATE=BUILD_AND_VALIDATE_BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
