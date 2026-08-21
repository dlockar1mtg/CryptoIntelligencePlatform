from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED_FRAGMENTS = (
    "BITCOIN_LIVE_REFRESH_AND_V4_OPERATIONALIZATION_V1",
    "V4_7D_VOLATILITY_STATE_EXTRA_TREES",
    "run_module1.py",
    "run_module6.py",
    "--phase",
    "sync",
    "--full-refresh",
    "CRYPTO_DATABASE_PATH",
    "EXPECTED_V3_RESULTS_SHA256",
    "EXPECTED_V4_MANIFEST_CONTENT_SHA256",
    "EXPECTED_DEVELOPMENT_RESULTS_SHA256",
    "v4_split_origin",
    "fit_predict",
    "candidate_features",
    "selected_v3_origins_for_group",
    "contract_preserving_operational_refit",
    "model_selection_reopened",
    "post_holdout_tuning_performed",
    "hyperparameter_search_performed",
    "feature_contract_changed",
    "first_prospective_observation_captured",
    "ledger_record_count",
    "module42_rerun_performed",
    "personal_portfolio_context_supplied",
    "REVIEW_BITCOIN_LIVE_REFRESH_AND_V4_OPERATIONALIZATION_RESULTS",
)

FORBIDDEN_FRAGMENTS = (
    "run_module42.py",
    "--full-refresh\"]",
    "--phase\", \"all",
    "--phase\", \"research",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--governance", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--records-dir", required=True)
    args = parser.parse_args()

    runner = Path(args.runner).resolve()
    governance = Path(args.governance).resolve()
    manifest = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()

    for path in (runner, governance, manifest):
        require(path.is_file(), f"Required preflight input missing: {path}")

    text = runner.read_text(encoding="utf-8")
    governance_text = governance.read_text(encoding="utf-8")

    for fragment in REQUIRED_FRAGMENTS:
        require(fragment in text, f"Runner missing required fragment: {fragment}")

    for fragment in FORBIDDEN_FRAGMENTS:
        require(fragment not in text, f"Runner contains forbidden fragment: {fragment}")

    for marker in (
        "MODULE1_INCREMENTAL_REFRESH_AUTHORIZED=TRUE",
        "MODULE1_FULL_REFRESH_AUTHORIZED=FALSE",
        "MODULE6_SYNC_AUTHORIZED=TRUE",
        "MODULE6_RESEARCH_PHASE_AUTHORIZED=FALSE",
        "V4_7D_FROZEN_FAMILY_OPERATIONAL_REFIT_AUTHORIZED=TRUE",
        "V4_MODEL_SELECTION_REOPENED=FALSE",
        "V4_POST_HOLDOUT_TUNING_AUTHORIZED=FALSE",
        "V4_HYPERPARAMETER_SEARCH_AUTHORIZED=FALSE",
        "V4_FEATURE_CONTRACT_CHANGE_AUTHORIZED=FALSE",
        "MODULE42_RERUN_AUTHORIZED=FALSE",
        "FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_AUTHORIZED=FALSE",
    ):
        require(marker in governance_text, f"Governance missing required marker: {marker}")

    import json
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    require(int(payload.get("record_count", -1)) == 0, "Ledger manifest record_count is not zero")
    record_files = list(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(record_files) == 0, "Forward-evidence ledger already contains records")

    print("BITCOIN_LIVE_REFRESH_AND_V4_OPERATIONALIZATION_RUNNER_VALIDATION=PASS")
    print("MODULE1_INCREMENTAL_REFRESH_PATH=AUTHORIZED")
    print("MODULE1_FULL_REFRESH_PATH=FORBIDDEN")
    print("MODULE6_SYNC_ONLY=TRUE")
    print("V4_7D_FROZEN_FAMILY=V4_7D_VOLATILITY_STATE_EXTRA_TREES")
    print("V4_CONTRACT_PRESERVING_OPERATIONAL_REFIT=TRUE")
    print("V4_MODEL_SELECTION_REOPENED=FALSE")
    print("V4_POST_HOLDOUT_TUNING_AUTHORIZED=FALSE")
    print("V4_30D_QUALIFIED_PREDICTION_AUTHORIZED=FALSE")
    print("V4_365D_QUALIFIED_PREDICTION_AUTHORIZED=FALSE")
    print("MODULE42_RERUN_AUTHORIZED=FALSE")
    print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
    print("LEDGER_RECORD_COUNT=0")
    print("PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("NEXT_GATE=EXECUTE_BITCOIN_LIVE_REFRESH_AND_V4_OPERATIONALIZATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
