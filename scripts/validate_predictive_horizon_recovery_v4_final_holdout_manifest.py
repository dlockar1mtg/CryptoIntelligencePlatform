from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_EVIDENCE_CLASS = "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME"
EXPECTED_HORIZONS = [7, 30, 365]
EXPECTED_SUPPORTED_GROUPS = 17
EXPECTED_DEVELOPMENT_ORIGINS_PER_GROUP = 50
EXPECTED_FINAL_HOLDOUT_ORIGINS_PER_GROUP = 10
EXPECTED_AVALANCHE365_FINAL_HOLDOUT_ORIGINS = 9
AVALANCHE365_KEY = ("avalanche", 365)


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
    require(path.is_file(), f"V4 final-holdout manifest missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))

    require(payload.get("experiment_id") == EXPECTED_EXPERIMENT_ID, "Unexpected V4 experiment id")
    require(payload.get("evidence_class") == EXPECTED_EVIDENCE_CLASS, "Unexpected evidence class")
    require(payload.get("recovery_horizons") == EXPECTED_HORIZONS, "Unexpected V4 recovery horizons")
    require(int(payload.get("supported_groups", 0)) == EXPECTED_SUPPORTED_GROUPS, "Unexpected supported-group count")
    require(int(payload.get("development_origins_per_group", 0)) == EXPECTED_DEVELOPMENT_ORIGINS_PER_GROUP, "Unexpected development-origin count")
    require(int(payload.get("final_holdout_origins_per_group", 0)) == EXPECTED_FINAL_HOLDOUT_ORIGINS_PER_GROUP, "Unexpected default final-holdout-origin count")
    require(payload.get("avalanche365_exception_governed") is True, "Avalanche365 governed exception missing")
    require(int(payload.get("avalanche365_development_origins", 0)) == EXPECTED_DEVELOPMENT_ORIGINS_PER_GROUP, "Unexpected Avalanche365 development-origin count")
    require(int(payload.get("avalanche365_final_holdout_origins", 0)) == EXPECTED_AVALANCHE365_FINAL_HOLDOUT_ORIGINS, "Unexpected Avalanche365 final-holdout count")
    require(payload.get("candidate_safe_membership_required") is True, "V4 candidate-safe membership control missing")
    require(payload.get("v2_consumed_origins_excluded") is True, "V2 consumed-origin exclusion missing")
    require(payload.get("v3_development_origins_excluded") is True, "V3 development-origin exclusion missing")
    require(payload.get("v3_final_holdout_origins_excluded") is True, "V3 final-holdout exclusion missing")
    require(payload.get("v3_final_holdout_reused") is False, "V3 final holdout was reused")
    require(payload.get("holdout_outcomes_viewed_before_freeze") is False, "V4 holdout outcomes were viewed before freeze")
    require(payload.get("exact_calendar_target_date_required") is True, "Exact calendar target-date control missing")
    require(payload.get("holdout_outcome_values_read_during_membership_selection") is False, "Holdout outcomes were read during membership selection")

    groups = payload.get("groups")
    require(isinstance(groups, list) and len(groups) == EXPECTED_SUPPORTED_GROUPS, "Unexpected V4 group manifest")

    seen_groups: set[tuple[str, int]] = set()
    for group in groups:
        asset = str(group.get("asset_id"))
        horizon = int(group.get("horizon_days", 0))
        key = (asset, horizon)
        require(key not in seen_groups, f"Duplicate V4 group: {key}")
        seen_groups.add(key)

        development = group.get("v4_development_origin_dates")
        final = group.get("v4_final_holdout_origin_dates")
        expected_final = (
            EXPECTED_AVALANCHE365_FINAL_HOLDOUT_ORIGINS
            if key == AVALANCHE365_KEY
            else EXPECTED_FINAL_HOLDOUT_ORIGINS_PER_GROUP
        )

        require(isinstance(development, list) and len(development) == EXPECTED_DEVELOPMENT_ORIGINS_PER_GROUP, f"Unexpected development origins for {key}")
        require(isinstance(final, list) and len(final) == expected_final, f"Unexpected final holdout origins for {key}")
        require(int(group.get("development_origin_count", len(development))) == EXPECTED_DEVELOPMENT_ORIGINS_PER_GROUP, f"Development-origin metadata mismatch for {key}")
        require(int(group.get("final_holdout_origin_count", len(final))) == expected_final, f"Final-holdout metadata mismatch for {key}")
        require(len(set(development)) == len(development), f"Duplicate development origin for {key}")
        require(len(set(final)) == len(final), f"Duplicate final holdout origin for {key}")
        require(set(development).isdisjoint(final), f"Development/final overlap for {key}")
        require(development == sorted(development), f"Development origins not chronological for {key}")
        require(final == sorted(final), f"Final holdout origins not chronological for {key}")
        require(max(development) < min(final), f"Final holdout is not later than V4 development for {key}")

    expected_groups = {
        (asset, horizon)
        for horizon in (7, 30)
        for asset in ("bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche")
    } | {
        (asset, 365)
        for asset in ("bitcoin", "ethereum", "solana", "chainlink", "avalanche")
    }
    require(seen_groups == expected_groups, "Unexpected V4 supported-group membership")

    expected_hash = payload.get("manifest_content_sha256")
    require(isinstance(expected_hash, str) and len(expected_hash) == 64, "Missing V4 manifest content hash")
    require(canonical_hash(payload) == expected_hash, "V4 manifest canonical hash mismatch")

    print("CRYPTO_V4_FINAL_HOLDOUT_MANIFEST_VALIDATION=PASS")
    print(f"SUPPORTED_GROUPS={EXPECTED_SUPPORTED_GROUPS}")
    print(f"DEVELOPMENT_ORIGINS_PER_GROUP={EXPECTED_DEVELOPMENT_ORIGINS_PER_GROUP}")
    print(f"DEFAULT_FINAL_HOLDOUT_ORIGINS_PER_GROUP={EXPECTED_FINAL_HOLDOUT_ORIGINS_PER_GROUP}")
    print(f"AVALANCHE365_FINAL_HOLDOUT_ORIGINS={EXPECTED_AVALANCHE365_FINAL_HOLDOUT_ORIGINS}")
    print(f"MANIFEST_CONTENT_SHA256={expected_hash}")
    print("CANDIDATE_SAFE_MEMBERSHIP_REQUIRED=TRUE")
    print("EXACT_CALENDAR_TARGET_DATE_REQUIRED=TRUE")
    print("HOLDOUT_OUTCOME_VALUES_READ_DURING_MEMBERSHIP_SELECTION=FALSE")
    print("HOLDOUT_OUTCOMES_VIEWED_BEFORE_FREEZE=FALSE")
    print("V3_FINAL_HOLDOUT_REUSED=FALSE")
    print("NEXT_GATE=PRESERVE_CANDIDATE_SAFE_V4_MANIFEST_BEFORE_DEVELOPMENT_PREFLIGHT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
