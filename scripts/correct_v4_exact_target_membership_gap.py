from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

EXPECTED_EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_OLD_CONTENT_SHA256 = "4b42d66a6cea1949b956fc5fe57545cb21abfe6b8cdddb0fe7f933b75734ca02"
EXPECTED_GAP_ASSET = "xrp"
EXPECTED_GAP_HORIZON = 7
EXPECTED_GAP_ORIGIN = "2021-01-13"
EXPECTED_GAP_TARGET = "2021-01-20"
CORRECTION_GENERATION = "EXACT_CALENDAR_TARGET_AVAILABILITY_V2"


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
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    manifest_path = Path(args.manifest).resolve()
    output = Path(args.output).resolve()
    require(database.is_file(), f"Database missing: {database}")
    require(manifest_path.is_file(), f"V4 manifest missing: {manifest_path}")
    require(not output.exists(), f"Correction output already exists: {output}")

    database_before = sha256(database)
    manifest_before = sha256(manifest_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(payload.get("experiment_id") == EXPECTED_EXPERIMENT_ID, "Unexpected V4 experiment id")
    require(payload.get("manifest_content_sha256") == EXPECTED_OLD_CONTENT_SHA256, "Unexpected source V4 manifest content hash")
    require(canonical_hash(payload) == EXPECTED_OLD_CONTENT_SHA256, "Source V4 manifest canonical hash mismatch")
    require(payload.get("holdout_outcomes_viewed_before_freeze") is False, "V4 holdout outcomes were already viewed")

    # Availability audit is date-only: do not read price values or calculate returns.
    import duckdb

    conn = duckdb.connect(str(database), read_only=True)
    try:
        dates = conn.execute(
            """
            SELECT observation_date
            FROM canonical_market_daily
            WHERE asset_id=? AND price_usd IS NOT NULL
            ORDER BY observation_date
            """,
            [EXPECTED_GAP_ASSET],
        ).fetchdf()
    finally:
        conn.close()

    source_dates = sorted(pd.to_datetime(dates["observation_date"]).dt.date.astype(str).unique().tolist())
    source_date_set = set(source_dates)
    require(EXPECTED_GAP_ORIGIN in source_date_set, "Expected gap origin is absent from source dates")
    require(EXPECTED_GAP_TARGET not in source_date_set, "Expected target date unexpectedly exists; correction premise changed")

    target_group = None
    for group in payload.get("groups", []):
        if str(group.get("asset_id")) == EXPECTED_GAP_ASSET and int(group.get("horizon_days", 0)) == EXPECTED_GAP_HORIZON:
            target_group = group
            break
    require(target_group is not None, "XRP 7d V4 group missing")

    development = list(target_group["v4_development_origin_dates"])
    holdout = list(target_group["v4_final_holdout_origin_dates"])
    require(development.count(EXPECTED_GAP_ORIGIN) == 1, "Expected XRP 7d development gap origin not found exactly once")
    gap_index = development.index(EXPECTED_GAP_ORIGIN)
    require(0 < gap_index < len(development) - 1, "Gap origin is at unsupported development boundary")
    previous_date = development[gap_index - 1]
    next_date = development[gap_index + 1]

    used_dates = set(development) | set(holdout)
    candidates = []
    gap_ts = pd.Timestamp(EXPECTED_GAP_ORIGIN)
    for date_key in source_dates:
        if not (previous_date < date_key < next_date):
            continue
        if date_key in used_dates:
            continue
        target_key = (pd.Timestamp(date_key) + pd.Timedelta(days=EXPECTED_GAP_HORIZON)).date().isoformat()
        if target_key not in source_date_set:
            continue
        distance = abs((pd.Timestamp(date_key) - gap_ts).days)
        candidates.append((distance, date_key, target_key))

    require(candidates, "No deterministic exact-target replacement exists between neighboring XRP 7d development origins")
    candidates.sort(key=lambda row: (row[0], row[1]))
    _, replacement_origin, replacement_target = candidates[0]

    corrected = json.loads(json.dumps(payload))
    corrected_group = next(
        group for group in corrected["groups"]
        if str(group.get("asset_id")) == EXPECTED_GAP_ASSET and int(group.get("horizon_days", 0)) == EXPECTED_GAP_HORIZON
    )
    corrected_development = list(corrected_group["v4_development_origin_dates"])
    corrected_development[gap_index] = replacement_origin
    require(corrected_development == sorted(corrected_development), "Corrected XRP 7d development origins are not chronological")
    require(len(set(corrected_development)) == len(corrected_development), "Corrected XRP 7d development origins contain duplicates")
    require(set(corrected_development).isdisjoint(corrected_group["v4_final_holdout_origin_dates"]), "Corrected development origin overlaps V4 final holdout")
    corrected_group["v4_development_origin_dates"] = corrected_development

    corrected["membership_rule_generation"] = CORRECTION_GENERATION
    corrected["supersedes_manifest_content_sha256"] = EXPECTED_OLD_CONTENT_SHA256
    corrected["exact_target_availability_correction"] = {
        "asset_id": EXPECTED_GAP_ASSET,
        "horizon_days": EXPECTED_GAP_HORIZON,
        "removed_origin_date": EXPECTED_GAP_ORIGIN,
        "missing_target_date": EXPECTED_GAP_TARGET,
        "replacement_origin_date": replacement_origin,
        "replacement_target_date": replacement_target,
        "selection_rule": "nearest_unused_origin_between_frozen_neighboring_development_origins_with_exact_calendar_target_date_available; tie_break_earlier_date",
        "holdout_membership_changed": False,
        "holdout_outcome_values_read": False,
    }
    corrected["holdout_outcomes_viewed_before_freeze"] = False
    corrected["manifest_content_sha256"] = canonical_hash(corrected)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(corrected, indent=2) + "\n", encoding="utf-8")

    require(sha256(database) == database_before, "Source database changed during exact-target correction")
    require(sha256(manifest_path) == manifest_before, "Source V4 manifest changed during correction")

    print("CRYPTO_V4_EXACT_TARGET_MEMBERSHIP_CORRECTION=PASS")
    print(f"REMOVED_DEVELOPMENT_ORIGIN={EXPECTED_GAP_ASSET}|{EXPECTED_GAP_HORIZON}|{EXPECTED_GAP_ORIGIN}")
    print(f"REPLACEMENT_DEVELOPMENT_ORIGIN={EXPECTED_GAP_ASSET}|{EXPECTED_GAP_HORIZON}|{replacement_origin}")
    print(f"REPLACEMENT_TARGET_DATE={replacement_target}")
    print("V4_FINAL_HOLDOUT_MEMBERSHIP_CHANGED=FALSE")
    print("HOLDOUT_OUTCOME_VALUES_READ=FALSE")
    print(f"CORRECTED_MANIFEST_CONTENT_SHA256={corrected['manifest_content_sha256']}")
    print("SOURCE_EVIDENCE_MODIFIED=FALSE")
    print("NEXT_GATE=VALIDATE_CORRECTED_V4_MEMBERSHIP_AND_REPLACE_MANIFEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
