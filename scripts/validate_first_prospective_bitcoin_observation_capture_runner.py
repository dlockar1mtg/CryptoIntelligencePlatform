from __future__ import annotations

import argparse
import ast
from pathlib import Path

REQUIRED_RUNNER_FRAGMENTS = (
    "FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_SOURCE_DISCOVERY_V1",
    "America/Chicago",
    "read_only=True",
    "record_count=0",
    "synthetic_initial_observation_allowed",
    "append_only_observation_records",
    "outcomes_unknown_at_initial_observation",
    "autonomous_execution_authorized",
    "canonical_market_daily",
    "MISSING_EVIDENCE_SYNTHESIZED=FALSE",
    "OUTCOME_PEEKING_ALLOWED=FALSE",
    "FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE",
    "CANONICAL_DATABASE_MODIFIED=FALSE",
    "NEXT_GATE=REVIEW_FIRST_PROSPECTIVE_BITCOIN_SOURCE_DISCOVERY",
    "Capture mode is not yet authorized after source discovery",
    "ed22cfb5eb83ac860527ca3c47c6b8d9e10a7cb3827ebb89ebd33fe8a324b9ca",
    "549bc0172dbefaf9936705df9da58ead29cd583141c5eaf294dd2fed5a693961",
)

PROHIBITED_RUNNER_FRAGMENTS = (
    "duckdb.connect(str(db), read_only=False)",
    "INSERT INTO",
    "UPDATE ",
    "DELETE FROM",
    "CREATE TABLE",
    "DROP TABLE",
    "ALTER TABLE",
    "BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=TRUE",
    "BITCOIN_RECOMMENDATION_POLICY_SKILL_CERTIFIED=TRUE",
    "AUTONOMOUS_EXECUTION_AUTHORIZED=TRUE",
)

REQUIRED_DESIGN_FRAGMENTS = (
    "BITCOIN_STRATEGIC_REGIME_FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_DESIGN_V1",
    "FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE",
    "OUTCOME_PEEKING_ALLOWED=FALSE",
    "MISSING_EVIDENCE_SYNTHESIZED=FALSE",
    "CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE",
    "BUILD_AND_VALIDATE_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_RUNNER",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--records-dir", required=True)
    args = parser.parse_args()

    runner = Path(args.runner).resolve()
    design = Path(args.design).resolve()
    manifest = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()

    for name, path in {"runner": runner, "design": design, "manifest": manifest}.items():
        require(path.is_file(), f"Required file missing: {name}={path}")

    runner_text = runner.read_text(encoding="utf-8")
    design_text = design.read_text(encoding="utf-8")
    manifest_text = manifest.read_text(encoding="utf-8")

    ast.parse(runner_text)

    for fragment in REQUIRED_RUNNER_FRAGMENTS:
        require(fragment.lower() in runner_text.lower(), f"Capture runner missing required boundary: {fragment}")

    for fragment in PROHIBITED_RUNNER_FRAGMENTS:
        require(fragment.lower() not in runner_text.lower(), f"Capture runner contains prohibited behavior: {fragment}")

    for fragment in REQUIRED_DESIGN_FRAGMENTS:
        require(fragment.lower() in design_text.lower(), f"Capture design missing required boundary: {fragment}")

    for fragment in (
        '"record_count": 0',
        '"synthetic_initial_observation_allowed": false',
        '"append_only_observation_records": true',
        '"outcomes_unknown_at_initial_observation": true',
        '"autonomous_execution_authorized": false',
    ):
        require(fragment.lower() in manifest_text.lower(), f"Ledger manifest missing required boundary: {fragment}")

    existing_records = sorted(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(existing_records) == 0, "First-capture validation requires zero existing observation records")

    print("FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_RUNNER_VALIDATION=PASS")
    print("RUNNER_MODE=SOURCE_DISCOVERY_FIRST")
    print("CAPTURE_MODE_AUTHORIZED=FALSE")
    print("DATABASE_ACCESS=READ_ONLY")
    print("LEDGER_RECORD_COUNT_REQUIRED=0")
    print("MISSING_EVIDENCE_SYNTHESIZED=FALSE")
    print("OUTCOME_PEEKING_ALLOWED=FALSE")
    print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
    print("BITCOIN_CYCLE_CALENDAR_ONLY_ACTION_AUTHORIZED=FALSE")
    print("BTC_ETH_RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED=TRUE")
    print("PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE")
    print("NEXT_GATE=EXECUTE_FIRST_PROSPECTIVE_BITCOIN_SOURCE_DISCOVERY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
