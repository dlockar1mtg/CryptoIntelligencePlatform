from crypto_platform.platform import load_all,connect
from crypto_platform.module36 import MODULE36_SCHEMA
def show(c,t,q):
 print(f'\n{t}\n'+('-'*len(t))); f=c.execute(q).fetchdf(); print(f.to_string(index=False) if not f.empty else 'No data.')
def main():
 s,_=load_all(); c=connect(s); c.execute(MODULE36_SCHEMA); show(c,'PORTFOLIO RISK','SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m36_portfolio_risk'); show(c,'ASSET RISK','SELECT asset_id,target_weight,annualized_volatility_pct,var_95_pct,cvar_95_pct,max_drawdown_365d_pct,marginal_risk_contribution_pct,risk_status FROM latest_m36_asset_risk'); show(c,'RISK-ADJUSTED ALLOCATIONS','SELECT asset_id,original_weight,final_risk_weight,risk_reduction_pct,action FROM latest_m36_risk_adjusted_allocations'); c.close()
if __name__=='__main__': main()
