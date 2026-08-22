from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--governance", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    runner = Path(args.runner)
    governance = Path(args.governance)
    manifest = Path(args.manifest)
    for path in (runner, governance, manifest):
        require(path.is_file(), f"Required file missing: {path}")

    runner_text = runner.read_text(encoding="utf-8")
    governance_text = governance.read_text(encoding="utf-8")
    manifest_text = manifest.read_text(encoding="utf-8")

    governance_markers = (
        "CRYPTO_BTC_ETH_STRATEGIC_ALIGNMENT_UIP_OUTPUT_V1",
        "BTC_PRIMARY=TRUE",
        "ETH_SECONDARY=TRUE",
        "ETH_BITCOIN_CYCLE_CONTEXT_ALLOWED=TRUE",
        "ETH_BITCOIN_CYCLE_ACTION_RULE_ALLOWED=FALSE",
        "SYNTHETIC_ETH_HALVING_CYCLE_ALLOWED=FALSE",
        "FIRST_ETHEREUM_PROSPECTIVE_OBSERVATION_AUTHORIZED=TRUE",
        "MODULE42_BTC_ETH_FINAL_AUTHORITY=FALSE",
        "BTC_ETH_STRATEGIC_OVERLAY_REQUIRED=TRUE",
        "PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE",
        "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
    )
    for marker in governance_markers:
        require(marker in governance_text, f"Governance marker missing: {marker}")

    runner_markers = (
        'ASSET_ID = "ethereum"',
        '"asset_role": "SECONDARY_LONG_DURATION_CRYPTO_ASSET"',
        '"strategic_state": "INSUFFICIENT_EVIDENCE"',
        '"tactical_new_capital_state": "INSUFFICIENT_EVIDENCE"',
        '"existing_position_state": "INSUFFICIENT_EVIDENCE"',
        '"context_role": "CROSS_MARKET_CONTEXT_ONLY_NOT_ETH_ACTION_RULE"',
        '"live_ethereum_inference_available": False',
        '"final_btc_eth_authority": False',
        '"synthetic_eth_halving_cycle_allowed": False',
        '"btc_eth_recommendation_policy_skill_certified": False',
        '"production_policy_change_authorized": False',
        '"autonomous_execution_authorized": False',
        'duckdb.connect(str(database), read_only=True)',
    )
    for marker in runner_markers:
        require(marker in runner_text, f"Runner marker missing: {marker}")

    prohibited_runner = (
        "run_module42",
        "fit_predict(",
        "INSERT INTO canonical_market_daily",
        "UPDATE canonical_market_daily",
        "DELETE FROM canonical_market_daily",
        "ACCUMULATE\"",
        "DISTRIBUTE\"",
        "HOLD_EXISTING\"",
        "ACCELERATE\"",
    )
    for token in prohibited_runner:
        require(token not in runner_text, f"Prohibited Ethereum capture token found: {token}")

    manifest_markers = (
        '"ledger_id": "ETHEREUM_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1"',
        '"record_count": 0',
        '"bitcoin_cycle_context_allowed": true',
        '"bitcoin_cycle_context_action_rule_allowed": false',
        '"synthetic_eth_halving_cycle_allowed": false',
        '"production_policy_change_authorized": false',
        '"autonomous_execution_authorized": false',
    )
    for marker in manifest_markers:
        require(marker in manifest_text, f"Manifest marker missing: {marker}")

    print("FIRST_PROSPECTIVE_ETHEREUM_OBSERVATION_CAPTURE_V1_STATIC_VALIDATION=PASS")
    print("ETH_ASSET_ROLE=SECONDARY_LONG_DURATION_CRYPTO_ASSET")
    print("BTC_CYCLE_CONTEXT_ONLY=TRUE")
    print("SYNTHETIC_ETH_CYCLE_ALLOWED=FALSE")
    print("STRATEGIC_STATE_LOCKED=INSUFFICIENT_EVIDENCE")
    print("TACTICAL_STATE_LOCKED=INSUFFICIENT_EVIDENCE")
    print("EXISTING_POSITION_STATE_LOCKED=INSUFFICIENT_EVIDENCE")
    print("MODULE42_FINAL_AUTHORITY=FALSE")
    print("CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE")
    print("NEXT_GATE=RUN_FIRST_PROSPECTIVE_ETHEREUM_OBSERVATION_PREFLIGHT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
