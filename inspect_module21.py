from crypto_platform.platform import load_all, connect
from crypto_platform.module21 import MODULE21_SCHEMA

def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE21_SCHEMA)

    show(conn, "CURRENT INVESTMENT DECISION", """
        SELECT observation_date, stance, confidence,
               target_btc_weight*100 AS target_btc_weight_pct,
               target_cash_weight*100 AS target_cash_weight_pct,
               action_score, dominant_regime,
               positive_return_probability_90d*100
                   AS positive_return_probability_90d_pct,
               drawdown_20_probability_90d*100
                   AS drawdown_20_probability_90d_pct,
               risk_score, governed_feature_count,
               production_status
        FROM latest_investment_decision
        ORDER BY observation_date DESC LIMIT 1
    """)

    show(conn, "DECISION RATIONALE", """
        SELECT rationale_rank, rationale_type,
               feature_key, feature_value,
               standardized_value, inferred_direction,
               contribution, rationale_text
        FROM latest_investment_decision_rationale
        ORDER BY observation_date DESC, rationale_rank
        LIMIT 12
    """)

    show(conn, "CURRENT REGIME PROBABILITIES", """
        SELECT observation_date,
               bull_probability*100 AS bull_pct,
               recovery_probability*100 AS recovery_pct,
               sideways_probability*100 AS sideways_pct,
               correction_probability*100 AS correction_pct,
               bear_probability*100 AS bear_pct,
               dominant_regime,
               regime_confidence*100 AS regime_confidence_pct
        FROM latest_market_regime_probabilities
        ORDER BY observation_date DESC LIMIT 1
    """)

    show(conn, "INVESTMENT PROBABILITIES", """
        SELECT observation_date, forward_horizon_days,
               positive_return_probability*100
                   AS positive_return_probability_pct,
               drawdown_20_probability*100
                   AS drawdown_20_probability_pct,
               liquidity_expansion_probability*100
                   AS liquidity_expansion_probability_pct,
               probability_confidence*100
                   AS probability_confidence_pct,
               model_quality_status
        FROM latest_investment_probabilities
        ORDER BY observation_date DESC, forward_horizon_days
    """)

    show(conn, "MODEL QUALITY", """
        SELECT target_key, forward_horizon_days,
               feature_count, training_rows, testing_rows,
               accuracy_pct, roc_auc, brier_score,
               quality_status
        FROM latest_decision_model_quality
    """)

    show(conn, "RISK SNAPSHOT", """
        SELECT observation_date, volatility_30d_pct,
               volatility_90d_pct,
               historical_var_95_1d_pct,
               historical_cvar_95_1d_pct,
               maximum_drawdown_365d_pct,
               expected_30d_loss_pct,
               risk_score, risk_level
        FROM latest_investment_risk_snapshot
        ORDER BY observation_date DESC LIMIT 1
    """)

    show(conn, "DECISION SHADOW SUMMARY", """
        SELECT start_date, end_date, periods,
               total_return_pct, annualized_return_pct,
               annualized_volatility_pct, sharpe_ratio,
               maximum_drawdown_pct, btc_total_return_pct,
               btc_excess_pct, information_ratio,
               benchmark_win_rate_pct,
               average_btc_weight_pct,
               average_turnover_pct,
               transaction_cost_drag_pct,
               promotion_status, promotion_reason
        FROM latest_decision_shadow_summary
    """)

    show(conn, "RECENT DECISION SHADOW PERIODS", """
        SELECT rebalance_date, next_rebalance_date,
               stance, btc_weight*100 AS btc_weight_pct,
               cash_weight*100 AS cash_weight_pct,
               action_score,
               portfolio_return_pct, btc_return_pct,
               excess_return_pct, turnover_pct,
               transaction_cost_pct
        FROM latest_decision_shadow_periods
        ORDER BY rebalance_date DESC LIMIT 18
    """)

    show(conn, "LATEST MODULE 21 RUNS", """
        SELECT started_at_utc, completed_at_utc,
               status, governed_features,
               probability_models, current_stance,
               current_btc_weight,
               shadow_periods, shadow_return_pct,
               btc_return_pct, shadow_excess_pct,
               promoted, notes
        FROM module21_runs
        ORDER BY started_at_utc DESC LIMIT 10
    """)

    conn.close()

if __name__ == "__main__":
    main()
