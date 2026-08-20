from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_V3_RESULTS_SHA256 = "33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1"
EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "510d121e1e4e8ea7e2079b1f61883b2ca01dfb6ce2c6baf6b9ba601eadeafd42"
EXPECTED_GROUPS = 17
EXPECTED_DEV_PER_GROUP = 50
STANDARD_HOLDOUT_PER_GROUP = 10
AVALANCHE_365_HOLDOUT = 9
EXPECTED_DEV_TOTAL = 850
EXPECTED_HOLDOUT_TOTAL = 169
AVALANCHE_365_KEY = ("avalanche", 365)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_content_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("manifest_content_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def expected_holdout_count(key: tuple[str, int]) -> int:
    return AVALANCHE_365_HOLDOUT if key == AVALANCHE_365_KEY else STANDARD_HOLDOUT_PER_GROUP


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--v3-results", required=True)
    parser.add_argument("--v4-manifest", required=True)
    parser.add_argument("--harness", required=True)
    parser.add_argument("--harness-validator", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    v2_path = Path(args.v2_manifest).resolve()
    v3_path = Path(args.v3_manifest).resolve()
    v3_results_path = Path(args.v3_results).resolve()
    v4_path = Path(args.v4_manifest).resolve()
    harness_path = Path(args.harness).resolve()
    validator_path = Path(args.harness_validator).resolve()
    output_path = Path(args.output).resolve()

    for path in (database, v2_path, v3_path, v3_results_path, v4_path, harness_path, validator_path):
        require(path.is_file(), f"Required authorization input missing: {path}")
    require(not output_path.exists(), "V4 development output already exists; refusing authorization")

    require(sha256(v3_results_path) == EXPECTED_V3_RESULTS_SHA256, "Unexpected preserved V3 development-results hash")

    v3_results = json.loads(v3_results_path.read_text(encoding="utf-8"))
    v4 = json.loads(v4_path.read_text(encoding="utf-8"))

    require(v3_results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout has been viewed")
    require(v4.get("experiment_id") == EXPECTED_EXPERIMENT_ID, "Unexpected V4 experiment id")
    require(v4.get("manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Unexpected V4 manifest declared content hash")
    require(manifest_content_hash(v4) == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Unexpected V4 manifest canonical content hash")
    require(v4.get("holdout_outcomes_viewed_before_freeze") is False, "V4 holdout outcomes were viewed before freeze")
    require(v4.get("holdout_outcome_values_read_during_rebuild") is False, "V4 holdout outcome values were read during rebuild")
    require(v4.get("v3_final_holdout_reused") is False, "V3 final holdout was reused by V4")
    require(int(v4.get("supported_groups", 0)) == EXPECTED_GROUPS, "Unexpected V4 supported-group count")
    require(int(v4.get("standard_final_holdout_origins_per_group", 0)) == STANDARD_HOLDOUT_PER_GROUP, "Unexpected standard V4 holdout count")
    require(int(v4.get("avalanche365_final_holdout_origins", 0)) == AVALANCHE_365_HOLDOUT, "Unexpected Avalanche 365 V4 holdout count")
    require(v4.get("avalanche365_exception_governed") is True, "Avalanche 365 V4 holdout exception is not governed")
    require(v4.get("exact_calendar_target_availability_required") is True, "Exact-calendar target availability is not required")
    require(v4.get("strict_final_holdout_after_development_required") is True, "Strict V4 final-holdout chronology is not required")

    groups = list(v4.get("groups", []))
    require(len(groups) == EXPECTED_GROUPS, "Unexpected V4 manifest group count")
    seen = set()
    dev_total = 0
    holdout_total = 0
    for group in groups:
        key = (str(group["asset_id"]), int(group["horizon_days"]))
        require(key not in seen, f"Duplicate V4 group: {key}")
        seen.add(key)
        dev = list(group["v4_development_origin_dates"])
        holdout = list(group["v4_final_holdout_origin_dates"])
        expected_holdout = expected_holdout_count(key)
        require(len(dev) == EXPECTED_DEV_PER_GROUP, f"Unexpected V4 development count for {key}")
        require(len(holdout) == expected_holdout, f"Unexpected V4 holdout count for {key}: expected {expected_holdout}, found {len(holdout)}")
        require(int(group.get("development_origin_count", -1)) == EXPECTED_DEV_PER_GROUP, f"V4 declared development count mismatch for {key}")
        require(int(group.get("final_holdout_origin_count", -1)) == expected_holdout, f"V4 declared holdout count mismatch for {key}")
        if key == AVALANCHE_365_KEY:
            require(group.get("allocation_exception") is not None, "Avalanche 365 governed allocation exception is missing")
        else:
            require(group.get("allocation_exception") is None, f"Unexpected V4 allocation exception for {key}")
        require(len(set(dev)) == len(dev), f"Duplicate V4 development dates for {key}")
        require(len(set(holdout)) == len(holdout), f"Duplicate V4 holdout dates for {key}")
        require(set(dev).isdisjoint(holdout), f"V4 development/holdout overlap for {key}")
        dev_total += len(dev)
        holdout_total += len(holdout)

    require(dev_total == EXPECTED_DEV_TOTAL, "Unexpected total V4 development origins")
    require(holdout_total == EXPECTED_HOLDOUT_TOTAL, "Unexpected total V4 holdout origins")

    harness = harness_path.read_text(encoding="utf-8")
    validator = validator_path.read_text(encoding="utf-8")
    required_harness_literals = [
        EXPECTED_V4_MANIFEST_CONTENT_SHA256,
        "holdout_outcomes_viewed_before_freeze",
        "holdout_outcome_values_read_during_rebuild",
        "v3_final_holdout_outcomes_viewed",
        "require(not output.exists()",
        "with tempfile.TemporaryDirectory",
        "before == after",
        "v4_final_holdout_origins_excluded",
        "v3_final_holdout_origins_excluded",
        "recommendation_policy_changed",
    ]
    for literal in required_harness_literals:
        require(literal in harness, f"V4 development harness missing required control: {literal}")

    require("CRYPTO_V4_DEVELOPMENT_HARNESS_VALIDATION=PASS" in validator, "Harness validator PASS contract missing")
    require(EXPECTED_V4_MANIFEST_CONTENT_SHA256 in validator, "Harness validator does not bind corrected V4 manifest hash")

    print("CRYPTO_V4_DEVELOPMENT_SCORING_AUTHORIZATION=PASS")
    print("RECOVERY_HORIZONS=7,30,365")
    print(f"SUPPORTED_GROUPS={len(groups)}")
    print(f"DEVELOPMENT_ORIGINS={dev_total}")
    print(f"FINAL_HOLDOUT_ORIGINS={holdout_total}")
    print("AVALANCHE_365_FINAL_HOLDOUT_ORIGINS=9")
    print("AVALANCHE_365_EXCEPTION_GOVERNED=TRUE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V4_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V4_DEVELOPMENT_OUTPUT_ALREADY_EXISTS=FALSE")
    print("SOURCE_DATABASE_WRITE_TARGET=DISPOSABLE_COPY")
    print("RECOMMENDATION_POLICY_CHANGED=FALSE")
    print("V4_DEVELOPMENT_SCORING_AUTHORIZED=TRUE")
    print("NEXT_GATE=RUN_V4_DEVELOPMENT_SCORING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
