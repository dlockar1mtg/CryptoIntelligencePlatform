from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb
import pandas as pd

EXPECTED_EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_OLD_CONTENT_SHA256 = "4b42d66a6cea1949b956fc5fe57545cb21abfe6b8cdddb0fe7f933b75734ca02"
EXPECTED_GENERATION = "EXACT_CALENDAR_TARGET_AVAILABILITY_V2"
EXPECTED_GROUPS = 17
EXPECTED_DEVELOPMENT = 50
EXPECTED_HOLDOUT = 10


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("manifest_content_sha256", None)
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--old-manifest", required=True)
    parser.add_argument("--corrected-manifest", required=True)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    old_path = Path(args.old_manifest).resolve()
    corrected_path = Path(args.corrected_manifest).resolve()
    for path in (database, old_path, corrected_path):
        require(path.is_file(), f"Required input missing: {path}")

    database_before = sha256(database)
    old_before = sha256(old_path)
    corrected_before = sha256(corrected_path)
    old = json.loads(old_path.read_text(encoding="utf-8"))
    corrected = json.loads(corrected_path.read_text(encoding="utf-8"))

    require(old.get("manifest_content_sha256") == EXPECTED_OLD_CONTENT_SHA256, "Unexpected old V4 manifest hash")
    require(corrected.get("experiment_id") == EXPECTED_EXPERIMENT_ID, "Unexpected corrected experiment id")
    require(corrected.get("membership_rule_generation") == EXPECTED_GENERATION, "Unexpected corrected membership generation")
    require(corrected.get("supersedes_manifest_content_sha256") == EXPECTED_OLD_CONTENT_SHA256, "Corrected manifest does not supersede expected V4 manifest")
    require(corrected.get("holdout_outcomes_viewed_before_freeze") is False, "Corrected manifest claims holdout outcomes were viewed")
    require(corrected.get("v3_final_holdout_reused") is False, "Corrected manifest reuses V3 holdout")
    require(canonical_hash(corrected) == corrected.get("manifest_content_sha256"), "Corrected manifest canonical hash mismatch")

    old_groups = {(str(g["asset_id"]), int(g["horizon_days"])): g for g in old["groups"]}
    new_groups = {(str(g["asset_id"]), int(g["horizon_days"])): g for g in corrected["groups"]}
    require(len(new_groups) == EXPECTED_GROUPS and set(new_groups) == set(old_groups), "Corrected supported-group set changed")

    changed_groups = []
    development_changes = []
    holdout_changes = []
    for key in sorted(old_groups):
        old_dev = list(old_groups[key]["v4_development_origin_dates"])
        new_dev = list(new_groups[key]["v4_development_origin_dates"])
        old_hold = list(old_groups[key]["v4_final_holdout_origin_dates"])
        new_hold = list(new_groups[key]["v4_final_holdout_origin_dates"])
        require(len(new_dev) == EXPECTED_DEVELOPMENT, f"Corrected development count changed for {key}")
        require(len(new_hold) == EXPECTED_HOLDOUT, f"Corrected holdout count changed for {key}")
        require(new_dev == sorted(new_dev), f"Corrected development dates not chronological for {key}")
        require(new_hold == sorted(new_hold), f"Corrected holdout dates not chronological for {key}")
        require(len(set(new_dev)) == len(new_dev), f"Duplicate corrected development dates for {key}")
        require(len(set(new_hold)) == len(new_hold), f"Duplicate corrected holdout dates for {key}")
        require(set(new_dev).isdisjoint(new_hold), f"Corrected development/holdout overlap for {key}")
        if old_dev != new_dev or old_hold != new_hold:
            changed_groups.append(key)
        if old_dev != new_dev:
            development_changes.append(key)
        if old_hold != new_hold:
            holdout_changes.append(key)

    require(changed_groups == [("xrp", 7)], f"Unexpected corrected groups: {changed_groups}")
    require(development_changes == [("xrp", 7)], f"Unexpected development membership changes: {development_changes}")
    require(not holdout_changes, f"V4 final holdout membership changed: {holdout_changes}")

    correction = corrected.get("exact_target_availability_correction") or {}
    require(correction.get("asset_id") == "xrp" and int(correction.get("horizon_days", 0)) == 7, "Unexpected correction group")
    require(correction.get("removed_origin_date") == "2021-01-13", "Unexpected removed development origin")
    require(correction.get("missing_target_date") == "2021-01-20", "Unexpected missing target date")
    replacement = str(correction.get("replacement_origin_date"))
    replacement_target = str(correction.get("replacement_target_date"))
    require(correction.get("holdout_membership_changed") is False, "Correction changed holdout membership")
    require(correction.get("holdout_outcome_values_read") is False, "Correction read holdout outcome values")

    # Date-only target endpoint validation for every corrected development and holdout date.
    conn = duckdb.connect(str(database), read_only=True)
    try:
        date_rows = conn.execute(
            """
            SELECT asset_id, observation_date
            FROM canonical_market_daily
            WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
              AND price_usd IS NOT NULL
            ORDER BY asset_id, observation_date
            """
        ).fetchdf()
    finally:
        conn.close()
    date_rows["observation_date"] = pd.to_datetime(date_rows["observation_date"])
    date_sets = {
        asset: set(group["observation_date"].dt.date.astype(str))
        for asset, group in date_rows.groupby("asset_id")
    }

    dev_checked = 0
    holdout_checked = 0
    for (asset, horizon), group in sorted(new_groups.items()):
        source_dates = date_sets[asset]
        for origin in group["v4_development_origin_dates"]:
            target = (pd.Timestamp(origin) + pd.Timedelta(days=horizon)).date().isoformat()
            require(target in source_dates, f"Corrected development exact target missing: {asset}|{horizon}|{origin}|{target}")
            dev_checked += 1
        for origin in group["v4_final_holdout_origin_dates"]:
            target = (pd.Timestamp(origin) + pd.Timedelta(days=horizon)).date().isoformat()
            require(target in source_dates, f"Corrected holdout exact target missing: {asset}|{horizon}|{origin}|{target}")
            holdout_checked += 1

    require(dev_checked == 850, f"Expected 850 corrected development origins, checked {dev_checked}")
    require(holdout_checked == 170, f"Expected 170 corrected holdout origins, checked {holdout_checked}")
    require((pd.Timestamp(replacement) + pd.Timedelta(days=7)).date().isoformat() == replacement_target, "Replacement target endpoint mismatch")

    require(sha256(database) == database_before, "Database changed during corrected-manifest validation")
    require(sha256(old_path) == old_before, "Old manifest changed during corrected-manifest validation")
    require(sha256(corrected_path) == corrected_before, "Corrected manifest changed during validation")

    print("CRYPTO_V4_EXACT_TARGET_CORRECTED_MANIFEST_VALIDATION=PASS")
    print("CHANGED_GROUPS=1")
    print("CHANGED_GROUP=xrp|7")
    print("V4_FINAL_HOLDOUT_MEMBERSHIP_CHANGED=FALSE")
    print(f"DEVELOPMENT_ORIGINS_EXACT_TARGET_CHECKED={dev_checked}")
    print(f"HOLDOUT_ORIGINS_EXACT_TARGET_CHECKED={holdout_checked}")
    print("HOLDOUT_OUTCOME_VALUES_READ=FALSE")
    print(f"CORRECTED_MANIFEST_CONTENT_SHA256={corrected['manifest_content_sha256']}")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=REPLACE_AND_PRESERVE_CORRECTED_V4_MANIFEST_THEN_RERUN_PREFLIGHT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
