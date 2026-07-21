from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module13 import MODULE13_SCHEMA
EXPORTS={
 "latest_market_structure":"SELECT * FROM latest_market_structure",
 "market_structure_daily":"SELECT * FROM market_structure_daily",
 "latest_derivatives_signals":"SELECT * FROM latest_derivatives_signals",
 "derivatives_signal_current":"SELECT * FROM derivatives_signal_current",
 "latest_investment_recommendations":"SELECT * FROM latest_investment_recommendations",
 "investment_recommendations":"SELECT * FROM investment_recommendations",
 "latest_portfolio_recommendation":"SELECT * FROM latest_portfolio_recommendation",
 "portfolio_recommendation":"SELECT * FROM portfolio_recommendation",
 "module13_runs":"SELECT * FROM module13_runs",
}
def main():
 s,_=load_all(); c=connect(s); c.execute(MODULE13_SCHEMA)
 d=path_for(s,"export_directory"); d.mkdir(parents=True,exist_ok=True)
 for n,q in EXPORTS.items():
  f=c.execute(q).fetchdf(); o=d/f"{n}.csv"; f.to_csv(o,index=False); print(f"{n}: {len(f)} rows -> {o}")
 c.close()
if __name__=="__main__":main()
