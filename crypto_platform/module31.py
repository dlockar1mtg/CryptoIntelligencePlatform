from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from crypto_platform.platform import load_all, connect
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.ml.classes import canonical_classes
from crypto_platform.ml.validation import multiclass_brier_score, validate_probability_matrix

MODULE31_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module31_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module30_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    historical_rows INTEGER,
    forward_return_rows INTEGER,
    calibration_rows INTEGER,
    persistence_rows INTEGER,
    investment_value_score DOUBLE,
    validation_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m31_calibration_comparison(
    run_id VARCHAR,
    method VARCHAR,
    observations INTEGER,
    multiclass_log_loss DOUBLE,
    multiclass_brier_score DOUBLE,
    top_class_mae DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, method)
);

CREATE TABLE IF NOT EXISTS m31_persistence_validation(
    run_id VARCHAR,
    method VARCHAR,
    smoothing DOUBLE,
    transition_strength DOUBLE,
    observations INTEGER,
    accuracy_pct DOUBLE,
    log_loss DOUBLE,
    brier_score DOUBLE,
    switch_rate_pct DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, method)
);

CREATE TABLE IF NOT EXISTS m31_forward_return_validation(
    run_id VARCHAR,
    signal_source VARCHAR,
    regime VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    observations INTEGER,
    mean_forward_return_pct DOUBLE,
    median_forward_return_pct DOUBLE,
    positive_return_rate_pct DOUBLE,
    annualized_information_ratio DOUBLE,
    worst_forward_return_pct DOUBLE,
    best_forward_return_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, signal_source, regime, asset_id, horizon_days)
);

CREATE TABLE IF NOT EXISTS m31_regime_economic_scorecard(
    run_id VARCHAR,
    signal_source VARCHAR,
    regime VARCHAR,
    horizon_days INTEGER,
    observations INTEGER,
    cross_asset_return_spread_pct DOUBLE,
    risk_on_minus_btc_pct DOUBLE,
    btc_mean_return_pct DOUBLE,
    alt_mean_return_pct DOUBLE,
    positive_asset_share_pct DOUBLE,
    economic_separation_score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, signal_source, regime, horizon_days)
);

CREATE TABLE IF NOT EXISTS m31_global_feature_validation(
    run_id VARCHAR,
    feature_key VARCHAR,
    mean_absolute_contribution DOUBLE,
    contribution_std DOUBLE,
    positive_support_rate_pct DOUBLE,
    top_driver_rate_pct DOUBLE,
    stability_score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key)
);

CREATE TABLE IF NOT EXISTS m31_disagreement_outcomes(
    run_id VARCHAR,
    disagreement_group VARCHAR,
    horizon_days INTEGER,
    observations INTEGER,
    btc_mean_return_pct DOUBLE,
    alt_mean_return_pct DOUBLE,
    positive_btc_rate_pct DOUBLE,
    positive_alt_rate_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, disagreement_group, horizon_days)
);

CREATE TABLE IF NOT EXISTS m31_research_summary(
    run_id VARCHAR PRIMARY KEY,
    selected_calibration VARCHAR,
    selected_persistence_method VARCHAR,
    selected_accuracy_pct DOUBLE,
    selected_log_loss DOUBLE,
    selected_brier_score DOUBLE,
    clean_economic_separation DOUBLE,
    legacy_economic_separation DOUBLE,
    disagreement_information_value DOUBLE,
    investment_value_score DOUBLE,
    validation_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m31_calibration_comparison AS
SELECT * FROM m31_calibration_comparison WHERE run_id=(SELECT run_id FROM module31_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY selected DESC, multiclass_log_loss;
CREATE OR REPLACE VIEW latest_m31_persistence_validation AS
SELECT * FROM m31_persistence_validation WHERE run_id=(SELECT run_id FROM module31_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY selected DESC, log_loss;
CREATE OR REPLACE VIEW latest_m31_forward_return_validation AS
SELECT * FROM m31_forward_return_validation WHERE run_id=(SELECT run_id FROM module31_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY signal_source, regime, horizon_days, asset_id;
CREATE OR REPLACE VIEW latest_m31_regime_economic_scorecard AS
SELECT * FROM m31_regime_economic_scorecard WHERE run_id=(SELECT run_id FROM module31_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY signal_source, horizon_days, economic_separation_score DESC;
CREATE OR REPLACE VIEW latest_m31_global_feature_validation AS
SELECT * FROM m31_global_feature_validation WHERE run_id=(SELECT run_id FROM module31_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY stability_score DESC;
CREATE OR REPLACE VIEW latest_m31_disagreement_outcomes AS
SELECT * FROM m31_disagreement_outcomes WHERE run_id=(SELECT run_id FROM module31_runs ORDER BY started_at_utc DESC LIMIT 1) ORDER BY horizon_days, disagreement_group;
CREATE OR REPLACE VIEW latest_m31_research_summary AS
SELECT * FROM m31_research_summary WHERE run_id=(SELECT run_id FROM module31_runs ORDER BY started_at_utc DESC LIMIT 1);
"""

CORE_ASSETS = ['bitcoin','ethereum','solana','chainlink','xrp','avalanche']

def utcnow(): return datetime.now(timezone.utc)

class Module31Runner:
    def __init__(self):
        self.settings,_=load_all(); self.conn=connect(self.settings)
        self.conn.execute(MODULE30_SCHEMA); self.conn.execute(MODULE31_SCHEMA)
        self.cfg=self.settings['module31']; self.run_id=str(uuid.uuid4()); self.started=utcnow()
        row=self.conn.execute("SELECT run_id FROM module30_runs WHERE status='SUCCESS' ORDER BY started_at_utc DESC LIMIT 1").fetchone()
        if row is None: raise RuntimeError('No successful Module 30 run is available.')
        self.source_run=str(row[0]); self.classes=canonical_classes()

    def upsert(self, table, frame):
        if frame.empty: return
        self.conn.register('_m31_stage', frame); cols=','.join(frame.columns)
        self.conn.execute(f'INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _m31_stage')
        self.conn.unregister('_m31_stage')

    def history(self):
        p=self.conn.execute('SELECT observation_date,regime,probability FROM clean_probability_history WHERE run_id=? ORDER BY observation_date,regime',[self.source_run]).fetchdf()
        h=self.conn.execute('SELECT observation_date,actual_legacy_regime,clean_regime,model_agreement FROM clean_regime_history WHERE run_id=? ORDER BY observation_date',[self.source_run]).fetchdf()
        p['observation_date']=pd.to_datetime(p['observation_date']); h['observation_date']=pd.to_datetime(h['observation_date'])
        matrix=p.pivot(index='observation_date',columns='regime',values='probability').reindex(columns=self.classes)
        h=h.set_index('observation_date').reindex(matrix.index)
        validate_probability_matrix(matrix.to_numpy(), self.classes)
        return matrix,h

    def prices(self):
        f=self.conn.execute("SELECT asset_id,observation_date,price_usd FROM canonical_market_daily WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche') AND price_usd IS NOT NULL ORDER BY observation_date,asset_id").fetchdf()
        f['observation_date']=pd.to_datetime(f['observation_date'])
        return f.pivot(index='observation_date',columns='asset_id',values='price_usd').sort_index()

    def calibrations(self, probs, labels):
        raw=probs.to_numpy(); y=np.asarray(labels)
        rows=[]; methods={}
        # Identity
        methods['IDENTITY']=raw
        # Multinomial Platt
        model=LogisticRegression(max_iter=2500,class_weight='balanced',C=.75,random_state=820)
        model.fit(np.log(np.clip(raw,1e-9,1)), y)
        out=model.predict_proba(np.log(np.clip(raw,1e-9,1)))
        aligned=np.zeros_like(raw); idx={c:i for i,c in enumerate(self.classes)}
        for j,c in enumerate(model.classes_): aligned[:,idx[c]]=out[:,j]
        methods['PLATT_MULTICLASS']=aligned/aligned.sum(axis=1,keepdims=True)
        # Top-class isotonic confidence, preserving relative non-top shares.
        top=raw.argmax(axis=1); top_conf=raw.max(axis=1); correct=(self.classes[top]==y).astype(float)
        iso=IsotonicRegression(out_of_bounds='clip')
        if len(np.unique(top_conf))>1 and len(np.unique(correct))>1:
            iso.fit(top_conf,correct); calibrated_top=np.clip(iso.predict(top_conf),1e-6,1-1e-6)
            iso_probs=raw.copy()
            for i in range(len(raw)):
                rest=raw[i].copy(); rest[top[i]]=0; s=rest.sum()
                iso_probs[i]=rest*(1-calibrated_top[i])/s if s>0 else np.repeat((1-calibrated_top[i])/(len(self.classes)-1),len(self.classes))
                iso_probs[i,top[i]]=calibrated_top[i]
            methods['ISOTONIC_TOPCLASS']=iso_probs
        best=None
        for name,matrix in methods.items():
            validate_probability_matrix(matrix,self.classes)
            ll=log_loss(y,matrix,labels=self.classes.tolist()); br=multiclass_brier_score(matrix,y,self.classes)
            mae=float(np.mean(np.abs(matrix.max(axis=1)-(self.classes[matrix.argmax(axis=1)]==y).astype(float))))
            rows.append({'run_id':self.run_id,'method':name,'observations':len(y),'multiclass_log_loss':ll,'multiclass_brier_score':br,'top_class_mae':mae,'selected':False,'calculated_at_utc':utcnow()})
            if best is None or (ll,br)<(best[1],best[2]): best=(name,ll,br,matrix)
        for r in rows: r['selected']=r['method']==best[0]
        return pd.DataFrame(rows),best

    def persistence(self, calibrated, labels):
        y=np.asarray(labels); transition=pd.DataFrame(1.0,index=self.classes,columns=self.classes)
        for a,b in zip(y[:-1],y[1:]): transition.loc[a,b]+=1
        transition=transition.div(transition.sum(axis=1),axis=0)
        candidates=[]
        for smoothing in self.cfg['persistence']['smoothing_values']:
            for strength in self.cfg['persistence']['transition_strength_values']:
                out=[]; previous=None; previous_regime=y[0]
                for i,p in enumerate(calibrated):
                    prior=transition.loc[previous_regime].reindex(self.classes).to_numpy()
                    q=p*np.power(np.clip(prior,1e-8,1),float(strength)); q=q/q.sum()
                    if previous is not None: q=float(smoothing)*previous+(1-float(smoothing))*q; q=q/q.sum()
                    out.append(q); previous=q; previous_regime=self.classes[int(np.argmax(q))]
                out=np.vstack(out); pred=self.classes[out.argmax(axis=1)]
                acc=float(np.mean(pred==y)*100); ll=log_loss(y,out,labels=self.classes.tolist()); br=multiclass_brier_score(out,y,self.classes)
                switch=float(np.mean(pred[1:]!=pred[:-1])*100) if len(pred)>1 else 0
                objective=acc-.12*ll-0.03*switch
                candidates.append((objective,smoothing,strength,acc,ll,br,switch,out))
        candidates.sort(key=lambda x:x[0],reverse=True); best=candidates[0]
        rows=[]
        for i,c in enumerate(candidates):
            rows.append({'run_id':self.run_id,'method':f'PERSIST_{i+1:03d}','smoothing':float(c[1]),'transition_strength':float(c[2]),'observations':len(y),'accuracy_pct':c[3],'log_loss':c[4],'brier_score':c[5],'switch_rate_pct':c[6],'selected':i==0,'calculated_at_utc':utcnow()})
        return pd.DataFrame(rows),best

    def forward_returns(self, clean_labels, legacy_labels, prices):
        rows=[]; scores=[]
        sources={'CLEAN':clean_labels,'LEGACY':legacy_labels}
        horizons=[int(x) for x in self.cfg['forward_returns']['horizons_days']]
        for source,labels in sources.items():
            labels=labels.reindex(prices.index).ffill()
            for horizon in horizons:
                forward=prices.shift(-horizon)/prices-1
                for regime in self.classes:
                    mask=labels==regime
                    asset_means=[]; positive_assets=[]
                    for asset in prices.columns:
                        s=forward.loc[mask,asset].dropna()
                        if s.empty: continue
                        mean=float(s.mean()*100); asset_means.append(mean); positive_assets.append(mean>0)
                        std=float(s.std())
                        ir=float((s.mean()/std)*math.sqrt(365/horizon)) if std>0 else 0.0
                        rows.append({'run_id':self.run_id,'signal_source':source,'regime':regime,'asset_id':asset,'horizon_days':horizon,'observations':len(s),'mean_forward_return_pct':mean,'median_forward_return_pct':float(s.median()*100),'positive_return_rate_pct':float((s>0).mean()*100),'annualized_information_ratio':ir,'worst_forward_return_pct':float(s.min()*100),'best_forward_return_pct':float(s.max()*100),'calculated_at_utc':utcnow()})
                    if asset_means:
                        btc=float(forward.loc[mask,'bitcoin'].dropna().mean()*100) if 'bitcoin' in forward else 0
                        alt_cols=[c for c in prices.columns if c!='bitcoin']; alt=float(forward.loc[mask,alt_cols].stack().mean()*100)
                        spread=float(max(asset_means)-min(asset_means)); separation=float(np.std(asset_means)+abs(alt-btc)*.5)
                        scores.append({'run_id':self.run_id,'signal_source':source,'regime':regime,'horizon_days':horizon,'observations':int(mask.sum()),'cross_asset_return_spread_pct':spread,'risk_on_minus_btc_pct':alt-btc,'btc_mean_return_pct':btc,'alt_mean_return_pct':alt,'positive_asset_share_pct':float(np.mean(positive_assets)*100),'economic_separation_score':separation,'calculated_at_utc':utcnow()})
        return pd.DataFrame(rows),pd.DataFrame(scores)

    def disagreement(self, history, prices):
        rows=[]; horizons=[int(x) for x in self.cfg['forward_returns']['horizons_days']]
        history=history.reindex(prices.index)
        groups=pd.Series(np.where(history['clean_regime']==history['actual_legacy_regime'],'AGREE','DISAGREE'),index=history.index)
        for horizon in horizons:
            f=prices.shift(-horizon)/prices-1
            for group in ['AGREE','DISAGREE']:
                mask=groups==group; btc=f.loc[mask,'bitcoin'].dropna(); alt=f.loc[mask,[c for c in prices.columns if c!='bitcoin']].stack().dropna()
                if btc.empty or alt.empty: continue
                rows.append({'run_id':self.run_id,'disagreement_group':group,'horizon_days':horizon,'observations':int(mask.sum()),'btc_mean_return_pct':float(btc.mean()*100),'alt_mean_return_pct':float(alt.mean()*100),'positive_btc_rate_pct':float((btc>0).mean()*100),'positive_alt_rate_pct':float((alt>0).mean()*100),'calculated_at_utc':utcnow()})
        return pd.DataFrame(rows)

    def feature_global(self):
        f=self.conn.execute('SELECT feature_key,probability_contribution,rank FROM clean_feature_contributions WHERE run_id=?',[self.source_run]).fetchdf()
        if f.empty: return pd.DataFrame()
        rows=[]
        for feature,g in f.groupby('feature_key'):
            absmean=float(g['probability_contribution'].abs().mean())
            rows.append({'run_id':self.run_id,'feature_key':feature,'mean_absolute_contribution':absmean,'contribution_std':float(g['probability_contribution'].std() or 0),'positive_support_rate_pct':float((g['probability_contribution']>0).mean()*100),'top_driver_rate_pct':float((g['rank']==1).mean()*100),'stability_score':float(absmean/(1+float(g['probability_contribution'].std() or 0))*100),'calculated_at_utc':utcnow()})
        return pd.DataFrame(rows)

    def run(self):
        self.conn.execute(
            """
            INSERT INTO module31_runs(
                run_id,
                source_module30_run_id,
                started_at_utc,
                completed_at_utc,
                status,
                historical_rows,
                forward_return_rows,
                calibration_rows,
                persistence_rows,
                investment_value_score,
                validation_status,
                recommendation,
                notes,
                platform_version
            )
            VALUES(
                ?, ?, ?, NULL, 'RUNNING',
                0, 0, 0, 0,
                NULL, NULL, NULL, NULL,
                '8.2.2'
            )
            """,
            [self.run_id, self.source_run, self.started],
        )
        try:
            probs,hist=self.history(); calibration,bestcal=self.calibrations(probs,hist['actual_legacy_regime'].to_numpy()); persistence,bestpersist=self.persistence(bestcal[3],hist['actual_legacy_regime'].to_numpy())
            selected_probs=bestpersist[7]; selected_labels=pd.Series(self.classes[selected_probs.argmax(axis=1)],index=probs.index)
            prices=self.prices(); returns,scorecard=self.forward_returns(selected_labels,hist['actual_legacy_regime'],prices)
            disagreements=self.disagreement(hist,prices); feature=self.feature_global()
            for table,frame in [('m31_calibration_comparison',calibration),('m31_persistence_validation',persistence),('m31_forward_return_validation',returns),('m31_regime_economic_scorecard',scorecard),('m31_disagreement_outcomes',disagreements),('m31_global_feature_validation',feature)]: self.upsert(table,frame)
            clean_sep=float(scorecard.loc[scorecard.signal_source=='CLEAN','economic_separation_score'].mean())
            legacy_sep=float(scorecard.loc[scorecard.signal_source=='LEGACY','economic_separation_score'].mean())
            if not disagreements.empty:
                pivot=disagreements.pivot(index='horizon_days',columns='disagreement_group',values='btc_mean_return_pct')
                disagreement_value=float((pivot.get('DISAGREE',pd.Series(dtype=float))-pivot.get('AGREE',pd.Series(dtype=float))).abs().mean())
            else: disagreement_value=0.0
            value_score=float(50 + min((clean_sep-legacy_sep)*5,25) + min(disagreement_value,15) - min(bestpersist[4]*2,25))
            passed=(bestpersist[3]>=float(self.cfg['validation']['minimum_accuracy_pct']) and bestpersist[4]<=float(self.cfg['validation']['maximum_log_loss']) and clean_sep>=legacy_sep)
            status='PASSED' if passed else 'LIMITED'; rec='READY_FOR_ENSEMBLE_INTELLIGENCE' if passed else 'CONTINUE_RESEARCH_VALIDATION'
            summary=pd.DataFrame([{'run_id':self.run_id,'selected_calibration':bestcal[0],'selected_persistence_method':'PERSIST_001','selected_accuracy_pct':bestpersist[3],'selected_log_loss':bestpersist[4],'selected_brier_score':bestpersist[5],'clean_economic_separation':clean_sep,'legacy_economic_separation':legacy_sep,'disagreement_information_value':disagreement_value,'investment_value_score':value_score,'validation_status':status,'advancement_recommendation':rec,'calculated_at_utc':utcnow()}]); self.upsert('m31_research_summary',summary)
            self.conn.execute("UPDATE module31_runs SET completed_at_utc=?,status='SUCCESS',historical_rows=?,forward_return_rows=?,calibration_rows=?,persistence_rows=?,investment_value_score=?,validation_status=?,recommendation=?,notes=? WHERE run_id=?",[utcnow(),len(hist),len(returns),len(calibration),len(persistence),value_score,status,rec,'Investment usefulness is evaluated using forward returns; Module 30 remains OBSERVATION.',self.run_id])
            self.conn.close(); return summary.iloc[0].to_dict()
        except Exception as exc:
            self.conn.execute("UPDATE module31_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",[utcnow(),str(exc)[:1000],self.run_id]); self.conn.close(); raise

def run_module31(): return Module31Runner().run()
