from crypto_platform.platform import load_all, connect
from crypto_platform.module40 import MODULE40_SCHEMA


def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(
        frame.to_string(index=False)
        if not frame.empty
        else "No data."
    )


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE40_SCHEMA)

    show(conn, "MEMORY SUMMARY", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m40_memory_summary
    """)

    show(conn, "PENDING FORECASTS", """
        SELECT forecast_date,
               outcome_due_date,
               asset_id,
               horizon_days,
               predicted_return_pct,
               calibrated_probability_positive,
               calibrated_lower_return_pct,
               calibrated_upper_return_pct,
               forecast_confidence,
               predictive_regime,
               outcome_status
        FROM latest_m40_pending_forecasts
    """)

    show(conn, "MATURED FORECASTS", """
        SELECT forecast_date,
               realized_date,
               asset_id,
               horizon_days,
               predicted_return_pct,
               realized_return_pct,
               absolute_error_pct,
               direction_correct,
               interval_covered,
               calibrated_probability_positive
        FROM latest_m40_matured_forecasts
    """)

    show(conn, "LEARNING SUMMARY", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m40_learning_summary
    """)

    show(conn, "CALIBRATION CURVE", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m40_calibration_curve
    """)

    show(conn, "MODEL LEADERBOARD", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m40_model_leaderboard
    """)

    show(conn, "RETRAINING RECOMMENDATIONS", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m40_retraining_recommendations
    """)

    show(conn, "LATEST RUNS", """
        SELECT started_at_utc,
               completed_at_utc,
               status,
               forecasts_ingested,
               model_snapshots_ingested,
               attribution_snapshots_ingested,
               outcomes_matured,
               learning_summary_rows,
               calibration_curve_rows,
               models_evaluated,
               earliest_forecast_date,
               latest_forecast_date,
               realized_horizons,
               memory_status,
               continuous_learning_status,
               recommendation,
               notes
        FROM module40_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()


if __name__ == "__main__":
    main()
