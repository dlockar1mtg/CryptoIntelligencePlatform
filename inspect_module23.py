from crypto_platform.platform import load_all,connect
from crypto_platform.module23 import MODULE23_SCHEMA
def show(c,t,q):
 print(f'\n{t}\n'+'-'*len(t)); f=c.execute(q).fetchdf(); print(f.to_string(index=False) if not f.empty else 'No data.')
def main():
 s,_=load_all(); c=connect(s); c.execute(MODULE23_SCHEMA)
 show(c,'AUDITED BACKTEST SUMMARY','SELECT * EXCLUDE(run_id,source_module22_run_id,calculated_at_utc) FROM latest_audited_backtest_summary')
 show(c,'AUDIT FINDINGS','SELECT severity,audit_category,finding_key,finding_value,threshold_value,affected_rows,finding_message,remediation FROM latest_backtest_audit_findings')
 show(c,'BENCHMARK AUDIT','SELECT benchmark_name,total_return_pct,annualized_return_pct,annualized_volatility_pct,sharpe_ratio,maximum_drawdown_pct,excess_vs_audited_portfolio_pct FROM latest_benchmark_audit_summary')
 show(c,'PERFORMANCE ATTRIBUTION','SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_performance_attribution_audit')
 show(c,'DRAWDOWN LABEL AUDIT','SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_drawdown_label_audit')
 show(c,'BOOTSTRAP EXCESS AUDIT','SELECT simulations,seed,mean_excess_return_pct,median_excess_return_pct,lower_95_pct,upper_95_pct,probability_excess_positive*100 AS probability_excess_positive_pct,probability_excess_above_10pct*100 AS probability_excess_above_10pct_pct FROM latest_bootstrap_excess_audit')
 show(c,'LARGEST ACCOUNTING ERRORS','SELECT rebalance_date,next_rebalance_date,corrected_portfolio_return_pct,stored_portfolio_return_max_pct,stored_vs_corrected_error_pct,btc_return_pct,period_valid FROM latest_audited_portfolio_periods ORDER BY ABS(stored_vs_corrected_error_pct) DESC LIMIT 20')
 show(c,'LATEST MODULE 23 RUNS','SELECT * EXCLUDE(run_id,audited_module22_run_id) FROM module23_runs ORDER BY started_at_utc DESC LIMIT 10'); c.close()
if __name__=='__main__': main()
