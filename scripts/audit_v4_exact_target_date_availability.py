from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb

EXPECTED_EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_GROUPS = 17
EXPECTED_DEVELOPMENT_ORIGINS = 50
EXPECTED_HOLDOUT_ORIGINS = 10


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v4-manifest", required=True)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    manifest_path = Path(args.v4_manifest).resolve()
    require(database.is_file(), f"Database missing: {database}")
    require(manifest_path.is_file(), f"V4 manifest missing: {manifest_path}")

    before_database = sha256(database)
    before_manifest = sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    require(manifest.get("experiment_id") == EXPECTED_EXPERIMENT_ID, "Unexpected V4 experiment id")
    require(manifest.get("holdout_outcomes_viewed_before_freeze") is False, "V4 holdout outcomes were viewed before freeze")
    require(manifest.get("v3_final_holdout_reused") is False, "V3 final holdout was reused")
    groups = manifest.get("groups", [])
    require(len(groups) == EXPECTED_GROUPS, f"Expected {EXPECTED_GROUPS} groups, found {len(groups)}")

    conn = duckdb.connect(str(database), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT asset_id, CAST(observation_date AS DATE) AS observation_date
            FROM canonical_market_daily
            WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
              AND price_usd IS NOT NULL
            ORDER BY asset_id, observation_date
            """
        ).fetchall()
    finally:
        conn.close()

    dates_by_asset: dict[str, set[str]] = {}
    for asset_id, observation_date in rows:
        dates_by_asset.setdefault(str(asset_id), set()).add(observation_date.isoformat())

    development_missing: list[dict] = []
    holdout_missing: list[dict] = []
    development_checked = 0
    holdout_checked = 0

    from datetime import date, timedelta

    for group in groups:
        asset = str(group["asset_id"])
        horizon = int(group["horizon_days"])
        development = list(group["v4_development_origin_dates"])
        holdout = list(group["v4_final_holdout_origin_dates"])
        require(len(development) == EXPECTED_DEVELOPMENT_ORIGINS, f"Unexpected development count for {asset} {horizon}d")
        require(len(holdout) == EXPECTED_HOLDOUT_ORIGINS, f"Unexpected holdout count for {asset} {horizon}d")
        available_dates = dates_by_asset.get(asset, set())

        for origin in development:
            target_date = (date.fromisoformat(origin) + timedelta(days=horizon)).isoformat()
            development_checked += 1
            if target_date not in available_dates:
                development_missing.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "origin_date": origin,
                    "required_target_date": target_date,
                })

        # Availability-only audit: do not read, summarize, or score target price values.
        for origin in holdout:
            target_date = (date.fromisoformat(origin) + timedelta(days=horizon)).isoformat()
            holdout_checked += 1
            if target_date not in available_dates:
                holdout_missing.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "origin_date": origin,
                    "required_target_date": target_date,
                })

    after_database = sha256(database)
    after_manifest = sha256(manifest_path)
    require(before_database == after_database, "Database changed during exact-target availability audit")
    require(before_manifest == after_manifest, "V4 manifest changed during exact-target availability audit")

    print("CRYPTO_V4_EXACT_TARGET_DATE_AVAILABILITY_AUDIT=PASS")
    print(f"DEVELOPMENT_ORIGINS_CHECKED={development_checked}")
    print(f"HOLDOUT_ORIGINS_CHECKED={holdout_checked}")
    print(f"DEVELOPMENT_EXACT_TARGET_DATE_GAPS={len(development_missing)}")
    print(f"HOLDOUT_EXACT_TARGET_DATE_GAPS={len(holdout_missing)}")
    for row in development_missing:
        print(
            "DEVELOPMENT_GAP="
            f"{row['asset_id']}|{row['horizon_days']}|{row['origin_date']}|{row['required_target_date']}"
        )
    for row in holdout_missing:
        print(
            "HOLDOUT_GAP="
            f"{row['asset_id']}|{row['horizon_days']}|{row['origin_date']}|{row['required_target_date']}"
        )
    print("HOLDOUT_OUTCOME_VALUES_READ=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print(
        "NEXT_GATE="
        + (
            "REBUILD_V4_MEMBERSHIP_UNDER_EXACT_CALENDAR_TARGET_AVAILABILITY"
            if development_missing or holdout_missing
            else "RESUME_V4_DEVELOPMENT_PREFLIGHT"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
