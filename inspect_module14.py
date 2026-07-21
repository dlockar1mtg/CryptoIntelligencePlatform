from crypto_platform.platform import load_all, connect
from crypto_platform.module14 import MODULE14_SCHEMA

def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE14_SCHEMA)

    show(conn, "PORTFOLIO BACKTEST SUMMARY", '''
        SELECT start_date,end_date,rebalance_periods,
               total_return_pct,annualized_return_pct,
               annualized_volatility_pct,sharpe_ratio,
               maximum_drawdown_pct,benchmark_total_return_pct,
               benchmark_annualized_return_pct,excess_return_pct,
               tracking_error_pct,information_ratio,
               average_turnover_pct,transaction_cost_drag_pct,
               positive_period_rate_pct,benchmark_win_rate_pct,
               promoted,promotion_reason
        FROM latest_portfolio_backtest_summary
    ''')
    show(conn, "SCORING VALIDATION SUMMARY", '''
        SELECT forward_horizon_days,sample_count,signal_dates,
               spearman_rank_correlation,top_half_hit_rate_pct,
               benchmark_outperformance_rate_pct,
               top_score_minus_bottom_score_pct,
               average_forward_return_pct,average_excess_return_pct
        FROM latest_score_validation_summary
        ORDER BY forward_horizon_days
    ''')
    show(conn, "REGIME VALIDATION", '''
        SELECT regime,periods,portfolio_return_pct,
               benchmark_return_pct,excess_return_pct,
               win_rate_pct,maximum_drawdown_pct
        FROM latest_portfolio_regime_validation
        ORDER BY regime
    ''')
    show(conn, "RECENT BACKTEST PERIODS", '''
        SELECT rebalance_date,next_rebalance_date,
               MAX(portfolio_period_return_pct)
                   AS portfolio_period_return_pct,
               MAX(benchmark_period_return_pct)
                   AS benchmark_period_return_pct,
               MAX(turnover)*100 AS turnover_pct,
               MAX(transaction_cost_pct)
                   AS transaction_cost_pct
        FROM latest_portfolio_backtest_periods
        GROUP BY rebalance_date,next_rebalance_date
        ORDER BY rebalance_date DESC
        LIMIT 18
    ''')
    show(conn, "LATEST MODULE 14 RUNS", '''
        SELECT started_at_utc,completed_at_utc,status,
               rebalance_periods,validation_rows,
               portfolio_return_pct,benchmark_return_pct,
               excess_return_pct,maximum_drawdown_pct,
               information_ratio,promoted,notes
        FROM module14_runs
        ORDER BY started_at_utc DESC LIMIT 10
    ''')
    conn.close()

if __name__ == "__main__":
    main()
