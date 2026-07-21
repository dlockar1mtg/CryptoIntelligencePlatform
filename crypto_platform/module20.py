from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score

from crypto_platform.platform import load_all, connect
from crypto_platform.module17 import MODULE17_SCHEMA
from crypto_platform.module18 import MODULE18_SCHEMA
from crypto_platform.module19 import MODULE19_SCHEMA

MODULE20_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module20_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    model_rows INTEGER,
    explainability_rows INTEGER,
    redundancy_rows INTEGER,
    aging_rows INTEGER,
    shadow_periods INTEGER,
    shadow_return_pct DOUBLE,
    btc_return_pct DOUBLE,
    shadow_excess_pct DOUBLE,
    shadow_promoted BOOLEAN,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS feature_model_comparison(
    run_id VARCHAR,
    feature_group VARCHAR,
    forward_horizon_days INTEGER,
    model_name VARCHAR,
    training_rows INTEGER,
    testing_rows INTEGER,
    out_of_sample_r2 DOUBLE,
    out_of_sample_mae DOUBLE,
    directional_accuracy_pct DOUBLE,
    rank_correlation DOUBLE,
    selected_model BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_group, forward_horizon_days, model_name)
);

CREATE TABLE IF NOT EXISTS model_feature_explainability(
    run_id VARCHAR,
    feature_group VARCHAR,
    forward_horizon_days INTEGER,
    model_name VARCHAR,
    feature_key VARCHAR,
    importance_mean DOUBLE,
    importance_std DOUBLE,
    importance_rank INTEGER,
    feature_return_correlation DOUBLE,
    inferred_direction VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_group, forward_horizon_days, model_name, feature_key)
);

CREATE TABLE IF NOT EXISTS feature_redundancy_analysis(
    run_id VARCHAR,
    feature_a VARCHAR,
    feature_b VARCHAR,
    sample_count INTEGER,
    pearson_correlation DOUBLE,
    absolute_correlation DOUBLE,
    redundancy_status VARCHAR,
    preferred_feature VARCHAR,
    preference_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_a, feature_b)
);

CREATE TABLE IF NOT EXISTS feature_evidence_aging(
    run_id VARCHAR,
    feature_key VARCHAR,
    prior_registry_status VARCHAR,
    aged_registry_status VARCHAR,
    prior_promotion_score DOUBLE,
    aged_promotion_score DOUBLE,
    recent_windows INTEGER,
    recent_mean_spearman DOUBLE,
    recent_sign_consistency_pct DOUBLE,
    evidence_age_days INTEGER,
    decay_multiplier DOUBLE,
    aging_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key)
);

CREATE TABLE IF NOT EXISTS shadow_portfolio_periods(
    run_id VARCHAR,
    rebalance_date DATE,
    next_rebalance_date DATE,
    btc_weight DOUBLE,
    cash_weight DOUBLE,
    composite_signal DOUBLE,
    active_feature_count INTEGER,
    portfolio_return_pct DOUBLE,
    btc_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    turnover_pct DOUBLE,
    transaction_cost_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, rebalance_date)
);

CREATE TABLE IF NOT EXISTS shadow_portfolio_summary(
    run_id VARCHAR PRIMARY KEY,
    start_date DATE,
    end_date DATE,
    periods INTEGER,
    promoted_feature_count INTEGER,
    total_return_pct DOUBLE,
    annualized_return_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    btc_total_return_pct DOUBLE,
    btc_annualized_return_pct DOUBLE,
    btc_excess_pct DOUBLE,
    information_ratio DOUBLE,
    benchmark_win_rate_pct DOUBLE,
    average_btc_weight_pct DOUBLE,
    average_turnover_pct DOUBLE,
    transaction_cost_drag_pct DOUBLE,
    promotion_status VARCHAR,
    promotion_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_feature_model_comparison AS
SELECT x.* FROM feature_model_comparison x
JOIN (SELECT run_id FROM module20_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id)
ORDER BY feature_group, forward_horizon_days, out_of_sample_r2 DESC;

CREATE OR REPLACE VIEW latest_model_feature_explainability AS
SELECT x.* FROM model_feature_explainability x
JOIN (SELECT run_id FROM module20_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id)
ORDER BY feature_group, forward_horizon_days, importance_rank;

CREATE OR REPLACE VIEW latest_feature_redundancy AS
SELECT x.* FROM feature_redundancy_analysis x
JOIN (SELECT run_id FROM module20_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id)
ORDER BY absolute_correlation DESC;

CREATE OR REPLACE VIEW latest_feature_evidence_aging AS
SELECT x.* FROM feature_evidence_aging x
JOIN (SELECT run_id FROM module20_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id)
ORDER BY aged_promotion_score DESC;

CREATE OR REPLACE VIEW latest_shadow_portfolio_periods AS
SELECT x.* FROM shadow_portfolio_periods x
JOIN (SELECT run_id FROM module20_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id)
ORDER BY rebalance_date;

CREATE OR REPLACE VIEW latest_shadow_portfolio_summary AS
SELECT x.* FROM shadow_portfolio_summary x
JOIN (SELECT run_id FROM module20_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
"""

FEATURE_GROUPS = {
    "MACRO": ["dollar_index", "high_yield_spread", "vix", "macro_liquidity_score"],
    "SENTIMENT": ["fear_greed_index", "risk_appetite_score"],
    "MARKET_STRUCTURE": [
        "btc_dominance_proxy_pct", "total2_market_cap_proxy_usd",
        "total3_market_cap_proxy_usd", "core_breadth_above_sma50_pct",
        "core_median_return_30d_pct", "btc_return_30d_pct",
    ],
    "LIQUIDITY_FLOWS": ["stablecoin_supply_usd", "stablecoin_growth_30d_pct", "etf_net_flow_usd"],
}

def utcnow(): return datetime.now(timezone.utc)

def annual_metrics(returns: pd.Series, periods_per_year: float):
    curve=(1+returns).cumprod(); total=float(curve.iloc[-1]-1) if len(curve) else 0.0
    years=max(len(returns)/periods_per_year,1/periods_per_year)
    ann=(1+total)**(1/years)-1 if total>-1 else -1.0
    vol=float(returns.std(ddof=1)*np.sqrt(periods_per_year)) if len(returns)>1 else 0.0
    dd=curve/curve.cummax()-1 if len(curve) else pd.Series(dtype=float)
    return total,ann,vol,(ann/vol if vol>0 else None),(float(dd.min()) if len(dd) else 0.0)

class Module20Runner:
    def __init__(self):
        self.settings,_=load_all(); self.conn=connect(self.settings)
        self.conn.execute(MODULE17_SCHEMA); self.conn.execute(MODULE18_SCHEMA); self.conn.execute(MODULE19_SCHEMA); self.conn.execute(MODULE20_SCHEMA)
        self.cfg=self.settings['module20']; self.run_id=str(uuid.uuid4()); self.started=utcnow()

    def upsert(self,table,frame):
        if frame.empty:return
        self.conn.register('_m20_stage',frame); cols=','.join(frame.columns)
        self.conn.execute(f'INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _m20_stage'); self.conn.unregister('_m20_stage')

    def frame(self):
        f=self.conn.execute('SELECT * FROM crypto_features_daily ORDER BY observation_date').fetchdf()
        if f.empty: raise RuntimeError('Feature warehouse is empty. Run Modules 17-19 first.')
        f['observation_date']=pd.to_datetime(f['observation_date']); return f

    def models(self):
        c=self.cfg['models']; seed=int(c['random_state'])
        return {
            'RANDOM_FOREST':RandomForestRegressor(n_estimators=int(c['n_estimators']),min_samples_leaf=int(c['min_samples_leaf']),random_state=seed,n_jobs=-1),
            'EXTRA_TREES':ExtraTreesRegressor(n_estimators=int(c['n_estimators']),min_samples_leaf=int(c['min_samples_leaf']),random_state=seed,n_jobs=-1),
            'GRADIENT_BOOSTING':GradientBoostingRegressor(n_estimators=int(c['gradient_estimators']),learning_rate=float(c['learning_rate']),max_depth=int(c['max_depth']),min_samples_leaf=int(c['min_samples_leaf']),random_state=seed,loss='huber'),
            'HIST_GRADIENT_BOOSTING':HistGradientBoostingRegressor(max_iter=int(c['hist_iterations']),learning_rate=float(c['learning_rate']),max_leaf_nodes=int(c['max_leaf_nodes']),min_samples_leaf=int(c['min_samples_leaf']),l2_regularization=float(c['l2_regularization']),random_state=seed),
        }

    def model_compare(self,f):
        rows=[]; explain=[]; split_fraction=float(self.cfg['models']['training_fraction'])
        for group,configured in FEATURE_GROUPS.items():
            features=[x for x in configured if x in f.columns and f[x].notna().sum()>=int(self.cfg['models']['minimum_total_rows'])]
            if len(features)<2: continue
            for horizon in self.cfg['horizons_days']:
                target=f'forward_{horizon}'; d=f.copy(); d[target]=(d['btc_price_usd'].shift(-int(horizon))/d['btc_price_usd']-1)*100
                sample=d[features+[target]].dropna(); split=int(len(sample)*split_fraction)
                if split<int(self.cfg['models']['minimum_training_rows']) or len(sample)-split<int(self.cfg['models']['minimum_testing_rows']): continue
                train,test=sample.iloc[:split],sample.iloc[split:]
                local=[]
                for name,model in self.models().items():
                    model.fit(train[features],train[target]); pred=model.predict(test[features])
                    r2=float(r2_score(test[target],pred)); mae=float(mean_absolute_error(test[target],pred)); direction=float((np.sign(pred)==np.sign(test[target])).mean()*100); rank=float(pd.Series(pred).rank().corr(test[target].reset_index(drop=True).rank()))
                    local.append((name,model,r2,mae,direction,rank))
                selected=max(local,key=lambda x:x[2])[0]
                for name,model,r2,mae,direction,rank in local:
                    rows.append({'run_id':self.run_id,'feature_group':group,'forward_horizon_days':int(horizon),'model_name':name,'training_rows':len(train),'testing_rows':len(test),'out_of_sample_r2':r2,'out_of_sample_mae':mae,'directional_accuracy_pct':direction,'rank_correlation':rank,'selected_model':name==selected,'calculated_at_utc':utcnow()})
                    if name==selected:
                        pi=permutation_importance(model,test[features],test[target],n_repeats=int(self.cfg['explainability']['n_repeats']),random_state=int(self.cfg['models']['random_state']),n_jobs=-1)
                        order=np.argsort(-pi.importances_mean)
                        for rank_i,idx in enumerate(order,1):
                            corr=float(test[features[idx]].corr(test[target])) if test[features[idx]].nunique()>1 else 0.0
                            explain.append({'run_id':self.run_id,'feature_group':group,'forward_horizon_days':int(horizon),'model_name':name,'feature_key':features[idx],'importance_mean':float(pi.importances_mean[idx]),'importance_std':float(pi.importances_std[idx]),'importance_rank':rank_i,'feature_return_correlation':corr,'inferred_direction':'POSITIVE' if corr>0 else 'NEGATIVE' if corr<0 else 'NEUTRAL','calculated_at_utc':utcnow()})
        a=pd.DataFrame(rows); b=pd.DataFrame(explain); self.upsert('feature_model_comparison',a); self.upsert('model_feature_explainability',b); return a,b

    def redundancy(self,f):
        registry=self.conn.execute("SELECT feature_key,promotion_score,registry_status FROM latest_feature_registry WHERE production_eligible=TRUE").fetchdf()
        keys=[x for x in registry['feature_key'].tolist() if x in f.columns]
        scores=dict(zip(registry['feature_key'],registry['promotion_score'])); rows=[]; threshold=float(self.cfg['redundancy']['absolute_correlation_threshold'])
        for i,a in enumerate(keys):
            for b in keys[i+1:]:
                s=f[[a,b]].dropna()
                if len(s)<int(self.cfg['redundancy']['minimum_observations']):continue
                corr=float(s[a].corr(s[b])); status='REDUNDANT' if abs(corr)>=threshold else 'DISTINCT'
                preferred=a if scores.get(a,0)>=scores.get(b,0) else b
                rows.append({'run_id':self.run_id,'feature_a':a,'feature_b':b,'sample_count':len(s),'pearson_correlation':corr,'absolute_correlation':abs(corr),'redundancy_status':status,'preferred_feature':preferred if status=='REDUNDANT' else None,'preference_reason':('Higher feature-registry promotion score.' if status=='REDUNDANT' else 'Correlation below redundancy threshold.'),'calculated_at_utc':utcnow()})
        out=pd.DataFrame(rows); self.upsert('feature_redundancy_analysis',out); return out

    def aging(self):
        reg=self.conn.execute('SELECT * FROM latest_feature_registry').fetchdf(); roll=self.conn.execute('SELECT * FROM latest_feature_rolling_validation').fetchdf(); rows=[]
        recent_n=int(self.cfg['aging']['recent_windows']); today=pd.Timestamp.now(tz='UTC').tz_localize(None)
        for _,r in reg.iterrows():
            s=roll[roll.feature_key==r.feature_key].sort_values(['testing_end_date','forward_horizon_days']).tail(recent_n)
            mean=float(s.testing_spearman.mean()) if len(s) else 0.0; consistency=float(s.sign_consistent.mean()*100) if len(s) else 0.0
            latest=pd.to_datetime(r.latest_date) if pd.notna(r.latest_date) else None; age=(today-latest).days if latest is not None else 9999
            freshness=max(0.0,1-age/float(self.cfg['aging']['full_decay_days'])); evidence=max(0.25,min(1.0,(abs(mean)/float(self.cfg['aging']['target_recent_absolute_spearman']))*.55+(consistency/100)*.45)) if len(s) else .25
            multiplier=freshness*evidence if r.production_eligible else 0.0; aged=float(r.promotion_score)*multiplier
            status=r.registry_status
            if status=='PROMOTED_SHADOW' and (aged<float(self.cfg['aging']['shadow_minimum_score']) or consistency<float(self.cfg['aging']['minimum_recent_sign_consistency_pct'])): status='WATCHLIST_AGED'
            elif status=='WATCHLIST' and aged<float(self.cfg['aging']['watchlist_minimum_score']): status='RESEARCH_ONLY_AGED'
            rows.append({'run_id':self.run_id,'feature_key':r.feature_key,'prior_registry_status':r.registry_status,'aged_registry_status':status,'prior_promotion_score':float(r.promotion_score),'aged_promotion_score':aged,'recent_windows':len(s),'recent_mean_spearman':mean,'recent_sign_consistency_pct':consistency,'evidence_age_days':age,'decay_multiplier':multiplier,'aging_reason':f'freshness={freshness:.3f}; evidence={evidence:.3f}; recent_windows={len(s)}','calculated_at_utc':utcnow()})
        out=pd.DataFrame(rows); self.upsert('feature_evidence_aging',out); return out

    def shadow(self,f,aging,redundancy):
        eligible=aging[aging.aged_registry_status=='PROMOTED_SHADOW'].copy()
        if eligible.empty: eligible=aging[(aging.prior_registry_status=='PROMOTED_SHADOW') & (aging.aged_promotion_score>=float(self.cfg['shadow']['fallback_minimum_aged_score']))].copy()
        redundant=redundancy[redundancy.redundancy_status=='REDUNDANT'] if not redundancy.empty else pd.DataFrame()
        remove=set()
        for _,r in redundant.iterrows(): remove.add(r.feature_b if r.preferred_feature==r.feature_a else r.feature_a)
        features=[x for x in eligible.feature_key.tolist() if x in f.columns and x not in remove]
        if not features: return pd.DataFrame(),pd.DataFrame()
        directions={}
        rv=self.conn.execute('SELECT feature_key,AVG(testing_spearman) mean_s FROM latest_feature_rolling_validation GROUP BY feature_key').fetchdf()
        for _,r in rv.iterrows(): directions[r.feature_key]=1.0 if r.mean_s>=0 else -1.0
        d=f[['observation_date','btc_price_usd']+features].copy().set_index('observation_date').sort_index()
        monthly=d.resample('30D').last().dropna(subset=['btc_price_usd']); rows=[]; prev=1.0; cost=float(self.cfg['shadow']['transaction_cost_bps'])/10000
        for i in range(len(monthly)-1):
            date,next_date=monthly.index[i],monthly.index[i+1]; hist=d.loc[:date].tail(int(self.cfg['shadow']['zscore_lookback_days']))
            signals=[]
            for x in features:
                s=hist[x].dropna()
                if len(s)<int(self.cfg['shadow']['minimum_feature_history']):continue
                std=s.std(); z=0.0 if not std or pd.isna(std) else float((s.iloc[-1]-s.mean())/std); signals.append(np.clip(z,-2,2)*directions.get(x,1.0))
            if not signals:continue
            composite=float(np.mean(signals)); btc_weight=float(np.clip(float(self.cfg['shadow']['neutral_btc_weight'])+composite*float(self.cfg['shadow']['signal_weight_slope']),float(self.cfg['shadow']['minimum_btc_weight']),float(self.cfg['shadow']['maximum_btc_weight'])))
            btc_ret=float(monthly.btc_price_usd.iloc[i+1]/monthly.btc_price_usd.iloc[i]-1); turnover=abs(btc_weight-prev); tx=turnover*cost; port=btc_weight*btc_ret-tx
            rows.append({'run_id':self.run_id,'rebalance_date':date.date(),'next_rebalance_date':next_date.date(),'btc_weight':btc_weight,'cash_weight':1-btc_weight,'composite_signal':composite,'active_feature_count':len(signals),'portfolio_return_pct':port*100,'btc_return_pct':btc_ret*100,'excess_return_pct':(port-btc_ret)*100,'turnover_pct':turnover*100,'transaction_cost_pct':tx*100,'calculated_at_utc':utcnow()}); prev=btc_weight
        periods=pd.DataFrame(rows)
        if periods.empty:return periods,pd.DataFrame()
        pr=periods.portfolio_return_pct/100; br=periods.btc_return_pct/100; p=annual_metrics(pr,365/30); b=annual_metrics(br,365/30); active=pr-br; te=float(active.std(ddof=1)*np.sqrt(365/30)); ir=(p[1]-b[1])/te if te>0 else None
        promoted=(p[0]-b[0])*100>=float(self.cfg['shadow']['minimum_excess_return_pct']) and (ir or -999)>=float(self.cfg['shadow']['minimum_information_ratio']) and p[4]*100>=float(self.cfg['shadow']['maximum_drawdown_floor_pct'])
        summary=pd.DataFrame([{'run_id':self.run_id,'start_date':periods.rebalance_date.min(),'end_date':periods.next_rebalance_date.max(),'periods':len(periods),'promoted_feature_count':len(features),'total_return_pct':p[0]*100,'annualized_return_pct':p[1]*100,'annualized_volatility_pct':p[2]*100,'sharpe_ratio':p[3],'maximum_drawdown_pct':p[4]*100,'btc_total_return_pct':b[0]*100,'btc_annualized_return_pct':b[1]*100,'btc_excess_pct':(p[0]-b[0])*100,'information_ratio':ir,'benchmark_win_rate_pct':float((pr>br).mean()*100),'average_btc_weight_pct':float(periods.btc_weight.mean()*100),'average_turnover_pct':float(periods.turnover_pct.mean()),'transaction_cost_drag_pct':float(periods.transaction_cost_pct.sum()),'promotion_status':'SHADOW_VALIDATED' if promoted else 'RESEARCH_ONLY','promotion_reason':('Cleared shadow portfolio thresholds.' if promoted else 'Did not clear all shadow portfolio thresholds.'),'calculated_at_utc':utcnow()}])
        self.upsert('shadow_portfolio_periods',periods); self.upsert('shadow_portfolio_summary',summary); return periods,summary

    def run(self):
        self.conn.execute("UPDATE module20_runs SET status='FAILED',completed_at_utc=?,notes=COALESCE(notes,'')||'; interrupted prior run' WHERE status='RUNNING'",[utcnow()])
        self.conn.execute("INSERT INTO module20_runs VALUES(?,?,NULL,'RUNNING',0,0,0,0,0,NULL,NULL,NULL,FALSE,NULL,'4.2.3')",[self.run_id,self.started])
        try:
            f=self.frame(); models,explain=self.model_compare(f); red=self.redundancy(f); age=self.aging(); periods,summary=self.shadow(f,age,red)
            shadow_return=float(summary.iloc[0].total_return_pct) if not summary.empty else None; btc_return=float(summary.iloc[0].btc_total_return_pct) if not summary.empty else None; excess=float(summary.iloc[0].btc_excess_pct) if not summary.empty else None; promoted=bool(summary.iloc[0].promotion_status=='SHADOW_VALIDATED') if not summary.empty else False
            self.conn.execute("UPDATE module20_runs SET completed_at_utc=?,status='SUCCESS',model_rows=?,explainability_rows=?,redundancy_rows=?,aging_rows=?,shadow_periods=?,shadow_return_pct=?,btc_return_pct=?,shadow_excess_pct=?,shadow_promoted=?,notes=? WHERE run_id=?",[utcnow(),len(models),len(explain),len(red),len(age),len(periods),shadow_return,btc_return,excess,promoted,'Research maturity only; Module 13 remains unchanged.',self.run_id])
            self.conn.close(); return {'run_id':self.run_id,'status':'SUCCESS','model_rows':len(models),'explainability_rows':len(explain),'redundancy_rows':len(red),'aging_rows':len(age),'shadow_periods':len(periods),'shadow_return_pct':shadow_return,'btc_return_pct':btc_return,'shadow_excess_pct':excess,'shadow_promoted':promoted}
        except Exception as exc:
            self.conn.execute("UPDATE module20_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",[utcnow(),str(exc)[:1000],self.run_id]); self.conn.close(); raise

def run_module20(): return Module20Runner().run()
