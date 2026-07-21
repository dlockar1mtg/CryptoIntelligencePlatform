from crypto_platform.platform import load_all, connect
from crypto_platform.module37 import MODULE37_SCHEMA


EXPECTED_COLUMNS = [
    "run_id",
    "source_module35_run_id",
    "source_module36_run_id",
    "started_at_utc",
    "completed_at_utc",
    "status",
    "candidate_rows",
    "allocation_rows",
    "frontier_rows",
    "risk_contribution_rows",
    "selected_candidate_id",
    "selected_method",
    "expected_return_pct",
    "expected_volatility_pct",
    "expected_sharpe",
    "diversification_ratio",
    "effective_assets",
    "concentration_score",
    "cash_weight",
    "turnover_pct",
    "validation_status",
    "recommendation",
    "notes",
    "platform_version",
]


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE37_SCHEMA)
    columns = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE lower(table_name)='module37_runs'
        ORDER BY ordinal_position
        """
    ).fetchdf()["column_name"].tolist()
    conn.close()

    assert columns == EXPECTED_COLUMNS, (
        f"module37_runs schema mismatch. "
        f"Expected {EXPECTED_COLUMNS}, got {columns}"
    )
    print("v9.2.0 Module 37 schema preflight passed.")
    print(f"module37_runs columns: {len(columns)}")


if __name__ == "__main__":
    main()
