from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED_RUNNER_FRAGMENTS = (
    "BITCOIN_LIVE_INPUT_AUTHORITY_RESOLUTION_V1",
    "read_only=True",
    "V4_7D_VOLATILITY_STATE_EXTRA_TREES",
    "canonical_market_daily",
    "latest_asset_market",
    "latest_m42_asset_recommendations",
    "latest_m42_portfolio_plan",
    "latest_macro_observations",
    "latest_macro_regime",
    "record_count",
    "FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE",
    "MISSING_EVIDENCE_SYNTHESIZED=FALSE",
    "OUTCOME_PEEKING_ALLOWED=FALSE",
    "CANONICAL_DATABASE_MODIFIED=FALSE",
    "AUTHORITY_DECISIONS_DEFERRED=TRUE",
    "REVIEW_BITCOIN_LIVE_INPUT_AUTHORITY_RESOLUTION",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runner", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--records-dir", required=True)
    args = p.parse_args()

    runner = Path(args.runner).resolve()
    manifest = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()

    require(runner.is_file(), f"Runner missing: {runner}")
    require(manifest.is_file(), f"Manifest missing: {manifest}")
    text = runner.read_text(encoding="utf-8")
    manifest_text = manifest.read_text(encoding="utf-8")

    for fragment in REQUIRED_RUNNER_FRAGMENTS:
        require(fragment.lower() in text.lower(), f"Runner missing required boundary: {fragment}")

    for fragment in (
        '"record_count": 0',
        '"synthetic_initial_observation_allowed": false',
        '"autonomous_execution_authorized": false',
    ):
        require(fragment.lower() in manifest_text.lower(), f"Manifest missing required boundary: {fragment}")

    record_files = list(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(record_files) == 0, "Prospective observation ledger must remain empty")

    print("BITCOIN_LIVE_INPUT_AUTHORITY_RESOLUTION_RUNNER_VALIDATION=PASS")
    print("DATABASE_ACCESS=READ_ONLY")
    print("LEDGER_RECORD_COUNT_REQUIRED=0")
    print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
    print("MISSING_EVIDENCE_SYNTHESIZED=FALSE")
    print("OUTCOME_PEEKING_ALLOWED=FALSE")
    print("CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE")
    print("AUTHORITY_DECISIONS_DEFERRED=TRUE")
    print("NEXT_GATE=EXECUTE_BITCOIN_LIVE_INPUT_AUTHORITY_RESOLUTION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
