from __future__ import annotations
import json, math, uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from crypto_platform.platform import load_all, connect
from crypto_platform.module34 import MODULE34_SCHEMA

MODULE35_SCHEMA=r"""
CREATE TABLE IF NOT EXISTS module35_runs(
 run_id VARCHAR PRIMARY KEY,source_module34_run_id VARCHAR,started_at_utc TIMESTAMPTZ,
 completed_at_utc TIMESTAMPTZ,status VARCHAR,allocation_rows INTEGER,candidate_rows INTEGER,
 correlation_rows INTEGER,current_recommendation VARCHAR,portfolio_confidence DOUBLE,
 portfolio_heat DOUBLE,diversification_score DOUBLE,expected_return_pct DOUBLE,
 expected_volatility_pct DOUBLE,expected_sharpe DOUBLE,cash_weight DOUBLE,
 validation_status VARCHAR,notes VARCHAR,platform_version VARCHAR);
CREATE TABLE IF NOT EXISTS m35_portfolio_allocations(
 run_id VARCHAR,observation_date DATE,asset_id VARCHAR,raw_target_weight DOUBLE,
 final_target_weight DOUBLE,current_weight DOUBLE,trade_weight DOUBLE,allocation_status VARCHAR,
 calculated_at_utc TIMESTAMPTZ,PRIMARY KEY(run_id,observation_date,asset_id));
CREATE TABLE IF NOT EXISTS m35_portfolio_candidates(
 run_id VARCHAR,candidate_id VARCHAR,method VARCHAR,expected_return_pct DOUBLE,
 expected_volatility_pct DOUBLE,expected_sharpe DOUBLE,diversification_score DOUBLE,
 concentration_score DOUBLE,turnover_pct DOUBLE,objective_score DOUBLE,selected BOOLEAN,
 weights_json VARCHAR,calculated_at_utc TIMESTAMPTZ,PRIMARY KEY(run_id,candidate_id));
CREATE TABLE IF NOT EXISTS m35_portfolio_correlations(
 run_id VARCHAR,observation_date DATE,asset_id_1 VARCHAR,asset_id_2 VARCHAR,
 correlation_90d DOUBLE,calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,observation_date,asset_id_1,asset_id_2));
CREATE TABLE IF NOT EXISTS m35_portfolio_statistics(
 run_id VARCHAR PRIMARY KEY,observation_date DATE,expected_return_pct DOUBLE,
 expected_volatility_pct DOUBLE,expected_sharpe DOUBLE,diversification_score DOUBLE,
 effective_assets DOUBLE,concentration_score DOUBLE,portfolio_heat DOUBLE,
 portfolio_confidence DOUBLE,cash_weight DOUBLE,recommendation VARCHAR,
 calculated_at_utc TIMESTAMPTZ);
CREATE OR REPLACE VIEW latest_m35_portfolio_allocations AS SELECT * FROM m35_portfolio_allocations WHERE run_id=(SELECT run_id FROM module35_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY final_target_weight DESC;
CREATE OR REPLACE VIEW latest_m35_portfolio_candidates AS SELECT * FROM m35_portfolio_candidates WHERE run_id=(SELECT run_id FROM module35_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY selected DESC,objective_score DESC;
CREATE OR REPLACE VIEW latest_m35_portfolio_correlations AS SELECT * FROM m35_portfolio_correlations WHERE run_id=(SELECT run_id FROM module35_runs ORDER BY started_at_utc DESC LIMIT 1);
CREATE OR REPLACE VIEW latest_m35_portfolio_statistics AS SELECT * FROM m35_portfolio_statistics WHERE run_id=(SELECT run_id FROM module35_runs ORDER BY started_at_utc DESC LIMIT 1);
"""
ASSETS=['bitcoin','ethereum','solana','chainlink','xrp','avalanche']
def utcnow(): return datetime.now(timezone.utc)
def norm(x):
 x=np.clip(np.asarray(x,float),0,None); s=x.sum(); return x/s if s>0 else np.repeat(1/len(x),len(x))
class Module35Runner:
 def __init__(self):
  self.settings,_=load_all(); self.conn=connect(self.settings); self.conn.execute(MODULE34_SCHEMA); self.conn.execute(MODULE35_SCHEMA)
  self.cfg=self.settings['module35']; self.run_id=str(uuid.uuid4()); self.started=utcnow()
  row=self.conn.execute("SELECT run_id FROM module34_runs WHERE status='SUCCESS' AND validation_status='PASSED' ORDER BY started_at_utc DESC LIMIT 1").fetchone()
  if row is None: raise RuntimeError('A passed Module 34 run is required.')
  self.source=str(row[0])
 def upsert(self,t,f):
  if f.empty:return
  self.conn.register('_s',f); c=','.join(f.columns); self.conn.execute(f'INSERT OR REPLACE INTO {t}({c}) SELECT {c} FROM _s'); self.conn.unregister('_s')
 def prices(self):
  f=self.conn.execute("SELECT asset_id,observation_date,price_usd FROM canonical_market_daily WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche') AND price_usd IS NOT NULL ORDER BY observation_date,asset_id").fetchdf(); f['observation_date']=pd.to_datetime(f['observation_date']); return f.pivot(index='observation_date',columns='asset_id',values='price_usd').reindex(columns=ASSETS).sort_index()
 def run(self):
  self.conn.execute("INSERT INTO module35_runs VALUES(?,?,?,NULL,'RUNNING',0,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'9.0.0')",[self.run_id,self.source,self.started])
  try:
   prices=self.prices(); r=prices.pct_change(fill_method=None).dropna(how='all').fillna(0).tail(int(self.cfg['lookback_days']))
   ex=self.conn.execute("SELECT observation_date,held_regime,target_risk_exposure FROM m34_execution_daily WHERE run_id=? ORDER BY observation_date DESC LIMIT 1",[self.source]).fetchdf().iloc[0]
   current_rows=self.conn.execute("SELECT asset_id,arg_max(executed_weight,observation_date) current_weight FROM m34_trade_ledger WHERE run_id=? GROUP BY asset_id",[self.source]).fetchdf(); cm=dict(zip(current_rows.asset_id,current_rows.current_weight)); current=np.array([float(cm.get(a,0)) for a in ASSETS])
   mu=r.mean().to_numpy()*365; cov=r.cov().to_numpy()*365; vol=np.sqrt(np.clip(np.diag(cov),1e-12,None)); risk=float(ex['target_risk_exposure'])
   methods={'INVERSE_VOLATILITY':norm(1/vol),'MOMENTUM':norm(np.clip((1+r).prod().to_numpy()-1,0,None)),'RISK_ADJUSTED':norm(np.clip(mu/vol,0,None)),'EQUAL_WEIGHT':np.repeat(1/6,6)}
   rows=[]; wm={}; maxw=float(self.cfg['max_asset_weight'])
   for i,(name,w) in enumerate(methods.items(),1):
    w=np.minimum(w,maxw); w=norm(w)*risk; er=float(w@mu); ev=float(np.sqrt(w@cov@w)); sh=er/ev if ev>0 else 0; conc=float(np.sum((w/max(w.sum(),1e-9))**2)); div=float(min((1/conc)/6,1)*100); turn=float(np.abs(w-current).sum()*100); obj=45*sh+.25*div-.05*turn-8*conc; cid=f'P{i:03d}'
    rows.append({'run_id':self.run_id,'candidate_id':cid,'method':name,'expected_return_pct':er*100,'expected_volatility_pct':ev*100,'expected_sharpe':sh,'diversification_score':div,'concentration_score':conc*100,'turnover_pct':turn,'objective_score':obj,'selected':False,'weights_json':json.dumps(dict(zip(ASSETS,map(float,w)))),'calculated_at_utc':utcnow()}); wm[cid]=w
   cand=pd.DataFrame(rows); bi=cand.objective_score.idxmax(); cand.loc[bi,'selected']=True; cid=str(cand.loc[bi,'candidate_id']); w=wm[cid]; sel=cand.loc[bi]; cash=max(1-w.sum(),0); total=np.append(w,cash); conc=float(np.sum(total**2)); eff=1/conc; div=float(min(eff/7,1)*100)
   confrow=self.conn.execute("SELECT clean_probability,model_agreement,historical_reliability,drift_status FROM latest_clean_regime_current LIMIT 1").fetchone(); conf=50.0
   if confrow:
    p,a,h,d=confrow; df=1 if d=='LOW' else .85 if d=='MODERATE' else .65; conf=100*(.4*float(p)+.25*float(a)+.25*float(h)+.1*df)
   heat=min(100,float(sel.expected_volatility_pct)/max(float(self.cfg['target_volatility_pct']),1e-9)*100*max(w.sum(),.01)); rec='AGGRESSIVE_ACCUMULATION' if conf>=80 and heat<75 else 'MODERATE_ACCUMULATION' if conf>=65 and heat<85 else 'HOLD' if conf>=50 else 'DEFENSIVE'; date=pd.to_datetime(ex['observation_date']).date()
   alloc=[]
   for a,x,c in zip(ASSETS,w,current): alloc.append({'run_id':self.run_id,'observation_date':date,'asset_id':a,'raw_target_weight':float(x),'final_target_weight':float(x),'current_weight':float(c),'trade_weight':float(x-c),'allocation_status':'INCREASE' if x>c+.01 else 'REDUCE' if x<c-.01 else 'HOLD','calculated_at_utc':utcnow()})
   alloc.append({'run_id':self.run_id,'observation_date':date,'asset_id':'CASH','raw_target_weight':cash,'final_target_weight':cash,'current_weight':max(1-current.sum(),0),'trade_weight':cash-max(1-current.sum(),0),'allocation_status':'HOLD','calculated_at_utc':utcnow()})
   corr=r.tail(90).corr(); cr=[{'run_id':self.run_id,'observation_date':date,'asset_id_1':a,'asset_id_2':b,'correlation_90d':float(corr.loc[a,b]),'calculated_at_utc':utcnow()} for a in ASSETS for b in ASSETS]
   stats=pd.DataFrame([{'run_id':self.run_id,'observation_date':date,'expected_return_pct':float(sel.expected_return_pct),'expected_volatility_pct':float(sel.expected_volatility_pct),'expected_sharpe':float(sel.expected_sharpe),'diversification_score':div,'effective_assets':eff,'concentration_score':conc*100,'portfolio_heat':heat,'portfolio_confidence':conf,'cash_weight':cash,'recommendation':rec,'calculated_at_utc':utcnow()}])
   self.upsert('m35_portfolio_allocations',pd.DataFrame(alloc)); self.upsert('m35_portfolio_candidates',cand); self.upsert('m35_portfolio_correlations',pd.DataFrame(cr)); self.upsert('m35_portfolio_statistics',stats)
   self.conn.execute("UPDATE module35_runs SET completed_at_utc=?,status='SUCCESS',allocation_rows=?,candidate_rows=?,correlation_rows=?,current_recommendation=?,portfolio_confidence=?,portfolio_heat=?,diversification_score=?,expected_return_pct=?,expected_volatility_pct=?,expected_sharpe=?,cash_weight=?,validation_status='PASSED',notes=? WHERE run_id=?",[utcnow(),len(alloc),len(cand),len(cr),rec,conf,heat,div,float(sel.expected_return_pct),float(sel.expected_volatility_pct),float(sel.expected_sharpe),cash,f'Selected {sel.method} portfolio.',self.run_id])
   self.conn.close(); return stats.iloc[0].to_dict()
  except Exception as e:
   self.conn.execute("UPDATE module35_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",[utcnow(),str(e)[:1000],self.run_id]); self.conn.close(); raise
def run_module35(): return Module35Runner().run()
