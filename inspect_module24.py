from crypto_platform.platform import load_all, connect
from crypto_platform.module24 import MODULE24_SCHEMA


def show(conn, title, sql):
    print(f'\n{title}')
    print('-' * len(title))
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else 'No data.')


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE24_SCHEMA)
    show(conn, 'ALPHA RESEARCH SUMMARY', '''
        SELECT * EXCLUDE(run_id, calculated_at_utc)
        FROM latest_alpha_research_summary
    ''')
    show(conn, 'SELECTED WALK-FORWARD CANDIDATES', '''
        SELECT fold_number, candidate_id,
               training_start_date, training_end_date,
               testing_start_date, testing_end_date,
               training_objective, testing_return_pct,
               btc_return_pct, equal_weight_return_pct,
               inverse_volatility_return_pct,
               excess_vs_btc_pct, maximum_drawdown_pct,
               information_ratio, average_cash_weight_pct,
               average_turnover_pct, transaction_cost_drag_pct
        FROM latest_alpha_walk_forward_results
        WHERE selected_for_fold=TRUE
        ORDER BY fold_number
    ''')
    show(conn, 'DRAWDOWN LABEL VALIDATION', '''
        SELECT * EXCLUDE(run_id, calculated_at_utc)
        FROM latest_alpha_label_validation
    ''')
    show(conn, 'BOOTSTRAP ALPHA VALIDATION', '''
        SELECT * EXCLUDE(run_id, calculated_at_utc)
        FROM latest_alpha_bootstrap_validation
    ''')
    show(conn, 'LATEST MODULE 24 RUNS', '''
        SELECT * EXCLUDE(run_id)
        FROM module24_runs
        ORDER BY started_at_utc DESC LIMIT 10
    ''')
    conn.close()


if __name__ == '__main__':
    main()
