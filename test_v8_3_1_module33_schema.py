from crypto_platform.platform import load_all, connect
from crypto_platform.module33 import MODULE33_SCHEMA


EXPECTED_COLUMNS = [
    "run_id",
    "source_module32_run_id",
    "source_module30_run_id",
    "started_at_utc",
    "completed_at_utc",
    "status",
    "candidate_rows",
    "daily_rows",
    "cost_sensitivity_rows",
    "drift_rows",
    "selected_candidate_id",
    "selected_strategy",
    "annualized_turnover_pct",
    "selected_sharpe",
    "selected_max_drawdown_pct",
    "btc_sharpe",
    "btc_max_drawdown_pct",
    "adjusted_drift_status",
    "validation_status",
    "recommendation",
    "notes",
    "platform_version",
]


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE33_SCHEMA)
    columns = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE lower(table_name)='module33_runs'
        ORDER BY ordinal_position
        """
    ).fetchdf()["column_name"].tolist()
    conn.close()

    assert columns == EXPECTED_COLUMNS, (
        f"module33_runs schema mismatch. "
        f"Expected {EXPECTED_COLUMNS}, got {columns}"
    )
    print("v8.3.1 Module 33 schema preflight passed.")
    print(f"module33_runs columns: {len(columns)}")


if __name__ == "__main__":
    main()
