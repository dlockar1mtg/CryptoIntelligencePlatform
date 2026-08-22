from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()

    contract = Path(args.contract).resolve()
    require(contract.is_file(), f"Contract missing: {contract}")

    text = contract.read_text(encoding="utf-8")

    required_fragments = [
        "CRYPTO_BTC_ETH_FORWARD_ACCUMULATION_CYCLE_POLICY_V1",
        "Bitcoin and Ethereum are treated as long-duration accumulation assets",
        "approximately three-year intended holding period",
        "2026-2027: expected accumulation / post-peak reset and recovery window",
        "2028: expected halving / transition regime",
        "2029: expected late-cycle distribution opportunity window",
        "These year labels are not deterministic execution rules",
        "`ACCUMULATE`",
        "`HOLD`",
        "`DISTRIBUTE`",
        "`ACCELERATE`",
        "`NORMAL`",
        "`DELAY`",
        "`HOLD_EXISTING`",
        "`STAGED_DISTRIBUTION`",
        "Existing holdings and new-capital deployment are separate decisions",
        "A negative 7d forecast during a strategic `ACCUMULATE` regime",
        "not as an automatic instruction to sell existing BTC/ETH",
        "Historical recommendations may not be rewritten after outcomes mature",
        "approximately three-year forward outcomes",
        "`IMMEDIATE_DEPLOYMENT`",
        "`FIXED_DCA`",
        "`BTC_BUY_AND_HOLD`",
        "`BTC_ETH_BUY_AND_HOLD`",
        "`BTC_DOMINANT_BTC_ETH`",
        "`UIP_TACTICAL_ACCUMULATION`",
        "small-sample uncertainty",
        "A visually recognizable pattern is not sufficient for certification",
        "`INSUFFICIENT_EVIDENCE_FOR_POLICY_SKILL`",
        "Primary capital-decision certification scope:",
        "- Bitcoin",
        "- Ethereum",
        "7d: `V4_7D_VOLATILITY_STATE_EXTRA_TREES` confirmed on the one-time final holdout",
        "30d: `NO_QUALIFIED_WINNER`",
        "365d: `NO_QUALIFIED_WINNER`",
        "V4 30d and 365d final holdouts remain sealed",
        "V3 final holdout remains sealed",
        "post-holdout V4 tuning remains prohibited",
        "does not itself certify recommendation-policy skill",
        "does not authorize:",
        "- autonomous trading",
        "- automatic order placement",
        "deterministic buying or selling based only on calendar year or halving date",
        "`BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED`",
        "`DESIGN_BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY`",
        "`BUILD_FORWARD_BTC_ETH_RECOMMENDATION_EVIDENCE_LEDGER`",
    ]

    for fragment in required_fragments:
        require(fragment in text, f"Required contract fragment missing: {fragment}")

    prohibited_fragments = [
        "BTC_ETH_RECOMMENDATION_POLICY_SKILL_CERTIFIED=TRUE",
        "PRODUCTION_PROMOTION_ALLOWED=TRUE",
        "AUTONOMOUS_EXECUTION_ALLOWED=TRUE",
        "V4_30D_FINAL_HOLDOUT_OUTCOMES_VIEWED=TRUE",
        "V4_365D_FINAL_HOLDOUT_OUTCOMES_VIEWED=TRUE",
        "V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=TRUE",
    ]

    for fragment in prohibited_fragments:
        require(fragment not in text, f"Prohibited authority fragment present: {fragment}")

    print("CRYPTO_BTC_ETH_FORWARD_ACCUMULATION_CYCLE_POLICY_CONTRACT_VALIDATION=PASS")
    print("PRIMARY_ASSETS=bitcoin,ethereum")
    print("INVESTMENT_MANDATE=LONG_DURATION_ACCUMULATION")
    print("APPROXIMATE_NEW_BTC_HOLDING_THESIS_YEARS=3")
    print("STRATEGIC_STATES=ACCUMULATE,HOLD,DISTRIBUTE,INSUFFICIENT_EVIDENCE")
    print("TACTICAL_NEW_CAPITAL_STATES=ACCELERATE,NORMAL,DELAY,NO_NEW_CAPITAL,INSUFFICIENT_EVIDENCE")
    print("EXISTING_POSITION_STATES=HOLD_EXISTING,STAGED_DISTRIBUTION,RISK_REDUCTION,INSUFFICIENT_EVIDENCE")
    print("BITCOIN_FOUR_YEAR_CYCLE_STATUS=HYPOTHESIS_REQUIRING_QUANTITATIVE_VALIDATION")
    print("CALENDAR_ONLY_EXECUTION_ALLOWED=FALSE")
    print("SHORT_TERM_NEGATIVE_FORECAST_AUTOMATIC_SELL_ALLOWED=FALSE")
    print("HISTORICAL_POLICY_SKILL_STATUS=INSUFFICIENT_EVIDENCE_FOR_POLICY_SKILL")
    print("BTC_ETH_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE")
    print("AUTONOMOUS_EXECUTION_ALLOWED=FALSE")
    print("PRODUCTION_POLICY_CHANGE_ALLOWED=FALSE")
    print("V4_30D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V4_365D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("POST_HOLDOUT_V4_TUNING_ALLOWED=FALSE")
    print("NEXT_GATE=DESIGN_BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
