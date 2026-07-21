from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from crypto_platform.platform import load_all, connect, path_for

def table_count(conn, table_name: str) -> int:
    try:
        return int(
            conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]
        )
    except Exception:
        return -1

def main() -> None:
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    print(f"Active database: {database}")

    conn = connect(settings)
    try:
        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}

        if "module14_runs" in tables:
            conn.execute(
                """
                UPDATE module14_runs
                SET status='FAILED',
                    completed_at_utc=?,
                    notes=COALESCE(notes,'') ||
                          CASE WHEN COALESCE(notes,'')='' THEN '' ELSE '; ' END ||
                          'Marked failed by v3.3.5 recovery hotfix.'
                WHERE status='RUNNING'
                """,
                [datetime.now(timezone.utc)],
            )

        counts = {
            name: table_count(conn, name)
            for name in [
                "market_history",
                "exchange_ohlcv",
                "canonical_market_daily",
                "research_market_daily",
            ]
        }
    finally:
        conn.close()

    print("Warehouse counts")
    print("----------------")
    for name, count in counts.items():
        print(f"{name}: {count}")

    raw_rows = max(0, counts["market_history"]) + max(
        0, counts["exchange_ohlcv"]
    )
    canonical_rows = max(0, counts["canonical_market_daily"])

    if canonical_rows > 0:
        print("\nCanonical history is already available.")
        print("Next command: python run_module14.py")
    elif raw_rows > 0:
        print("\nRaw history exists, but canonical history is empty.")
        print("Next commands:")
        print("  python run_module6.py --phase sync")
        print("  python run_module14.py")
    else:
        print("\nBoth raw and canonical history are empty.")
        print("Next commands:")
        print("  python run_module1.py")
        print("  python run_module6.py --phase sync")
        print("  python run_module14.py")

if __name__ == "__main__":
    main()
