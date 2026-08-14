from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def scalar(connection: duckdb.DuckDBPyConnection, sql: str):
    return connection.execute(sql).fetchone()[0]


def quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def table_columns(connection: duckdb.DuckDBPyConnection, table: str) -> list[dict]:
    rows = connection.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
    return [
        {
            "cid": row[0],
            "name": row[1],
            "type": row[2],
            "notnull": bool(row[3]),
            "default": row[4],
            "pk": bool(row[5]),
        }
        for row in rows
    ]


def max_timestamp_evidence(connection: duckdb.DuckDBPyConnection, table: str, columns: list[dict]) -> dict[str, str | None]:
    candidates = []
    for col in columns:
        name = str(col["name"])
        lower = name.lower()
        if any(token in lower for token in ("date", "time", "timestamp", "as_of", "observed", "created", "updated")):
            candidates.append(name)
    result: dict[str, str | None] = {}
    for name in candidates[:12]:
        try:
            value = scalar(connection, f"SELECT MAX({quote_ident(name)}) FROM {quote_ident(table)}")
            result[name] = None if value is None else str(value)
        except Exception:
            continue
    return result


def newest_json(root: Path, pattern: str) -> Path | None:
    matches = [p for p in root.glob(pattern) if p.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def load_json(path: Path | None):
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": f"{type(exc).__name__}: {exc}", "_path": str(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only audit of local Crypto state for UIP R2 recovery.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    database = args.database.resolve()

    if not repo_root.is_dir():
        raise RuntimeError(f"Crypto repository root not found: {repo_root}")
    if not database.is_file():
        raise RuntimeError(f"Crypto database not found: {database}")

    evidence: dict = {
        "status": "CRYPTO_R2_RECOVERY_AUDIT_PASS",
        "repo_root": str(repo_root),
        "database": {
            "path": str(database),
            "size_bytes": database.stat().st_size,
            "sha256": sha256(database),
        },
        "database_open_mode": "READ_ONLY",
        "tables": {},
        "key_tables": {},
        "local_operations": {},
        "mutations_performed": False,
    }

    connection = duckdb.connect(str(database), read_only=True)
    try:
        tables = [row[0] for row in connection.execute("SHOW TABLES").fetchall()]
        evidence["table_count"] = len(tables)
        evidence["tables"] = {"names": tables}

        key_names = [
            "asset_market_daily",
            "asset_master",
            "forecasts",
            "recommendations",
            "risk_metrics",
            "portfolio_positions",
        ]
        for table in key_names:
            if table not in tables:
                evidence["key_tables"][table] = {"present": False}
                continue
            columns = table_columns(connection, table)
            count = int(scalar(connection, f"SELECT COUNT(*) FROM {quote_ident(table)}"))
            evidence["key_tables"][table] = {
                "present": True,
                "row_count": count,
                "columns": [c["name"] for c in columns],
                "max_timestamp_evidence": max_timestamp_evidence(connection, table, columns),
            }
    finally:
        connection.close()

    operations = repo_root / "data" / "operations" / "crypto"
    production_runs = operations / "production_runs"
    latest_run_summary = None
    if production_runs.is_dir():
        candidates = list(production_runs.glob("*/run_summary.json"))
        if candidates:
            latest_run_summary = max(candidates, key=lambda p: p.stat().st_mtime)

    hosted_readiness = operations / "hosted_readiness.json"
    uip_delivery = operations / "uip_delivery"
    latest_delivery_summary = newest_json(uip_delivery, "*/package_summary.json") if uip_delivery.is_dir() else None

    evidence["local_operations"] = {
        "latest_run_summary_path": None if latest_run_summary is None else str(latest_run_summary),
        "latest_run_summary": load_json(latest_run_summary),
        "hosted_readiness_path": str(hosted_readiness) if hosted_readiness.is_file() else None,
        "hosted_readiness": load_json(hosted_readiness if hosted_readiness.is_file() else None),
        "latest_uip_delivery_summary_path": None if latest_delivery_summary is None else str(latest_delivery_summary),
        "latest_uip_delivery_summary": load_json(latest_delivery_summary),
    }

    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    print("CRYPTO_R2_RECOVERY_AUDIT=PASS")
    print("DATABASE_OPEN_MODE=READ_ONLY")
    print("MUTATIONS_PERFORMED=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
