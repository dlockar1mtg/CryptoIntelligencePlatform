from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb

RUN_ID = "BITCOIN_FIRST_OBSERVATION_GITHUB_FRED_MACRO_REFRESH_V1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(command: list[str], cwd: Path, env: dict[str, str]) -> dict:
    proc = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {"command": command, "exit_code": int(proc.returncode), "output": proc.stdout}


def json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def table_snapshot(conn: duckdb.DuckDBPyConnection, table: str) -> dict:
    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    if table not in tables:
        return {"exists": False}
    columns = [row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()]
    time_column = next(
        (name for name in ("observation_date", "regime_date", "calculation_date", "date") if name in columns),
        None,
    )
    latest_time = None
    latest_row = None
    if time_column:
        latest_time = conn.execute(f"SELECT MAX({time_column}) FROM {table}").fetchone()[0]
        if latest_time is not None:
            row = conn.execute(
                f"SELECT * FROM {table} WHERE {time_column} = ? ORDER BY {time_column} DESC LIMIT 1",
                [latest_time],
            ).fetchone()
            if row is not None:
                latest_row = {name: json_value(value) for name, value in zip(columns, row)}
    return {
        "exists": True,
        "columns": columns,
        "time_column": time_column,
        "latest_time": None if latest_time is None else str(latest_time),
        "latest_row": latest_row,
    }


def latest_bitcoin(conn: duckdb.DuckDBPyConnection) -> dict | None:
    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    if "canonical_market_daily" not in tables:
        return None
    row = conn.execute(
        "SELECT observation_date, price_usd FROM canonical_market_daily "
        "WHERE asset_id='bitcoin' AND price_usd IS NOT NULL "
        "ORDER BY observation_date DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return {"observation_date": str(row[0]), "price_usd": float(row[1])}


def macro_series_freshness(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    if "macro_observations" not in tables:
        return []
    columns = {row[1] for row in conn.execute("PRAGMA table_info('macro_observations')").fetchall()}
    series_column = next((name for name in ("series_id", "series", "indicator", "metric") if name in columns), None)
    date_column = next((name for name in ("observation_date", "date") if name in columns), None)
    if not series_column or not date_column:
        return []
    rows = conn.execute(
        f"SELECT {series_column}, MAX({date_column}) AS latest_date, COUNT(*) AS row_count "
        f"FROM macro_observations GROUP BY {series_column} ORDER BY {series_column}"
    ).fetchall()
    return [
        {"series": str(series), "latest_observation_date": str(latest), "row_count": int(count)}
        for series, latest, count in rows
    ]


def snapshot(database: Path) -> dict:
    with duckdb.connect(str(database), read_only=True) as conn:
        return {
            "bitcoin": latest_bitcoin(conn),
            "macro_tables": {
                table: table_snapshot(conn, table)
                for table in (
                    "macro_observations",
                    "latest_macro_observations",
                    "macro_regime_daily",
                    "latest_macro_regime",
                )
            },
            "macro_series_freshness": macro_series_freshness(conn),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--records-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    database = Path(args.database).resolve()
    manifest_path = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()
    output = Path(args.output).resolve()

    for path in (repo_root, database, manifest_path):
        require(path.exists(), f"Required input missing: {path}")
    require(not output.exists(), "Macro-refresh evidence output already exists; refusing overwrite")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(int(manifest.get("record_count", -1)) == 0, "Forward-evidence ledger is not empty")
    records = list(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(records) == 0, "Forward-evidence record files already exist")

    fred_present = bool(os.environ.get("FRED_API_KEY", "").strip())
    require(fred_present, "FRED_API_KEY is not available in the GitHub execution environment")

    db_hash_before = sha256(database)
    manifest_hash_before = sha256(manifest_path)
    before = snapshot(database)

    env = dict(os.environ)
    env["CRYPTO_DATABASE_PATH"] = str(database)

    module1 = run([sys.executable, "run_module1.py"], repo_root, env)
    require(module1["exit_code"] == 0, "Module 1 incremental refresh failed")
    require("--full-refresh" not in module1["command"], "Full refresh was unexpectedly invoked")

    module6 = run([sys.executable, "run_module6.py", "--phase", "sync"], repo_root, env)
    require(module6["exit_code"] == 0, "Module 6 sync failed")

    after = snapshot(database)
    db_hash_after = sha256(database)
    require(sha256(manifest_path) == manifest_hash_before, "Ledger manifest changed during macro refresh")
    records_after = list(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(records_after) == 0, "Prospective observation was created during macro refresh")

    report = {
        "run_id": RUN_ID,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "environment": "staging",
        "fred_api_key_configured": True,
        "fred_api_key_value_recorded": False,
        "module1_incremental_refresh_executed": True,
        "module1_full_refresh_executed": False,
        "module6_sync_executed": True,
        "module42_rerun_performed": False,
        "first_prospective_observation_captured": False,
        "ledger_record_count": 0,
        "database_sha256_before": db_hash_before,
        "database_sha256_after": db_hash_after,
        "before": before,
        "after": after,
        "module1": module1,
        "module6": module6,
        "production_pipeline_executed": False,
        "production_policy_changed": False,
        "autonomous_execution_authorized": False,
        "next_gate": "REVIEW_GITHUB_FRED_MACRO_REFRESH_FOR_FIRST_BITCOIN_OBSERVATION",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("BITCOIN_FIRST_OBSERVATION_GITHUB_FRED_MACRO_REFRESH=PASS")
    print("FRED_API_KEY_CONFIGURED=TRUE")
    print("FRED_API_KEY_VALUE_RECORDED=FALSE")
    print("MODULE1_INCREMENTAL_REFRESH_EXECUTED=TRUE")
    print("MODULE1_FULL_REFRESH_EXECUTED=FALSE")
    print("MODULE6_SYNC_EXECUTED=TRUE")
    print("MODULE42_RERUN_PERFORMED=FALSE")
    print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
    print("LEDGER_RECORD_COUNT=0")
    print("PRODUCTION_PIPELINE_EXECUTED=FALSE")
    print("PRODUCTION_POLICY_CHANGED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("NEXT_GATE=REVIEW_GITHUB_FRED_MACRO_REFRESH_FOR_FIRST_BITCOIN_OBSERVATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
