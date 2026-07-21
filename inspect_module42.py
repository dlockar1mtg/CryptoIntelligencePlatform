from crypto_platform.platform import load_all, connect
from crypto_platform.module42 import MODULE42_SCHEMA


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
    conn.execute(MODULE42_SCHEMA)

    show(conn, "DECISION SUMMARY", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m42_decision_summary
    """)

    show(conn, "ASSET RECOMMENDATIONS", """
        SELECT recommendation_date,
               asset_id,
               current_price,
               investment_score,
               best_action,
               best_current_portfolio_pct,
               weight_change_pct,
               suggested_timeline,
               entry_strategy,
               conviction,
               forecast_confidence,
               reliability_score,
               primary_reason,
               evidence_status
        FROM latest_m42_asset_recommendations
    """)

    show(conn, "7-DAY AND 30-DAY PRICES", """
        SELECT asset_id,
               horizon_label,
               projection_date,
               current_price,
               bear_price,
               median_price,
               bull_price,
               projection_confidence,
               evidence_status
        FROM latest_m42_price_projections
        WHERE horizon_label IN ('7D','30D')
        ORDER BY asset_id, horizon_days
    """)

    show(conn, "QUARTERLY PRICE PATH THROUGH MONTH 48", """
        SELECT asset_id,
               horizon_label,
               projection_date,
               bear_price,
               median_price,
               bull_price,
               median_return_pct,
               projection_confidence,
               evidence_status
        FROM latest_m42_price_projections
        WHERE horizon_months>=3
        ORDER BY asset_id, horizon_days
    """)

    show(conn, "EXECUTION PLAN", """
        SELECT asset_id,
               target_weight,
               current_weight,
               trade_weight,
               trade_action,
               execution_stage,
               execution_window,
               tranche_pct,
               trigger_description
        FROM latest_m42_portfolio_plan
    """)

    show(conn, "LATEST RUNS", """
        SELECT started_at_utc,
               completed_at_utc,
               status,
               recommendation_rows,
               projection_rows,
               assets_covered,
               horizons_covered,
               total_target_risk_weight,
               target_cash_weight,
               overall_action,
               overall_timeline,
               evidence_status,
               recommendation,
               notes
        FROM module42_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()


if __name__ == "__main__":
    main()
