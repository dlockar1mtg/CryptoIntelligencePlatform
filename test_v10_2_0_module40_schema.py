from crypto_platform.platform import load_all, connect
from crypto_platform.module40 import MODULE40_SCHEMA


EXPECTED_COLUMNS = [
    "run_id",
    "source_module38_run_id",
    "source_module39_run_id",
    "started_at_utc",
    "completed_at_utc",
    "status",
    "forecasts_ingested",
    "model_snapshots_ingested",
    "attribution_snapshots_ingested",
    "outcomes_matured",
    "learning_summary_rows",
    "calibration_curve_rows",
    "models_evaluated",
    "earliest_forecast_date",
    "latest_forecast_date",
    "realized_horizons",
    "memory_status",
    "continuous_learning_status",
    "recommendation",
    "notes",
    "platform_version",
]


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE40_SCHEMA)
    columns = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE lower(table_name)='module40_runs'
        ORDER BY ordinal_position
        """
    ).fetchdf()["column_name"].tolist()
    conn.close()

    assert columns == EXPECTED_COLUMNS, (
        f"module40_runs schema mismatch. "
        f"Expected {EXPECTED_COLUMNS}, got {columns}"
    )
    print("v10.2.0 Module 40 schema preflight passed.")
    print(f"module40_runs columns: {len(columns)}")


if __name__ == "__main__":
    main()
