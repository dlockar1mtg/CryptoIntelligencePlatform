from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

INSPECTION_ID = "FIRST_PROSPECTIVE_BITCOIN_INPUT_GAP_REVIEW_V1"
TIMEZONE = "America/Chicago"

TABLE_GROUPS = {
    "price": [
        "canonical_market_daily",
        "asset_market_daily",
        "latest_asset_market",
    ],
    "module42": [
        "latest_m42_asset_recommendations",
        "m42_asset_recommendations",
        "module42_runs",
        "latest_m42_portfolio_plan",
        "m42_portfolio_plan",
    ],
    "forecast": [
        "latest_predictive_classifications",
        "predictive_classification_current",
        "latest_ml_predictions",
        "ml_predictions_current",
        "latest_robust_calibrated_predictive",
        "robust_calibrated_predictive_current",
        "latest_calibrated_predictive",
        "calibrated_predictive_current",
        "latest_m38_asset_forecasts",
        "m38_asset_forecasts",
        "latest_model_snapshots",
        "model_snapshots_daily",
    ],
    "portfolio": [
        "latest_portfolio_summary",
        "portfolio_summary",
        "latest_portfolio_recommendation",
        "latest_portfolio_recommendations",
        "latest_m35_portfolio_allocations",
        "m35_portfolio_allocations",
        "latest_m44_portfolio_value",
        "m44_portfolio_value",
    ],
    "macro": [
        "latest_macro_observations",
        "macro_observations",
        "latest_macro_regime",
        "macro_regime_daily",
        "macro_series_catalog",
    ],
}

ASSET_COLUMNS = (
    "asset_id",
    "asset",
    "symbol",
    "ticker",
    "asset_symbol",
    "crypto_asset",
)

TIME_COLUMNS = (
    "operating_date",
    "date",
    "as_of_date",
    "timestamp",
    "observed_at",
    "run_timestamp",
    "created_at",
    "updated_at",
    "price_date",
    "forecast_date",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def qident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def scalar(con: duckdb.DuckDBPyConnection, sql: str, params=None):
    row = con.execute(sql, params or []).fetchone()
    return None if row is None else row[0]


def table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    return bool(
        scalar(
            con,
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name=?",
            [table],
        )
    )


def columns_for(con: duckdb.DuckDBPyConnection, table: str) -> list[dict]:
    rows = con.execute(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='main' AND table_name=? ORDER BY ordinal_position",
        [table],
    ).fetchall()
    return [{"name": r[0], "type": r[1]} for r in rows]


def pick_asset_column(columns: list[str]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for candidate in ASSET_COLUMNS:
        if candidate in lower:
            return lower[candidate]
    return None


def pick_time_column(columns: list[str]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for candidate in TIME_COLUMNS:
        if candidate in lower:
            return lower[candidate]
    return None


def bitcoin_filter(asset_column: str) -> tuple[str, list[str]]:
    col = qident(asset_column)
    return f"lower(cast({col} as varchar)) IN (?, ?, ?, ?)", ["bitcoin", "btc", "btc-usd", "btcusd"]


def normalize_value(value):
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, bytes):
        return value.hex()
    return value


def inspect_table(con: duckdb.DuckDBPyConnection, table: str) -> dict:
    if not table_exists(con, table):
        return {"table": table, "exists": False}

    columns_meta = columns_for(con, table)
    columns = [c["name"] for c in columns_meta]
    asset_col = pick_asset_column(columns)
    time_col = pick_time_column(columns)

    result = {
        "table": table,
        "exists": True,
        "columns": columns_meta,
        "asset_column": asset_col,
        "time_column": time_col,
        "row_count": int(scalar(con, f"SELECT COUNT(*) FROM {qident(table)}") or 0),
        "bitcoin_row_count": None,
        "latest_time": None,
        "sample_latest_bitcoin_rows": [],
    }

    where_sql = ""
    params: list[str] = []
    if asset_col:
        filt, params = bitcoin_filter(asset_col)
        where_sql = " WHERE " + filt
        result["bitcoin_row_count"] = int(
            scalar(con, f"SELECT COUNT(*) FROM {qident(table)}{where_sql}", params) or 0
        )

    if time_col:
        try:
            result["latest_time"] = normalize_value(
                scalar(
                    con,
                    f"SELECT MAX({qident(time_col)}) FROM {qident(table)}{where_sql}",
                    params,
                )
            )
        except Exception as exc:
            result["latest_time_error"] = str(exc)

    if asset_col and result["bitcoin_row_count"]:
        order_sql = f" ORDER BY {qident(time_col)} DESC NULLS LAST" if time_col else ""
        try:
            cursor = con.execute(
                f"SELECT * FROM {qident(table)}{where_sql}{order_sql} LIMIT 3",
                params,
            )
            names = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            result["sample_latest_bitcoin_rows"] = [
                {name: normalize_value(value) for name, value in zip(names, row)}
                for row in rows
            ]
        except Exception as exc:
            result["sample_error"] = str(exc)

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--preserved-discovery", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--records-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    preserved_discovery = Path(args.preserved_discovery).resolve()
    manifest = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()
    output = Path(args.output).resolve()

    for name, path in {
        "database": database,
        "preserved_discovery": preserved_discovery,
        "manifest": manifest,
    }.items():
        if not path.is_file():
            raise RuntimeError(f"Required input missing: {name}={path}")

    if output.exists():
        raise RuntimeError(f"Refusing to overwrite existing review artifact: {output}")

    manifest_json = json.loads(manifest.read_text(encoding="utf-8"))
    if int(manifest_json.get("record_count", -1)) != 0:
        raise RuntimeError("Ledger manifest record_count must remain zero before input-gap review")

    record_files = list(records_dir.rglob("*.json")) if records_dir.exists() else []
    if record_files:
        raise RuntimeError("Ledger must contain zero recommendation records before input-gap review")

    database_sha_before = sha256_file(database)
    discovery_sha = sha256_file(preserved_discovery)

    now = datetime.now(ZoneInfo(TIMEZONE))
    inspection = {
        "inspection_id": INSPECTION_ID,
        "inspection_timestamp": now.isoformat(),
        "operating_date": now.date().isoformat(),
        "operating_timezone": TIMEZONE,
        "database_read_only": True,
        "database_sha256_before": database_sha_before,
        "preserved_source_discovery_sha256": discovery_sha,
        "ledger_record_count_before": 0,
        "capture_performed": False,
        "missing_evidence_synthesized": False,
        "outcome_peeking_allowed": False,
        "table_groups": {},
    }

    con = duckdb.connect(str(database), read_only=True)
    try:
        for group, tables in TABLE_GROUPS.items():
            inspection["table_groups"][group] = [inspect_table(con, t) for t in tables]
    finally:
        con.close()

    database_sha_after = sha256_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("Canonical database changed during read-only input-gap review")

    inspection["database_sha256_after"] = database_sha_after
    inspection["canonical_database_modified"] = False

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inspection, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("FIRST_PROSPECTIVE_BITCOIN_INPUT_GAP_REVIEW=PASS")
    print("DATABASE_ACCESS=READ_ONLY")
    print("LEDGER_RECORD_COUNT=0")
    print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
    print("MISSING_EVIDENCE_SYNTHESIZED=FALSE")
    print("OUTCOME_PEEKING_ALLOWED=FALSE")
    print("CANONICAL_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=REVIEW_BITCOIN_INPUT_GAP_TABLE_AUTHORITIES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
