from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_TOURNAMENT_V3"
EXPECTED_SUPPORTED_GROUPS = 29
EXPECTED_ROWS_PER_GROUP = 10
EXPECTED_TOTAL_ROWS = 290


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def canonical_manifest_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("manifest_content_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    path = Path(args.manifest).resolve()
    require(path.is_file(), f"Manifest missing: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))

    require(manifest.get("experiment_id") == EXPECTED_EXPERIMENT_ID, "Unexpected experiment id")
    require(manifest.get("holdout_role") == "FINAL_POST_TOURNAMENT_SELECTION_HOLDOUT", "Unexpected holdout role")
    require(manifest.get("holdout_outcomes_viewed_before_freeze") is False, "V3 holdout was not frozen pre-outcome")
    require(int(manifest.get("supported_groups", -1)) == EXPECTED_SUPPORTED_GROUPS, "Unexpected supported-group count")
    require(int(manifest.get("rows_per_supported_group", -1)) == EXPECTED_ROWS_PER_GROUP, "Unexpected rows per supported group")
    require(len(manifest.get("groups", [])) == EXPECTED_SUPPORTED_GROUPS, "Unexpected group manifest length")
    require(canonical_manifest_hash(manifest) == manifest.get("manifest_content_sha256"), "Manifest content hash mismatch")

    seen_groups: set[tuple[str, int]] = set()
    total_rows = 0
    for group in manifest["groups"]:
        key = (str(group["asset_id"]), int(group["horizon_days"]))
        require(key not in seen_groups, f"Duplicate group: {key}")
        seen_groups.add(key)
        dates = list(group["v3_final_holdout_origin_dates"])
        require(len(dates) == EXPECTED_ROWS_PER_GROUP, f"Expected 10 dates for {key}")
        require(len(set(dates)) == EXPECTED_ROWS_PER_GROUP, f"Duplicate holdout date for {key}")
        total_rows += len(dates)

    require(total_rows == EXPECTED_TOTAL_ROWS, f"Expected 290 total V3 holdout rows, got {total_rows}")
    require(("xrp", 365) not in seen_groups, "XRP 365d must remain unsupported")
    require(
        any(str(r.get("asset_id")) == "xrp" and int(r.get("horizon_days", -1)) == 365 for r in manifest.get("unsupported_groups", [])),
        "Explicit XRP 365d unsupported record missing",
    )

    print("CRYPTO_V3_FROZEN_FINAL_HOLDOUT_MANIFEST_VALIDATION=PASS")
    print("V3_HOLDOUT_OUTCOMES_VIEWED_BEFORE_FREEZE=FALSE")
    print("SUPPORTED_GROUPS=29")
    print("ROWS_PER_SUPPORTED_GROUP=10")
    print("TOTAL_FROZEN_HOLDOUT_ROWS=290")
    print(f"MANIFEST_CONTENT_SHA256={manifest['manifest_content_sha256']}")
    print("NEXT_GATE=CHECKPOINT_FROZEN_V3_FINAL_HOLDOUT_MANIFEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
