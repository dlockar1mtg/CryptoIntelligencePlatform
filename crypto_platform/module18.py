from __future__ import annotations
import itertools, uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from crypto_platform.platform import load_all, connect
from crypto_platform.module17 import MODULE17_SCHEMA

MODULE18_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS module18_runs(run_id VARCHAR PRIMARY KEY,started_at_utc TIMESTAMPTZ,completed_at_utc TIMESTAMPTZ,status VARCHAR,stablecoin_history_rows INTEGER,corrected_readiness_rows INTEGER,interaction_rows INTEGER,permutation_rows INTEGER,regime_rows INTEGER,notes VARCHAR,platform_version VARCHAR);
CREATE TABLE IF NOT EXISTS feature_readiness_v2(run_id VARCHAR,feature_key VARCHAR,first_date DATE,latest_date DATE,active_window_days INTEGER,non_null_count INTEGER,active_window_coverage_pct DOUBLE,full_table_coverage_pct DOUBLE,best_absolute_spearman DOUBLE,readiness_status VARCHAR,limitation VARCHAR,calculated_at_utc TIMESTAMPTZ,PRIMARY KEY(run_id,feature_key));
CREATE TABLE IF NOT EXISTS feature_interaction_validation(run_id VARCHAR,feature_a VARCHAR,feature_b VARCHAR,interaction_type VARCHAR,forward_horizon_days INTEGER,sample_count INTEGER,spearman_correlation DOUBLE,top_quartile_forward_return_pct DOUBLE,bottom_quartile_forward_return_pct DOUBLE,top_minus_bottom_pct DOUBLE,calculated_at_utc TIMESTAMPTZ,PRIMARY KEY(run_id,feature_a,feature_b,interaction_type,forward_horizon_days));
CREATE TABLE IF NOT EXISTS feature_permutation_importance(run_id VARCHAR,forward_horizon_days INTEGER,feature_key VARCHAR,sample_count INTEGER,base_r2 DOUBLE,importance_mean DOUBLE,importance_std DOUBLE,importance_rank INTEGER,calculated_at_utc TIMESTAMPTZ,PRIMARY KEY(run_id,forward_horizon_days,feature_key));
CREATE TABLE IF NOT EXISTS feature_regime_stability(run_id VARCHAR,feature_key VARCHAR,forward_horizon_days INTEGER,regime VARCHAR,sample_count INTEGER,spearman_correlation DOUBLE,directional_hit_rate_pct DOUBLE,top_minus_bottom_pct DOUBLE,calculated_at_utc TIMESTAMPTZ,PRIMARY KEY(run_id,feature_key,forward_horizon_days,regime));
CREATE OR REPLACE VIEW latest_feature_readiness_v2 AS SELECT x.* FROM feature_readiness_v2 x JOIN (SELECT run_id FROM module18_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id) ORDER BY readiness_status,best_absolute_spearman DESC;
CREATE OR REPLACE VIEW latest_feature_interactions AS SELECT x.* FROM feature_interaction_validation x JOIN (SELECT run_id FROM module18_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id) ORDER BY ABS(spearman_correlation) DESC NULLS LAST;
CREATE OR REPLACE VIEW latest_feature_permutation_importance AS SELECT x.* FROM feature_permutation_importance x JOIN (SELECT run_id FROM module18_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id) ORDER BY forward_horizon_days,importance_rank;
CREATE OR REPLACE VIEW latest_feature_regime_stability AS SELECT x.* FROM feature_regime_stability x JOIN (SELECT run_id FROM module18_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
'''
FEATURES=['btc_dominance_proxy_pct','total2_market_cap_proxy_usd','total3_market_cap_proxy_usd','stablecoin_growth_30d_pct','fear_greed_index','etf_net_flow_usd','core_breadth_above_sma50_pct','core_median_return_30d_pct','dollar_index','high_yield_spread','vix','macro_liquidity_score','risk_appetite_score']
def utcnow(): return datetime.now(timezone.utc)
class Module18Runner:
    def __init__(self):
        self.settings,_=load_all(); self.conn=connect(self.settings); self.conn.execute(MODULE17_SCHEMA); self.conn.execute(MODULE18_SCHEMA); self.cfg=self.settings['module18']; self.run_id=str(uuid.uuid4()); self.started=utcnow(); self.session=requests.Session(); self.session.headers.update({'User-Agent':'CryptoIntelligencePlatform/4.2.1'})
    def upsert(self,table,frame):
        if frame.empty:return
        self.conn.register('_m18',frame); cols=','.join(frame.columns); self.conn.execute(f'INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _m18'); self.conn.unregister('_m18')
    def collect_stablecoin_history(self):
        if not self.cfg['collection']['enabled']: return 0
        try:
            r=self.session.get(self.cfg['collection']['url'],timeout=int(self.cfg['collection']['timeout_seconds'])); r.raise_for_status(); rows=[]
            for item in r.json():
                ts=item.get('date') or item.get('timestamp'); value=item.get('totalCirculatingUSD') or item.get('totalCirculating') or item.get('total')
                if isinstance(value,dict): value=sum(float(v or 0) for v in value.values())
                try: date=pd.to_datetime(int(ts),unit='s',utc=True).date(); value=float(value)
                except Exception: continue
                rows.append({'feature_key':'STABLECOIN_SUPPLY_USD','observation_date':date,'value':value,'unit':'usd','source':'defillama_history','source_quality':'PUBLIC_API','collected_at_utc':utcnow()})
            frame=pd.DataFrame(rows); self.upsert('external_feature_observations',frame); return len(frame)
        except Exception:return 0
    def feature_frame(self):
        frame=self.conn.execute('SELECT * FROM crypto_features_daily ORDER BY observation_date').fetchdf()
        if frame.empty: raise RuntimeError('Module 17 feature warehouse is empty. Run Module 17 first.')
        frame['observation_date']=pd.to_datetime(frame['observation_date'])
        stable=self.conn.execute("SELECT observation_date,value FROM external_feature_observations WHERE feature_key='STABLECOIN_SUPPLY_USD' QUALIFY ROW_NUMBER() OVER(PARTITION BY observation_date ORDER BY collected_at_utc DESC)=1 ORDER BY observation_date").fetchdf()
        if not stable.empty:
            stable['observation_date']=pd.to_datetime(stable['observation_date']); frame=frame.merge(stable.rename(columns={'value':'_stable'}),on='observation_date',how='left'); frame['stablecoin_supply_usd']=frame['_stable'].combine_first(frame['stablecoin_supply_usd']); frame['stablecoin_growth_30d_pct']=frame['stablecoin_supply_usd'].pct_change(30,fill_method=None)*100; frame=frame.drop(columns=['_stable']); self.upsert('crypto_features_daily',frame)
        return frame
    def corrected_readiness(self,frame):
        validation=self.conn.execute('SELECT * FROM latest_feature_validation').fetchdf(); total=len(frame); rows=[]
        keys=[k for k in FEATURES+['btc_return_30d_pct','stablecoin_supply_usd','btc_dominance_pct','total_market_cap_usd'] if k in frame.columns]
        for key in keys:
            mask=frame[key].notna(); n=int(mask.sum())
            if n:
                dates=frame.loc[mask,'observation_date']; first=dates.min(); latest=dates.max(); active=(latest-first).days+1; coverage=n/active*100
            else:first=latest=None; active=0; coverage=0.0
            subset=validation[validation['feature_key']==key] if not validation.empty else pd.DataFrame(); best=float(subset['spearman_correlation'].abs().max()) if not subset.empty else 0.0; rules=self.cfg['readiness']
            if n==0: status='NO_DATA'; limitation='No observations available.'
            elif active>=int(rules['minimum_history_days']) and coverage>=float(rules['minimum_active_window_coverage_pct']) and best>=float(rules['minimum_absolute_spearman']): status='READY_FOR_RESEARCH'; limitation=None
            else: status='LIMITED'; limitation=f'active_window_days={active}; active_coverage_pct={coverage:.1f}; best_abs_spearman={best:.3f}'
            rows.append({'run_id':self.run_id,'feature_key':key,'first_date':first.date() if first is not None else None,'latest_date':latest.date() if latest is not None else None,'active_window_days':active,'non_null_count':n,'active_window_coverage_pct':coverage,'full_table_coverage_pct':n/total*100 if total else 0,'best_absolute_spearman':best,'readiness_status':status,'limitation':limitation,'calculated_at_utc':utcnow()})
        out=pd.DataFrame(rows); self.upsert('feature_readiness_v2',out); return out
    @staticmethod
    def add_forward(frame,h):
        out=frame.copy(); out[f'forward_{h}']=(out['btc_price_usd'].shift(-h)/out['btc_price_usd']-1)*100; return out
    def interactions(self,frame):
        ready=self.conn.execute("SELECT feature_key FROM latest_feature_readiness_v2 WHERE readiness_status='READY_FOR_RESEARCH' ORDER BY best_absolute_spearman DESC").fetchdf(); keys=ready['feature_key'].tolist()[:int(self.cfg['interactions']['maximum_features'])] if not ready.empty else []; rows=[]
        for a,b in list(itertools.combinations(keys,2))[:int(self.cfg['interactions']['maximum_pairs'])]:
            for h in self.cfg['horizons_days']:
                target=f'forward_{h}'; sample=self.add_forward(frame,int(h))[[a,b,target]].dropna()
                if len(sample)<int(self.cfg['interactions']['minimum_observations']): continue
                za=(sample[a]-sample[a].mean())/sample[a].std(); zb=(sample[b]-sample[b].mean())/sample[b].std()
                for typ,signal in {'zscore_sum':za+zb,'rank_product':sample[a].rank(pct=True)*sample[b].rank(pct=True)}.items():
                    future=sample[target]; corr=signal.rank().corr(future.rank()); lo=signal.quantile(.25); hi=signal.quantile(.75); top=future[signal>=hi].mean(); bottom=future[signal<=lo].mean()
                    rows.append({'run_id':self.run_id,'feature_a':a,'feature_b':b,'interaction_type':typ,'forward_horizon_days':int(h),'sample_count':len(sample),'spearman_correlation':float(corr),'top_quartile_forward_return_pct':float(top),'bottom_quartile_forward_return_pct':float(bottom),'top_minus_bottom_pct':float(top-bottom),'calculated_at_utc':utcnow()})
        out=pd.DataFrame(rows); self.upsert('feature_interaction_validation',out); return out
    def permutation(self,frame):
        if not self.cfg['permutation']['enabled']: return pd.DataFrame()
        minimum=int(self.cfg['permutation']['minimum_observations']); keys=[k for k in FEATURES if k in frame.columns and frame[k].notna().sum()>=minimum]; rows=[]
        for h in self.cfg['horizons_days']:
            target=f'forward_{h}'; sample=self.add_forward(frame,int(h))[keys+[target]].dropna()
            if len(sample)<minimum or len(keys)<2: continue
            split=int(len(sample)*.75); train=sample.iloc[:split]; test=sample.iloc[split:]
            model=RandomForestRegressor(n_estimators=int(self.cfg['permutation']['n_estimators']),min_samples_leaf=15,random_state=int(self.cfg['permutation']['random_state']),n_jobs=1); model.fit(train[keys],train[target]); base=model.score(test[keys],test[target]); imp=permutation_importance(model,test[keys],test[target],n_repeats=int(self.cfg['permutation']['n_repeats']),random_state=int(self.cfg['permutation']['random_state']),n_jobs=1)
            for rank,i in enumerate(np.argsort(-imp.importances_mean),1):
                rows.append({'run_id':self.run_id,'forward_horizon_days':int(h),'feature_key':keys[i],'sample_count':len(sample),'base_r2':float(base),'importance_mean':float(imp.importances_mean[i]),'importance_std':float(imp.importances_std[i]),'importance_rank':rank,'calculated_at_utc':utcnow()})
        out=pd.DataFrame(rows); self.upsert('feature_permutation_importance',out); return out
    def regime_stability(self,frame):
        sma=frame['btc_price_usd'].rolling(int(self.cfg['regimes']['sma_days']),min_periods=100).mean(); momentum=frame['btc_price_usd'].pct_change(int(self.cfg['regimes']['momentum_days']),fill_method=None); sample=frame.copy(); sample['regime']=np.select([(sample['btc_price_usd']>=sma)&(momentum>0),(sample['btc_price_usd']<sma)&(momentum<0)],['BULL','BEAR'],default='TRANSITION'); rows=[]
        for key in FEATURES:
            if key not in sample.columns: continue
            for h in self.cfg['horizons_days']:
                target=f'forward_{h}'; forward=self.add_forward(sample,int(h))[[key,'regime',target]].dropna()
                for regime,group in forward.groupby('regime'):
                    if len(group)<int(self.cfg['regimes']['minimum_observations']): continue
                    future=group[target]; corr=group[key].rank().corr(future.rank()); median=group[key].median(); hit=(((group[key]-median)*future)>0).mean()*100; lo=group[key].quantile(.25); hi=group[key].quantile(.75); spread=future[group[key]>=hi].mean()-future[group[key]<=lo].mean()
                    rows.append({'run_id':self.run_id,'feature_key':key,'forward_horizon_days':int(h),'regime':regime,'sample_count':len(group),'spearman_correlation':float(corr),'directional_hit_rate_pct':float(hit),'top_minus_bottom_pct':float(spread),'calculated_at_utc':utcnow()})
        out=pd.DataFrame(rows); self.upsert('feature_regime_stability',out); return out
    def run(self):
        self.conn.execute("UPDATE module18_runs SET status='FAILED',completed_at_utc=? WHERE status='RUNNING'",[utcnow()]); self.conn.execute("INSERT INTO module18_runs VALUES(?,?,NULL,'RUNNING',0,0,0,0,0,NULL,'4.2.1')",[self.run_id,self.started])
        try:
            stable=self.collect_stablecoin_history(); frame=self.feature_frame(); readiness=self.corrected_readiness(frame); interactions=self.interactions(frame); permutation_rows=self.permutation(frame); regimes=self.regime_stability(frame); notes="Coverage is measured over each feature's active window. Public-provider history remains separated from derived proxies."
            self.conn.execute("UPDATE module18_runs SET completed_at_utc=?,status='SUCCESS',stablecoin_history_rows=?,corrected_readiness_rows=?,interaction_rows=?,permutation_rows=?,regime_rows=?,notes=? WHERE run_id=?",[utcnow(),stable,len(readiness),len(interactions),len(permutation_rows),len(regimes),notes,self.run_id]); self.conn.close(); return {'run_id':self.run_id,'status':'SUCCESS','stablecoin_history_rows':stable,'readiness_rows':len(readiness),'interaction_rows':len(interactions),'permutation_rows':len(permutation_rows),'regime_rows':len(regimes)}
        except Exception as exc:
            self.conn.execute("UPDATE module18_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",[utcnow(),str(exc)[:1000],self.run_id]); self.conn.close(); raise

def run_module18(): return Module18Runner().run()
