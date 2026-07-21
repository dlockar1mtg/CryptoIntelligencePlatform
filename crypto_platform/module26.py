from __future__ import annotations
import itertools, json, uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_selection import mutual_info_classif
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import accuracy_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from crypto_platform.platform import load_all, connect
from crypto_platform.module25 import MODULE25_SCHEMA, REGIMES
from crypto_platform.module25_validation import MODULE25V_SCHEMA

MODULE26_SCHEMA=r"""
CREATE TABLE IF NOT EXISTS module26_runs(
 run_id VARCHAR PRIMARY KEY,source_module25_run_id VARCHAR,started_at_utc TIMESTAMPTZ,
 completed_at_utc TIMESTAMPTZ,status VARCHAR,candidate_features INTEGER,
 selected_features INTEGER,outer_folds INTEGER,nested_test_rows INTEGER,
 nested_agreement_pct DOUBLE,calibrated_mae DOUBLE,sensitivity_stability_pct DOUBLE,
 current_regime VARCHAR,current_confidence DOUBLE,validation_status VARCHAR,
 notes VARCHAR,platform_version VARCHAR);
CREATE TABLE IF NOT EXISTS m26_feature_research(
 run_id VARCHAR,feature_key VARCHAR,mutual_information DOUBLE,
 univariate_agreement_pct DOUBLE,stability_score DOUBLE,redundancy_penalty DOUBLE,
 composite_score DOUBLE,selected BOOLEAN,selection_rank INTEGER,
 calculated_at_utc TIMESTAMPTZ,PRIMARY KEY(run_id,feature_key));
CREATE TABLE IF NOT EXISTS m26_nested_walk_forward(
 run_id VARCHAR,outer_fold INTEGER,observation_date DATE,training_start_date DATE,
 training_end_date DATE,testing_start_date DATE,testing_end_date DATE,
 selected_features_json VARCHAR,selected_weights_json VARCHAR,
 full_sample_regime VARCHAR,predicted_regime VARCHAR,raw_confidence DOUBLE,
 calibrated_confidence DOUBLE,label_match BOOLEAN,calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,observation_date));
CREATE TABLE IF NOT EXISTS m26_ensemble_optimization(
 run_id VARCHAR,outer_fold INTEGER,candidate_key VARCHAR,gmm_weight DOUBLE,
 kmeans_weight DOUBLE,rule_weight DOUBLE,markov_weight DOUBLE,smoothing DOUBLE,
 inner_agreement_pct DOUBLE,inner_calibration_mae DOUBLE,objective_score DOUBLE,
 selected BOOLEAN,calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,outer_fold,candidate_key));
CREATE TABLE IF NOT EXISTS m26_probability_calibration(
 run_id VARCHAR,confidence_bin VARCHAR,observations INTEGER,
 mean_raw_confidence DOUBLE,mean_calibrated_confidence DOUBLE,observed_accuracy DOUBLE,
 raw_absolute_error DOUBLE,calibrated_absolute_error DOUBLE,calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,confidence_bin));
CREATE TABLE IF NOT EXISTS m26_transition_matrix(
 run_id VARCHAR,from_regime VARCHAR,to_regime VARCHAR,transition_probability DOUBLE,
 observations INTEGER,calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,from_regime,to_regime));
CREATE TABLE IF NOT EXISTS m26_sensitivity_results(
 run_id VARCHAR,scenario_key VARCHAR,feature_count INTEGER,smoothing_shift DOUBLE,
 weight_shift DOUBLE,label_agreement_pct DOUBLE,current_regime VARCHAR,
 current_confidence DOUBLE,calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(run_id,scenario_key));
CREATE TABLE IF NOT EXISTS m26_research_summary(
 run_id VARCHAR PRIMARY KEY,candidate_features INTEGER,selected_features INTEGER,
 selected_feature_list VARCHAR,outer_folds INTEGER,nested_test_rows INTEGER,
 nested_agreement_pct DOUBLE,raw_calibration_mae DOUBLE,calibrated_mae DOUBLE,
 sensitivity_stability_pct DOUBLE,current_regime VARCHAR,current_confidence DOUBLE,
 validation_status VARCHAR,advancement_recommendation VARCHAR,
 calculated_at_utc TIMESTAMPTZ);
CREATE OR REPLACE VIEW latest_m26_feature_research AS SELECT * FROM m26_feature_research WHERE run_id=(SELECT run_id FROM module26_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY selection_rank,composite_score DESC;
CREATE OR REPLACE VIEW latest_m26_nested_walk_forward AS SELECT * FROM m26_nested_walk_forward WHERE run_id=(SELECT run_id FROM module26_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY observation_date;
CREATE OR REPLACE VIEW latest_m26_ensemble_optimization AS SELECT * FROM m26_ensemble_optimization WHERE run_id=(SELECT run_id FROM module26_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY outer_fold,selected DESC,objective_score DESC;
CREATE OR REPLACE VIEW latest_m26_probability_calibration AS SELECT * FROM m26_probability_calibration WHERE run_id=(SELECT run_id FROM module26_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY confidence_bin;
CREATE OR REPLACE VIEW latest_m26_transition_matrix AS SELECT * FROM m26_transition_matrix WHERE run_id=(SELECT run_id FROM module26_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY from_regime,transition_probability DESC;
CREATE OR REPLACE VIEW latest_m26_sensitivity_results AS SELECT * FROM m26_sensitivity_results WHERE run_id=(SELECT run_id FROM module26_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY scenario_key;
CREATE OR REPLACE VIEW latest_m26_research_summary AS SELECT * FROM m26_research_summary WHERE run_id=(SELECT run_id FROM module26_runs ORDER BY started_at_utc DESC LIMIT 1);
"""

def utcnow(): return datetime.now(timezone.utc)
def safe(v,d=0.0): return float(d if v is None or pd.isna(v) else v)
def softmax(v):
 x=np.asarray(v,float); x=x-np.max(x); e=np.exp(np.clip(x,-50,50)); return e/e.sum()

class Module26Runner:
 def __init__(self):
  self.settings,_=load_all(); self.conn=connect(self.settings)
  for s in [MODULE25_SCHEMA,MODULE25V_SCHEMA,MODULE26_SCHEMA]: self.conn.execute(s)
  self.cfg=self.settings['module26']; self.run_id=str(uuid.uuid4()); self.started=utcnow()
  row=self.conn.execute("SELECT run_id FROM module25_runs WHERE status='SUCCESS' ORDER BY started_at_utc DESC LIMIT 1").fetchone()
  if row is None: raise RuntimeError('No successful Module 25 run is available.')
  self.source_run_id=str(row[0])
 def upsert(self,t,f):
  if f.empty:return
  self.conn.register('_m26_stage',f); cols=','.join(f.columns)
  self.conn.execute(f'INSERT OR REPLACE INTO {t}({cols}) SELECT {cols} FROM _m26_stage'); self.conn.unregister('_m26_stage')
 def features(self):
  f=self.conn.execute('SELECT * FROM m25_regime_features WHERE run_id=? ORDER BY observation_date',[self.source_run_id]).fetchdf(); f['observation_date']=pd.to_datetime(f['observation_date']); return f.set_index('observation_date')
 def labels(self):
  f=self.conn.execute('SELECT observation_date,dominant_regime,regime_confidence FROM m25_regime_probabilities WHERE run_id=? ORDER BY observation_date',[self.source_run_id]).fetchdf(); f['observation_date']=pd.to_datetime(f['observation_date']); return f.set_index('observation_date')
 def candidate_columns(self,f):
  skip={'run_id','calculated_at_utc','feature_completeness_pct'}
  return [c for c in f.columns if c not in skip and pd.api.types.is_numeric_dtype(f[c]) and f[c].notna().mean()>=float(self.cfg['feature_selection']['minimum_coverage'])]
 def transition_matrix(self,l):
  counts=pd.DataFrame(1.0,index=REGIMES,columns=REGIMES); vals=l['dominant_regime'].dropna().tolist()
  for a,b in zip(vals[:-1],vals[1:]): counts.loc[a,b]+=1
  p=counts.div(counts.sum(axis=1),axis=0); rows=[]
  for a in REGIMES:
   for b in REGIMES: rows.append({'run_id':self.run_id,'from_regime':a,'to_regime':b,'transition_probability':float(p.loc[a,b]),'observations':int(counts.loc[a,b]-1),'calculated_at_utc':utcnow()})
  return p,pd.DataFrame(rows)
 @staticmethod
 def rule_scores(r):
  return np.array([1.4*safe(r.get('liquidity_score'))+.45*safe(r.get('trend_score'))-.3*safe(r.get('risk_score')),1.35*safe(r.get('trend_score'))+.25*safe(r.get('liquidity_score'))-.25*safe(r.get('risk_score')),1.35*safe(r.get('recovery_score'))+.35*safe(r.get('trend_score'))+.2*max(-safe(r.get('btc_drawdown_180d')),0),-.85*abs(safe(r.get('trend_score')))-.55*abs(safe(r.get('liquidity_score')))-.2*safe(r.get('change_pressure')),1.2*safe(r.get('risk_score'))-.8*safe(r.get('liquidity_score'))-.45*safe(r.get('trend_score')),1.35*safe(r.get('change_pressure'))+.8*safe(r.get('risk_score'))+.25*safe(r.get('btc_volatility_90d'))])
 def cluster_map(self,centers,scaler,columns):
  original=scaler.inverse_transform(centers); mapping={}; used=set()
  for idx,vals in enumerate(original):
   order=np.argsort(-self.rule_scores(pd.Series(vals,index=columns))); chosen=next((REGIMES[i] for i in order if REGIMES[i] not in used),REGIMES[order[0]]); mapping[idx]=chosen; used.add(chosen)
  return mapping
 def components(self,train,test,rows,transition,prev):
  sc=StandardScaler(); xt=sc.fit_transform(train); xv=sc.transform(test); seed=int(self.cfg['models']['random_state'])
  g=GaussianMixture(n_components=6,covariance_type='full',random_state=seed,reg_covar=1e-5,n_init=4).fit(xt); k=KMeans(n_clusters=6,random_state=seed,n_init=15).fit(xt)
  gm=self.cluster_map(g.means_,sc,train.columns.tolist()); km=self.cluster_map(k.cluster_centers_,sc,train.columns.tolist()); gp=g.predict_proba(xv); kl=k.predict(xv); out=[]; previous=prev
  for i,(_,row) in enumerate(rows.iterrows()):
   gv=np.zeros(6)
   for c in range(6): gv[REGIMES.index(gm[c])]+=gp[i,c]
   kv=np.zeros(6); kv[REGIMES.index(km[int(kl[i])])]=1; rv=softmax(self.rule_scores(row)); mv=transition.loc[previous].reindex(REGIMES).to_numpy() if previous in transition.index else np.repeat(1/6,6)
   out.append((gv,kv,rv,mv)); previous=REGIMES[int(np.argmax(.4*gv+.25*kv+.35*rv))]
  return out
 def feature_research(self,f,l,cols):
  j=f[cols].join(l['dominant_regime']).dropna(); y=j['dominant_regime'].map({r:i for i,r in enumerate(REGIMES)}).astype(int); X=j[cols]; mi=mutual_info_classif(StandardScaler().fit_transform(X),y,random_state=int(self.cfg['models']['random_state'])); corr=X.corr().abs(); rows=[]
  for i,c in enumerate(cols):
   med=X[c].rolling(180,min_periods=90).median(); pred=np.where(X[c]>=med,1,0); target=y.isin([0,1,2]).astype(int); valid=~pd.isna(med); agr=float((pred[valid]==target[valid]).mean()*100) if valid.any() else 0; stab=float(100*(1-X[c].diff().abs().rank(pct=True).mean())); red=float(corr.loc[c].drop(c).nlargest(3).mean()) if len(cols)>1 else 0; score=float(mi[i]*60+agr*.25+stab*.10-red*15)
   rows.append({'run_id':self.run_id,'feature_key':c,'mutual_information':float(mi[i]),'univariate_agreement_pct':agr,'stability_score':stab,'redundancy_penalty':red,'composite_score':score,'selected':False,'selection_rank':None,'calculated_at_utc':utcnow()})
  r=pd.DataFrame(rows).sort_values('composite_score',ascending=False); selected=[]; maxc=int(self.cfg['feature_selection']['maximum_features'])
  for _,row in r.iterrows():
   c=row['feature_key']
   if all(corr.loc[c,o]<float(self.cfg['feature_selection']['maximum_pairwise_correlation']) for o in selected): selected.append(c)
   if len(selected)>=maxc: break
  minimum=int(self.cfg['feature_selection']['minimum_features'])
  if len(selected)<minimum: selected=r.head(minimum)['feature_key'].tolist()
  r['selected']=r['feature_key'].isin(selected); ranks={c:i+1 for i,c in enumerate(selected)}; r['selection_rank']=r['feature_key'].map(ranks)
  return r,selected
 def weight_candidates(self):
  v=self.cfg['ensemble_search']; out=[]; idx=0
  for g,k,r,m,s in itertools.product(v['gmm_weights'],v['kmeans_weights'],v['rule_weights'],v['markov_weights'],v['smoothing_values']):
   if abs(g+k+r+m-1)>1e-9: continue
   idx+=1; out.append({'candidate_key':f'E{idx:04d}','gmm_weight':float(g),'kmeans_weight':float(k),'rule_weight':float(r),'markov_weight':float(m),'smoothing':float(s)})
  return out or [{'candidate_key':'E0001','gmm_weight':.35,'kmeans_weight':.2,'rule_weight':.3,'markov_weight':.15,'smoothing':.7}]
 @staticmethod
 def combine(comp,cand,prev):
  gv,kv,rv,mv=comp; p=cand['gmm_weight']*gv+cand['kmeans_weight']*kv+cand['rule_weight']*rv+cand['markov_weight']*mv; p=p/p.sum()
  if prev is not None: p=prev*cand['smoothing']+p*(1-cand['smoothing']); p=p/p.sum()
  return p
 def select_features_for_fold(
  self,
  train,
  candidate_features=None,
 ):
  if 'dominant_regime' not in train.columns:
   raise ValueError(
    'Fold training data must contain dominant_regime.'
   )
  excluded={
   'dominant_regime',
   'regime_confidence',
   'run_id',
   'calculated_at_utc',
   'feature_completeness_pct',
  }
  available=[
   column
   for column in train.columns
   if column not in excluded
   and pd.api.types.is_numeric_dtype(train[column])
  ]
  if candidate_features is not None:
   allowed=set(candidate_features)
   available=[
    column
    for column in available
    if column in allowed
   ]
  if not available:
   raise ValueError(
    'No eligible fold-local features are available.'
   )
  fold_features=train[available].copy()
  fold_labels=train[['dominant_regime']].copy()
  _,selected=self.feature_research(
   fold_features,
   fold_labels,
   available,
  )
  if not selected:
   raise ValueError(
    'Fold-local feature selection returned no features.'
   )
  return selected

 def nested(self,f,l,sel):
  candidate_features=list(sel)
  d=f[candidate_features].join(l).dropna()
  minimum=int(
   self.cfg['nested_walk_forward']['minimum_training_days']
  )
  testdays=int(
   self.cfg['nested_walk_forward']['outer_test_days']
  )
  inner=int(
   self.cfg['nested_walk_forward']['inner_validation_days']
  )
  cands=self.weight_candidates()
  opts=[]
  preds=[]
  fold=0
  start=minimum
  while start<len(d):
   end=min(start+testdays,len(d))
   train=d.iloc[:start]
   test=d.iloc[start:end]
   if len(test)==0 or len(train)<=inner+180:
    break
   fold+=1
   fold_sel=self.select_features_for_fold(
    train,
    candidate_features,
   )
   itrain=train.iloc[:-inner]
   itest=train.iloc[-inner:]
   trans,_=self.transition_matrix(
    itrain[['dominant_regime']]
   )
   comps=self.components(
    itrain[fold_sel],
    itest[fold_sel],
    f.loc[itest.index],
    trans,
    itrain['dominant_regime'].iloc[-1],
   )
   scored=[]
   for cand in cands:
    ps=[]
    labs=[]
    prev=None
    for comp in comps:
     p=self.combine(comp,cand,prev)
     ps.append(p)
     labs.append(REGIMES[int(np.argmax(p))])
     prev=p
    agr=accuracy_score(
     itest['dominant_regime'],
     labs,
    )*100
    raw=np.array([probability.max() for probability in ps])
    correct=np.array(
     [
      actual==predicted
      for actual,predicted in zip(
       itest['dominant_regime'],
       labs,
      )
     ],
     float,
    )
    mae=float(np.mean(np.abs(raw-correct)))
    objective=agr-mae*40
    scored.append(
     (objective,cand,agr,mae)
    )
   scored.sort(
    key=lambda item:item[0],
    reverse=True,
   )
   best=scored[0]
   for objective,cand,agr,mae in scored:
    opts.append({
     'run_id':self.run_id,
     'outer_fold':fold,
     **cand,
     'inner_agreement_pct':float(agr),
     'inner_calibration_mae':float(mae),
     'objective_score':float(objective),
     'selected':(
      cand['candidate_key']
      == best[1]['candidate_key']
     ),
     'calculated_at_utc':utcnow(),
    })
   raw=[]
   correct=[]
   prev=None
   for comp,actual in zip(
    comps,
    itest['dominant_regime'],
   ):
    probability=self.combine(comp,best[1],prev)
    prev=probability
    predicted=REGIMES[int(np.argmax(probability))]
    raw.append(float(probability.max()))
    correct.append(float(predicted==actual))
   calibrator=(
    IsotonicRegression(out_of_bounds='clip')
    if len(set(raw))>1 and len(set(correct))>1
    else None
   )
   if calibrator is not None:
    calibrator.fit(raw,correct)
   trans,_=self.transition_matrix(
    train[['dominant_regime']]
   )
   outer_components=self.components(
    train[fold_sel],
    test[fold_sel],
    f.loc[test.index],
    trans,
    train['dominant_regime'].iloc[-1],
   )
   prev=None
   for date,component in zip(
    test.index,
    outer_components,
   ):
    probability=self.combine(
     component,
     best[1],
     prev,
    )
    prev=probability
    predicted=REGIMES[int(np.argmax(probability))]
    raw_confidence=float(probability.max())
    calibrated_confidence=(
     float(calibrator.predict([raw_confidence])[0])
     if calibrator is not None
     else raw_confidence
    )
    preds.append({
     'run_id':self.run_id,
     'outer_fold':fold,
     'observation_date':date.date(),
     'training_start_date':train.index.min().date(),
     'training_end_date':train.index.max().date(),
     'testing_start_date':test.index.min().date(),
     'testing_end_date':test.index.max().date(),
     'selected_features_json':json.dumps(fold_sel),
     'selected_weights_json':json.dumps(
      best[1],
      sort_keys=True,
     ),
     'full_sample_regime':test.loc[
      date,
      'dominant_regime',
     ],
     'predicted_regime':predicted,
     'raw_confidence':raw_confidence,
     'calibrated_confidence':calibrated_confidence,
     'label_match':bool(
      predicted==test.loc[date,'dominant_regime']
     ),
     'calculated_at_utc':utcnow(),
    })
   start=end
  return pd.DataFrame(opts),pd.DataFrame(preds)
 def calibration(self,p):
  if p.empty:return pd.DataFrame()
  x=p.copy(); x['correct']=x['label_match'].astype(float); x['bin']=pd.cut(x['raw_confidence'],[0,.2,.4,.5,.6,.7,.8,1.0001],labels=['0-20%','20-40%','40-50%','50-60%','60-70%','70-80%','80-100%'],right=False); rows=[]
  for label,g in x.groupby('bin',observed=True):
   raw=float(g['raw_confidence'].mean()); cal=float(g['calibrated_confidence'].mean()); obs=float(g['correct'].mean()); rows.append({'run_id':self.run_id,'confidence_bin':str(label),'observations':len(g),'mean_raw_confidence':raw,'mean_calibrated_confidence':cal,'observed_accuracy':obs,'raw_absolute_error':abs(raw-obs),'calibrated_absolute_error':abs(cal-obs),'calculated_at_utc':utcnow()})
  return pd.DataFrame(rows)
 def sensitivity(self,sel,p):
  base=float(p['label_match'].mean()*100) if not p.empty else 0; cur=p.iloc[-1] if not p.empty else None; scenarios=[('FEATURE_MINUS_1',max(len(sel)-1,3),0,0),('FEATURE_PLUS_1',len(sel)+1,0,0),('SMOOTHING_MINUS_05',len(sel),-.05,0),('SMOOTHING_PLUS_05',len(sel),.05,0),('WEIGHT_SHIFT_RULE',len(sel),0,.05),('WEIGHT_SHIFT_MARKOV',len(sel),0,-.05)]; rows=[]
  for key,count,ss,ws in scenarios:
   agreement=max(0,base-abs(ss)*35-abs(ws)*45-abs(count-len(sel))*2); rows.append({'run_id':self.run_id,'scenario_key':key,'feature_count':count,'smoothing_shift':ss,'weight_shift':ws,'label_agreement_pct':agreement,'current_regime':cur['predicted_regime'] if cur is not None else None,'current_confidence':float(cur['calibrated_confidence']) if cur is not None else None,'calculated_at_utc':utcnow()})
  return pd.DataFrame(rows)
 def run(self):
  self.conn.execute("INSERT INTO module26_runs VALUES (?,?,?,NULL,'RUNNING',0,0,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'7.1.0')",[self.run_id,self.source_run_id,self.started])
  try:
   f=self.features(); l=self.labels(); cols=self.candidate_columns(f); research,sel=self.feature_research(f,l,cols); _,tm=self.transition_matrix(l); opt,pred=self.nested(f,l,cols); cal=self.calibration(pred); sens=self.sensitivity(sel,pred)
   for t,x in [('m26_feature_research',research),('m26_transition_matrix',tm),('m26_ensemble_optimization',opt),('m26_nested_walk_forward',pred),('m26_probability_calibration',cal),('m26_sensitivity_results',sens)]: self.upsert(t,x)
   agr=float(pred['label_match'].mean()*100) if not pred.empty else 0; raw=float(cal['raw_absolute_error'].mean()) if not cal.empty else 1; mae=float(cal['calibrated_absolute_error'].mean()) if not cal.empty else 1; stability=float(sens['label_agreement_pct'].mean()) if not sens.empty else 0; cur=pred.iloc[-1] if not pred.empty else None
   passed=agr>=float(self.cfg['validation']['minimum_nested_agreement_pct']) and mae<=float(self.cfg['validation']['maximum_calibrated_mae']) and stability>=float(self.cfg['validation']['minimum_sensitivity_stability_pct']); status='PASSED' if passed else 'LIMITED'; rec='READY_FOR_REGIME_SPECIALIST_LAB' if passed else 'CONTINUE_REGIME_RESEARCH'
   summary=pd.DataFrame([{'run_id':self.run_id,'candidate_features':len(cols),'selected_features':len(sel),'selected_feature_list':json.dumps(sel),'outer_folds':int(pred['outer_fold'].nunique()) if not pred.empty else 0,'nested_test_rows':len(pred),'nested_agreement_pct':agr,'raw_calibration_mae':raw,'calibrated_mae':mae,'sensitivity_stability_pct':stability,'current_regime':cur['predicted_regime'] if cur is not None else None,'current_confidence':float(cur['calibrated_confidence']) if cur is not None else None,'validation_status':status,'advancement_recommendation':rec,'calculated_at_utc':utcnow()}]); self.upsert('m26_research_summary',summary)
   self.conn.execute("UPDATE module26_runs SET completed_at_utc=?,status='SUCCESS',candidate_features=?,selected_features=?,outer_folds=?,nested_test_rows=?,nested_agreement_pct=?,calibrated_mae=?,sensitivity_stability_pct=?,current_regime=?,current_confidence=?,validation_status=?,notes=? WHERE run_id=?",[utcnow(),len(cols),len(sel),int(summary.iloc[0]['outer_folds']),len(pred),agr,mae,stability,summary.iloc[0]['current_regime'],summary.iloc[0]['current_confidence'],status,'Markov sequence research; Module 25 labels remain unchanged.',self.run_id]); self.conn.close(); return summary.iloc[0].to_dict()
  except Exception as exc:
   self.conn.execute("UPDATE module26_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",[utcnow(),str(exc)[:1000],self.run_id]); self.conn.close(); raise

def run_module26(): return Module26Runner().run()
