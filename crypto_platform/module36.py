from __future__ import annotations
import math, uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from crypto_platform.platform import load_all, connect
from crypto_platform.module35 import MODULE35_SCHEMA
MODULE36_SCHEMA=r"""
CREATE TABLE IF NOT EXISTS module36_runs(
 run_id VARCHAR PRIMARY KEY,source_module35_run_id VARCHAR,started_at_utc TIMESTAMPTZ,
 completed_at_utc TIMESTAMPTZ,status VARCHAR,asset_risk_rows INTEGER,
 portfolio_risk_rows INTEGER,adjusted_allocation_rows INTEGER,portfolio_var_95_pct DOUBLE,
 portfolio_cvar_95_pct DOUBLE,expected_shortfall_pct DOUBLE,target_volatility_pct DOUBLE,
 realized_volatility_pct DOUBLE,volatility_scaler DOUBLE,tail_risk_status VARCHAR,
 liquidity_risk_status VARCHAR,overall_risk_status VARCHAR,recommendation VARCHAR,
 notes VARCHAR,platform_version VARCHAR);
CREATE TABLE IF NOT EXISTS m36_asset_risk(
 run_id VARCHAR,observation_date DATE,asset_id VARCHAR,target_weight DOUBLE,
 annualized_volatility_pct DOUBLE,var_95_pct DOUBLE,cvar_95_pct DOUBLE,
 max_drawdown_365d_pct DOUBLE,liquidity_score DOUBLE,marginal_risk_contribution_pct DOUBLE,
 risk_status VARCHAR,calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,observation_date,asset_id));
CREATE TABLE IF NOT EXISTS m36_portfolio_risk(
 run_id VARCHAR PRIMARY KEY,observation_date DATE,portfolio_var_95_pct DOUBLE,
 portfolio_cvar_95_pct DOUBLE,expected_shortfall_pct DOUBLE,annualized_volatility_pct DOUBLE,
 target_volatility_pct DOUBLE,volatility_scaler DOUBLE,maximum_drawdown_365d_pct DOUBLE,
 probability_of_loss_pct DOUBLE,tail_risk_status VARCHAR,liquidity_risk_status VARCHAR,
 overall_risk_status VARCHAR,calculated_at_utc TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS m36_risk_adjusted_allocations(
 run_id VARCHAR,observation_date DATE,asset_id VARCHAR,original_weight DOUBLE,
 volatility_adjusted_weight DOUBLE,final_risk_weight DOUBLE,risk_reduction_pct DOUBLE,
 action VARCHAR,calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,observation_date,asset_id));
CREATE OR REPLACE VIEW latest_m36_asset_risk AS SELECT * FROM m36_asset_risk WHERE run_id=(SELECT run_id FROM module36_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY marginal_risk_contribution_pct DESC;
CREATE OR REPLACE VIEW latest_m36_portfolio_risk AS SELECT * FROM m36_portfolio_risk WHERE run_id=(SELECT run_id FROM module36_runs ORDER BY started_at_utc DESC LIMIT 1);
CREATE OR REPLACE VIEW latest_m36_risk_adjusted_allocations AS SELECT * FROM m36_risk_adjusted_allocations WHERE run_id=(SELECT run_id FROM module36_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY final_risk_weight DESC;
"""
ASSETS=['bitcoin','ethereum','solana','chainlink','xrp','avalanche']
def utcnow(): return datetime.now(timezone.utc)
class Module36Runner:
 def __init__(self):
  self.settings,_=load_all(); self.conn=connect(self.settings); self.conn.execute(MODULE35_SCHEMA); self.conn.execute(MODULE36_SCHEMA); self.cfg=self.settings['module36']; self.run_id=str(uuid.uuid4()); self.started=utcnow(); row=self.conn.execute("SELECT run_id FROM module35_runs WHERE status='SUCCESS' AND validation_status='PASSED' ORDER BY started_at_utc DESC LIMIT 1").fetchone();
  if row is None: raise RuntimeError('A passed Module 35 run is required.')
  self.source=str(row[0])
 def upsert(self,t,f):
  if f.empty:return
  self.conn.register('_s',f); c=','.join(f.columns); self.conn.execute(f'INSERT OR REPLACE INTO {t}({c}) SELECT {c} FROM _s'); self.conn.unregister('_s')
 def run(self):
  self.conn.execute("INSERT INTO module36_runs VALUES(?,?,?,NULL,'RUNNING',0,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'9.1.0')",[self.run_id,self.source,self.started])
  try:
   f=self.conn.execute("SELECT asset_id,observation_date,price_usd FROM canonical_market_daily WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche') AND price_usd IS NOT NULL ORDER BY observation_date,asset_id").fetchdf(); f['observation_date']=pd.to_datetime(f['observation_date']); prices=f.pivot(index='observation_date',columns='asset_id',values='price_usd').reindex(columns=ASSETS).sort_index(); r=prices.pct_change(fill_method=None).dropna(how='all').fillna(0).tail(int(self.cfg['lookback_days']))
   a=self.conn.execute("SELECT observation_date,asset_id,final_target_weight FROM m35_portfolio_allocations WHERE run_id=?",[self.source]).fetchdf(); a['observation_date']=pd.to_datetime(a['observation_date']); date=a.observation_date.max().date(); w=np.array([float(a.loc[a.asset_id==x,'final_target_weight'].iloc[0]) if not a.loc[a.asset_id==x].empty else 0 for x in ASSETS]); cov=r.cov().to_numpy()*365; pvol=float(np.sqrt(w@cov@w)); target=float(self.cfg['target_volatility_pct'])/100; scaler=min(target/max(pvol,1e-9),1.0); adj=w*scaler; pr=(r*w).sum(axis=1); var=float(pr.quantile(.05)); cvar=float(pr[pr<=var].mean()); cum=(1+pr).cumprod(); dd=cum/cum.cummax()-1; mdd=float(dd.min()); pl=float((pr<0).mean()*100); tail='HIGH' if abs(cvar)>.05 else 'MODERATE' if abs(cvar)>.03 else 'LOW'; overall='HIGH_RISK' if tail=='HIGH' or pvol>target*1.5 else 'MODERATE_RISK' if tail=='MODERATE' or pvol>target else 'CONTROLLED'; rec='DE_RISK' if overall=='HIGH_RISK' else 'HOLD_RISK_BUDGET' if overall=='MODERATE_RISK' else 'RISK_WITHIN_LIMITS'; marginal=cov@w; total=float(w@cov@w); rc=w*marginal/max(total,1e-12)
   ar=[]; rr=[]
   for i,x in enumerate(ASSETS):
    xret=r[x]; xv=float(xret.std()*math.sqrt(365)); xv95=float(xret.quantile(.05)); xc=float(xret[xret<=xv95].mean()); xcum=(1+xret).cumprod(); xdd=xcum/xcum.cummax()-1; status='HIGH' if xv>.8 else 'MODERATE' if xv>.5 else 'LOW'; ar.append({'run_id':self.run_id,'observation_date':date,'asset_id':x,'target_weight':float(w[i]),'annualized_volatility_pct':xv*100,'var_95_pct':xv95*100,'cvar_95_pct':xc*100,'max_drawdown_365d_pct':float(xdd.min()*100),'liquidity_score':100.0,'marginal_risk_contribution_pct':float(rc[i]*100),'risk_status':status,'calculated_at_utc':utcnow()}); rr.append({'run_id':self.run_id,'observation_date':date,'asset_id':x,'original_weight':float(w[i]),'volatility_adjusted_weight':float(adj[i]),'final_risk_weight':float(adj[i]),'risk_reduction_pct':float(max(w[i]-adj[i],0)*100),'action':'REDUCE' if adj[i]<w[i]-.01 else 'HOLD','calculated_at_utc':utcnow()})
   cash_orig=float(a.loc[a.asset_id=='CASH','final_target_weight'].iloc[0]) if not a.loc[a.asset_id=='CASH'].empty else max(1-w.sum(),0); cash=1-adj.sum(); rr.append({'run_id':self.run_id,'observation_date':date,'asset_id':'CASH','original_weight':cash_orig,'volatility_adjusted_weight':cash,'final_risk_weight':cash,'risk_reduction_pct':0.0,'action':'INCREASE' if cash>cash_orig+.01 else 'HOLD','calculated_at_utc':utcnow()})
   pf=pd.DataFrame([{'run_id':self.run_id,'observation_date':date,'portfolio_var_95_pct':var*100,'portfolio_cvar_95_pct':cvar*100,'expected_shortfall_pct':cvar*100,'annualized_volatility_pct':pvol*100,'target_volatility_pct':target*100,'volatility_scaler':scaler,'maximum_drawdown_365d_pct':mdd*100,'probability_of_loss_pct':pl,'tail_risk_status':tail,'liquidity_risk_status':'LOW','overall_risk_status':overall,'calculated_at_utc':utcnow()}])
   self.upsert('m36_asset_risk',pd.DataFrame(ar)); self.upsert('m36_portfolio_risk',pf); self.upsert('m36_risk_adjusted_allocations',pd.DataFrame(rr)); self.conn.execute("UPDATE module36_runs SET completed_at_utc=?,status='SUCCESS',asset_risk_rows=?,portfolio_risk_rows=1,adjusted_allocation_rows=?,portfolio_var_95_pct=?,portfolio_cvar_95_pct=?,expected_shortfall_pct=?,target_volatility_pct=?,realized_volatility_pct=?,volatility_scaler=?,tail_risk_status=?,liquidity_risk_status='LOW',overall_risk_status=?,recommendation=?,notes=? WHERE run_id=?",[utcnow(),len(ar),len(rr),var*100,cvar*100,cvar*100,target*100,pvol*100,scaler,tail,overall,rec,'Risk-adjusted allocations derived from Module 35.',self.run_id]); self.conn.close(); d=pf.iloc[0].to_dict(); d['recommendation']=rec; return d
  except Exception as e:
   self.conn.execute("UPDATE module36_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",[utcnow(),str(e)[:1000],self.run_id]); self.conn.close(); raise
def run_module36(): return Module36Runner().run()
