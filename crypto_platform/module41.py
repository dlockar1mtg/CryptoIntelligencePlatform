from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module40 import MODULE40_SCHEMA

MODULE41_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module41_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module40_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    model_weight_rows INTEGER,
    horizon_rows INTEGER,
    confidence_rows INTEGER,
    feedback_rows INTEGER,
    matured_forecasts INTEGER,
    evidence_ratio DOUBLE,
    high_priority_models INTEGER,
    meta_learning_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m41_adaptive_model_weights(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    model_key VARCHAR,
    validation_prior_weight DOUBLE,
    realized_performance_weight DOUBLE,
    evidence_weight DOUBLE,
    adaptive_weight DOUBLE,
    matured_forecasts INTEGER,
    weight_change DOUBLE,
    model_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id,asset_id,horizon_days,model_key)
);

CREATE TABLE IF NOT EXISTS m41_horizon_reliability(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    forecasts_stored INTEGER,
    matured_forecasts INTEGER,
    validation_mae_pct DOUBLE,
    realized_mae_pct DOUBLE,
    directional_accuracy_pct DOUBLE,
    brier_score DOUBLE,
    interval_coverage_pct DOUBLE,
    reliability_score DOUBLE,
    reliability_grade VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id,asset_id,horizon_days)
);

CREATE TABLE IF NOT EXISTS m41_confidence_adjustments(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    raw_confidence DOUBLE,
    evidence_ratio DOUBLE,
    reliability_score DOUBLE,
    calibration_gap DOUBLE,
    adjusted_confidence DOUBLE,
    confidence_change DOUBLE,
    confidence_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id,asset_id,horizon_days)
);

CREATE TABLE IF NOT EXISTS m41_optimizer_feedback(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    latest_predicted_return_pct DOUBLE,
    realized_bias_pct DOUBLE,
    reliability_multiplier DOUBLE,
    confidence_multiplier DOUBLE,
    adaptive_expected_return_pct DOUBLE,
    feedback_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id,asset_id,horizon_days)
);

CREATE TABLE IF NOT EXISTS m41_retraining_plan(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    model_key VARCHAR,
    matured_forecasts INTEGER,
    adaptive_weight DOUBLE,
    realized_mae_pct DOUBLE,
    drift_detected BOOLEAN,
    priority VARCHAR,
    action VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id,asset_id,horizon_days,model_key)
);

CREATE TABLE IF NOT EXISTS m41_meta_summary(
    run_id VARCHAR PRIMARY KEY,
    adaptive_models INTEGER,
    asset_horizons INTEGER,
    matured_forecasts INTEGER,
    evidence_ratio DOUBLE,
    mean_reliability_score DOUBLE,
    mean_confidence_change DOUBLE,
    high_priority_models INTEGER,
    meta_learning_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m41_adaptive_model_weights AS
SELECT * FROM m41_adaptive_model_weights
WHERE run_id=(SELECT run_id FROM module41_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY asset_id,horizon_days,adaptive_weight DESC;

CREATE OR REPLACE VIEW latest_m41_horizon_reliability AS
SELECT * FROM m41_horizon_reliability
WHERE run_id=(SELECT run_id FROM module41_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY reliability_score DESC;

CREATE OR REPLACE VIEW latest_m41_confidence_adjustments AS
SELECT * FROM m41_confidence_adjustments
WHERE run_id=(SELECT run_id FROM module41_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY asset_id,horizon_days;

CREATE OR REPLACE VIEW latest_m41_optimizer_feedback AS
SELECT * FROM m41_optimizer_feedback
WHERE run_id=(SELECT run_id FROM module41_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY horizon_days,adaptive_expected_return_pct DESC;

CREATE OR REPLACE VIEW latest_m41_retraining_plan AS
SELECT * FROM m41_retraining_plan
WHERE run_id=(SELECT run_id FROM module41_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
asset_id,horizon_days,model_key;

CREATE OR REPLACE VIEW latest_m41_meta_summary AS
SELECT * FROM m41_meta_summary
WHERE run_id=(SELECT run_id FROM module41_runs ORDER BY started_at_utc DESC LIMIT 1);
"""


def utcnow():
    return datetime.now(timezone.utc)


class Module41Runner:
    def __init__(self):
        self.settings,_=load_all()
        self.conn=connect(self.settings)
        self.conn.execute(MODULE40_SCHEMA)
        self.conn.execute(MODULE41_SCHEMA)
        self.cfg=self.settings["module41"]
        self.run_id=str(uuid.uuid4())
        self.started=utcnow()
        row=self.conn.execute(
            "SELECT run_id FROM module40_runs WHERE status='SUCCESS' "
            "ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("A successful Module 40 run is required.")
        self.source40=str(row[0])

    def upsert(self,table,frame):
        if frame.empty:return
        self.conn.register("_m41",frame)
        cols=",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _m41"
        )
        self.conn.unregister("_m41")

    def model_weights(self):
        models=self.conn.execute(
            """
            SELECT fm.asset_id,fm.horizon_days,mm.model_key,
                   mm.ensemble_weight,mm.validation_mae_pct,
                   fm.outcome_status,fm.absolute_error_pct
            FROM m40_model_memory mm
            JOIN m40_forecast_memory fm USING(forecast_memory_id)
            """
        ).fetchdf()
        rows=[]
        minimum=int(self.cfg["minimum_matured_forecasts"])
        for (asset,horizon),group in models.groupby(["asset_id","horizon_days"]):
            model_stats=[]
            matured_forecasts=int(
                group[group.outcome_status=="MATURED"]
                ["forecast_memory_id"].nunique()
            ) if "forecast_memory_id" in group else int(
                group[group.outcome_status=="MATURED"].shape[0]/max(group.model_key.nunique(),1)
            )
            evidence=min(matured_forecasts/max(minimum,1),1.0)
            for model,mg in group.groupby("model_key"):
                prior=float(mg["ensemble_weight"].mean())
                matured=mg[mg.outcome_status=="MATURED"]
                if matured.empty:
                    realized_score=prior
                    realized_mae=np.nan
                else:
                    realized_mae=float(matured.absolute_error_pct.mean())
                    realized_score=1/max(realized_mae,1e-6)
                model_stats.append([model,prior,realized_score,realized_mae])
            priors=np.array([x[1] for x in model_stats],float)
            priors=priors/priors.sum()
            realized=np.array([x[2] for x in model_stats],float)
            realized=realized/realized.sum()
            adaptive=(1-evidence)*priors+evidence*realized
            adaptive=adaptive/adaptive.sum()
            for x,p,r,a in zip(model_stats,priors,realized,adaptive):
                rows.append({
                    "run_id":self.run_id,"asset_id":asset,
                    "horizon_days":int(horizon),"model_key":x[0],
                    "validation_prior_weight":float(p),
                    "realized_performance_weight":float(r),
                    "evidence_weight":evidence,"adaptive_weight":float(a),
                    "matured_forecasts":matured_forecasts,
                    "weight_change":float(a-p),
                    "model_status":"ADAPTIVE" if evidence>=1 else "VALIDATION_PRIOR",
                    "calculated_at_utc":utcnow(),
                })
        return pd.DataFrame(rows)

    def reliability(self):
        memory=self.conn.execute("SELECT * FROM m40_forecast_memory").fetchdf()
        models=self.conn.execute(
            """
            SELECT fm.asset_id,fm.horizon_days,AVG(mm.validation_mae_pct) validation_mae
            FROM m40_model_memory mm JOIN m40_forecast_memory fm USING(forecast_memory_id)
            GROUP BY fm.asset_id,fm.horizon_days
            """
        ).fetchdf()
        rows=[]; minimum=int(self.cfg["minimum_matured_forecasts"])
        for (asset,horizon),group in memory.groupby(["asset_id","horizon_days"]):
            matured=group[group.outcome_status=="MATURED"]
            val=models[(models.asset_id==asset)&(models.horizon_days==horizon)]
            validation_mae=float(val.validation_mae.iloc[0]) if not val.empty else np.nan
            n=len(matured); evidence=min(n/max(minimum,1),1)
            if n:
                realized_mae=float(matured.absolute_error_pct.mean())
                direction=float(matured.direction_correct.mean()*100)
                probs=matured.calibrated_probability_positive.astype(float)
                outcomes=matured.probability_outcome.astype(float)
                brier=float(np.mean((probs-outcomes)**2))
                coverage=float(matured.interval_covered.mean()*100)
                score=float(evidence*(.30*max(100-realized_mae,0)+.25*direction+
                    .20*max(100-brier*100,0)+.15*coverage+
                    .10*max(100-validation_mae,0)))
            else:
                realized_mae=direction=brier=coverage=np.nan
                score=float((1-evidence)*max(100-validation_mae,0)*.25)
            grade=("PROVEN" if evidence>=1 and score>=65 else
                   "DEVELOPING" if n>0 else "INSUFFICIENT_EVIDENCE")
            rows.append({
                "run_id":self.run_id,"asset_id":asset,"horizon_days":int(horizon),
                "forecasts_stored":len(group),"matured_forecasts":n,
                "validation_mae_pct":validation_mae,
                "realized_mae_pct":realized_mae,
                "directional_accuracy_pct":direction,"brier_score":brier,
                "interval_coverage_pct":coverage,"reliability_score":score,
                "reliability_grade":grade,"calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows)

    def confidence_and_feedback(self,reliability):
        latest=self.conn.execute(
            """
            SELECT * FROM m40_forecast_memory
            QUALIFY row_number() OVER(
                PARTITION BY asset_id,horizon_days
                ORDER BY forecast_date DESC,created_at_utc DESC
            )=1
            """
        ).fetchdf()
        confidence_rows=[]; feedback_rows=[]
        minimum=int(self.cfg["minimum_matured_forecasts"])
        for _,row in latest.iterrows():
            rel=reliability[
                (reliability.asset_id==row.asset_id)&
                (reliability.horizon_days==row.horizon_days)
            ].iloc[0]
            evidence=min(int(rel.matured_forecasts)/max(minimum,1),1)
            reliability_factor=float(rel.reliability_score)/100
            matured=self.conn.execute(
                "SELECT AVG(forecast_error_pct) FROM m40_forecast_memory "
                "WHERE asset_id=? AND horizon_days=? AND outcome_status='MATURED'",
                [row.asset_id,int(row.horizon_days)]
            ).fetchone()[0]
            bias=float(matured) if matured is not None else 0.0
            calibration_gap=0.0
            raw=float(row.forecast_confidence)
            adjusted=float(np.clip(
                raw*((1-evidence)*.75+evidence*max(reliability_factor,.25)),
                0,1
            ))
            confidence_rows.append({
                "run_id":self.run_id,"asset_id":row.asset_id,
                "horizon_days":int(row.horizon_days),"raw_confidence":raw,
                "evidence_ratio":evidence,"reliability_score":float(rel.reliability_score),
                "calibration_gap":calibration_gap,"adjusted_confidence":adjusted,
                "confidence_change":adjusted-raw,
                "confidence_status":"EVIDENCE_ADJUSTED" if evidence>0 else "CONSERVATIVE_BASELINE",
                "calculated_at_utc":utcnow(),
            })
            prediction=float(row.predicted_return_pct)
            adaptive=float((prediction+bias)*(.5+.5*adjusted))
            feedback_rows.append({
                "run_id":self.run_id,"asset_id":row.asset_id,
                "horizon_days":int(row.horizon_days),
                "latest_predicted_return_pct":prediction,
                "realized_bias_pct":bias,
                "reliability_multiplier":reliability_factor,
                "confidence_multiplier":adjusted,
                "adaptive_expected_return_pct":adaptive,
                "feedback_status":"ACTIVE_FEEDBACK" if evidence>=1 else "OBSERVATION_ONLY",
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(confidence_rows),pd.DataFrame(feedback_rows)

    def retraining(self,weights,reliability):
        rows=[]
        recs=self.conn.execute(
            """
            SELECT asset_id,horizon_days,drift_detected,retraining_priority
            FROM latest_m40_retraining_recommendations
            """
        ).fetchdf()
        for _,w in weights.iterrows():
            rel=reliability[
                (reliability.asset_id==w.asset_id)&
                (reliability.horizon_days==w.horizon_days)
            ].iloc[0]
            match=recs[(recs.asset_id==w.asset_id)&(recs.horizon_days==w.horizon_days)]
            drift=bool(match.drift_detected.iloc[0]) if not match.empty else False
            base_priority=str(match.retraining_priority.iloc[0]) if not match.empty else "LOW"
            priority="HIGH" if drift and w.matured_forecasts>=self.cfg["minimum_matured_forecasts"] else base_priority
            action=("RETRAIN_AND_REVALIDATE" if priority=="HIGH" else
                    "REVIEW_MODEL_WEIGHT" if priority=="MEDIUM" else
                    "CONTINUE_OBSERVATION")
            rows.append({
                "run_id":self.run_id,"asset_id":w.asset_id,
                "horizon_days":int(w.horizon_days),"model_key":w.model_key,
                "matured_forecasts":int(w.matured_forecasts),
                "adaptive_weight":float(w.adaptive_weight),
                "realized_mae_pct":float(rel.realized_mae_pct) if pd.notna(rel.realized_mae_pct) else np.nan,
                "drift_detected":drift,"priority":priority,"action":action,
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows)

    def run(self):
        self.conn.execute(
            "INSERT INTO module41_runs VALUES(?,?,?,NULL,'RUNNING',0,0,0,0,0,0,0,NULL,NULL,NULL,'11.0.0')",
            [self.run_id,self.source40,self.started]
        )
        try:
            weights=self.model_weights()
            reliability=self.reliability()
            confidence,feedback=self.confidence_and_feedback(reliability)
            retraining=self.retraining(weights,reliability)
            for table,frame in [
                ("m41_adaptive_model_weights",weights),
                ("m41_horizon_reliability",reliability),
                ("m41_confidence_adjustments",confidence),
                ("m41_optimizer_feedback",feedback),
                ("m41_retraining_plan",retraining),
            ]: self.upsert(table,frame)
            matured=int(reliability.matured_forecasts.sum()/max(reliability.asset_id.nunique(),1)) if not reliability.empty else 0
            minimum=int(self.cfg["minimum_matured_forecasts"])
            evidence=min(matured/max(minimum,1),1)
            high=int((retraining.priority=="HIGH").sum()) if not retraining.empty else 0
            mean_rel=float(reliability.reliability_score.mean()) if not reliability.empty else 0
            mean_change=float(confidence.confidence_change.mean()) if not confidence.empty else 0
            status=("ACTIVE_META_LEARNING" if evidence>=1 else "ACCUMULATING_EVIDENCE")
            recommendation=("ADAPTIVE_WEIGHTS_READY" if evidence>=1 and high==0 else
                            "RETRAIN_PRIORITY_MODELS" if high else
                            "CONTINUE_MEMORY_ACCUMULATION")
            summary=pd.DataFrame([{
                "run_id":self.run_id,"adaptive_models":len(weights),
                "asset_horizons":len(reliability),"matured_forecasts":matured,
                "evidence_ratio":evidence,"mean_reliability_score":mean_rel,
                "mean_confidence_change":mean_change,
                "high_priority_models":high,"meta_learning_status":status,
                "advancement_recommendation":recommendation,
                "calculated_at_utc":utcnow(),
            }])
            self.upsert("m41_meta_summary",summary)
            self.conn.execute(
                """
                UPDATE module41_runs SET completed_at_utc=?,status='SUCCESS',
                model_weight_rows=?,horizon_rows=?,confidence_rows=?,feedback_rows=?,
                matured_forecasts=?,evidence_ratio=?,high_priority_models=?,
                meta_learning_status=?,recommendation=?,notes=? WHERE run_id=?
                """,
                [utcnow(),len(weights),len(reliability),len(confidence),len(feedback),
                 matured,evidence,high,status,recommendation,
                 "Adaptive model priors, horizon reliability, confidence controls, "
                 "optimizer feedback, and retraining plan completed.",self.run_id]
            )
            self.conn.close()
            return summary.iloc[0].to_dict()
        except Exception as exc:
            self.conn.execute(
                "UPDATE module41_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",
                [utcnow(),str(exc)[:1000],self.run_id]
            )
            self.conn.close()
            raise


def run_module41():
    return Module41Runner().run()
