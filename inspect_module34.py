from crypto_platform.platform import load_all,connect
from crypto_platform.module34 import MODULE34_SCHEMA

def show(c,title,sql):
    print(f"\n{title}\n{'-'*len(title)}")
    f=c.execute(sql).fetchdf()
    print(f.to_string(index=False) if not f.empty else "No data.")

def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE34_SCHEMA)
    show(c,"VALIDATION SUMMARY","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m34_validation_summary")
    show(c,"SELECTED EXECUTION POLICY","SELECT * EXCLUDE(run_id,calculated_at_utc,selected) FROM latest_m34_execution_candidates WHERE selected=TRUE")
    show(c,"TOP EXECUTION POLICIES","SELECT candidate_id,rebalance_frequency_days,rebalance_band_pct,minimum_trade_pct,exposure_smoothing_alpha,annual_turnover_budget_pct,trade_days,total_trades,sharpe_ratio,maximum_drawdown_pct,annualized_turnover_pct,total_transaction_cost_pct,tracking_error_pct,objective_score FROM latest_m34_execution_candidates LIMIT 20")
    show(c,"EXECUTION DRIFT","SELECT window_end_date,window_days,reference_days,observations,jensen_shannon_distance,wasserstein_top_probability,wasserstein_entropy,disagreement_rate_pct,execution_tracking_error_pct,drift_score,drift_status FROM latest_m34_execution_drift LIMIT 30")
    show(c,"COST SENSITIVITY","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m34_cost_sensitivity")
    show(c,"BENCHMARK COMPARISON","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m34_benchmark_summary")
    show(c,"RECENT EXECUTION","SELECT observation_date,held_regime,target_risk_exposure,smoothed_risk_exposure,target_gross_weight,executed_gross_weight,daily_return,cumulative_return,turnover,transaction_cost,trade_executed,turnover_budget_remaining_pct FROM latest_m34_execution_daily ORDER BY observation_date DESC LIMIT 30")
    show(c,"RECENT TRADES","SELECT observation_date,asset_id,prior_weight,target_weight,executed_weight,trade_weight,trade_notional_pct,transaction_cost,execution_reason FROM latest_m34_trade_ledger ORDER BY observation_date DESC,asset_id LIMIT 60")
    show(c,"LATEST RUNS","SELECT started_at_utc,completed_at_utc,status,execution_candidate_rows,execution_daily_rows,trade_rows,drift_rows,cost_rows,selected_candidate_id,selected_sharpe,selected_max_drawdown_pct,selected_turnover_pct,btc_sharpe,btc_max_drawdown_pct,execution_drift_status,validation_status,recommendation,notes FROM module34_runs ORDER BY started_at_utc DESC LIMIT 10")
    c.close()

if __name__=="__main__":
    main()
