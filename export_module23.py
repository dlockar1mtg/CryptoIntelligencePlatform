from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module23 import MODULE23_SCHEMA
E={'latest_audited_backtest_summary':'SELECT * FROM latest_audited_backtest_summary','audited_backtest_summary':'SELECT * FROM audited_backtest_summary','latest_backtest_audit_findings':'SELECT * FROM latest_backtest_audit_findings','backtest_audit_findings':'SELECT * FROM backtest_audit_findings','latest_audited_portfolio_periods':'SELECT * FROM latest_audited_portfolio_periods','audited_portfolio_periods':'SELECT * FROM audited_portfolio_periods','latest_benchmark_audit_summary':'SELECT * FROM latest_benchmark_audit_summary','benchmark_audit_summary':'SELECT * FROM benchmark_audit_summary','latest_performance_attribution_audit':'SELECT * FROM latest_performance_attribution_audit','latest_drawdown_label_audit':'SELECT * FROM latest_drawdown_label_audit','latest_bootstrap_excess_audit':'SELECT * FROM latest_bootstrap_excess_audit','module23_runs':'SELECT * FROM module23_runs'}
def main():
 s,_=load_all(); c=connect(s); c.execute(MODULE23_SCHEMA); d=path_for(s,'export_directory'); d.mkdir(parents=True,exist_ok=True)
 for n,q in E.items():
  f=c.execute(q).fetchdf(); o=d/f'{n}.csv'; f.to_csv(o,index=False); print(f'{n}: {len(f)} rows -> {o}')
 c.close()
if __name__=='__main__': main()
