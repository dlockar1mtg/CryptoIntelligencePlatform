from crypto_platform.platform import load_all, connect
from crypto_platform.module33 import MODULE33_SCHEMA


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
    conn.execute(MODULE33_SCHEMA)

    show(conn, "VALIDATION SUMMARY", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m33_validation_summary
    """)

    show(conn, "SELECTED DECISION CANDIDATE", """
        SELECT candidate_id,
               temperature,
               probability_floor,
               switch_margin,
               minimum_hold_days,
               confidence_floor,
               maximum_risk_exposure,
               observations,
               cumulative_return_pct,
               cagr_pct,
               annualized_volatility_pct,
               sharpe_ratio,
               sortino_ratio,
               maximum_drawdown_pct,
               calmar_ratio,
               annualized_turnover_pct,
               total_transaction_cost_pct,
               switch_count,
               objective_score
        FROM latest_m33_decision_candidates
        WHERE selected=TRUE
    """)

    show(conn, "TOP DECISION CANDIDATES", """
        SELECT candidate_id,
               temperature,
               switch_margin,
               minimum_hold_days,
               confidence_floor,
               maximum_risk_exposure,
               sharpe_ratio,
               maximum_drawdown_pct,
               annualized_turnover_pct,
               total_transaction_cost_pct,
               switch_count,
               objective_score
        FROM latest_m33_decision_candidates
        ORDER BY objective_score DESC
        LIMIT 20
    """)

    show(conn, "ADJUSTED PROBABILITY DRIFT", """
        SELECT window_end_date,
               window_days,
               observations,
               rolling_reference_days,
               mean_top_probability,
               mean_entropy,
               probability_psi,
               entropy_psi,
               confidence_shift_pct,
               disagreement_rate_pct,
               drift_score,
               drift_status
        FROM latest_m33_adjusted_probability_drift
        LIMIT 30
    """)

    show(conn, "COST SENSITIVITY", """
        SELECT transaction_cost_bps,
               observations,
               cumulative_return_pct,
               cagr_pct,
               sharpe_ratio,
               maximum_drawdown_pct,
               annualized_turnover_pct,
               total_transaction_cost_pct,
               passed
        FROM latest_m33_cost_sensitivity
    """)

    show(conn, "BENCHMARK COMPARISON", """
        SELECT strategy_key,
               observations,
               cumulative_return_pct,
               cagr_pct,
               annualized_volatility_pct,
               sharpe_ratio,
               sortino_ratio,
               maximum_drawdown_pct,
               calmar_ratio,
               annualized_turnover_pct,
               total_transaction_cost_pct,
               selected
        FROM latest_m33_benchmark_comparison
    """)

    show(conn, "RECENT OPTIMIZED DECISIONS", """
        SELECT observation_date,
               raw_regime,
               held_regime,
               raw_probability,
               regularized_probability,
               confidence_multiplier,
               target_risk_exposure,
               daily_return,
               cumulative_return,
               turnover,
               transaction_cost,
               switched
        FROM latest_m33_optimized_daily
        ORDER BY observation_date DESC
        LIMIT 30
    """)

    show(conn, "LATEST RUNS", """
        SELECT started_at_utc,
               completed_at_utc,
               status,
               candidate_rows,
               daily_rows,
               cost_sensitivity_rows,
               drift_rows,
               selected_candidate_id,
               selected_strategy,
               annualized_turnover_pct,
               selected_sharpe,
               selected_max_drawdown_pct,
               btc_sharpe,
               btc_max_drawdown_pct,
               adjusted_drift_status,
               validation_status,
               recommendation,
               notes
        FROM module33_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()


if __name__ == "__main__":
    main()
