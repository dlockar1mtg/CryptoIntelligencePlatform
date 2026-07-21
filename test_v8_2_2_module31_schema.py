from crypto_platform.platform import load_all, connect
from crypto_platform.module31 import MODULE31_SCHEMA

EXPECTED_COLUMNS = [
    "run_id",
    "source_module30_run_id",
    "started_at_utc",
    "completed_at_utc",
    "status",
    "historical_rows",
    "forward_return_rows",
    "calibration_rows",
    "persistence_rows",
    "investment_value_score",
    "validation_status",
    "recommendation",
    "notes",
    "platform_version",
]

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE31_SCHEMA)
    columns = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE lower(table_name)='module31_runs'
        ORDER BY ordinal_position
        """
    ).fetchdf()["column_name"].tolist()
    conn.close()

    assert columns == EXPECTED_COLUMNS, (
        f"module31_runs schema mismatch. "
        f"Expected {EXPECTED_COLUMNS}, got {columns}"
    )
    print("Module 31 actual-schema preflight passed.")
    print(f"module31_runs columns: {len(columns)}")
    print("Schema matches v8.2.2 run-start and completion statements.")

if __name__ == "__main__":
    main()
