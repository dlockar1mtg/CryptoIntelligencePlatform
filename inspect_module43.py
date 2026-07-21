from crypto_platform.platform import load_all, connect
from crypto_platform.module43 import MODULE43_SCHEMA


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
    conn.execute(MODULE43_SCHEMA)

    show(conn, "INVESTMENT COMMITTEE BRIEF", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m43_committee_brief
    """)

    show(conn, "RANKED OPPORTUNITIES", """
        SELECT opportunity_rank,
               asset_id,
               investment_score,
               relative_opportunity_score,
               best_action,
               conviction_tier,
               target_portfolio_pct,
               forecast_confidence,
               reliability_score,
               opportunity_status,
               primary_reason,
               evidence_status
        FROM latest_m43_opportunity_ranking
    """)

    show(conn, "WHAT CHANGED", """
        SELECT asset_id,
               current_action,
               prior_action,
               action_changed,
               score_change,
               target_weight_change_pct,
               confidence_change,
               median_30d_price_change_pct,
               median_3m_price_change_pct,
               change_classification,
               change_summary
        FROM latest_m43_decision_changes
    """)

    show(conn, "ACTION UPGRADE/DOWNGRADE TRIGGERS", """
        SELECT asset_id,
               current_action,
               upgrade_action,
               upgrade_condition,
               downgrade_action,
               downgrade_condition,
               current_distance_to_upgrade,
               trigger_status
        FROM latest_m43_action_triggers
    """)

    show(conn, "THESIS AND INVALIDATION MONITOR", """
        SELECT asset_id,
               thesis_summary,
               supporting_evidence,
               invalidation_condition,
               downside_risk,
               monitoring_priority,
               thesis_status
        FROM latest_m43_thesis_monitor
    """)

    show(conn, "BUY NOW VERSUS WAIT", """
        SELECT asset_id,
               current_action,
               current_price,
               median_7d_price,
               median_30d_price,
               median_3m_price,
               buy_now_30d_return_pct,
               wait_7d_then_30d_return_pct,
               wait_30d_then_3m_return_pct,
               estimated_wait_advantage_pct,
               timing_preference,
               timing_confidence,
               timing_reason
        FROM latest_m43_buy_wait_analysis
    """)

    show(conn, "LATEST RUNS", """
        SELECT started_at_utc,
               completed_at_utc,
               status,
               ranked_assets,
               change_rows,
               trigger_rows,
               thesis_rows,
               timing_rows,
               positive_actions,
               material_changes,
               evidence_status,
               committee_decision,
               recommendation,
               notes
        FROM module43_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()


if __name__ == "__main__":
    main()
