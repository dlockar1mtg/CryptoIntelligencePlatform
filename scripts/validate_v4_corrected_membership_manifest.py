from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_EXPERIMENT = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_GROUPS = 17
EXPECTED_SUPERSEDED_FILE_SHA256 = "dcaf32dccb8ab1031f7a6bea884e676deb0732466dc73a499d75e7d792f61b57"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def canonical_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("manifest_content_sha256", None)
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    path = Path(args.manifest).resolve()
    require(path.is_file(), f"Corrected V4 manifest missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))

    require(payload.get("experiment_id") == EXPECTED_EXPERIMENT, "Unexpected V4 experiment id")
    require(int(payload.get("manifest_revision", 0)) == 2, "Corrected V4 manifest revision must be 2")
    require(int(payload.get("supported_groups", 0)) == EXPECTED_GROUPS, "Unexpected supported-group count")
    require(int(payload.get("standard_development_origins_per_group", 0)) == 50, "Unexpected standard development count")
    require(int(payload.get("standard_final_holdout_origins_per_group", 0)) == 10, "Unexpected standard holdout count")
    require(int(payload.get("avalanche365_final_holdout_origins", 0)) == 9, "Avalanche365 holdout exception must be 9")
    require(payload.get("avalanche365_exception_governed") is True, "Avalanche365 exception is not governed")
    require(payload.get("supersedes_manifest_file_sha256") == EXPECTED_SUPERSEDED_FILE_SHA256, "Unexpected superseded manifest hash")
    require(payload.get("exact_calendar_target_availability_required") is True, "Exact calendar target availability not required")
    require(payload.get("strict_final_holdout_after_development_required") is True, "Strict chronological holdout boundary not required")
    require(payload.get("v3_final_holdout_reused") is False, "V3 final holdout was reused")
    require(payload.get("holdout_outcomes_viewed_before_freeze") is False, "V4 holdout outcomes were viewed before freeze")
    require(payload.get("holdout_outcome_values_read_during_rebuild") is False, "V4 holdout values were read during rebuild")
    require(payload.get("holdout_outcome_signs_read_during_rebuild") is False, "V4 holdout signs were read during rebuild")
    require(payload.get("holdout_outcome_magnitudes_read_during_rebuild") is False, "V4 holdout magnitudes were read during rebuild")
    require(payload.get("manifest_content_sha256") == canonical_hash(payload), "Corrected manifest canonical hash mismatch")

    groups = payload.get("groups", [])
    require(len(groups) == EXPECTED_GROUPS, "Unexpected corrected V4 group count")
    keys = [(str(g["asset_id"]), int(g["horizon_days"])) for g in groups]
    require(len(set(keys)) == EXPECTED_GROUPS, "Duplicate V4 group")

    expected = {(asset, horizon) for horizon in (7, 30, 365) for asset in ("bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche") if not (asset == "xrp" and horizon == 365)}
    require(set(keys) == expected, "Unexpected V4 group set")

    final_total = 0
    for group in groups:
        key = (str(group["asset_id"]), int(group["horizon_days"]))
        dev = list(group["v4_development_origin_dates"])
        final = list(group["v4_final_holdout_origin_dates"])
        require(len(dev) == 50, f"Development count is not 50 for {key}")
        expected_final = 9 if key == ("avalanche", 365) else 10
        require(len(final) == expected_final, f"Unexpected final holdout count for {key}")
        require(int(group.get("development_origin_count", -1)) == 50, f"Development count metadata mismatch for {key}")
        require(int(group.get("final_holdout_origin_count", -1)) == expected_final, f"Final count metadata mismatch for {key}")
        require(len(set(dev)) == len(dev), f"Duplicate development date for {key}")
        require(len(set(final)) == len(final), f"Duplicate final date for {key}")
        require(set(dev).isdisjoint(final), f"Development/final overlap for {key}")
        require(max(dev) < min(final), f"Final holdout is not strictly later than development for {key}")
        if key == ("avalanche", 365):
            require(group.get("allocation_exception") == "AVALANCHE365_FINAL_HOLDOUT_9", "Avalanche365 exception marker missing")
        else:
            require(group.get("allocation_exception") is None, f"Unexpected allocation exception for {key}")
        final_total += len(final)

    require(final_total == 169, f"Expected corrected V4 final-holdout total of 169, found {final_total}")

    print("CRYPTO_V4_CORRECTED_MEMBERSHIP_MANIFEST_VALIDATION=PASS")
    print("SUPPORTED_GROUPS=17")
    print("DEVELOPMENT_ORIGINS_TOTAL=850")
    print("FINAL_HOLDOUT_ORIGINS_TOTAL=169")
    print("AVALANCHE365_DEVELOPMENT_ORIGINS=50")
    print("AVALANCHE365_FINAL_HOLDOUT_ORIGINS=9")
    print("STRICT_FINAL_HOLDOUT_AFTER_DEVELOPMENT=TRUE")
    print("EXACT_CALENDAR_TARGET_AVAILABILITY_REQUIRED=TRUE")
    print("V3_FINAL_HOLDOUT_REUSED=FALSE")
    print("HOLDOUT_OUTCOMES_VIEWED_BEFORE_FREEZE=FALSE")
    print(f"MANIFEST_CONTENT_SHA256={payload['manifest_content_sha256']}")
    print("NEXT_GATE=PRESERVE_CORRECTED_V4_MEMBERSHIP_AND_RERUN_DEVELOPMENT_PREFLIGHT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
