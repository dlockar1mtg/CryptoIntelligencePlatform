from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    path = Path(args.manifest).resolve()
    require(path.is_file(), f"Manifest missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))

    expected_sha = str(payload.pop("manifest_content_sha256"))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    actual_sha = hashlib.sha256(canonical).hexdigest()
    require(actual_sha == expected_sha, "Frozen V2 holdout manifest SHA mismatch")

    require(payload["experiment_id"] == "CRYPTO_NATIVE_PREDICTIVE_MODEL_IMPROVEMENT_V2", "Unexpected experiment id")
    require(payload["holdout_outcomes_viewed_before_freeze"] is False, "Holdout outcome isolation was not preserved")
    require(int(payload["rows_per_supported_group"]) == 10, "Expected ten frozen rows per supported group")
    require(int(payload["supported_groups"]) == 29, "Expected 29 supported groups")
    groups = payload["groups"]
    require(len(groups) == 29, "Expected 29 group records")

    all_dates = []
    for group in groups:
        dates = list(group["v2_holdout_origin_dates"])
        require(len(dates) == 10, "Each supported group must contain exactly ten frozen origins")
        require(len(set(dates)) == 10, "Duplicate frozen origin within a group")
        all_dates.extend((group["asset_id"], int(group["horizon_days"]), d) for d in dates)

    unsupported = payload["unsupported_groups"]
    require(
        any(r["asset_id"] == "xrp" and int(r["horizon_days"]) == 365 for r in unsupported),
        "Expected explicit XRP 365d unsupported group",
    )

    print("CRYPTO_V2_FROZEN_HOLDOUT_MANIFEST_VALIDATION=PASS")
    print("V2_HOLDOUT_OUTCOMES_VIEWED_BEFORE_FREEZE=FALSE")
    print("SUPPORTED_GROUPS=29")
    print("ROWS_PER_SUPPORTED_GROUP=10")
    print("TOTAL_FROZEN_HOLDOUT_ROWS=290")
    print(f"MANIFEST_CONTENT_SHA256={expected_sha}")
    print("NEXT_GATE=CHECKPOINT_FROZEN_V2_HOLDOUT_MANIFEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
