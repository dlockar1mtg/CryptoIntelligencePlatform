from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--authorization", required=True)
    args = parser.parse_args()

    runner = Path(args.runner).read_text(encoding="utf-8")
    authorization = Path(args.authorization).read_text(encoding="utf-8")

    runner_markers = (
        'EXPECTED_V4_SHA256 = "4fb9c06cc69ac47e22bb881954e05b61f5b8dba0392133d601f5946807b739c2"',
        'EXPECTED_MACRO_SHA256 = "67626cb87b9c041d47a685bc9a41fd47ab15c07f6db419a0e3c0d92b028d65c9"',
        '"strategic_state": "INSUFFICIENT_EVIDENCE"',
        '"tactical_new_capital_state": "INSUFFICIENT_EVIDENCE"',
        '"existing_position_state": "INSUFFICIENT_EVIDENCE"',
        '"recomputed_for_capture": False',
        '"module42_rerun_performed": False',
        '"return_7d_exact": None',
        '"return_30d_exact": None',
        '"return_90d_exact": None',
        '"return_180d_exact": None',
        '"return_365d_exact": None',
        '"return_1095d_exact": None',
        '"production_policy_change_authorized": False',
        '"autonomous_execution_authorized": False',
        '"canonical_database_write_authorized": False',
        'require(sha256(database) == database_hash_before, "Canonical database changed during observation capture")',
    )
    for marker in runner_markers:
        require(marker in runner, f"Runner marker missing: {marker}")

    prohibited_runner_markers = (
        "duckdb.connect(",
        "run_module42",
        "run_module1",
        "run_module6",
        "fit_predict(",
        "hyperparameter",
    )
    for marker in prohibited_runner_markers:
        require(marker not in runner, f"Prohibited capture-runner behavior marker present: {marker}")

    authorization_markers = (
        "BITCOIN_FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_AUTHORIZATION_V1",
        "FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_AUTHORIZED=TRUE",
        "STRATEGIC_STATE=INSUFFICIENT_EVIDENCE",
        "TACTICAL_NEW_CAPITAL_STATE=INSUFFICIENT_EVIDENCE",
        "EXISTING_POSITION_STATE=INSUFFICIENT_EVIDENCE",
        "V4_RECOMPUTE_FOR_CAPTURE_AUTHORIZED=FALSE",
        "MISSING_EVIDENCE_SYNTHESIZED=FALSE",
        "CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE",
        "PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE",
        "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
    )
    for marker in authorization_markers:
        require(marker in authorization, f"Authorization marker missing: {marker}")

    print("FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_V2_STATIC_VALIDATION=PASS")
    print("STRATEGIC_STATE_LOCKED=INSUFFICIENT_EVIDENCE")
    print("TACTICAL_STATE_LOCKED=INSUFFICIENT_EVIDENCE")
    print("EXISTING_POSITION_STATE_LOCKED=INSUFFICIENT_EVIDENCE")
    print("V4_RECOMPUTE_AUTHORIZED=FALSE")
    print("MODULE42_RERUN_AUTHORIZED=FALSE")
    print("CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE")
    print("PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("NEXT_GATE=RUN_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_V2_PREFLIGHT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
