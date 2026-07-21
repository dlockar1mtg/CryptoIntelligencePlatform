from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
from crypto_platform.platform import load_all,connect
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA
from crypto_platform.module12 import MODULE12_SCHEMA
from crypto_platform.module13 import Module13Runner,MODULE13_SCHEMA

def main():
 settings,assets=load_all()
 with tempfile.TemporaryDirectory() as temp:
  settings["platform"]["database_path"]=str(Path(temp)/"test.duckdb")
  c=connect(settings)
  for schema in [MODULE10_SCHEMA,MODULE11_SCHEMA,MODULE12_SCHEMA,MODULE13_SCHEMA]: c.execute(schema)
  now=pd.Timestamp.now(tz="UTC")
  universe=[]
  history=[]
  for i,a in enumerate(assets):
   universe.append({"asset_id":a["asset_id"],"symbol":a["symbol"],"name":a.get("name",a["asset_id"]),"market_cap_rank":i+1,"market_cap_usd":1e12/(i+1),"volume_24h_usd":1e9,"current_price_usd":100.0,"price_change_24h_pct":1.0,"price_change_7d_pct":2.0,"price_change_30d_pct":5.0,"circulating_supply":1e8,"total_supply":1e8,"max_supply":2e8,"ath_change_pct":-30.0,"inclusion_status":"INCLUDED","inclusion_reason":"test","is_core":True,"discovered_at_utc":now,"updated_at_utc":now})
   rng=np.random.default_rng(100+i)
   prices=100*np.exp(np.cumsum(rng.normal(.0005,.02,500)))
   dates=pd.date_range("2025-01-01",periods=500,freq="D")
   for d,p in zip(dates,prices):
    history.append({"asset_id":a["asset_id"],"observation_date":d.date(),"price_usd":float(p),"market_cap_usd":None,"volume_24h_usd":1e8,"source":"coinbase","source_symbol":a["coinbase_product"],"collected_at_utc":now})
  uf=pd.DataFrame(universe); hf=pd.DataFrame(history)
  c.register("u",uf); c.execute("INSERT INTO research_universe SELECT * FROM u"); c.unregister("u")
  c.register("h",hf); c.execute("INSERT INTO research_market_daily SELECT * FROM h"); c.unregister("h")
  tax=pd.DataFrame([{"asset_id":a["asset_id"],"sector":"LAYER_1","subsector":"LAYER_1","layer_type":"L1","is_meme":False,"is_exchange_token":False,"is_privacy":False,"is_rwa":False,"is_ai":False,"taxonomy_method":"test","updated_at_utc":now} for a in assets])
  c.register("t",tax); c.execute("INSERT INTO research_asset_taxonomy SELECT * FROM t"); c.unregister("t"); c.close()
  r=Module13Runner(); r.conn.close(); r.settings=settings; r.assets=assets; r.config=settings["module13"]; r.conn=connect(settings); r.conn.execute(MODULE13_SCHEMA)
  result=r.run()
  assert result["status"]=="SUCCESS"
  assert result["assets_analyzed"]==6
  check=connect(settings)
  assert check.execute("SELECT COUNT(*) FROM latest_market_structure").fetchone()[0]==6
  assert check.execute("SELECT COUNT(*) FROM latest_investment_recommendations").fetchone()[0]==6
  total=check.execute("SELECT SUM(target_weight) FROM latest_portfolio_recommendation").fetchone()[0]
  assert abs(total-1.0)<1e-6
  check.close()
 print("Crypto v3.3 market-structure smoke test passed.")
if __name__=="__main__":main()
