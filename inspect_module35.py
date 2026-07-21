from crypto_platform.platform import load_all,connect
from crypto_platform.module35 import MODULE35_SCHEMA
def show(c,t,q):
 print(f'\n{t}\n'+('-'*len(t))); f=c.execute(q).fetchdf(); print(f.to_string(index=False) if not f.empty else 'No data.')
def main():
 s,_=load_all(); c=connect(s); c.execute(MODULE35_SCHEMA); show(c,'PORTFOLIO STATISTICS','SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m35_portfolio_statistics'); show(c,'TARGET ALLOCATIONS','SELECT asset_id,current_weight,final_target_weight,trade_weight,allocation_status FROM latest_m35_portfolio_allocations'); show(c,'PORTFOLIO CANDIDATES','SELECT candidate_id,method,expected_return_pct,expected_volatility_pct,expected_sharpe,diversification_score,turnover_pct,objective_score,selected FROM latest_m35_portfolio_candidates'); c.close()
if __name__=='__main__': main()
