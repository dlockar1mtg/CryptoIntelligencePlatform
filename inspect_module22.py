from crypto_platform.platform import load_all, connect
from crypto_platform.module22 import MODULE22_SCHEMA

def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE22_SCHEMA)

    show(conn, "CURRENT SIX-ASSET ALLOCATION", """
        SELECT observation_date, asset_id,
               target_weight*100 AS target_weight_pct,
               expected_score, volatility_90d_pct,
               momentum_90d_pct,
               relative_strength_90d_pct,
               risk_penalty, allocation_reason
        FROM latest_six_asset_allocations
    """)

    show(conn, "CURRENT ENSEMBLE REGIME", """
        SELECT observation_date,
               trend_vote, macro_vote, liquidity_vote,
               volatility_vote, breadth_vote,
               bull_probability*100 AS bull_pct,
               recovery_probability*100 AS recovery_pct,
               sideways_probability*100 AS sideways_pct,
               correction_probability*100 AS correction_pct,
               bear_probability*100 AS bear_pct,
               dominant_regime, confidence*100 AS confidence_pct
        FROM latest_ensemble_regime
        ORDER BY observation_date DESC LIMIT 1
    """)

    show(conn, "SELECTED INTELLIGENCE MODELS", """
        SELECT target_key, forward_horizon_days,
               model_name, training_rows, testing_rows,
               accuracy_pct, roc_auc, brier_score,
               rank_score
        FROM latest_intelligence_model_comparison
        WHERE selected_model=TRUE
    """)

    show(conn, "MODEL COMPARISON", """
        SELECT target_key, forward_horizon_days,
               model_name, accuracy_pct, roc_auc,
               brier_score, rank_score, selected_model
        FROM latest_intelligence_model_comparison
    """)

    show(conn, "WALK-FORWARD VALIDATION", """
        SELECT fold_number, training_start_date,
               training_end_date, testing_start_date,
               testing_end_date, portfolio_return_pct,
               btc_return_pct, excess_return_pct,
               maximum_drawdown_pct, information_ratio,
               average_cash_weight_pct
        FROM latest_intelligence_walk_forward
    """)

    show(conn, "INTELLIGENCE PORTFOLIO SUMMARY", """
        SELECT * EXCLUDE(run_id, calculated_at_utc)
        FROM latest_intelligence_portfolio_summary
    """)

    show(conn, "RECENT INTELLIGENCE PERIODS", """
        SELECT rebalance_date, next_rebalance_date,
               asset_id, target_weight*100 AS target_weight_pct,
               realized_return_pct, contribution_pct,
               portfolio_period_return_pct,
               btc_period_return_pct, turnover_pct,
               transaction_cost_pct
        FROM latest_intelligence_portfolio_periods
        ORDER BY rebalance_date DESC, target_weight DESC
        LIMIT 40
    """)

    show(conn, "LATEST MODULE 22 RUNS", """
        SELECT started_at_utc, completed_at_utc,
               status, expanded_features, model_rows,
               selected_models, allocation_rows,
               walk_forward_folds, portfolio_return_pct,
               btc_return_pct, excess_return_pct,
               information_ratio, promotion_status, notes
        FROM module22_runs
        ORDER BY started_at_utc DESC LIMIT 10
    """)

    conn.close()

if __name__ == "__main__":
    main()
