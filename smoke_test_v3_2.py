from pathlib import Path
import tempfile,pandas as pd
from crypto_platform.platform import load_all,connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA
from crypto_platform.module12 import Module12Runner,MODULE12_SCHEMA,symbol_equivalent
def main():
 assert symbol_equivalent('BTC','XBT'); assert not symbol_equivalent('PI','PIEVERSE'); assert not symbol_equivalent('M','MOON')
 s,core=load_all()
 with tempfile.TemporaryDirectory() as td:
  s['platform']['database_path']=str(Path(td)/'test.duckdb'); c=connect(s)
  for x in [MODULE2_SCHEMA,MODULE3_SCHEMA,MODULE5_SCHEMA,MODULE6_SCHEMA,MODULE7_SCHEMA,MODULE8_SCHEMA,MODULE9_SCHEMA,MODULE10_SCHEMA,MODULE11_SCHEMA,MODULE12_SCHEMA]: c.execute(x)
  now=pd.Timestamp.now(tz='UTC'); u=pd.DataFrame([{'asset_id':'bitcoin','symbol':'BTC','name':'Bitcoin','market_cap_rank':1,'market_cap_usd':1e12,'volume_24h_usd':1e10,'current_price_usd':100000.0,'price_change_24h_pct':1.0,'price_change_7d_pct':2.0,'price_change_30d_pct':3.0,'circulating_supply':1.9e7,'total_supply':2.1e7,'max_supply':2.1e7,'ath_change_pct':-10.0,'inclusion_status':'INCLUDED','inclusion_reason':'test','is_core':True,'discovered_at_utc':now,'updated_at_utc':now},{'asset_id':'pi-network','symbol':'PI','name':'Pi','market_cap_rank':20,'market_cap_usd':1e9,'volume_24h_usd':1e8,'current_price_usd':1.0,'price_change_24h_pct':1.0,'price_change_7d_pct':2.0,'price_change_30d_pct':3.0,'circulating_supply':1e9,'total_supply':1e9,'max_supply':None,'ath_change_pct':-50.0,'inclusion_status':'INCLUDED','inclusion_reason':'test','is_core':False,'discovered_at_utc':now,'updated_at_utc':now}]); c.register('u',u); c.execute('INSERT INTO research_universe SELECT * FROM u'); c.unregister('u')
  m=pd.DataFrame([{'provider':'kraken','provider_symbol':'XXBTZUSD','base_asset_code':'XXBT','normalized_base_symbol':'XBT','quote_asset_code':'ZUSD','normalized_quote_symbol':'USD','market_type':'spot','active':True,'metadata_json':'{}','collected_at_utc':now},{'provider':'kraken','provider_symbol':'PIEVERSEUSD','base_asset_code':'PIEVERSE','normalized_base_symbol':'PIEVERSE','quote_asset_code':'ZUSD','normalized_quote_symbol':'USD','market_type':'spot','active':True,'metadata_json':'{}','collected_at_utc':now},{'provider':'binance','provider_symbol':'BTCUSDT','base_asset_code':'BTC','normalized_base_symbol':'BTC','quote_asset_code':'USDT','normalized_quote_symbol':'USDT','market_type':'perpetual','active':True,'metadata_json':'{}','collected_at_utc':now}]); c.register('m',m); c.execute('INSERT INTO exchange_metadata_markets SELECT * FROM m'); c.unregister('m')
  h=pd.DataFrame([{'asset_id':'bitcoin','observation_date':pd.Timestamp('1970-01-01').date(),'price_usd':1.0,'market_cap_usd':None,'volume_24h_usd':1.0,'source':'kraken','source_symbol':'XXBTZUSD','collected_at_utc':now},{'asset_id':'bitcoin','observation_date':pd.Timestamp('2025-01-01').date(),'price_usd':100000.0,'market_cap_usd':None,'volume_24h_usd':1e9,'source':'kraken','source_symbol':'XXBTZUSD','collected_at_utc':now}]); c.register('h',h); c.execute('INSERT INTO research_market_daily SELECT * FROM h'); c.unregister('h'); c.close()
  r=Module12Runner(); r.conn.close(); r.settings=s; r.core_assets=core; r.config=s['module12']; r.conn=connect(s)
  for x in [MODULE2_SCHEMA,MODULE3_SCHEMA,MODULE5_SCHEMA,MODULE6_SCHEMA,MODULE7_SCHEMA,MODULE8_SCHEMA,MODULE9_SCHEMA,MODULE10_SCHEMA,MODULE11_SCHEMA,MODULE12_SCHEMA]: r.conn.execute(x)
  r.conn.execute("INSERT INTO module12_runs VALUES (?,?,NULL,'RUNNING',0,0,0,0,0,0,'test','3.2.0')",[r.run_id,now]); v,j=r.audit_and_rebuild(u,m); rem=r.clean_history(); assert v==2 and j==0 and rem>=1
  q=connect(s); assert q.execute("SELECT COUNT(*) FROM exchange_symbol_map WHERE asset_id='pi-network' AND active=TRUE").fetchone()[0]==0; assert q.execute("SELECT COUNT(*) FROM exchange_symbol_map WHERE asset_id='bitcoin' AND active=TRUE").fetchone()[0]==2; assert q.execute("SELECT COUNT(*) FROM research_market_daily WHERE observation_date='1970-01-01'").fetchone()[0]==0; q.close()
 print('Crypto v3.2 data-integrity smoke test passed.')
if __name__=='__main__': main()
