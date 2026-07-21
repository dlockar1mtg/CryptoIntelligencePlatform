from crypto_platform.platform import load_all, connect
from crypto_platform.module31 import MODULE31_SCHEMA

EXPECTED_COLUMNS = [
    "run_id",
    "source_module30_run_id",
    "started_at_utc",
    "completed_at_utc",
    "status",
    "calibration_rows",
    "persistence_rows",
    "forward_return_rows",
    "economic_score_rows",
    "selected_accuracy_pct",
    "selected_log_loss",
    "clean_economic_score",
    "legacy_economic_score",
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
    print("Module 31 schema preflight passed.")
    print(f"module31_runs columns: {len(columns)}")

if __name__ == "__main__":
    main()
