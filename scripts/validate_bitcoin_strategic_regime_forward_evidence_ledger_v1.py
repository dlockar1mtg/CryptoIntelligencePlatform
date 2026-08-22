from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_SPEC_FRAGMENTS = (
    "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1",
    "INITIAL_LEDGER_RECORD_COUNT=0",
    "SYNTHETIC_INITIAL_OBSERVATION_ALLOWED=FALSE",
    "BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE",
    "BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE",
    "BITCOIN_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE",
    "BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE",
    "V4_MODEL_SELECTION_REOPENED=FALSE",
    "PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE",
    "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
    "No nearest-date substitution",
    "Missing evidence remains missing",
    "record_created_before_outcomes_known",
    "record_correction_of_observation_id",
    "IMMEDIATE_DEPLOYMENT",
    "FIXED_DCA",
    "BTC_BUY_AND_HOLD",
    "BTC_ETH_BUY_AND_HOLD",
    "BTC_DOMINANT_BTC_ETH",
    "UIP_TACTICAL_ACCUMULATION",
    "CASH_WHILE_WAITING",
)

REQUIRED_CONTRACT_FRAGMENTS = (
    "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_CONTRACT_V1",
    "BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE",
    "BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE",
    "BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE",
    "records created before outcomes are known",
    "No autonomous purchase or sale execution is authorized",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--records-dir", required=True)
    args = parser.parse_args()

    spec = Path(args.spec).resolve()
    manifest = Path(args.manifest).resolve()
    contract = Path(args.contract).resolve()
    records_dir = Path(args.records_dir).resolve()

    require(spec.is_file(), f"Ledger specification missing: {spec}")
    require(manifest.is_file(), f"Ledger manifest missing: {manifest}")
    require(contract.is_file(), f"Forward evidence contract missing: {contract}")

    spec_text = spec.read_text(encoding="utf-8")
    contract_text = contract.read_text(encoding="utf-8")

    for fragment in REQUIRED_SPEC_FRAGMENTS:
        require(fragment.lower() in spec_text.lower(), f"Ledger specification missing required boundary: {fragment}")

    for fragment in REQUIRED_CONTRACT_FRAGMENTS:
        require(fragment.lower() in contract_text.lower(), f"Forward evidence contract missing required boundary: {fragment}")

    payload = json.loads(manifest.read_text(encoding="utf-8"))

    require(payload.get("ledger_id") == "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1", "Unexpected ledger id")
    require(payload.get("schema_version") == 1, "Unexpected ledger schema version")
    require(payload.get("asset_scope") == ["bitcoin"], "Unexpected ledger asset scope")
    require(payload.get("record_count") == 0, "Zero-record ledger must have record_count=0")
    require(payload.get("initial_record_count") == 0, "Zero-record ledger must have initial_record_count=0")
    require(payload.get("synthetic_initial_observation_allowed") is False, "Synthetic initial observation unexpectedly allowed")
    require(payload.get("append_only_observation_records") is True, "Ledger records are not append-only")
    require(payload.get("correction_requires_separate_record") is True, "Ledger corrections do not require separate records")
    require(payload.get("outcomes_unknown_at_initial_observation") is True, "Initial observations do not preserve unknown-outcome semantics")
    require(payload.get("nearest_date_substitution_allowed") is False, "Nearest-date substitution unexpectedly allowed")
    require(payload.get("missing_outcomes_synthesized") is False, "Missing outcomes unexpectedly synthesized")
    require(payload.get("cycle_phase_strategic_regime_input_authorized") is True, "Strategic regime input authority missing")
    require(payload.get("calendar_only_action_authorized") is False, "Calendar-only action unexpectedly authorized")
    require(payload.get("bitcoin_recommendation_policy_skill_certified") is False, "Recommendation-policy skill unexpectedly certified")
    require(payload.get("btc_eth_recommendation_policy_skill_not_certified") is True, "BTC/ETH uncertified status missing")
    require(payload.get("v4_model_selection_reopened") is False, "V4 unexpectedly reopened")
    require(payload.get("production_policy_change_authorized") is False, "Production policy change unexpectedly authorized")
    require(payload.get("autonomous_execution_authorized") is False, "Autonomous execution unexpectedly authorized")
    require(payload.get("governing_contract") == "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_CONTRACT_V1", "Unexpected governing contract")
    require(payload.get("governing_ledger_specification") == "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1", "Unexpected governing ledger specification")

    record_files = []
    if records_dir.exists():
        require(records_dir.is_dir(), f"Records path exists but is not a directory: {records_dir}")
        record_files = sorted(p for p in records_dir.rglob("*.json") if p.is_file())

    require(len(record_files) == 0, "Zero-record ledger unexpectedly contains recommendation observations")

    print("BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_VALIDATION=PASS")
    print("LEDGER_ID=BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1")
    print("ASSET_SCOPE=bitcoin")
    print("LEDGER_RECORD_COUNT=0")
    print("SYNTHETIC_INITIAL_OBSERVATION_ALLOWED=FALSE")
    print("APPEND_ONLY_OBSERVATION_RECORDS=TRUE")
    print("CORRECTION_REQUIRES_SEPARATE_RECORD=TRUE")
    print("OUTCOMES_UNKNOWN_AT_INITIAL_OBSERVATION=TRUE")
    print("NEAREST_DATE_SUBSTITUTION_ALLOWED=FALSE")
    print("MISSING_OUTCOMES_SYNTHESIZED=FALSE")
    print("BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE")
    print("BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE")
    print("BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE")
    print("V4_MODEL_SELECTION_REOPENED=FALSE")
    print("PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("NEXT_GATE=DESIGN_FIRST_PROSPECTIVE_BITCOIN_STRATEGIC_REGIME_OBSERVATION_CAPTURE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
