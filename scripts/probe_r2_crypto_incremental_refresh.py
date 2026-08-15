from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.production.hosted import evaluate_hosted_database  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def scalar(conn: duckdb.DuckDBPyConnection, sql: str):
    row = conn.execute(sql).fetchone()
    return None if row is None else row[0]


def inspect_database(path: Path) -> dict:
    conn = duckdb.connect(str(path), read_only=True)
    try:
        market_rows = int(scalar(conn, "SELECT COUNT(*) FROM asset_market_daily") or 0)
        latest_market = scalar(conn, "SELECT MAX(observation_date) FROM asset_market_daily")
        ohlcv_rows = int(scalar(conn, "SELECT COUNT(*) FROM asset_ohlcv") or 0)
        latest_ohlcv = scalar(conn, "SELECT MAX(close_time_utc) FROM asset_ohlcv")
        macro_rows = int(scalar(conn, "SELECT COUNT(*) FROM macro_observations") or 0)
        latest_macro = scalar(conn, "SELECT MAX(observation_date) FROM macro_observations")
        latest_collection = conn.execute(
            """
            SELECT run_id, completed_at_utc, status,
                   COALESCE(successful_collectors, 0), COALESCE(failed_collectors, 0),
                   COALESCE(rows_received, 0), COALESCE(rows_inserted, 0), COALESCE(rows_updated, 0)
            FROM collection_runs
            ORDER BY completed_at_utc DESC NULLS LAST
            LIMIT 1
            """
        ).fetchone()
        providers = conn.execute(
            """
            SELECT provider_name, provider_group, status, checked_at_utc,
                   COALESCE(error_message, '')
            FROM latest_provider_health
            ORDER BY provider_name, provider_group
            """
        ).fetchall()
    finally:
        conn.close()

    return {
        "asset_market_daily": {
            "row_count": market_rows,
            "latest_observation": None if latest_market is None else str(latest_market),
        },
        "asset_ohlcv": {
            "row_count": ohlcv_rows,
            "latest_close_time_utc": None if latest_ohlcv is None else str(latest_ohlcv),
        },
        "macro_observations": {
            "row_count": macro_rows,
            "latest_observation": None if latest_macro is None else str(latest_macro),
        },
        "latest_collection": None
        if latest_collection is None
        else {
            "run_id": str(latest_collection[0]),
            "completed_at_utc": str(latest_collection[1]),
            "status": str(latest_collection[2]),
            "successful_collectors": int(latest_collection[3]),
            "failed_collectors": int(latest_collection[4]),
            "rows_received": int(latest_collection[5]),
            "rows_inserted": int(latest_collection[6]),
            "rows_updated": int(latest_collection[7]),
        },
        "latest_provider_health": [
            {
                "provider_name": str(row[0]),
                "provider_group": str(row[1]),
                "status": str(row[2]),
                "checked_at_utc": str(row[3]),
                "error_message": str(row[4]),
            }
            for row in providers
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe the supported non-full-refresh Crypto collection path on a disposable database copy."
    )
    parser.add_argument("--source-database", type=Path, required=True)
    args = parser.parse_args()

    source = args.source_database.resolve()
    if not source.is_file():
        raise RuntimeError(f"Source Crypto database not found: {source}")

    source_hash_before = sha256(source)
    source_size_before = source.stat().st_size

    with tempfile.TemporaryDirectory(prefix="crypto-r2-incremental-probe-") as temp_name:
        temp_root = Path(temp_name)
        probe_db = temp_root / "crypto_intelligence.duckdb"
        shutil.copy2(source, probe_db)

        before = inspect_database(probe_db)

        env = os.environ.copy()
        env["CRYPTO_DATABASE_PATH"] = str(probe_db)
        env.pop("CRYPTO_PRODUCTION_RUN_ID", None)
        env.pop("CRYPTO_PRODUCTION_STAGE", None)
        env.pop("CRYPTO_PRODUCTION_MODULE", None)

        completed = subprocess.run(
            [sys.executable, str(ROOT / "run_module1.py")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        after = inspect_database(probe_db)
        hosted = evaluate_hosted_database(probe_db)

        source_hash_after = sha256(source)
        source_size_after = source.stat().st_size
        source_unchanged = (
            source_hash_before == source_hash_after
            and source_size_before == source_size_after
        )
        if not source_unchanged:
            raise RuntimeError("Source Crypto database changed during disposable probe.")

        market_before = before["asset_market_daily"]["latest_observation"]
        market_after = after["asset_market_daily"]["latest_observation"]
        collection = after.get("latest_collection") or {}
        providers = after.get("latest_provider_health") or []
        unhealthy = [p for p in providers if p.get("status", "").upper() not in {"ONLINE", "AVAILABLE", "HEALTHY", "PASS"}]

        viable = (
            completed.returncode == 0
            and hosted.get("status") == "PASS"
            and collection.get("status", "").upper() in {"PASS", "SUCCESS", "COMPLETED"}
            and int(collection.get("failed_collectors", 0) or 0) == 0
            and market_after is not None
            and market_after != market_before
            and not unhealthy
        )

        payload = {
            "status": "CRYPTO_R2_INCREMENTAL_PROBE_PASS",
            "probe_mode": "DISPOSABLE_DATABASE_COPY",
            "full_refresh": False,
            "source_database": str(source),
            "source_database_sha256": source_hash_before,
            "source_database_unchanged": source_unchanged,
            "module1_return_code": int(completed.returncode),
            "module1_stdout_tail": (completed.stdout or "")[-8000:],
            "module1_stderr_tail": (completed.stderr or "")[-8000:],
            "before": before,
            "after": after,
            "hosted_readiness": hosted,
            "incremental_refresh_viable": viable,
            "next_gate": (
                "R2_CRYPTO_DISPOSABLE_FULL_PIPELINE"
                if viable
                else "R2_CRYPTO_PROVIDER_OR_FRESHNESS_REMEDIATION"
            ),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        print("CRYPTO_R2_INCREMENTAL_PROBE=PASS")
        print(f"INCREMENTAL_REFRESH_VIABLE={str(viable).upper()}")
        print(f"SOURCE_DATABASE_UNCHANGED={str(source_unchanged).upper()}")
        print(f"NEXT_GATE={payload['next_gate']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
