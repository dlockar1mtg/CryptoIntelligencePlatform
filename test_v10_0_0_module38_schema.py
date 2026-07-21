from crypto_platform.platform import load_all, connect
from crypto_platform.module38 import MODULE38_SCHEMA


EXPECTED_COLUMNS = [
    "run_id",
    "source_module37_run_id",
    "source_module30_run_id",
    "started_at_utc",
    "completed_at_utc",
    "status",
    "forecast_rows",
    "model_rows",
    "transition_rows",
    "attribution_rows",
    "portfolio_rows",
    "horizons_completed",
    "assets_completed",
    "mean_validation_mae_pct",
    "mean_forecast_confidence",
    "predictive_regime",
    "predictive_regime_confidence",
    "portfolio_expected_return_pct",
    "forecast_risk_status",
    "recommendation",
    "notes",
    "platform_version",
]


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE38_SCHEMA)
    columns = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE lower(table_name)='module38_runs'
        ORDER BY ordinal_position
        """
    ).fetchdf()["column_name"].tolist()
    conn.close()

    assert columns == EXPECTED_COLUMNS, (
        f"module38_runs schema mismatch. "
        f"Expected {EXPECTED_COLUMNS}, got {columns}"
    )
    print("v10.0.0 Module 38 schema preflight passed.")
    print(f"module38_runs columns: {len(columns)}")


if __name__ == "__main__":
    main()
