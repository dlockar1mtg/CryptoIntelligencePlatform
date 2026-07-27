from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export collector-level evidence for the latest Crypto collection run."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    connection = duckdb.connect(str(args.database), read_only=True)
    try:
        latest = connection.execute(
            """
            SELECT run_id, completed_at_utc, status,
                   COALESCE(successful_collectors, 0),
                   COALESCE(failed_collectors, 0),
                   COALESCE(rows_received, 0),
                   COALESCE(notes, '')
            FROM collection_runs
            ORDER BY completed_at_utc DESC NULLS LAST
            LIMIT 1
            """
        ).fetchone()

        if latest is None:
            payload = {
                "status": "FAIL",
                "reason": "No collection run found."
            }
        else:
            run_id = latest[0]
            columns = [
                row[0]
                for row in connection.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'collection_results'
                    ORDER BY ordinal_position
                    """
                ).fetchall()
            ]

            rows = connection.execute(
                """
                SELECT *
                FROM collection_results
                WHERE run_id = ?
                ORDER BY collector_name, provider_name, dataset_name
                """,
                [run_id],
            ).fetchall()

            results = [
                dict(zip(columns, row))
                for row in rows
            ]

            payload = {
                "status": "PASS",
                "latest_collection": {
                    "run_id": run_id,
                    "completed_at_utc": str(latest[1]),
                    "status": latest[2],
                    "successful_collectors": int(latest[3]),
                    "failed_collectors": int(latest[4]),
                    "rows_received": int(latest[5]),
                    "notes": latest[6],
                },
                "collector_results": results,
                "failed_or_skipped_collectors": [
                    result
                    for result in results
                    if str(result.get("status", "")).upper()
                    not in {"PASS", "SUCCESS", "COMPLETED"}
                ],
            }
    finally:
        connection.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
