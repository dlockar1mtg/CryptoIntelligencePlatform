from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED_DESIGN_FRAGMENTS = (
    "BITCOIN_STRATEGIC_REGIME_FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_DESIGN_V1",
    "America/Chicago",
    "OUTCOME_PEEKING_ALLOWED=FALSE",
    "MISSING_EVIDENCE_SYNTHESIZED=FALSE",
    "SYNTHETIC_ZERO_ALLOWED=FALSE",
    "SYNTHETIC_NEUTRAL_ALLOWED=FALSE",
    "SYNTHETIC_WORST_CASE_ALLOWED=FALSE",
    "data/research/bitcoin_strategic_regime_forward_evidence_v1/records/",
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
    "BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE",
    "Module42 remains semantic authority",
    "Module44 remains diagnostic only",
    "V4_MODEL_SELECTION_REOPENED=FALSE",
    "V4_RETRAINING_AUTHORIZED=FALSE",
    "INITIAL_OUTCOMES_MUST_BE_UNMATURED=TRUE",
    "NEAREST_DATE_SUBSTITUTION_ALLOWED=FALSE",
    "APPEND_ONLY_OBSERVATION_RECORDS=TRUE",
    "CORRECTION_REQUIRES_SEPARATE_RECORD=TRUE",
    "record_count=0",
    "FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE",
    "BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE",
    "PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE",
    "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
    "CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE",
    "ed22cfb5eb83ac860527ca3c47c6b8d9e10a7cb3827ebb89ebd33fe8a324b9ca",
    "549bc0172dbefaf9936705df9da58ead29cd583141c5eaf294dd2fed5a693961",
    "BUILD_AND_VALIDATE_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_RUNNER",
)

REQUIRED_CONTRACT_FRAGMENTS = (
    "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_CONTRACT_V1",
    "BITCOIN_CYCLE_PHASE_STRATEGIC_REGIME_INPUT_AUTHORIZED=TRUE",
    "BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE",
    "BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE",
    "No autonomous purchase or sale execution is authorized",
)

REQUIRED_LEDGER_FRAGMENTS = (
    "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1",
    "append-only",
    "The ledger begins with zero recommendation observations",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--ledger-spec", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    design = Path(args.design).resolve()
    contract = Path(args.contract).resolve()
    ledger_spec = Path(args.ledger_spec).resolve()
    manifest = Path(args.manifest).resolve()

    for name, path in {
        "design": design,
        "contract": contract,
        "ledger_spec": ledger_spec,
        "manifest": manifest,
    }.items():
        require(path.is_file(), f"Required file missing: {name}={path}")

    design_text = design.read_text(encoding="utf-8")
    contract_text = contract.read_text(encoding="utf-8")
    ledger_text = ledger_spec.read_text(encoding="utf-8")
    manifest_text = manifest.read_text(encoding="utf-8")

    for fragment in REQUIRED_DESIGN_FRAGMENTS:
        require(fragment.lower() in design_text.lower(), f"Capture design missing required boundary: {fragment}")

    for fragment in REQUIRED_CONTRACT_FRAGMENTS:
        require(fragment.lower() in contract_text.lower(), f"Forward contract missing required boundary: {fragment}")

    for fragment in REQUIRED_LEDGER_FRAGMENTS:
        require(fragment.lower() in ledger_text.lower(), f"Ledger spec missing required boundary: {fragment}")

    for fragment in (
        '"ledger_id": "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1"',
        '"record_count": 0',
        '"synthetic_initial_observation_allowed": false',
        '"append_only_observation_records": true',
        '"outcomes_unknown_at_initial_observation": true',
        '"autonomous_execution_authorized": false',
    ):
        require(fragment.lower() in manifest_text.lower(), f"Ledger manifest missing required boundary: {fragment}")

    print("BITCOIN_STRATEGIC_REGIME_FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_DESIGN_VALIDATION=PASS")
    print("LEDGER_MUST_BE_EMPTY_BEFORE_FIRST_CAPTURE=TRUE")
    print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
    print("OBSERVATION_TIMEZONE=America/Chicago")
    print("OUTCOME_PEEKING_ALLOWED=FALSE")
    print("INITIAL_OUTCOMES_MUST_BE_UNMATURED=TRUE")
    print("MISSING_EVIDENCE_SYNTHESIZED=FALSE")
    print("BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE")
    print("MODULE42_SEMANTIC_AUTHORITY=PRESERVED")
    print("MODULE44_CERTIFICATION_AUTHORITY=FALSE")
    print("V4_MODEL_SELECTION_REOPENED=FALSE")
    print("V4_RETRAINING_AUTHORIZED=FALSE")
    print("BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE")
    print("PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE")
    print("NEXT_GATE=BUILD_AND_VALIDATE_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_RUNNER")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
