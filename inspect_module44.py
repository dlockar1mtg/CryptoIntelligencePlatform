from crypto_platform.platform import load_all, connect
from crypto_platform.module44 import MODULE44_SCHEMA


def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")


def main():
    s, _ = load_all()
    c = connect(s)
    c.execute(MODULE44_SCHEMA)
    show(c, "ECONOMIC VALUE SUMMARY", "SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m44_economic_value_summary")
    show(c, "DECISION OUTCOMES", "SELECT recommendation_date,asset_id,horizon_days,best_action,investment_score,outcome_status,realized_return_pct,strategy_return_pct,excess_vs_cash_pct,excess_vs_buy_hold_pct,direction_correct,economic_value_positive FROM latest_m44_decision_outcomes")
    show(c, "BENCHMARK COMPARISON", "SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m44_benchmark_comparison")
    show(c, "ACTION ECONOMIC VALUE", "SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m44_action_value")
    show(c, "TIMING VALUE", "SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m44_timing_value")
    show(c, "HORIZON VALUE", "SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m44_horizon_value")
    show(c, "PORTFOLIO VALUE", "SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m44_portfolio_value")
    show(c, "LATEST RUNS", "SELECT started_at_utc,completed_at_utc,status,decision_rows,matured_rows,benchmark_rows,timing_rows,action_rows,horizon_rows,portfolio_rows,live_evidence_ratio,economic_value_status,recommendation,notes FROM module44_runs ORDER BY started_at_utc DESC LIMIT 10")
    c.close()


if __name__ == "__main__":
    main()
