from crypto_platform.platform import load_all, connect
from crypto_platform.module15 import MODULE15_SCHEMA

def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE15_SCHEMA)

    show(conn, "CALIBRATED STRATEGY RECOMMENDATION", '''
        SELECT selected_variant,evidence_status,out_of_sample_folds,
               out_of_sample_total_return_pct,
               out_of_sample_btc_return_pct,
               out_of_sample_btc_excess_pct,
               out_of_sample_information_ratio,
               out_of_sample_maximum_drawdown_pct,
               out_of_sample_benchmark_win_rate_pct,
               baseline_total_return_pct,
               baseline_btc_excess_pct,recommendation
        FROM latest_calibrated_strategy_recommendation
    ''')
    show(conn, "FULL-SAMPLE VARIANT COMPARISON", '''
        SELECT variant_name,total_return_pct,
               annualized_return_pct,annualized_volatility_pct,
               sharpe_ratio,maximum_drawdown_pct,
               btc_return_pct,equal_weight_return_pct,
               btc_eth_return_pct,btc_excess_pct,
               equal_weight_excess_pct,btc_eth_excess_pct,
               information_ratio,benchmark_win_rate_pct,
               average_turnover_pct,transaction_cost_drag_pct,
               objective_score
        FROM latest_strategy_variant_results
        WHERE evaluation_scope='FULL_SAMPLE'
        ORDER BY objective_score DESC
    ''')
    show(conn, "WALK-FORWARD SELECTION", '''
        SELECT fold_number,training_start_date,training_end_date,
               testing_start_date,testing_end_date,
               selected_variant,training_objective_score,
               test_total_return_pct,test_btc_return_pct,
               test_btc_excess_pct,test_information_ratio,
               test_maximum_drawdown_pct,
               test_benchmark_win_rate_pct
        FROM latest_walk_forward_selection
        ORDER BY fold_number
    ''')
    show(conn, "BENCHMARK COMPARISON", '''
        SELECT benchmark_name,start_date,end_date,total_return_pct,
               annualized_return_pct,annualized_volatility_pct,
               sharpe_ratio,maximum_drawdown_pct
        FROM latest_benchmark_comparison
        ORDER BY total_return_pct DESC
    ''')
    show(conn, "LATEST MODULE 15 RUNS", '''
        SELECT started_at_utc,completed_at_utc,status,
               variants_tested,walk_forward_folds,
               selected_variant,selected_oos_return_pct,
               selected_btc_excess_pct,
               selected_information_ratio,
               selected_maximum_drawdown_pct,
               promoted,notes
        FROM module15_runs
        ORDER BY started_at_utc DESC LIMIT 10
    ''')
    conn.close()

if __name__ == "__main__":
    main()
