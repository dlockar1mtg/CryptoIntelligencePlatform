from crypto_platform.platform import load_all, connect
from crypto_platform.module38 import MODULE38_SCHEMA


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
    conn.execute(MODULE38_SCHEMA)

    show(conn, "PORTFOLIO FORECAST", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m38_portfolio_forecast
    """)

    show(conn, "ASSET FORECASTS", """
        SELECT forecast_date,
               asset_id,
               horizon_days,
               current_price,
               predicted_return_pct,
               predicted_price,
               lower_return_pct,
               upper_return_pct,
               probability_positive,
               forecast_confidence,
               model_agreement,
               regime_adjustment_pct,
               macro_adjustment_pct,
               forecast_status
        FROM latest_m38_asset_forecasts
    """)

    show(conn, "MODEL VALIDATION", """
        SELECT asset_id,
               horizon_days,
               model_key,
               validation_rows,
               validation_mae_pct,
               validation_rmse_pct,
               directional_accuracy_pct,
               ensemble_weight,
               selected
        FROM latest_m38_model_validation
    """)

    show(conn, "REGIME TRANSITIONS", """
        SELECT current_regime,
               next_regime,
               transition_probability,
               expected_duration_days,
               transition_rank
        FROM latest_m38_regime_transitions
    """)

    show(conn, "FORECAST ATTRIBUTION", """
        SELECT asset_id,
               horizon_days,
               driver_key,
               driver_category,
               contribution_pct,
               contribution_direction,
               importance_rank
        FROM latest_m38_forecast_attribution
        WHERE importance_rank <= 5
    """)

    show(conn, "OPTIMIZER FEEDBACK", """
        SELECT asset_id,
               horizon_days,
               module37_expected_return_pct,
               predictive_return_pct,
               blended_optimizer_return_pct,
               predictive_weight,
               optimizer_weight
        FROM latest_m38_predictive_expected_returns
    """)

    show(conn, "LATEST RUNS", """
        SELECT started_at_utc,
               completed_at_utc,
               status,
               forecast_rows,
               model_rows,
               transition_rows,
               attribution_rows,
               portfolio_rows,
               horizons_completed,
               assets_completed,
               mean_validation_mae_pct,
               mean_forecast_confidence,
               predictive_regime,
               predictive_regime_confidence,
               portfolio_expected_return_pct,
               forecast_risk_status,
               recommendation,
               notes
        FROM module38_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()


if __name__ == "__main__":
    main()
