from __future__ import annotations
import math, uuid
from datetime import datetime, timezone
from typing import Any
import numpy as np
import pandas as pd
from crypto_platform.platform import load_all, connect
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module22 import MODULE22_SCHEMA

MODULE23_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module23_runs(
 run_id VARCHAR PRIMARY KEY, audited_module22_run_id VARCHAR,
 started_at_utc TIMESTAMPTZ, completed_at_utc TIMESTAMPTZ,
 status VARCHAR, periods_audited INTEGER, critical_findings INTEGER,
 warning_findings INTEGER, stored_return_pct DOUBLE,
 corrected_return_pct DOUBLE, btc_return_pct DOUBLE,
 corrected_excess_pct DOUBLE, bootstrap_probability_excess_positive DOUBLE,
 audit_status VARCHAR, promotion_status VARCHAR, notes VARCHAR,
 platform_version VARCHAR);
CREATE TABLE IF NOT EXISTS backtest_audit_findings(
 run_id VARCHAR, finding_id VARCHAR, severity VARCHAR,
 audit_category VARCHAR, finding_key VARCHAR, finding_value DOUBLE,
 threshold_value DOUBLE, affected_rows INTEGER, finding_message VARCHAR,
 remediation VARCHAR, calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,finding_id));
CREATE TABLE IF NOT EXISTS audited_portfolio_periods(
 run_id VARCHAR, source_module22_run_id VARCHAR, rebalance_date DATE,
 next_rebalance_date DATE, asset_count INTEGER, risky_weight DOUBLE,
 cash_weight DOUBLE, contribution_sum_pct DOUBLE,
 transaction_cost_pct DOUBLE, corrected_portfolio_return_pct DOUBLE,
 stored_portfolio_return_min_pct DOUBLE,
 stored_portfolio_return_max_pct DOUBLE,
 stored_vs_corrected_error_pct DOUBLE, btc_return_pct DOUBLE,
 equal_weight_core_return_pct DOUBLE, btc_cash_60_40_return_pct DOUBLE,
 inverse_volatility_return_pct DOUBLE, turnover_pct DOUBLE,
 period_valid BOOLEAN, calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,rebalance_date));
CREATE TABLE IF NOT EXISTS benchmark_audit_summary(
 run_id VARCHAR, benchmark_name VARCHAR, start_date DATE, end_date DATE,
 periods INTEGER, total_return_pct DOUBLE, annualized_return_pct DOUBLE,
 annualized_volatility_pct DOUBLE, sharpe_ratio DOUBLE,
 maximum_drawdown_pct DOUBLE, excess_vs_audited_portfolio_pct DOUBLE,
 calculated_at_utc TIMESTAMPTZ, PRIMARY KEY(run_id,benchmark_name));
CREATE TABLE IF NOT EXISTS performance_attribution_audit(
 run_id VARCHAR, attribution_component VARCHAR,
 cumulative_contribution_pct DOUBLE, average_period_contribution_pct DOUBLE,
 positive_periods_pct DOUBLE, explanation VARCHAR,
 calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,attribution_component));
CREATE TABLE IF NOT EXISTS drawdown_label_audit(
 run_id VARCHAR, forward_horizon_days INTEGER, selected_model VARCHAR,
 selected_auc DOUBLE, inverted_auc DOUBLE, selected_brier_score DOUBLE,
 selected_accuracy_pct DOUBLE, label_status VARCHAR,
 recommendation VARCHAR, calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,forward_horizon_days));
CREATE TABLE IF NOT EXISTS bootstrap_excess_audit(
 run_id VARCHAR PRIMARY KEY, simulations INTEGER, seed INTEGER,
 mean_excess_return_pct DOUBLE, median_excess_return_pct DOUBLE,
 lower_95_pct DOUBLE, upper_95_pct DOUBLE,
 probability_excess_positive DOUBLE,
 probability_excess_above_10pct DOUBLE,
 calculated_at_utc TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS audited_backtest_summary(
 run_id VARCHAR PRIMARY KEY, source_module22_run_id VARCHAR,
 start_date DATE, end_date DATE, periods INTEGER,
 stored_total_return_pct DOUBLE, corrected_total_return_pct DOUBLE,
 corrected_annualized_return_pct DOUBLE,
 corrected_annualized_volatility_pct DOUBLE,
 corrected_sharpe_ratio DOUBLE, corrected_maximum_drawdown_pct DOUBLE,
 btc_total_return_pct DOUBLE, btc_excess_pct DOUBLE,
 equal_weight_core_total_return_pct DOUBLE,
 btc_cash_60_40_total_return_pct DOUBLE,
 inverse_volatility_total_return_pct DOUBLE,
 tracking_error_pct DOUBLE, information_ratio DOUBLE,
 benchmark_win_rate_pct DOUBLE, average_cash_weight_pct DOUBLE,
 average_turnover_pct DOUBLE, transaction_cost_drag_pct DOUBLE,
 critical_findings INTEGER, warning_findings INTEGER,
 audit_status VARCHAR, promotion_status VARCHAR,
 promotion_reason VARCHAR, calculated_at_utc TIMESTAMPTZ);
CREATE OR REPLACE VIEW latest_backtest_audit_findings AS
 SELECT x.* FROM backtest_audit_findings x JOIN
 (SELECT run_id FROM module23_runs ORDER BY started_at_utc DESC LIMIT 1) r
 USING(run_id) ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'WARNING' THEN 2 ELSE 3 END;
CREATE OR REPLACE VIEW latest_audited_portfolio_periods AS
 SELECT x.* FROM audited_portfolio_periods x JOIN
 (SELECT run_id FROM module23_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id)
 ORDER BY rebalance_date;
CREATE OR REPLACE VIEW latest_benchmark_audit_summary AS
 SELECT x.* FROM benchmark_audit_summary x JOIN
 (SELECT run_id FROM module23_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
CREATE OR REPLACE VIEW latest_performance_attribution_audit AS
 SELECT x.* FROM performance_attribution_audit x JOIN
 (SELECT run_id FROM module23_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
CREATE OR REPLACE VIEW latest_drawdown_label_audit AS
 SELECT x.* FROM drawdown_label_audit x JOIN
 (SELECT run_id FROM module23_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
CREATE OR REPLACE VIEW latest_bootstrap_excess_audit AS
 SELECT x.* FROM bootstrap_excess_audit x JOIN
 (SELECT run_id FROM module23_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
CREATE OR REPLACE VIEW latest_audited_backtest_summary AS
 SELECT x.* FROM audited_backtest_summary x JOIN
 (SELECT run_id FROM module23_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
"""
CORE=['bitcoin','ethereum','solana','chainlink','xrp','avalanche']
def now(): return datetime.now(timezone.utc)
def sf(v,d=None): return d if v is None or pd.isna(v) else float(v)
def metrics(r,ppy):
 c=(1+r).cumprod(); total=float(c.iloc[-1]-1) if len(c) else 0.0
 years=max(len(r)/ppy,1/ppy); ann=(1+total)**(1/years)-1 if total>-1 else -1
 vol=float(r.std(ddof=1)*math.sqrt(ppy)) if len(r)>1 else 0.0
 sh=ann/vol if vol>0 else None; dd=float((c/c.cummax()-1).min()) if len(c) else 0.0
 return total,ann,vol,sh,dd
class Module23Runner:
 def __init__(self):
  self.settings,_=load_all(); self.conn=connect(self.settings)
  self.conn.execute(MODULE6_SCHEMA); self.conn.execute(MODULE22_SCHEMA); self.conn.execute(MODULE23_SCHEMA)
  self.cfg=self.settings['module23']; self.run_id=str(uuid.uuid4()); self.started=now()
  row=self.conn.execute("SELECT run_id FROM module22_runs WHERE status='SUCCESS' ORDER BY started_at_utc DESC LIMIT 1").fetchone()
  if not row: raise RuntimeError('No successful Module 22 run available.')
  self.source=str(row[0])
 def upsert(self,t,f):
  if f.empty:return
  self.conn.register('_s',f); cols=','.join(f.columns)
  self.conn.execute(f'INSERT OR REPLACE INTO {t}({cols}) SELECT {cols} FROM _s'); self.conn.unregister('_s')
 def finding(self,sev,cat,key,val,thr,n,msg,fix):
  return dict(run_id=self.run_id,finding_id=str(uuid.uuid4()),severity=sev,audit_category=cat,finding_key=key,finding_value=sf(val),threshold_value=sf(thr),affected_rows=int(n),finding_message=msg,remediation=fix,calculated_at_utc=now())
 def source_periods(self):
  f=self.conn.execute('SELECT * FROM intelligence_portfolio_periods WHERE run_id=? ORDER BY rebalance_date,asset_id',[self.source]).fetchdf()
  if f.empty: raise RuntimeError('No Module 22 periods found.')
  f['rebalance_date']=pd.to_datetime(f['rebalance_date']); f['next_rebalance_date']=pd.to_datetime(f['next_rebalance_date']); return f
 def prices(self):
  f=self.conn.execute("SELECT asset_id,observation_date,price_usd FROM canonical_market_daily WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche') AND price_usd IS NOT NULL ORDER BY observation_date,asset_id").fetchdf()
  f['observation_date']=pd.to_datetime(f['observation_date']); return f.pivot(index='observation_date',columns='asset_id',values='price_usd').sort_index()
 def verify(self,src,price):
  out=[]; finds=[]; tol=float(self.cfg['audit']['return_error_tolerance_pct'])
  for d,g in src.groupby('rebalance_date',sort=True):
   nds=g['next_rebalance_date'].drop_duplicates(); nd=nds.iloc[0]; valid=len(nds)==1 and nd>d
   if len(nds)!=1: finds.append(self.finding('CRITICAL','PERIOD_STRUCTURE','MULTIPLE_NEXT_DATES',len(nds),1,len(g),f'{d.date()} has multiple next dates.','Use one canonical next date.'))
   if nd<=d: finds.append(self.finding('CRITICAL','LOOKAHEAD_AND_TIME','NON_FORWARD_PERIOD',1,0,len(g),'Next date is not after rebalance date.','Require forward-only periods.'))
   if g['asset_id'].duplicated().any(): finds.append(self.finding('CRITICAL','PERIOD_STRUCTURE','DUPLICATE_ASSET_ROWS',g['asset_id'].duplicated().sum(),0,len(g),'Duplicate asset rows found.','Deduplicate period assets.')); valid=False
   wsum=float(g['target_weight'].sum())
   if abs(wsum-1)>1e-4: finds.append(self.finding('CRITICAL','PORTFOLIO_ACCOUNTING','WEIGHTS_NOT_ONE',wsum,1,len(g),'Weights do not sum to one.','Normalize weights.')); valid=False
   cost=float(g['transaction_cost_pct'].iloc[0]); contrib=float(g['contribution_pct'].sum()); corrected=contrib-cost
   stored_min=float(g['portfolio_period_return_pct'].min()); stored_max=float(g['portfolio_period_return_pct'].max()); err=stored_max-corrected
   if abs(err)>tol: finds.append(self.finding('CRITICAL','PORTFOLIO_ACCOUNTING','MAX_PARTIAL_RETURN_USED',err,tol,1,f'{d.date()} stored MAX partial={stored_max:.4f}% vs corrected={corrected:.4f}%.','Sum all contributions and subtract cost once.'))
   realized={a:(float(price.at[nd,a])/float(price.at[d,a])-1)*100 if d in price.index and nd in price.index else np.nan for a in CORE}
   independent=sum(float(r.target_weight)*(0 if r.asset_id=='CASH' else realized[r.asset_id]) for _,r in g.iterrows())-cost
   if abs(independent-corrected)>tol: finds.append(self.finding('CRITICAL','PRICE_RECONCILIATION','CONTRIBUTION_PRICE_MISMATCH',independent-corrected,tol,1,'Stored contributions do not match canonical prices.','Recompute from weights and prices.')); valid=False
   btc=realized['bitcoin']; eq=float(np.nanmean(list(realized.values()))); trailing=price.loc[:d].pct_change(fill_method=None).tail(90); vol=trailing[CORE].std().replace(0,np.nan); iw=(1/vol); iw=iw/iw.sum(); iv=float(sum(iw.get(a,0)*realized[a] for a in CORE))
   cash=float(g.loc[g.asset_id=='CASH','target_weight'].sum())
   out.append(dict(run_id=self.run_id,source_module22_run_id=self.source,rebalance_date=d.date(),next_rebalance_date=nd.date(),asset_count=int(g.asset_id.nunique()),risky_weight=1-cash,cash_weight=cash,contribution_sum_pct=contrib,transaction_cost_pct=cost,corrected_portfolio_return_pct=corrected,stored_portfolio_return_min_pct=stored_min,stored_portfolio_return_max_pct=stored_max,stored_vs_corrected_error_pct=err,btc_return_pct=btc,equal_weight_core_return_pct=eq,btc_cash_60_40_return_pct=.6*btc,inverse_volatility_return_pct=iv,turnover_pct=float(g.turnover_pct.iloc[0]),period_valid=valid,calculated_at_utc=now()))
  p=pd.DataFrame(out).sort_values('rebalance_date')
  zeros=int(np.isclose(p.corrected_portfolio_return_pct,0,atol=1e-12).sum())
  if zeros: finds.append(self.finding('WARNING','RETURN_PLAUSIBILITY','EXACT_ZERO_PERIODS',zeros,0,zeros,'Exact-zero audited periods found.','Verify active weights and prices.'))
  return p,pd.DataFrame(finds)
 def benchmarks(self,p):
  ppy=365/float(self.cfg['audit']['expected_rebalance_days']); audited=float((1+p.corrected_portfolio_return_pct/100).prod()-1); rows=[]
  for n,col in [('AUDITED_PORTFOLIO','corrected_portfolio_return_pct'),('BITCOIN','btc_return_pct'),('EQUAL_WEIGHT_CORE','equal_weight_core_return_pct'),('BTC_CASH_60_40','btc_cash_60_40_return_pct'),('INVERSE_VOLATILITY_CORE','inverse_volatility_return_pct')]:
   t,a,v,s,d=metrics(p[col]/100,ppy); rows.append(dict(run_id=self.run_id,benchmark_name=n,start_date=p.rebalance_date.min(),end_date=p.next_rebalance_date.max(),periods=len(p),total_return_pct=t*100,annualized_return_pct=a*100,annualized_volatility_pct=v*100,sharpe_ratio=s,maximum_drawdown_pct=d*100,excess_vs_audited_portfolio_pct=(t-audited)*100,calculated_at_utc=now()))
  return pd.DataFrame(rows)
 def attribution(self,p):
  actual=p.corrected_portfolio_return_pct; btc=p.btc_return_pct; market=p.risky_weight*btc; cost=-p.transaction_cost_pct; selection=actual-cost-market; cash=market-btc; residual=actual-(market+selection+cash+cost)
  rows=[]
  for k,s,e in [('MARKET_EXPOSURE',market,'Risky exposure applied to BTC return.'),('DIVERSIFICATION_AND_SELECTION',selection,'Asset selection and diversification versus BTC exposure.'),('CASH_TIMING',cash,'Effect of holding less than 100% BTC.'),('TRANSACTION_COSTS',cost,'Explicit trading-cost drag.'),('ATTRIBUTION_RESIDUAL',residual,'Additive reconciliation residual.')]: rows.append(dict(run_id=self.run_id,attribution_component=k,cumulative_contribution_pct=float(s.sum()),average_period_contribution_pct=float(s.mean()),positive_periods_pct=float((s>0).mean()*100),explanation=e,calculated_at_utc=now()))
  return pd.DataFrame(rows)
 def labels(self):
  f=self.conn.execute("SELECT forward_horizon_days,model_name,roc_auc,brier_score,accuracy_pct FROM intelligence_model_comparison WHERE run_id=? AND target_key='DRAWDOWN_20' AND selected_model=TRUE ORDER BY forward_horizon_days",[self.source]).fetchdf(); rows=[]
  for _,r in f.iterrows():
   auc=sf(r.roc_auc,.5); inv=1-auc
   if auc<.5 and inv>=float(self.cfg['labels']['minimum_inverted_auc']): st='POSSIBLY_INVERTED'; rec='Inspect class encoding and probability column; test 1-p.'
   elif auc<float(self.cfg['labels']['minimum_acceptable_auc']): st='WEAK'; rec='Do not use for allocation until target/features are revised.'
   else: st='ACCEPTABLE'; rec='Retain for further shadow validation.'
   rows.append(dict(run_id=self.run_id,forward_horizon_days=int(r.forward_horizon_days),selected_model=r.model_name,selected_auc=auc,inverted_auc=inv,selected_brier_score=sf(r.brier_score),selected_accuracy_pct=sf(r.accuracy_pct),label_status=st,recommendation=rec,calculated_at_utc=now()))
  return pd.DataFrame(rows)
 def bootstrap(self,p):
  sims=int(self.cfg['bootstrap']['simulations']); seed=int(self.cfg['bootstrap']['seed']); rng=np.random.default_rng(seed); pr=p.corrected_portfolio_return_pct.to_numpy()/100; br=p.btc_return_pct.to_numpy()/100; n=len(p); ex=np.empty(sims)
  for i in range(sims):
   idx=rng.integers(0,n,n); ex[i]=((np.prod(1+pr[idx])-1)-(np.prod(1+br[idx])-1))*100
  return pd.DataFrame([dict(run_id=self.run_id,simulations=sims,seed=seed,mean_excess_return_pct=float(ex.mean()),median_excess_return_pct=float(np.median(ex)),lower_95_pct=float(np.quantile(ex,.025)),upper_95_pct=float(np.quantile(ex,.975)),probability_excess_positive=float((ex>0).mean()),probability_excess_above_10pct=float((ex>10).mean()),calculated_at_utc=now())])
 def summary(self,p,b,f,boot):
  ppy=365/float(self.cfg['audit']['expected_rebalance_days']); pr=p.corrected_portfolio_return_pct/100; br=p.btc_return_pct/100; t,a,v,s,d=metrics(pr,ppy); bt,ba,_,_,_=metrics(br,ppy); act=pr-br; te=float(act.std(ddof=1)*math.sqrt(ppy)) if len(act)>1 else 0; ir=(a-ba)/te if te>0 else None
  stored=self.conn.execute('SELECT total_return_pct FROM intelligence_portfolio_summary WHERE run_id=?',[self.source]).fetchone(); stored=sf(stored[0]) if stored else None
  crit=int((f.severity=='CRITICAL').sum()) if not f.empty else 0; warn=int((f.severity=='WARNING').sum()) if not f.empty else 0; prob=float(boot.probability_excess_positive.iloc[0])
  passed=crit==0 and prob>=float(self.cfg['promotion']['minimum_probability_excess_positive']) and (t-bt)*100>=float(self.cfg['promotion']['minimum_corrected_excess_pct']) and ir is not None and ir>=float(self.cfg['promotion']['minimum_information_ratio'])
  if crit: ast='FAILED_CRITICAL'; pst='REVOKED_PENDING_FIX'; reason='Critical accounting/model findings invalidate the v5.1 promotion result.'
  elif passed: ast='PASSED'; pst='AUDIT_VALIDATED_CANDIDATE'; reason='Corrected accounting and bootstrap evidence cleared all thresholds.'
  else: ast='FAILED_EVIDENCE'; pst='RESEARCH_ONLY'; reason='Corrected performance did not clear all audit thresholds.'
  get=lambda n: float(b.loc[b.benchmark_name==n,'total_return_pct'].iloc[0])
  return pd.DataFrame([dict(run_id=self.run_id,source_module22_run_id=self.source,start_date=p.rebalance_date.min(),end_date=p.next_rebalance_date.max(),periods=len(p),stored_total_return_pct=stored,corrected_total_return_pct=t*100,corrected_annualized_return_pct=a*100,corrected_annualized_volatility_pct=v*100,corrected_sharpe_ratio=s,corrected_maximum_drawdown_pct=d*100,btc_total_return_pct=bt*100,btc_excess_pct=(t-bt)*100,equal_weight_core_total_return_pct=get('EQUAL_WEIGHT_CORE'),btc_cash_60_40_total_return_pct=get('BTC_CASH_60_40'),inverse_volatility_total_return_pct=get('INVERSE_VOLATILITY_CORE'),tracking_error_pct=te*100,information_ratio=ir,benchmark_win_rate_pct=float((pr>br).mean()*100),average_cash_weight_pct=float(p.cash_weight.mean()*100),average_turnover_pct=float(p.turnover_pct.mean()),transaction_cost_drag_pct=float(p.transaction_cost_pct.sum()),critical_findings=crit,warning_findings=warn,audit_status=ast,promotion_status=pst,promotion_reason=reason,calculated_at_utc=now())])
 def run(self):
  self.conn.execute("UPDATE module23_runs SET status='FAILED',completed_at_utc=?,notes=COALESCE(notes,'')||'; interrupted prior run' WHERE status='RUNNING'",[now()]); self.conn.execute("INSERT INTO module23_runs VALUES(?,?,?,NULL,'RUNNING',0,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'5.1.1')",[self.run_id,self.source,self.started])
  try:
   src=self.source_periods(); price=self.prices(); p,f=self.verify(src,price); b=self.benchmarks(p); a=self.attribution(p); l=self.labels(); boot=self.bootstrap(p)
   extra=[]
   for _,r in l.iterrows():
    if r.label_status in {'POSSIBLY_INVERTED','WEAK'}: extra.append(self.finding('CRITICAL' if r.label_status=='POSSIBLY_INVERTED' else 'WARNING','MODEL_LABELS',f'DRAWDOWN_{int(r.forward_horizon_days)}D_{r.label_status}',r.selected_auc,self.cfg['labels']['minimum_acceptable_auc'],1,f'Selected drawdown model AUC={r.selected_auc:.3f}.',r.recommendation))
   if extra: f=pd.concat([f,pd.DataFrame(extra)],ignore_index=True)
   s=self.summary(p,b,f,boot)
   for t,x in [('audited_portfolio_periods',p),('backtest_audit_findings',f),('benchmark_audit_summary',b),('performance_attribution_audit',a),('drawdown_label_audit',l),('bootstrap_excess_audit',boot),('audited_backtest_summary',s)]: self.upsert(t,x)
   r=s.iloc[0]; bp=float(boot.probability_excess_positive.iloc[0]); notes='Module 23 audit supersedes Module 22 promotion flag.'
   self.conn.execute("UPDATE module23_runs SET completed_at_utc=?,status='SUCCESS',periods_audited=?,critical_findings=?,warning_findings=?,stored_return_pct=?,corrected_return_pct=?,btc_return_pct=?,corrected_excess_pct=?,bootstrap_probability_excess_positive=?,audit_status=?,promotion_status=?,notes=? WHERE run_id=?",[now(),len(p),int(r.critical_findings),int(r.warning_findings),sf(r.stored_total_return_pct),float(r.corrected_total_return_pct),float(r.btc_total_return_pct),float(r.btc_excess_pct),bp,r.audit_status,r.promotion_status,notes,self.run_id]); self.conn.close()
   return dict(run_id=self.run_id,status='SUCCESS',source_module22_run_id=self.source,periods_audited=len(p),critical_findings=int(r.critical_findings),warning_findings=int(r.warning_findings),stored_return_pct=sf(r.stored_total_return_pct),corrected_return_pct=float(r.corrected_total_return_pct),btc_return_pct=float(r.btc_total_return_pct),corrected_excess_pct=float(r.btc_excess_pct),bootstrap_probability_excess_positive=bp,audit_status=r.audit_status,promotion_status=r.promotion_status)
  except Exception as e:
   self.conn.execute("UPDATE module23_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",[now(),str(e)[:1000],self.run_id]); self.conn.close(); raise
def run_module23(): return Module23Runner().run()
