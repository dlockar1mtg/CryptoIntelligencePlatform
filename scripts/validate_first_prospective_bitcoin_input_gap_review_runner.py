from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED_RUNNER_FRAGMENTS = (
    "FIRST_PROSPECTIVE_BITCOIN_INPUT_GAP_REVIEW_V1",
    "read_only=True",
    "canonical_market_daily",
    "latest_m42_asset_recommendations",
    "m42_asset_recommendations",
    "module42_runs",
    "latest_predictive_classifications",
    "ml_predictions_current",
    "latest_model_snapshots",
    "latest_portfolio_summary",
    "latest_m35_portfolio_allocations",
    "latest_macro_observations",
    "latest_macro_regime",
    "record_count",
    "capture_performed",
    "missing_evidence_synthesized",
    "outcome_peeking_allowed",
    "FIRST_PROSPECTIVE_BITCOIN_INPUT_GAP_REVIEW=PASS",
    "NEXT_GATE=REVIEW_BITCOIN_INPUT_GAP_TABLE_AUTHORITIES",
)

PROHIBITED_RUNNER_FRAGMENTS = (
    "duckdb.connect(str(database))",
    "INSERT INTO",
    "UPDATE ",
    "DELETE FROM",
    "CREATE TABLE",
    "DROP TABLE",
    "ALTER TABLE",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--preserved-discovery", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--records-dir", required=True)
    args = parser.parse_args()

    runner = Path(args.runner).resolve()
    discovery = Path(args.preserved_discovery).resolve()
    manifest = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()

    for name, path in {"runner": runner, "preserved_discovery": discovery, "manifest": manifest}.items():
        require(path.is_file(), f"Required file missing: {name}={path}")

    runner_text = runner.read_text(encoding="utf-8")
    discovery_text = discovery.read_text(encoding="utf-8")
    manifest_text = manifest.read_text(encoding="utf-8")

    for fragment in REQUIRED_RUNNER_FRAGMENTS:
        require(fragment.lower() in runner_text.lower(), f"Input-gap runner missing required boundary: {fragment}")

    for fragment in PROHIBITED_RUNNER_FRAGMENTS:
        require(fragment.lower() not in runner_text.lower(), f"Input-gap runner contains prohibited database-write pattern: {fragment}")

    for fragment in (
        '"inspection_id": "FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_SOURCE_DISCOVERY_V1"',
        '"capture_performed": false',
        '"module42_live_action_discovered": false',
        '"v4_live_inference_discovered": false',
        '"portfolio_context_discovered": false',
    ):
        require(fragment.lower() in discovery_text.lower(), f"Preserved discovery missing expected boundary: {fragment}")

    for fragment in (
        '"ledger_id": "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1"',
        '"record_count": 0',
        '"autonomous_execution_authorized": false',
    ):
        require(fragment.lower() in manifest_text.lower(), f"Ledger manifest missing expected boundary: {fragment}")

    if records_dir.exists():
        require(not list(records_dir.rglob("*.json")), "Ledger must remain empty before input-gap review")

    print("FIRST_PROSPECTIVE_BITCOIN_INPUT_GAP_REVIEW_RUNNER_VALIDATION=PASS")
    print("DATABASE_ACCESS=READ_ONLY")
    print("LEDGER_RECORD_COUNT_REQUIRED=0")
    print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
    print("MISSING_EVIDENCE_SYNTHESIZED=FALSE")
    print("OUTCOME_PEEKING_ALLOWED=FALSE")
    print("CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE")
    print("NEXT_GATE=EXECUTE_FIRST_PROSPECTIVE_BITCOIN_INPUT_GAP_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
