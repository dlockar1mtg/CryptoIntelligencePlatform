from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.preprocessing import StandardScaler

from crypto_platform.platform import load_all, connect
from crypto_platform.module38 import MODULE38_SCHEMA

MODULE39_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module39_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module38_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    calibration_rows INTEGER,
    interval_rows INTEGER,
    rolling_validation_rows INTEGER,
    stability_rows INTEGER,
    drift_rows INTEGER,
    scorecard_rows INTEGER,
    mean_calibrated_brier DOUBLE,
    mean_interval_coverage_pct DOUBLE,
    mean_directional_accuracy_pct DOUBLE,
    current_drift_status VARCHAR,
    validation_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m39_probability_calibration(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    calibration_method VARCHAR,
    validation_rows INTEGER,
    raw_brier_score DOUBLE,
    calibrated_brier_score DOUBLE,
    raw_log_loss DOUBLE,
    calibrated_log_loss DOUBLE,
    raw_mean_probability DOUBLE,
    calibrated_mean_probability DOUBLE,
    observed_positive_rate DOUBLE,
    calibration_improvement_pct DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id, horizon_days, calibration_method)
);

CREATE TABLE IF NOT EXISTS m39_calibrated_forecasts(
    run_id VARCHAR,
    forecast_date DATE,
    asset_id VARCHAR,
    horizon_days INTEGER,
    predicted_return_pct DOUBLE,
    raw_probability_positive DOUBLE,
    calibrated_probability_positive DOUBLE,
    conformal_lower_return_pct DOUBLE,
    conformal_upper_return_pct DOUBLE,
    interval_width_pct DOUBLE,
    calibration_method VARCHAR,
    forecast_confidence DOUBLE,
    forecast_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, forecast_date, asset_id, horizon_days)
);

CREATE TABLE IF NOT EXISTS m39_rolling_origin_validation(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    fold_number INTEGER,
    training_rows INTEGER,
    testing_rows INTEGER,
    training_end_date DATE,
    testing_start_date DATE,
    testing_end_date DATE,
    mae_pct DOUBLE,
    rmse_pct DOUBLE,
    directional_accuracy_pct DOUBLE,
    brier_score DOUBLE,
    interval_coverage_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id, horizon_days, fold_number)
);

CREATE TABLE IF NOT EXISTS m39_feature_stability(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    driver_key VARCHAR,
    folds INTEGER,
    mean_absolute_contribution DOUBLE,
    contribution_std DOUBLE,
    sign_consistency_pct DOUBLE,
    top_five_frequency_pct DOUBLE,
    rank_persistence_pct DOUBLE,
    stability_score DOUBLE,
    stability_grade VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id, horizon_days, driver_key)
);

CREATE TABLE IF NOT EXISTS m39_forecast_drift(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    current_forecast_date DATE,
    prior_forecast_date DATE,
    return_forecast_change_pct DOUBLE,
    probability_change DOUBLE,
    confidence_change DOUBLE,
    interval_width_change_pct DOUBLE,
    model_weight_distance DOUBLE,
    attribution_rank_change DOUBLE,
    drift_score DOUBLE,
    drift_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id, horizon_days)
);

CREATE TABLE IF NOT EXISTS m39_forecast_scorecard(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    forecasts_evaluated INTEGER,
    mean_absolute_error_pct DOUBLE,
    root_mean_squared_error_pct DOUBLE,
    directional_accuracy_pct DOUBLE,
    calibrated_brier_score DOUBLE,
    interval_coverage_pct DOUBLE,
    mean_interval_width_pct DOUBLE,
    realized_sharpe DOUBLE,
    scorecard_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id, horizon_days)
);

CREATE TABLE IF NOT EXISTS m39_validation_summary(
    run_id VARCHAR PRIMARY KEY,
    calibrated_forecasts INTEGER,
    calibration_improved_pct DOUBLE,
    mean_calibrated_brier DOUBLE,
    mean_interval_coverage_pct DOUBLE,
    mean_directional_accuracy_pct DOUBLE,
    stable_feature_pct DOUBLE,
    current_drift_status VARCHAR,
    scorecards_available INTEGER,
    validation_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m39_probability_calibration AS
SELECT * FROM m39_probability_calibration
WHERE run_id=(SELECT run_id FROM module39_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY asset_id,horizon_days,selected DESC;

CREATE OR REPLACE VIEW latest_m39_calibrated_forecasts AS
SELECT * FROM m39_calibrated_forecasts
WHERE run_id=(SELECT run_id FROM module39_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY horizon_days,predicted_return_pct DESC;

CREATE OR REPLACE VIEW latest_m39_rolling_origin_validation AS
SELECT * FROM m39_rolling_origin_validation
WHERE run_id=(SELECT run_id FROM module39_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY asset_id,horizon_days,fold_number;

CREATE OR REPLACE VIEW latest_m39_feature_stability AS
SELECT * FROM m39_feature_stability
WHERE run_id=(SELECT run_id FROM module39_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY stability_score DESC;

CREATE OR REPLACE VIEW latest_m39_forecast_drift AS
SELECT * FROM m39_forecast_drift
WHERE run_id=(SELECT run_id FROM module39_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY drift_score DESC;

CREATE OR REPLACE VIEW latest_m39_forecast_scorecard AS
SELECT * FROM m39_forecast_scorecard
WHERE run_id=(SELECT run_id FROM module39_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY asset_id,horizon_days;

CREATE OR REPLACE VIEW latest_m39_validation_summary AS
SELECT * FROM m39_validation_summary
WHERE run_id=(SELECT run_id FROM module39_runs ORDER BY started_at_utc DESC LIMIT 1);
"""


def utcnow():
    return datetime.now(timezone.utc)


def clip_probability(values):
    return np.clip(np.asarray(values,dtype=float),1e-4,1-1e-4)


class Module39Runner:
    def __init__(self):
        self.settings,_=load_all()
        self.conn=connect(self.settings)
        self.conn.execute(MODULE38_SCHEMA)
        self.conn.execute(MODULE39_SCHEMA)
        self.cfg=self.settings["module39"]
        self.run_id=str(uuid.uuid4())
        self.started=utcnow()
        row=self.conn.execute(
            "SELECT run_id FROM module38_runs WHERE status='SUCCESS' "
            "ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("A successful Module 38 run is required.")
        self.source_m38=str(row[0])

    def upsert(self,table,frame):
        if frame.empty:return
        self.conn.register("_m39_stage",frame)
        columns=",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) SELECT {columns} FROM _m39_stage"
        )
        self.conn.unregister("_m39_stage")

    def source_forecasts(self):
        return self.conn.execute(
            "SELECT * FROM m38_asset_forecasts WHERE run_id=? "
            "ORDER BY asset_id,horizon_days",[self.source_m38]
        ).fetchdf()

    def model_validation(self):
        return self.conn.execute(
            "SELECT * FROM m38_model_validation WHERE run_id=? "
            "ORDER BY asset_id,horizon_days,model_key",[self.source_m38]
        ).fetchdf()

    def attributions(self):
        return self.conn.execute(
            "SELECT * FROM m38_forecast_attribution WHERE run_id=?",
            [self.source_m38]
        ).fetchdf()

    def historical_forecasts(self):
        return self.conn.execute(
            """
            SELECT f.*, r.price_usd AS realized_price
            FROM m38_asset_forecasts f
            LEFT JOIN canonical_market_daily r
              ON r.asset_id=f.asset_id
             AND r.observation_date=CAST(f.forecast_date AS DATE)+f.horizon_days
            WHERE f.run_id<>?
            ORDER BY f.asset_id,f.horizon_days,f.forecast_date
            """,[self.source_m38]
        ).fetchdf()

    def calibration(self,forecasts,validation):
        rows=[]; calibrated=[]
        for _,forecast in forecasts.iterrows():
            asset=forecast["asset_id"]; horizon=int(forecast["horizon_days"])
            subset=validation[
                (validation.asset_id==asset)&
                (validation.horizon_days==horizon)
            ]
            directional=(subset["directional_accuracy_pct"]/100).clip(0.01,0.99)
            raw=np.repeat(float(forecast["probability_positive"]),len(subset))
            observed=(directional>=0.5).astype(int).to_numpy()
            minimum_calibration_rows=int(
                self.cfg.get(
                    "minimum_calibration_rows",
                    30,
                )
            )
            if (
                len(observed)<minimum_calibration_rows
                or len(np.unique(observed))<2
            ):
                selected_method="EVIDENCE_SHRINKAGE"
                empirical_rate=float(
                    directional.mean()
                    if len(directional)
                    else 0.5
                )
                evidence_weight=min(
                    len(observed)
                    / max(minimum_calibration_rows,1),
                    1.0,
                )
                calibrated_probability=float(
                    evidence_weight*empirical_rate+
                    (1-evidence_weight)*0.5
                )
                raw_brier=float(np.mean((raw-observed)**2)) if len(observed) else 0.25
                calibrated_brier=float(np.mean((calibrated_probability-observed)**2)) if len(observed) else raw_brier
                raw_ll=float(log_loss(observed,clip_probability(raw))) if len(np.unique(observed))>1 else 0.0
                calibrated_ll=float(log_loss(observed,np.repeat(clip_probability([calibrated_probability])[0],len(observed)))) if len(np.unique(observed))>1 else 0.0
            else:
                candidates=[]
                # Logistic/Platt calibration.
                logistic=LogisticRegression().fit(raw.reshape(-1,1),observed)
                p_log=logistic.predict_proba([[float(forecast["probability_positive"])]])[0,1]
                candidates.append(("PLATT",float(p_log)))
                # Isotonic calibration.
                iso=IsotonicRegression(out_of_bounds="clip").fit(raw,observed)
                p_iso=float(iso.predict([float(forecast["probability_positive"])])[0])
                candidates.append(("ISOTONIC",p_iso))
                raw_brier=float(brier_score_loss(observed,raw))
                raw_ll=float(log_loss(observed,clip_probability(raw)))
                scored=[]
                for method,p in candidates:
                    probs=np.repeat(clip_probability([p])[0],len(observed))
                    scored.append((method,p,float(brier_score_loss(observed,probs)),float(log_loss(observed,probs))))
                selected_method,calibrated_probability,calibrated_brier,calibrated_ll=min(scored,key=lambda x:x[2])
            improvement=(raw_brier-calibrated_brier)/max(raw_brier,1e-9)*100
            rows.append({
                "run_id":self.run_id,"asset_id":asset,"horizon_days":horizon,
                "calibration_method":selected_method,"validation_rows":len(subset),
                "raw_brier_score":raw_brier,"calibrated_brier_score":calibrated_brier,
                "raw_log_loss":raw_ll,"calibrated_log_loss":calibrated_ll,
                "raw_mean_probability":float(forecast["probability_positive"]),
                "calibrated_mean_probability":float(calibrated_probability),
                "observed_positive_rate":float(observed.mean()) if len(observed) else np.nan,
                "calibration_improvement_pct":improvement,"selected":True,
                "calculated_at_utc":utcnow(),
            })
            # Conformalized interval using model-validation RMSE as a conservative residual proxy.
            residual_scale=float(subset["validation_rmse_pct"].median()) if not subset.empty else float(forecast["upper_return_pct"]-forecast["lower_return_pct"])/2
            alpha=float(self.cfg["conformal_alpha"])
            multiplier=1.645 if alpha<=0.10 else 1.282
            half_width=max(residual_scale*multiplier,1.0)
            lower=float(forecast["predicted_return_pct"]-half_width)
            upper=float(forecast["predicted_return_pct"]+half_width)
            calibrated.append({
                "run_id":self.run_id,
                "forecast_date":forecast["forecast_date"],
                "asset_id":asset,"horizon_days":horizon,
                "predicted_return_pct":float(forecast["predicted_return_pct"]),
                "raw_probability_positive":float(forecast["probability_positive"]),
                "calibrated_probability_positive":float(np.clip(calibrated_probability,0,1)),
                "conformal_lower_return_pct":lower,
                "conformal_upper_return_pct":upper,
                "interval_width_pct":upper-lower,
                "calibration_method":selected_method,
                "forecast_confidence":float(forecast["forecast_confidence"]),
                "forecast_status":forecast["forecast_status"],
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows),pd.DataFrame(calibrated)

    def rolling_validation(self,forecasts,validation):
        rows=[]
        folds=int(self.cfg["rolling_folds"])
        for (asset,horizon),group in validation.groupby(["asset_id","horizon_days"]):
            n=len(group)
            fold_size=max(n//folds,1)
            for fold in range(folds):
                test=group.iloc[fold*fold_size:min((fold+1)*fold_size,n)]
                if test.empty:continue
                mae=float(test["validation_mae_pct"].mean())
                rmse=float(test["validation_rmse_pct"].mean())
                direction=float(test["directional_accuracy_pct"].mean())
                probability=np.clip(direction/100,1e-4,1-1e-4)
                observed=np.repeat(1 if direction>=50 else 0,len(test))
                brier=float(np.mean((probability-observed)**2))
                coverage=float(np.clip(100-mae,0,100))
                rows.append({
                    "run_id":self.run_id,"asset_id":asset,"horizon_days":int(horizon),
                    "fold_number":fold+1,
                    "training_rows":int(self.cfg["minimum_training_rows"]+fold*fold_size),
                    "testing_rows":len(test),"training_end_date":pd.Timestamp(forecasts["forecast_date"].max()).date(),
                    "testing_start_date":pd.Timestamp(forecasts["forecast_date"].max()).date(),
                    "testing_end_date":pd.Timestamp(forecasts["forecast_date"].max()).date(),
                    "mae_pct":mae,"rmse_pct":rmse,
                    "directional_accuracy_pct":direction,"brier_score":brier,
                    "interval_coverage_pct":coverage,"calculated_at_utc":utcnow(),
                })
        return pd.DataFrame(rows)

    def stability(self,attribution):
        rows=[]
        for (asset,horizon,driver),group in attribution.groupby(["asset_id","horizon_days","driver_key"]):
            values=group["contribution_pct"].astype(float)
            signs=np.sign(values)
            sign_consistency=max((signs>=0).mean(),(signs<=0).mean())*100
            top5=(group["importance_rank"]<=5).mean()*100
            rank_persistence=max(0,100-(group["importance_rank"].std(ddof=0) if len(group)>1 else 0)*15)
            mean_abs=float(values.abs().mean())
            std=float(values.std(ddof=0))
            evidence_factor=min(
                len(group)
                / max(
                    int(
                        self.cfg.get(
                            "minimum_stability_snapshots",
                            5,
                        )
                    ),
                    1,
                ),
                1.0,
            )
            raw_score=float(
                .35*sign_consistency+
                .30*top5+
                .20*rank_persistence+
                .15*(mean_abs/(mean_abs+std+1e-9)*100)
            )
            score=float(raw_score*evidence_factor)
            grade=(
                "INSUFFICIENT_EVIDENCE"
                if len(group)<int(
                    self.cfg.get(
                        "minimum_stability_snapshots",
                        5,
                    )
                )
                else "A" if score>=80
                else "B" if score>=65
                else "C" if score>=50
                else "D"
            )
            rows.append({
                "run_id":self.run_id,"asset_id":asset,"horizon_days":int(horizon),
                "driver_key":driver,"folds":len(group),
                "mean_absolute_contribution":mean_abs,"contribution_std":std,
                "sign_consistency_pct":sign_consistency,
                "top_five_frequency_pct":top5,
                "rank_persistence_pct":rank_persistence,
                "stability_score":score,
                "stability_grade":grade,
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows)

    def drift(self,current,validation,attribution):
        rows=[]
        previous=self.conn.execute(
            """
            SELECT * FROM m38_asset_forecasts
            WHERE run_id<>?
            QUALIFY row_number() OVER(
                PARTITION BY asset_id,horizon_days
                ORDER BY forecast_date DESC,calculated_at_utc DESC
            )=1
            """,[self.source_m38]
        ).fetchdf()
        for _,row in current.iterrows():
            prior=previous[
                (previous.asset_id==row.asset_id)&
                (previous.horizon_days==row.horizon_days)
            ]
            if prior.empty:
                return_change=prob_change=conf_change=width_change=0.0
                prior_date=row.forecast_date
            else:
                p=prior.iloc[0]
                return_change=float(row.predicted_return_pct-p.predicted_return_pct)
                prob_change=float(row.probability_positive-p.probability_positive)
                conf_change=float(row.forecast_confidence-p.forecast_confidence)
                width_now=float(row.upper_return_pct-row.lower_return_pct)
                width_prior=float(p.upper_return_pct-p.lower_return_pct)
                width_change=(width_now/width_prior-1)*100 if width_prior else 0.0
                prior_date=p.forecast_date
            weights=validation[
                (validation.asset_id==row.asset_id)&
                (validation.horizon_days==row.horizon_days)
            ]["ensemble_weight"].to_numpy()
            model_distance=float(np.std(weights)) if len(weights) else 0.0
            ranks=attribution[
                (attribution.asset_id==row.asset_id)&
                (attribution.horizon_days==row.horizon_days)
            ]["importance_rank"]
            rank_change=float(ranks.std(ddof=0)) if len(ranks)>1 else 0.0
            score=float(
                .30*min(abs(return_change)/20,1)+
                .20*min(abs(prob_change)/.30,1)+
                .15*min(abs(conf_change)/.30,1)+
                .15*min(abs(width_change)/50,1)+
                .10*min(model_distance/.25,1)+
                .10*min(rank_change/5,1)
            )
            status="CRITICAL" if score>=.75 else "WARNING" if score>=.45 else "STABLE"
            rows.append({
                "run_id":self.run_id,"asset_id":row.asset_id,
                "horizon_days":int(row.horizon_days),
                "current_forecast_date":row.forecast_date,
                "prior_forecast_date":prior_date,
                "return_forecast_change_pct":return_change,
                "probability_change":prob_change,"confidence_change":conf_change,
                "interval_width_change_pct":width_change,
                "model_weight_distance":model_distance,
                "attribution_rank_change":rank_change,
                "drift_score":score,"drift_status":status,
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows)

    def scorecards(self,historical):
        rows=[]
        if historical.empty:return pd.DataFrame(rows)
        for (asset,horizon),group in historical.groupby(["asset_id","horizon_days"]):
            usable=group.dropna(subset=["realized_price"])
            if usable.empty:continue
            realized=(usable["realized_price"]/usable["current_price"]-1)*100
            error=realized-usable["predicted_return_pct"]
            direction=float((np.sign(realized)==np.sign(usable["predicted_return_pct"])).mean()*100)
            probs=clip_probability(usable["probability_positive"])
            observed=(realized>0).astype(int)
            brier=float(brier_score_loss(observed,probs))
            coverage=float(((realized>=usable["lower_return_pct"])&(realized<=usable["upper_return_pct"])).mean()*100)
            strategy=np.sign(usable["predicted_return_pct"])*realized/100
            sharpe=float(strategy.mean()/strategy.std(ddof=0)*math.sqrt(365/max(int(horizon),1))) if strategy.std(ddof=0)>0 else 0.0
            status="PASSED" if direction>=55 and brier<=.25 else "LIMITED"
            rows.append({
                "run_id":self.run_id,"asset_id":asset,"horizon_days":int(horizon),
                "forecasts_evaluated":len(usable),
                "mean_absolute_error_pct":float(error.abs().mean()),
                "root_mean_squared_error_pct":float(np.sqrt(np.mean(error**2))),
                "directional_accuracy_pct":direction,
                "calibrated_brier_score":brier,
                "interval_coverage_pct":coverage,
                "mean_interval_width_pct":float((usable["upper_return_pct"]-usable["lower_return_pct"]).mean()),
                "realized_sharpe":sharpe,"scorecard_status":status,
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows)

    def run(self):
        self.conn.execute(
            "INSERT INTO module39_runs VALUES(?,?,?,NULL,'RUNNING',0,0,0,0,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'10.1.1')",
            [self.run_id,self.source_m38,self.started]
        )
        try:
            forecasts=self.source_forecasts()
            validation=self.model_validation()
            attribution=self.attributions()
            calibration,calibrated=self.calibration(forecasts,validation)
            rolling=self.rolling_validation(forecasts,validation)
            stability=self.stability(attribution)
            drift=self.drift(forecasts,validation,attribution)
            scorecards=self.scorecards(self.historical_forecasts())
            for table,frame in [
                ("m39_probability_calibration",calibration),
                ("m39_calibrated_forecasts",calibrated),
                ("m39_rolling_origin_validation",rolling),
                ("m39_feature_stability",stability),
                ("m39_forecast_drift",drift),
                ("m39_forecast_scorecard",scorecards),
            ]:self.upsert(table,frame)

            improvement=float((calibration["calibration_improvement_pct"]>0).mean()*100)
            mean_brier=float(calibration["calibrated_brier_score"].mean())
            coverage=float(rolling["interval_coverage_pct"].mean()) if not rolling.empty else 0.0
            direction=float(rolling["directional_accuracy_pct"].mean()) if not rolling.empty else 0.0
            evidence_ready=stability[
                stability["folds"]>=int(
                    self.cfg.get(
                        "minimum_stability_snapshots",
                        5,
                    )
                )
            ]
            stable_pct=float(
                (evidence_ready["stability_score"]>=65).mean()*100
            ) if not evidence_ready.empty else 0.0
            current_drift=(
                "CRITICAL" if (drift["drift_status"]=="CRITICAL").any()
                else "WARNING" if (drift["drift_status"]=="WARNING").any()
                else "STABLE"
            )
            minimum_scorecards=int(
                self.cfg["validation"].get(
                    "minimum_realized_scorecards",
                    6,
                )
            )
            evidence_ready=bool(
                len(scorecards)>=minimum_scorecards
                and calibration["validation_rows"].sum()
                >=int(
                    self.cfg.get(
                        "minimum_total_calibration_rows",
                        180,
                    )
                )
            )
            passed=bool(
                evidence_ready
                and mean_brier<=float(self.cfg["validation"]["maximum_brier"])
                and coverage>=float(self.cfg["validation"]["minimum_interval_coverage_pct"])
                and direction>=float(self.cfg["validation"]["minimum_directional_accuracy_pct"])
                and current_drift!="CRITICAL"
            )
            status=(
                "PASSED"
                if passed
                else "ACCUMULATING_EVIDENCE"
                if not evidence_ready
                else "LIMITED"
            )
            recommendation=(
                "READY_FOR_LIVE_FORECAST_MONITORING"
                if passed
                else "BUILD_FORECAST_MEMORY"
                if not evidence_ready
                else "FORECAST_VALIDATION_REQUIRES_REFINEMENT"
            )
            summary=pd.DataFrame([{
                "run_id":self.run_id,"calibrated_forecasts":len(calibrated),
                "calibration_improved_pct":improvement,
                "mean_calibrated_brier":mean_brier,
                "mean_interval_coverage_pct":coverage,
                "mean_directional_accuracy_pct":direction,
                "stable_feature_pct":stable_pct,
                "current_drift_status":current_drift,
                "scorecards_available":len(scorecards),
                "validation_status":status,
                "advancement_recommendation":recommendation,
                "calculated_at_utc":utcnow(),
            }])
            self.upsert("m39_validation_summary",summary)
            self.conn.execute(
                """
                UPDATE module39_runs SET completed_at_utc=?,status='SUCCESS',
                calibration_rows=?,interval_rows=?,rolling_validation_rows=?,
                stability_rows=?,drift_rows=?,scorecard_rows=?,
                mean_calibrated_brier=?,mean_interval_coverage_pct=?,
                mean_directional_accuracy_pct=?,current_drift_status=?,
                validation_status=?,recommendation=?,notes=?
                WHERE run_id=?
                """,
                [utcnow(),len(calibration),len(calibrated),len(rolling),len(stability),
                 len(drift),len(scorecards),mean_brier,coverage,direction,current_drift,
                 status,recommendation,
                 "Probability calibration, conformal intervals, rolling validation, "
                 "feature stability, drift monitoring, and realized scorecards completed.",
                 self.run_id]
            )
            self.conn.close()
            return summary.iloc[0].to_dict()
        except Exception as exc:
            self.conn.execute(
                "UPDATE module39_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",
                [utcnow(),str(exc)[:1000],self.run_id]
            )
            self.conn.close()
            raise


def run_module39():
    return Module39Runner().run()
