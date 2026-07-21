from pathlib import Path
import tempfile
import numpy as np,pandas as pd
from crypto_platform.platform import load_all,connect
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module16 import Module16Runner,MODULE16_SCHEMA

def main():
 settings,assets=load_all()
 with tempfile.TemporaryDirectory() as temp:
  settings['platform']['database_path']=str(Path(temp)/'test.duckdb')
  settings['module16']['optimization']['candidate_count']=12
  settings['module16']['optimization']['shortlist_count']=4
  settings['module16']['optimization']['minimum_walk_forward_folds']=2
  settings['module15']['research']['start_date']='2022-01-01'
  settings['module15']['walk_forward']['training_months']=12
  settings['module15']['walk_forward']['testing_months']=6
  settings['module15']['walk_forward']['step_months']=6
  settings['module15']['walk_forward']['minimum_folds']=2
  c=connect(settings);c.execute(MODULE6_SCHEMA);c.execute(MODULE16_SCHEMA)
  rng=np.random.default_rng(41);dates=pd.date_range('2020-01-01',periods=1700,freq='D');rows=[];common=rng.normal(.00045,.018,len(dates))
  for i,aid in enumerate(['bitcoin','ethereum','solana','chainlink','xrp','avalanche']):
   prices=100*np.exp(np.cumsum(common+rng.normal(.00003*i,.006+.001*i,len(dates))))
   for d,p in zip(dates,prices): rows.append({'asset_id':aid,'observation_date':d.date(),'price_usd':float(p),'market_cap_usd':1e10,'volume_24h_usd':1e8,'price_source':'test','market_cap_source':'test','volume_source':'test','source_rows':1,'collected_at_utc':pd.Timestamp.now(tz='UTC')})
  f=pd.DataFrame(rows);c.register('s',f);c.execute('INSERT INTO canonical_market_daily SELECT * FROM s');c.unregister('s');c.close()
  r=Module16Runner();r.conn.close();r.evaluator.conn.close();r.settings=settings;r.assets=assets;r.config=settings['module16'];r.conn=connect(settings);r.conn.execute(MODULE16_SCHEMA)
  r.evaluator.settings=settings;r.evaluator.assets=assets;r.evaluator.config=settings['module15'];r.evaluator.conn=connect(settings)
  result=r.run();assert result['status']=='SUCCESS';assert result['candidate_count']==12;assert result['walk_forward_count']==4
  ch=connect(settings);assert ch.execute('SELECT COUNT(*) FROM latest_candidate_rankings').fetchone()[0]==4;assert ch.execute('SELECT COUNT(*) FROM latest_parameter_importance').fetchone()[0]>0;ch.close()
 print('Crypto v4.1.0 optimization smoke test passed.')
if __name__=='__main__':main()
