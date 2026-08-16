from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"

KEYWORDS = (
    "forecast",
    "recommend",
    "decision",
    "signal",
    "backtest",
    "walk",
    "validation",
    "calibration",
    "performance",
    "regime",
    "prediction",
    "evaluation",
    "outcome",
    "price",
    "market",
    "module25v",
    "m25v_",
    "module39",
    "module42",
    "module43",
)


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def safe_scalar(conn: duckdb.DuckDBPyConnection, sql: str) -> Any:
    try:
        row = conn.execute(sql).fetchone()
        return None if row is None else row[0]
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit of native Crypto predictive/recommendation validation evidence."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--source-commit", default=EXPECTED_SOURCE_COMMIT)
    args = parser.parse_args()

    database = args.database.resolve()
    if not database.is_file():
        raise RuntimeError(f"Crypto database not found: {database}")
    if args.source_commit != EXPECTED_SOURCE_COMMIT:
        raise RuntimeError(
            f"Unexpected source commit. Expected {EXPECTED_SOURCE_COMMIT}, got {args.source_commit}"
        )

    conn = duckdb.connect(str(database), read_only=True)
    try:
        table_rows = conn.execute(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name
            """
        ).fetchall()

        candidates: list[dict[str, Any]] = []
        for schema, table, table_type in table_rows:
            lower = table.lower()
            if not any(keyword in lower for keyword in KEYWORDS):
                continue

            qualified = f"{qident(schema)}.{qident(table)}"
            row_count = safe_scalar(conn, f"SELECT COUNT(*) FROM {qualified}")

            columns = conn.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema=? AND table_name=?
                ORDER BY ordinal_position
                """,
                [schema, table],
            ).fetchall()
            column_names = [row[0] for row in columns]

            date_columns = [
                name for name in column_names
                if any(token in name.lower() for token in ("date", "time", "timestamp", "started_at", "completed_at", "generated_at", "created_at"))
            ]
            date_ranges: dict[str, dict[str, Any]] = {}
            for name in date_columns[:6]:
                minimum = safe_scalar(conn, f"SELECT MIN({qident(name)}) FROM {qualified}")
                maximum = safe_scalar(conn, f"SELECT MAX({qident(name)}) FROM {qualified}")
                if minimum is not None or maximum is not None:
                    date_ranges[name] = {
                        "min": None if minimum is None else str(minimum),
                        "max": None if maximum is None else str(maximum),
                    }

            candidates.append(
                {
                    "schema": schema,
                    "table": table,
                    "table_type": table_type,
                    "row_count": row_count,
                    "columns": column_names,
                    "date_ranges": date_ranges,
                }
            )

        module25_validation = [
            item for item in candidates
            if item["table"].startswith("m25v_") or item["table"] == "module25v_runs"
        ]
        recommendation_tables = [
            item for item in candidates
            if "recommend" in item["table"].lower() or "decision" in item["table"].lower() or "signal" in item["table"].lower()
        ]
        forecast_tables = [
            item for item in candidates
            if "forecast" in item["table"].lower() or "prediction" in item["table"].lower()
        ]
        performance_tables = [
            item for item in candidates
            if any(token in item["table"].lower() for token in ("performance", "backtest", "validation", "calibration", "walk_forward", "walkforward", "outcome"))
        ]

        populated_m25v = [item for item in module25_validation if (item["row_count"] or 0) > 0]
        populated_recommendations = [item for item in recommendation_tables if (item["row_count"] or 0) > 0]
        populated_forecasts = [item for item in forecast_tables if (item["row_count"] or 0) > 0]
        populated_performance = [item for item in performance_tables if (item["row_count"] or 0) > 0]

        payload = {
            "status": "CRYPTO_NATIVE_PREDICTIVE_VALIDATION_READINESS_AUDIT_COMPLETE",
            "database": str(database),
            "source_commit": args.source_commit,
            "read_only": True,
            "candidate_table_count": len(candidates),
            "module25_validation_tables": len(module25_validation),
            "module25_validation_populated": len(populated_m25v),
            "recommendation_or_signal_tables": len(recommendation_tables),
            "recommendation_or_signal_populated": len(populated_recommendations),
            "forecast_or_prediction_tables": len(forecast_tables),
            "forecast_or_prediction_populated": len(populated_forecasts),
            "performance_validation_tables": len(performance_tables),
            "performance_validation_populated": len(populated_performance),
            "candidates": candidates,
            "next_gate": "DESIGN_POINT_IN_TIME_NATIVE_RECOMMENDATION_AND_FORECAST_VALIDATION_FROM_AVAILABLE_EVIDENCE",
        }

        print(json.dumps(payload, indent=2, default=str))
        print("CRYPTO_NATIVE_PREDICTIVE_VALIDATION_READINESS_AUDIT=COMPLETE")
        print(f"M25V_POPULATED_TABLES={len(populated_m25v)}")
        print(f"RECOMMENDATION_SIGNAL_POPULATED_TABLES={len(populated_recommendations)}")
        print(f"FORECAST_PREDICTION_POPULATED_TABLES={len(populated_forecasts)}")
        print(f"PERFORMANCE_VALIDATION_POPULATED_TABLES={len(populated_performance)}")
        print("DATABASE_MODIFIED=FALSE")
        print("NEXT_GATE=DESIGN_POINT_IN_TIME_NATIVE_RECOMMENDATION_AND_FORECAST_VALIDATION_FROM_AVAILABLE_EVIDENCE")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
