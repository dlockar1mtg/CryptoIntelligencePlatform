from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.preprocessing import StandardScaler

from crypto_platform.platform import load_all, connect
from crypto_platform.module25 import MODULE25_SCHEMA
from crypto_platform.module29 import MODULE29_SCHEMA
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.module31 import MODULE31_SCHEMA
from crypto_platform.ml.classes import canonical_classes
from crypto_platform.ml.models import (
    fit_clean_models,
    predict_component_probabilities,
    blend_probabilities,
)
from crypto_platform.ml.validation import (
    multiclass_brier_score,
    validate_probability_matrix,
)

MODULE32_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module32_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module31_run_id VARCHAR,
    source_module30_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    feature_stability_rows INTEGER,
    probability_drift_rows INTEGER,
    retraining_policy_rows INTEGER,
    historical_stress_rows INTEGER,
    synthetic_stress_rows INTEGER,
    benchmark_rows INTEGER,
    best_retraining_policy VARCHAR,
    best_strategy VARCHAR,
    validation_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m32_feature_stability_history(
    run_id VARCHAR,
    fold_number INTEGER,
    training_start_date DATE,
    training_end_date DATE,
    testing_start_date DATE,
    testing_end_date DATE,
    feature_key VARCHAR,
    mean_absolute_contribution DOUBLE,
    contribution_std DOUBLE,
    positive_support_rate_pct DOUBLE,
    negative_support_rate_pct DOUBLE,
    sign_flip_rate_pct DOUBLE,
    mean_rank DOUBLE,
    rank_persistence_pct DOUBLE,
    stability_score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number, feature_key)
);

CREATE TABLE IF NOT EXISTS m32_feature_stability_summary(
    run_id VARCHAR,
    feature_key VARCHAR,
    folds INTEGER,
    mean_absolute_contribution DOUBLE,
    contribution_std DOUBLE,
    positive_support_rate_pct DOUBLE,
    sign_flip_rate_pct DOUBLE,
    mean_rank DOUBLE,
    rank_persistence_pct DOUBLE,
    stability_score DOUBLE,
    evidence_grade VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key)
);

CREATE TABLE IF NOT EXISTS m32_probability_drift(
    run_id VARCHAR,
    window_end_date DATE,
    window_days INTEGER,
    observations INTEGER,
    mean_top_probability DOUBLE,
    mean_entropy DOUBLE,
    accuracy_pct DOUBLE,
    log_loss DOUBLE,
    brier_score DOUBLE,
    switch_rate_pct DOUBLE,
    disagreement_rate_pct DOUBLE,
    probability_psi DOUBLE,
    calibration_deterioration_pct DOUBLE,
    drift_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, window_end_date, window_days)
);

CREATE TABLE IF NOT EXISTS m32_retraining_policy_validation(
    run_id VARCHAR,
    policy_key VARCHAR,
    retrain_interval_days INTEGER,
    observations INTEGER,
    retrain_count INTEGER,
    accuracy_pct DOUBLE,
    log_loss DOUBLE,
    brier_score DOUBLE,
    switch_rate_pct DOUBLE,
    mean_top_probability DOUBLE,
    computation_score DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, policy_key)
);

CREATE TABLE IF NOT EXISTS m32_historical_stress_validation(
    run_id VARCHAR,
    stress_episode_id VARCHAR,
    episode_type VARCHAR,
    start_date DATE,
    end_date DATE,
    observations INTEGER,
    btc_return_pct DOUBLE,
    btc_max_drawdown_pct DOUBLE,
    mean_clean_confidence DOUBLE,
    clean_switches INTEGER,
    dominant_clean_regime VARCHAR,
    dominant_legacy_regime VARCHAR,
    regime_agreement_pct DOUBLE,
    post_30d_btc_return_pct DOUBLE,
    stress_response_score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, stress_episode_id)
);

CREATE TABLE IF NOT EXISTS m32_synthetic_stress_validation(
    run_id VARCHAR,
    scenario_key VARCHAR,
    feature_key VARCHAR,
    shock_sigma DOUBLE,
    baseline_regime VARCHAR,
    stressed_regime VARCHAR,
    baseline_probability DOUBLE,
    stressed_probability DOUBLE,
    probability_change DOUBLE,
    model_agreement DOUBLE,
    monotonic_expected BOOLEAN,
    monotonic_passed BOOLEAN,
    response_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, scenario_key)
);

CREATE TABLE IF NOT EXISTS m32_benchmark_daily(
    run_id VARCHAR,
    observation_date DATE,
    strategy_key VARCHAR,
    daily_return DOUBLE,
    cumulative_return DOUBLE,
    turnover DOUBLE,
    transaction_cost DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, strategy_key)
);

CREATE TABLE IF NOT EXISTS m32_benchmark_summary(
    run_id VARCHAR,
    strategy_key VARCHAR,
    observations INTEGER,
    cumulative_return_pct DOUBLE,
    cagr_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    sortino_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    calmar_ratio DOUBLE,
    var_95_pct DOUBLE,
    cvar_95_pct DOUBLE,
    profitable_months_pct DOUBLE,
    annualized_turnover_pct DOUBLE,
    total_transaction_cost_pct DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, strategy_key)
);

CREATE TABLE IF NOT EXISTS m32_validation_summary(
    run_id VARCHAR PRIMARY KEY,
    stable_features INTEGER,
    mean_feature_stability_score DOUBLE,
    current_probability_drift_status VARCHAR,
    best_retraining_policy VARCHAR,
    best_retraining_log_loss DOUBLE,
    historical_stress_episodes INTEGER,
    synthetic_stress_pass_rate_pct DOUBLE,
    best_strategy VARCHAR,
    best_strategy_sharpe DOUBLE,
    btc_sharpe DOUBLE,
    best_strategy_max_drawdown_pct DOUBLE,
    btc_max_drawdown_pct DOUBLE,
    validation_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m32_feature_stability_history AS
SELECT * FROM m32_feature_stability_history
WHERE run_id=(SELECT run_id FROM module32_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY fold_number, stability_score DESC;

CREATE OR REPLACE VIEW latest_m32_feature_stability_summary AS
SELECT * FROM m32_feature_stability_summary
WHERE run_id=(SELECT run_id FROM module32_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY stability_score DESC;

CREATE OR REPLACE VIEW latest_m32_probability_drift AS
SELECT * FROM m32_probability_drift
WHERE run_id=(SELECT run_id FROM module32_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY window_end_date DESC, window_days;

CREATE OR REPLACE VIEW latest_m32_retraining_policy_validation AS
SELECT * FROM m32_retraining_policy_validation
WHERE run_id=(SELECT run_id FROM module32_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY selected DESC, log_loss;

CREATE OR REPLACE VIEW latest_m32_historical_stress_validation AS
SELECT * FROM m32_historical_stress_validation
WHERE run_id=(SELECT run_id FROM module32_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY start_date;

CREATE OR REPLACE VIEW latest_m32_synthetic_stress_validation AS
SELECT * FROM m32_synthetic_stress_validation
WHERE run_id=(SELECT run_id FROM module32_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY feature_key, shock_sigma;

CREATE OR REPLACE VIEW latest_m32_benchmark_daily AS
SELECT * FROM m32_benchmark_daily
WHERE run_id=(SELECT run_id FROM module32_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY observation_date, strategy_key;

CREATE OR REPLACE VIEW latest_m32_benchmark_summary AS
SELECT * FROM m32_benchmark_summary
WHERE run_id=(SELECT run_id FROM module32_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY selected DESC, sharpe_ratio DESC;

CREATE OR REPLACE VIEW latest_m32_validation_summary AS
SELECT * FROM m32_validation_summary
WHERE run_id=(SELECT run_id FROM module32_runs ORDER BY started_at_utc DESC LIMIT 1);
"""

CORE_ASSETS = [
    "bitcoin", "ethereum", "solana",
    "chainlink", "xrp", "avalanche",
]

REGIME_RISK = {
    "LIQUIDITY_EXPANSION": 1.00,
    "MOMENTUM_BULL": 1.00,
    "RECOVERY": 0.82,
    "RANGE_BOUND": 0.48,
    "MACRO_STRESS": 0.20,
    "VOLATILITY_SHOCK": 0.10,
}

REGIME_WEIGHTS = {
    "LIQUIDITY_EXPANSION": np.array([.30,.24,.16,.10,.10,.10]),
    "MOMENTUM_BULL": np.array([.30,.25,.18,.10,.09,.08]),
    "RECOVERY": np.array([.28,.24,.17,.11,.10,.10]),
    "RANGE_BOUND": np.array([.42,.28,.08,.08,.08,.06]),
    "MACRO_STRESS": np.array([.60,.24,.04,.04,.04,.04]),
    "VOLATILITY_SHOCK": np.array([.70,.20,.025,.025,.025,.025]),
}


def utcnow():
    return datetime.now(timezone.utc)


def entropy(probabilities):
    probabilities = np.clip(np.asarray(probabilities, dtype=float), 1e-12, 1)
    return -np.sum(probabilities * np.log(probabilities), axis=1)


def psi(expected, actual, bins=10):
    expected = pd.Series(expected).dropna().astype(float)
    actual = pd.Series(actual).dropna().astype(float)
    if len(expected) < 20 or len(actual) < 10:
        return 0.0
    edges = np.unique(np.quantile(expected, np.linspace(0,1,bins+1)))
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    e,_ = np.histogram(expected,bins=edges)
    a,_ = np.histogram(actual,bins=edges)
    ep = np.clip(e/max(e.sum(),1),1e-6,None)
    ap = np.clip(a/max(a.sum(),1),1e-6,None)
    return float(np.sum((ap-ep)*np.log(ap/ep)))


class Module32Runner:
    def __init__(self):
        self.settings,_ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE25_SCHEMA)
        self.conn.execute(MODULE29_SCHEMA)
        self.conn.execute(MODULE30_SCHEMA)
        self.conn.execute(MODULE31_SCHEMA)
        self.conn.execute(MODULE32_SCHEMA)
        self.cfg = self.settings["module32"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        row = self.conn.execute(
            "SELECT run_id,source_module30_run_id FROM module31_runs "
            "WHERE status='SUCCESS' ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("No successful Module 31 run is available.")
        self.source_m31 = str(row[0])
        self.source_m30 = str(row[1])
        frow = self.conn.execute(
            "SELECT stable_feature_list FROM m29_research_summary "
            "WHERE validation_status='PASSED' ORDER BY calculated_at_utc DESC LIMIT 1"
        ).fetchone()
        if frow is None:
            raise RuntimeError("No passed Module 29 stable feature registry is available.")
        self.features = list(json.loads(frow[0]))
        self.classes = canonical_classes()

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m32_stage", frame)
        cols = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({cols}) "
            f"SELECT {cols} FROM _m32_stage"
        )
        self.conn.unregister("_m32_stage")

    def feature_label_data(self):
        features = self.conn.execute(
            "SELECT * FROM m25_regime_features WHERE run_id=("
            "SELECT run_id FROM module25_runs WHERE status='SUCCESS' "
            "ORDER BY started_at_utc DESC LIMIT 1) ORDER BY observation_date"
        ).fetchdf()
        labels = self.conn.execute(
            "SELECT observation_date,dominant_regime FROM m25_regime_probabilities "
            "WHERE run_id=(SELECT run_id FROM module25_runs WHERE status='SUCCESS' "
            "ORDER BY started_at_utc DESC LIMIT 1) ORDER BY observation_date"
        ).fetchdf()
        features["observation_date"] = pd.to_datetime(features["observation_date"])
        labels["observation_date"] = pd.to_datetime(labels["observation_date"])
        frame = features.set_index("observation_date")[self.features].join(
            labels.set_index("observation_date")
        ).replace([np.inf,-np.inf],np.nan).dropna()
        return frame

    def clean_history(self):
        p = self.conn.execute(
            "SELECT observation_date,regime,probability FROM clean_probability_history "
            "WHERE run_id=? ORDER BY observation_date,regime",[self.source_m30]
        ).fetchdf()
        h = self.conn.execute(
            "SELECT observation_date,actual_legacy_regime,clean_regime,model_agreement "
            "FROM clean_regime_history WHERE run_id=? ORDER BY observation_date",
            [self.source_m30]
        ).fetchdf()
        p["observation_date"] = pd.to_datetime(p["observation_date"])
        h["observation_date"] = pd.to_datetime(h["observation_date"])
        matrix = p.pivot(index="observation_date",columns="regime",values="probability").reindex(columns=self.classes)
        history = h.set_index("observation_date").reindex(matrix.index)
        validate_probability_matrix(matrix.to_numpy(),self.classes)
        return matrix,history

    def prices(self):
        f = self.conn.execute(
            "SELECT asset_id,observation_date,price_usd FROM canonical_market_daily "
            "WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche') "
            "AND price_usd IS NOT NULL ORDER BY observation_date,asset_id"
        ).fetchdf()
        f["observation_date"] = pd.to_datetime(f["observation_date"])
        return f.pivot(index="observation_date",columns="asset_id",values="price_usd").reindex(columns=CORE_ASSETS).sort_index()

    def feature_stability(self, frame):
        min_train = int(self.cfg["feature_stability"]["minimum_training_days"])
        test_days = int(self.cfg["feature_stability"]["test_days"])
        rows=[]; fold=0; start=min_train
        while start < len(frame):
            end=min(start+test_days,len(frame)); train=frame.iloc[:start]; test=frame.iloc[start:end]
            if test.empty: break
            fold += 1
            scaler=StandardScaler(); xs=scaler.fit_transform(train[self.features])
            model=LogisticRegression(
                max_iter=2500,class_weight="balanced",random_state=830+fold
            ).fit(xs,train["dominant_regime"])
            standardized = pd.DataFrame(
                scaler.transform(test[self.features]),
                index=test.index,columns=self.features
            )
            class_index={c:i for i,c in enumerate(model.classes_)}
            predicted=model.predict(scaler.transform(test[self.features]))
            contributions=pd.DataFrame(index=test.index,columns=self.features,dtype=float)
            for date,pred in zip(test.index,predicted):
                coef=model.coef_[class_index[pred]]
                contributions.loc[date]=standardized.loc[date].to_numpy()*coef
            abs_rank=contributions.abs().rank(axis=1,ascending=False,method="average")
            for feature in self.features:
                values=contributions[feature].astype(float)
                signs=np.sign(values.to_numpy())
                flips=float(np.mean(signs[1:]!=signs[:-1])*100) if len(signs)>1 else 0.0
                mean_rank=float(abs_rank[feature].mean())
                rank_persistence=float((abs_rank[feature]<=3).mean()*100)
                std=float(values.std(ddof=1)) if len(values)>1 else 0.0
                absmean=float(values.abs().mean())
                score=float(
                    35*rank_persistence/100
                    +25*(1-min(flips/50,1))
                    +25*(absmean/(absmean+std+1e-9))
                    +15*max(0,1-mean_rank/max(len(self.features),1))
                )
                rows.append({
                    "run_id":self.run_id,"fold_number":fold,
                    "training_start_date":train.index.min().date(),
                    "training_end_date":train.index.max().date(),
                    "testing_start_date":test.index.min().date(),
                    "testing_end_date":test.index.max().date(),
                    "feature_key":feature,
                    "mean_absolute_contribution":absmean,
                    "contribution_std":std,
                    "positive_support_rate_pct":float((values>0).mean()*100),
                    "negative_support_rate_pct":float((values<0).mean()*100),
                    "sign_flip_rate_pct":flips,
                    "mean_rank":mean_rank,
                    "rank_persistence_pct":rank_persistence,
                    "stability_score":score,
                    "calculated_at_utc":utcnow(),
                })
            start=end
        history=pd.DataFrame(rows)
        summary=[]
        for feature,g in history.groupby("feature_key"):
            score=float(g["stability_score"].mean())
            summary.append({
                "run_id":self.run_id,"feature_key":feature,"folds":len(g),
                "mean_absolute_contribution":float(g["mean_absolute_contribution"].mean()),
                "contribution_std":float(g["mean_absolute_contribution"].std(ddof=1)) if len(g)>1 else 0.0,
                "positive_support_rate_pct":float(g["positive_support_rate_pct"].mean()),
                "sign_flip_rate_pct":float(g["sign_flip_rate_pct"].mean()),
                "mean_rank":float(g["mean_rank"].mean()),
                "rank_persistence_pct":float(g["rank_persistence_pct"].mean()),
                "stability_score":score,
                "evidence_grade":"A" if score>=75 else "B" if score>=60 else "C" if score>=45 else "D",
                "calculated_at_utc":utcnow(),
            })
        return history,pd.DataFrame(summary)

    def probability_drift(self, probs, hist):
        baseline_days=int(self.cfg["probability_drift"]["baseline_days"])
        windows=[int(x) for x in self.cfg["probability_drift"]["window_days"]]
        baseline=probs.iloc[:min(baseline_days,len(probs))]
        base_top=baseline.max(axis=1)
        base_labels=hist.loc[baseline.index,"actual_legacy_regime"]
        base_loss=log_loss(base_labels,baseline.to_numpy(),labels=self.classes.tolist())
        rows=[]
        for window in windows:
            for end in range(window,len(probs)+1,window):
                block=probs.iloc[end-window:end]
                h=hist.reindex(block.index)
                labels=h["actual_legacy_regime"].to_numpy()
                pred=self.classes[block.to_numpy().argmax(axis=1)]
                ll=log_loss(labels,block.to_numpy(),labels=self.classes.tolist())
                br=multiclass_brier_score(block.to_numpy(),labels,self.classes)
                switch=float(np.mean(pred[1:]!=pred[:-1])*100) if len(pred)>1 else 0.0
                disagreement=float((h["model_agreement"]<.55).mean()*100)
                pscore=psi(base_top,block.max(axis=1))
                deterioration=float((ll/base_loss-1)*100) if base_loss>0 else 0.0
                critical=pscore>=.25 or deterioration>=40 or disagreement>=50
                warning=pscore>=.10 or deterioration>=20 or disagreement>=35
                status="CRITICAL" if critical else "WARNING" if warning else "STABLE"
                rows.append({
                    "run_id":self.run_id,"window_end_date":block.index.max().date(),
                    "window_days":window,"observations":len(block),
                    "mean_top_probability":float(block.max(axis=1).mean()),
                    "mean_entropy":float(entropy(block.to_numpy()).mean()),
                    "accuracy_pct":float(np.mean(pred==labels)*100),
                    "log_loss":ll,"brier_score":br,"switch_rate_pct":switch,
                    "disagreement_rate_pct":disagreement,
                    "probability_psi":pscore,
                    "calibration_deterioration_pct":deterioration,
                    "drift_status":status,"calculated_at_utc":utcnow(),
                })
        return pd.DataFrame(rows)

    def retraining_policies(self, frame):
        policies={
            "STATIC_EXPANDING":0,
            "MONTHLY_30D":30,
            "BIMONTHLY_60D":60,
            "QUARTERLY_90D":90,
            "SEMIANNUAL_180D":180,
        }
        min_train=int(self.cfg["retraining"]["minimum_training_days"])
        candidate_weight=float(self.cfg["retraining"]["gradient_weight"])
        results=[]
        for key,interval in policies.items():
            predictions=[]; probabilities=[]; actual=[]; retrains=0
            bundle=None; last_train=None
            for i in range(min_train,len(frame)):
                need = bundle is None or (interval>0 and (last_train is None or i-last_train>=interval))
                if key=="STATIC_EXPANDING":
                    need=bundle is None
                if need:
                    train=frame.iloc[:i]
                    bundle=fit_clean_models(
                        train[self.features],train["dominant_regime"],830+retrains
                    )
                    retrains+=1; last_train=i
                x=frame.iloc[[i]][self.features]
                g,e=predict_component_probabilities(bundle,x,self.classes)
                p=blend_probabilities(g,e,candidate_weight)[0]
                probabilities.append(p)
                predictions.append(self.classes[int(np.argmax(p))])
                actual.append(frame.iloc[i]["dominant_regime"])
            matrix=np.vstack(probabilities)
            validate_probability_matrix(matrix,self.classes)
            acc=float(np.mean(np.asarray(predictions)==np.asarray(actual))*100)
            ll=log_loss(actual,matrix,labels=self.classes.tolist())
            br=multiclass_brier_score(matrix,actual,self.classes)
            switch=float(np.mean(np.asarray(predictions[1:])!=np.asarray(predictions[:-1]))*100)
            compute=100/(1+retrains)
            results.append({
                "run_id":self.run_id,"policy_key":key,
                "retrain_interval_days":interval,"observations":len(actual),
                "retrain_count":retrains,"accuracy_pct":acc,"log_loss":ll,
                "brier_score":br,"switch_rate_pct":switch,
                "mean_top_probability":float(matrix.max(axis=1).mean()),
                "computation_score":compute,"selected":False,
                "calculated_at_utc":utcnow(),
            })
        result=pd.DataFrame(results)
        result["objective"]=(
            result["accuracy_pct"]-12*result["log_loss"]
            -0.04*result["switch_rate_pct"]+0.02*result["computation_score"]
        )
        best=result.sort_values("objective",ascending=False).iloc[0]["policy_key"]
        result["selected"]=result["policy_key"]==best
        return result.drop(columns="objective")

    def historical_stress(self, prices, probs, hist):
        btc=prices["bitcoin"].dropna()
        ret=btc.pct_change()
        vol=ret.rolling(30).std()*math.sqrt(365)
        peak=btc.cummax(); drawdown=btc/peak-1
        flags=pd.Series(index=btc.index,dtype=object)
        flags.loc[drawdown<=-.20]="DRAWDOWN_20"
        flags.loc[vol>=vol.quantile(.90)]="VOLATILITY_SPIKE"
        recovery=btc.pct_change(30)>=.20
        flags.loc[recovery]="RAPID_RECOVERY"
        episodes=[]; current=None
        for date,value in flags.dropna().items():
            if current is None or value!=current["type"] or (date-current["last"]).days>3:
                if current is not None: episodes.append(current)
                current={"type":value,"start":date,"last":date}
            else:
                current["last"]=date
        if current is not None: episodes.append(current)
        rows=[]
        for idx,episode in enumerate(episodes,1):
            start,end=episode["start"],episode["last"]
            segment=btc.loc[start:end]
            if len(segment)<3: continue
            p=probs.reindex(segment.index).dropna()
            h=hist.reindex(p.index)
            if p.empty: continue
            pred=self.classes[p.to_numpy().argmax(axis=1)]
            legacy=h["actual_legacy_regime"].to_numpy()
            dominant_clean=pd.Series(pred).mode().iloc[0]
            dominant_legacy=pd.Series(legacy).mode().iloc[0]
            post_date=end+pd.Timedelta(days=30)
            future=btc.loc[btc.index>=post_date]
            post=float((future.iloc[0]/btc.loc[end]-1)*100) if not future.empty else np.nan
            dd=float((segment/segment.cummax()-1).min()*100)
            score=float(
                min(abs(dd),50)*.5
                +min(float(p.max(axis=1).mean()*100),100)*.25
                +float(np.mean(pred==legacy)*100)*.25
            )
            rows.append({
                "run_id":self.run_id,
                "stress_episode_id":f"STRESS_{idx:03d}",
                "episode_type":episode["type"],
                "start_date":start.date(),"end_date":end.date(),
                "observations":len(segment),
                "btc_return_pct":float((segment.iloc[-1]/segment.iloc[0]-1)*100),
                "btc_max_drawdown_pct":dd,
                "mean_clean_confidence":float(p.max(axis=1).mean()),
                "clean_switches":int(np.sum(pred[1:]!=pred[:-1])),
                "dominant_clean_regime":dominant_clean,
                "dominant_legacy_regime":dominant_legacy,
                "regime_agreement_pct":float(np.mean(pred==legacy)*100),
                "post_30d_btc_return_pct":post,
                "stress_response_score":score,
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows)

    def synthetic_stress(self, frame):
        train=frame.iloc[:-1]; current=frame.iloc[[-1]]
        bundle=fit_clean_models(train[self.features],train["dominant_regime"],839)
        g,e=predict_component_probabilities(bundle,current[self.features],self.classes)
        baseline=blend_probabilities(g,e,.60)[0]
        base_idx=int(np.argmax(baseline)); base_regime=self.classes[base_idx]
        shock_direction={
            "liquidity_score":-1,
            "btc_volatility_90d":1,
            "btc_distance_sma200":-1,
            "stablecoin_growth_30d":-1,
            "core_breadth":-1,
        }
        rows=[]
        for feature in self.features:
            direction=shock_direction.get(feature,-1)
            std=float(train[feature].std())
            previous_change=None
            for sigma in [1.0,2.0,3.0]:
                stressed=current[self.features].copy()
                stressed.iloc[0,stressed.columns.get_loc(feature)] += direction*sigma*std
                sg,se=predict_component_probabilities(bundle,stressed,self.classes)
                probability=blend_probabilities(sg,se,.60)[0]
                idx=int(np.argmax(probability))
                change=float(probability[base_idx]-baseline[base_idx])
                monotonic=True
                passed=True if previous_change is None else abs(change)>=abs(previous_change)-1e-9
                previous_change=change
                agreement=float(1-.5*np.abs(sg[0]-se[0]).sum())
                rows.append({
                    "run_id":self.run_id,
                    "scenario_key":f"{feature.upper()}_{int(sigma)}SIGMA",
                    "feature_key":feature,"shock_sigma":direction*sigma,
                    "baseline_regime":base_regime,
                    "stressed_regime":self.classes[idx],
                    "baseline_probability":float(baseline[base_idx]),
                    "stressed_probability":float(probability[base_idx]),
                    "probability_change":change,
                    "model_agreement":agreement,
                    "monotonic_expected":monotonic,
                    "monotonic_passed":bool(passed),
                    "response_status":"PASS" if passed else "FAIL",
                    "calculated_at_utc":utcnow(),
                })
        return pd.DataFrame(rows)

    def benchmark(self, prices, probs, hist):
        returns=prices.pct_change().dropna(how="all").fillna(0)
        common=returns.index.intersection(probs.index)
        returns=returns.loc[common]
        p=probs.reindex(common)
        legacy=hist.reindex(common)["actual_legacy_regime"].ffill()
        clean=pd.Series(self.classes[p.to_numpy().argmax(axis=1)],index=common)
        costs=float(self.cfg["benchmarks"]["transaction_cost_bps"])/10000
        strategies={}
        strategies["BTC_BUY_HOLD"]=pd.DataFrame(
            np.tile(np.array([1,0,0,0,0,0]),(len(common),1)),
            index=common,columns=CORE_ASSETS
        )
        strategies["EQUAL_WEIGHT_6"]=pd.DataFrame(
            np.tile(np.repeat(1/6,6),(len(common),1)),index=common,columns=CORE_ASSETS
        )
        strategies["BTC_ETH_60_40"]=pd.DataFrame(
            np.tile(np.array([.6,.4,0,0,0,0]),(len(common),1)),index=common,columns=CORE_ASSETS
        )
        # Inverse-volatility static daily target.
        vol=returns.rolling(90,min_periods=30).std().replace(0,np.nan)
        inv=1/vol; strategies["RISK_PARITY_6"]=inv.div(inv.sum(axis=1),axis=0).fillna(1/6)
        # Vol-target BTC, remainder cash (cash return is zero).
        btc_vol=returns["bitcoin"].rolling(30,min_periods=20).std()*math.sqrt(365)
        exposure=(.30/btc_vol).clip(0,1).fillna(.25)
        vt=pd.DataFrame(0.0,index=common,columns=CORE_ASSETS); vt["bitcoin"]=exposure
        strategies["VOL_TARGET_BTC"]=vt
        def regime_frame(labels):
            out=pd.DataFrame(0.0,index=common,columns=CORE_ASSETS)
            for date,regime in labels.items():
                base=REGIME_WEIGHTS.get(regime,np.repeat(1/6,6))
                risk=REGIME_RISK.get(regime,.5)
                out.loc[date]=base*risk
            return out
        strategies["LEGACY_REGIME"]=regime_frame(legacy)
        strategies["CLEAN_REGIME"]=regime_frame(clean)
        # Probability-weighted allocation.
        prob_weights=pd.DataFrame(0.0,index=common,columns=CORE_ASSETS)
        for date,row in p.iterrows():
            total=np.zeros(6)
            for regime,probability in row.items():
                total += probability*REGIME_WEIGHTS[regime]*REGIME_RISK[regime]
            prob_weights.loc[date]=total
        strategies["CLEAN_PROBABILITY"]=prob_weights

        daily_rows=[]; summary=[]
        for key,weights in strategies.items():
            weights=weights.reindex(common).ffill().fillna(0)
            held=weights.shift(1).fillna(weights.iloc[0])
            turnover=weights.diff().abs().sum(axis=1).fillna(weights.iloc[0].abs().sum())
            tc=turnover*costs
            strategy_return=(held*returns).sum(axis=1)-tc
            cumulative=(1+strategy_return).cumprod()
            years=max(len(strategy_return)/365,1/365)
            cagr=float(cumulative.iloc[-1]**(1/years)-1)
            vol_ann=float(strategy_return.std()*math.sqrt(365))
            sharpe=float(strategy_return.mean()/strategy_return.std()*math.sqrt(365)) if strategy_return.std()>0 else 0
            downside=strategy_return[strategy_return<0].std()
            sortino=float(strategy_return.mean()/downside*math.sqrt(365)) if downside and downside>0 else 0
            dd=cumulative/cumulative.cummax()-1
            maxdd=float(dd.min())
            calmar=float(cagr/abs(maxdd)) if maxdd<0 else 0
            q=float(strategy_return.quantile(.05))
            cvar=float(strategy_return[strategy_return<=q].mean())
            monthly=(1+strategy_return).resample("ME").prod()-1
            summary.append({
                "run_id":self.run_id,"strategy_key":key,"observations":len(strategy_return),
                "cumulative_return_pct":float((cumulative.iloc[-1]-1)*100),
                "cagr_pct":cagr*100,"annualized_volatility_pct":vol_ann*100,
                "sharpe_ratio":sharpe,"sortino_ratio":sortino,
                "maximum_drawdown_pct":maxdd*100,"calmar_ratio":calmar,
                "var_95_pct":q*100,"cvar_95_pct":cvar*100,
                "profitable_months_pct":float((monthly>0).mean()*100),
                "annualized_turnover_pct":float(turnover.mean()*365*100),
                "total_transaction_cost_pct":float(tc.sum()*100),
                "selected":False,"calculated_at_utc":utcnow(),
            })
            for date in common:
                daily_rows.append({
                    "run_id":self.run_id,"observation_date":date.date(),
                    "strategy_key":key,"daily_return":float(strategy_return.loc[date]),
                    "cumulative_return":float(cumulative.loc[date]),
                    "turnover":float(turnover.loc[date]),
                    "transaction_cost":float(tc.loc[date]),
                    "calculated_at_utc":utcnow(),
                })
        s=pd.DataFrame(summary)
        eligible=s[s["strategy_key"].isin(["CLEAN_REGIME","CLEAN_PROBABILITY"])]
        best=eligible.sort_values(["sharpe_ratio","maximum_drawdown_pct"],ascending=[False,False]).iloc[0]["strategy_key"]
        s["selected"]=s["strategy_key"]==best
        return pd.DataFrame(daily_rows),s

    def run(self):
        self.conn.execute(
            "INSERT INTO module32_runs VALUES("
            "?,?,?, ?,NULL,'RUNNING',0,0,0,0,0,0,NULL,NULL,NULL,NULL,NULL,'8.3.0')",
            [self.run_id,self.source_m31,self.source_m30,self.started]
        )
        try:
            frame=self.feature_label_data()
            probs,hist=self.clean_history()
            prices=self.prices()
            stability_history,stability_summary=self.feature_stability(frame)
            drift=self.probability_drift(probs,hist)
            retraining=self.retraining_policies(frame)
            historical=self.historical_stress(prices,probs,hist)
            synthetic=self.synthetic_stress(frame)
            daily,benchmarks=self.benchmark(prices,probs,hist)

            for table,data in [
                ("m32_feature_stability_history",stability_history),
                ("m32_feature_stability_summary",stability_summary),
                ("m32_probability_drift",drift),
                ("m32_retraining_policy_validation",retraining),
                ("m32_historical_stress_validation",historical),
                ("m32_synthetic_stress_validation",synthetic),
                ("m32_benchmark_daily",daily),
                ("m32_benchmark_summary",benchmarks),
            ]:
                self.upsert(table,data)

            best_policy=retraining.loc[retraining.selected,"policy_key"].iloc[0]
            best_log=float(retraining.loc[retraining.selected,"log_loss"].iloc[0])
            best_strategy=benchmarks.loc[benchmarks.selected,"strategy_key"].iloc[0]
            best_row=benchmarks[benchmarks.strategy_key==best_strategy].iloc[0]
            btc=benchmarks[benchmarks.strategy_key=="BTC_BUY_HOLD"].iloc[0]
            current_drift=drift.sort_values("window_end_date").iloc[-1]["drift_status"]
            stress_pass=float(synthetic["monotonic_passed"].mean()*100)
            mean_stability=float(stability_summary["stability_score"].mean())
            passed=(
                best_log<=float(self.cfg["validation"]["maximum_retraining_log_loss"])
                and stress_pass>=float(self.cfg["validation"]["minimum_synthetic_pass_rate_pct"])
                and float(best_row["sharpe_ratio"])>=float(btc["sharpe_ratio"])
                and float(best_row["maximum_drawdown_pct"])>float(btc["maximum_drawdown_pct"])
                and current_drift!="CRITICAL"
            )
            status="PASSED" if passed else "LIMITED"
            recommendation="READY_FOR_PORTFOLIO_INTELLIGENCE" if passed else "RESEARCH_VALIDATION_REQUIRES_REFINEMENT"
            summary=pd.DataFrame([{
                "run_id":self.run_id,"stable_features":len(stability_summary),
                "mean_feature_stability_score":mean_stability,
                "current_probability_drift_status":current_drift,
                "best_retraining_policy":best_policy,
                "best_retraining_log_loss":best_log,
                "historical_stress_episodes":len(historical),
                "synthetic_stress_pass_rate_pct":stress_pass,
                "best_strategy":best_strategy,
                "best_strategy_sharpe":float(best_row["sharpe_ratio"]),
                "btc_sharpe":float(btc["sharpe_ratio"]),
                "best_strategy_max_drawdown_pct":float(best_row["maximum_drawdown_pct"]),
                "btc_max_drawdown_pct":float(btc["maximum_drawdown_pct"]),
                "validation_status":status,
                "advancement_recommendation":recommendation,
                "calculated_at_utc":utcnow(),
            }])
            self.upsert("m32_validation_summary",summary)
            self.conn.execute(
                "UPDATE module32_runs SET completed_at_utc=?,status='SUCCESS',"
                "feature_stability_rows=?,probability_drift_rows=?,retraining_policy_rows=?,"
                "historical_stress_rows=?,synthetic_stress_rows=?,benchmark_rows=?,"
                "best_retraining_policy=?,best_strategy=?,validation_status=?,recommendation=?,notes=? "
                "WHERE run_id=?",
                [utcnow(),len(stability_history),len(drift),len(retraining),len(historical),
                 len(synthetic),len(benchmarks),best_policy,best_strategy,status,recommendation,
                 "Point-in-time retraining, stress testing, and common-date benchmark comparison completed. "
                 "Module 30 remains OBSERVATION.",self.run_id]
            )
            self.conn.close()
            return summary.iloc[0].to_dict()
        except Exception as exc:
            self.conn.execute(
                "UPDATE module32_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",
                [utcnow(),str(exc)[:1000],self.run_id]
            )
            self.conn.close()
            raise


def run_module32():
    return Module32Runner().run()
