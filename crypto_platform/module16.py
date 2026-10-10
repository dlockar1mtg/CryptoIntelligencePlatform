from __future__ import annotations
import hashlib, inspect, json, math, uuid
from datetime import datetime, timezone
from typing import Any
import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA
from crypto_platform.module12 import MODULE12_SCHEMA
from crypto_platform.module13 import MODULE13_SCHEMA
from crypto_platform.module14 import MODULE14_SCHEMA
from crypto_platform.module15 import MODULE15_SCHEMA, Module15Runner
from crypto_platform.optimization import ParameterSpace, CandidateGenerator
from crypto_platform.optimization.objective_function import composite_objective
from crypto_platform.optimization.registry import candidate_row

MODULE16_SCHEMA=r"""
CREATE TABLE IF NOT EXISTS optimization_runs(
 experiment_id VARCHAR PRIMARY KEY, started_at_utc TIMESTAMPTZ,
 completed_at_utc TIMESTAMPTZ, status VARCHAR, candidate_count INTEGER,
 evaluated_count INTEGER, cached_count INTEGER, shortlist_count INTEGER,
 walk_forward_count INTEGER, best_candidate_id VARCHAR,
 best_robust_score DOUBLE, notes VARCHAR, platform_version VARCHAR
);
CREATE TABLE IF NOT EXISTS strategy_candidates(
 experiment_id VARCHAR, candidate_id VARCHAR, parameter_hash VARCHAR,
 parameters_json VARCHAR, generation_seed INTEGER, status VARCHAR,
 created_at_utc TIMESTAMPTZ,
 PRIMARY KEY(experiment_id,candidate_id)
);
CREATE TABLE IF NOT EXISTS candidate_evaluation_cache(
 parameter_hash VARCHAR PRIMARY KEY, parameters_json VARCHAR,
 total_return_pct DOUBLE, annualized_return_pct DOUBLE,
 annualized_volatility_pct DOUBLE, sharpe_ratio DOUBLE,
 maximum_drawdown_pct DOUBLE, btc_return_pct DOUBLE,
 btc_excess_pct DOUBLE, information_ratio DOUBLE,
 benchmark_win_rate_pct DOUBLE, average_turnover_pct DOUBLE,
 transaction_cost_drag_pct DOUBLE, objective_score DOUBLE,
 periods INTEGER, evaluated_at_utc TIMESTAMPTZ, evaluator_version VARCHAR
);
CREATE TABLE IF NOT EXISTS candidate_results(
 experiment_id VARCHAR, candidate_id VARCHAR, evaluation_scope VARCHAR,
 fold_number INTEGER, total_return_pct DOUBLE, annualized_return_pct DOUBLE,
 annualized_volatility_pct DOUBLE, sharpe_ratio DOUBLE,
 maximum_drawdown_pct DOUBLE, btc_return_pct DOUBLE, btc_excess_pct DOUBLE,
 information_ratio DOUBLE, benchmark_win_rate_pct DOUBLE,
 average_turnover_pct DOUBLE, transaction_cost_drag_pct DOUBLE,
 objective_score DOUBLE, from_cache BOOLEAN, calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(experiment_id,candidate_id,evaluation_scope,fold_number)
);
CREATE TABLE IF NOT EXISTS candidate_rankings(
 experiment_id VARCHAR, candidate_id VARCHAR, full_sample_rank INTEGER,
 full_sample_objective DOUBLE, oos_folds INTEGER, oos_total_return_pct DOUBLE,
 oos_btc_return_pct DOUBLE, oos_btc_excess_pct DOUBLE,
 oos_information_ratio DOUBLE, oos_maximum_drawdown_pct DOUBLE,
 oos_benchmark_win_rate_pct DOUBLE, stability_score DOUBLE,
 robust_score DOUBLE, promotion_status VARCHAR, calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(experiment_id,candidate_id)
);
CREATE TABLE IF NOT EXISTS optimization_history(
 experiment_id VARCHAR, stage VARCHAR, candidate_id VARCHAR,
 event_type VARCHAR, event_message VARCHAR, event_at_utc TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS parameter_importance(
 experiment_id VARCHAR, parameter_name VARCHAR, correlation_to_objective DOUBLE,
 top_quartile_mean DOUBLE, bottom_quartile_mean DOUBLE, importance_score DOUBLE,
 calculated_at_utc TIMESTAMPTZ,
 PRIMARY KEY(experiment_id,parameter_name)
);
CREATE OR REPLACE VIEW latest_candidate_rankings AS
SELECT r.* FROM candidate_rankings r JOIN
 (SELECT experiment_id FROM optimization_runs ORDER BY started_at_utc DESC LIMIT 1) x
 USING(experiment_id) ORDER BY robust_score DESC;
CREATE OR REPLACE VIEW latest_strategy_candidates AS
SELECT c.* FROM strategy_candidates c JOIN
 (SELECT experiment_id FROM optimization_runs ORDER BY started_at_utc DESC LIMIT 1) x
 USING(experiment_id);
CREATE OR REPLACE VIEW latest_parameter_importance AS
SELECT p.* FROM parameter_importance p JOIN
 (SELECT experiment_id FROM optimization_runs ORDER BY started_at_utc DESC LIMIT 1) x
 USING(experiment_id) ORDER BY importance_score DESC;
"""

MODULE16_CACHE_MIGRATION="ALTER TABLE candidate_evaluation_cache ADD COLUMN IF NOT EXISTS data_fingerprint VARCHAR"

def utcnow(): return datetime.now(timezone.utc)

EVALUATOR_VERSION="4.2.0"

def data_fingerprint(histories,dates,module15_config):
    """Hash of everything a full-sample evaluation reads besides the candidate's parameters:
    the price histories, the rebalance dates, the Module 15 settings and evaluator code.
    The evaluation cache is keyed by parameter hash AND this, so new prices are evaluated."""
    h=hashlib.sha256()
    h.update(EVALUATOR_VERSION.encode())
    h.update(json.dumps(module15_config,sort_keys=True,default=str).encode())
    try:h.update(inspect.getsource(Module15Runner).encode())
    except (OSError,TypeError):h.update(b"module15-source-unavailable")
    for asset in sorted(histories):
        series=histories[asset]
        h.update(f"|{asset}|{len(series)}|".encode())
        h.update(np.ascontiguousarray(pd.DatetimeIndex(series.index).as_unit("ns").asi8).tobytes())
        h.update(np.ascontiguousarray(series.to_numpy(dtype="float64")).tobytes())
    h.update(json.dumps([pd.Timestamp(d).isoformat() for d in dates]).encode())
    return h.hexdigest()

class Module16Runner:
    def __init__(self):
        self.settings,self.assets=load_all(); self.conn=connect(self.settings)
        for schema in [MODULE2_SCHEMA,MODULE3_SCHEMA,MODULE5_SCHEMA,MODULE6_SCHEMA,
          MODULE7_SCHEMA,MODULE8_SCHEMA,MODULE9_SCHEMA,MODULE10_SCHEMA,MODULE11_SCHEMA,
          MODULE12_SCHEMA,MODULE13_SCHEMA,MODULE14_SCHEMA,MODULE15_SCHEMA,MODULE16_SCHEMA]:
            self.conn.execute(schema)
        # Kept out of MODULE16_SCHEMA, which other modules also execute.
        self.conn.execute(MODULE16_CACHE_MIGRATION)
        self.config=self.settings["module16"]
        self.experiment_id=f"EXP-{utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        self.started=utcnow()
        self.data_fingerprint=None
        self.evaluator=Module15Runner(); self.evaluator.conn.close()
        self.evaluator.settings=self.settings; self.evaluator.assets=self.assets
        self.evaluator.config=self.settings["module15"]
        self.evaluator.conn=connect(self.settings)

    def upsert(self,table,frame):
        if frame.empty:return
        self.conn.register('_m16_stage',frame); cols=','.join(frame.columns)
        self.conn.execute(f"INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _m16_stage")
        self.conn.unregister('_m16_stage')

    def metrics_row(self,candidate_id,scope,fold,metrics,from_cache=False):
        return {"experiment_id":self.experiment_id,"candidate_id":candidate_id,
          "evaluation_scope":scope,"fold_number":fold,
          "total_return_pct":metrics["total_return"]*100,
          "annualized_return_pct":metrics["annualized_return"]*100,
          "annualized_volatility_pct":metrics["annualized_volatility"]*100,
          "sharpe_ratio":metrics["sharpe"],"maximum_drawdown_pct":metrics["maximum_drawdown"]*100,
          "btc_return_pct":metrics["btc_return"]*100,"btc_excess_pct":metrics["btc_excess"]*100,
          "information_ratio":metrics["information_ratio"],
          "benchmark_win_rate_pct":metrics["benchmark_win_rate"],
          "average_turnover_pct":metrics["average_turnover"]*100,
          "transaction_cost_drag_pct":metrics["transaction_cost_drag"]*100,
          "objective_score":composite_objective(metrics),"from_cache":from_cache,
          "calculated_at_utc":utcnow()}

    def cache_lookup(self,parameter_hash):
        row=self.conn.execute("SELECT * FROM candidate_evaluation_cache WHERE parameter_hash=? AND data_fingerprint=?",[parameter_hash,self.data_fingerprint]).fetchdf()
        return None if row.empty else row.iloc[0]

    def cache_metrics(self,row):
        return {"total_return":row.total_return_pct/100,"annualized_return":row.annualized_return_pct/100,
          "annualized_volatility":row.annualized_volatility_pct/100,"sharpe":row.sharpe_ratio,
          "maximum_drawdown":row.maximum_drawdown_pct/100,"btc_return":row.btc_return_pct/100,
          "btc_excess":row.btc_excess_pct/100,"information_ratio":row.information_ratio,
          "benchmark_win_rate":row.benchmark_win_rate_pct,"average_turnover":row.average_turnover_pct/100,
          "transaction_cost_drag":row.transaction_cost_drag_pct/100,"objective_score":row.objective_score,
          "periods":int(row.periods),"equal_weight_return":0,"btc_eth_return":0,
          "equal_weight_excess":0,"btc_eth_excess":0,"tracking_error":0}

    def cache_store(self,candidate,metrics):
        p=candidate["parameters"]
        frame=pd.DataFrame([{ "parameter_hash":candidate["parameter_hash"],
          "parameters_json":json.dumps(p,sort_keys=True),"total_return_pct":metrics["total_return"]*100,
          "annualized_return_pct":metrics["annualized_return"]*100,
          "annualized_volatility_pct":metrics["annualized_volatility"]*100,"sharpe_ratio":metrics["sharpe"],
          "maximum_drawdown_pct":metrics["maximum_drawdown"]*100,"btc_return_pct":metrics["btc_return"]*100,
          "btc_excess_pct":metrics["btc_excess"]*100,"information_ratio":metrics["information_ratio"],
          "benchmark_win_rate_pct":metrics["benchmark_win_rate"],
          "average_turnover_pct":metrics["average_turnover"]*100,
          "transaction_cost_drag_pct":metrics["transaction_cost_drag"]*100,
          "objective_score":composite_objective(metrics),"periods":metrics["periods"],
          "evaluated_at_utc":utcnow(),"evaluator_version":EVALUATOR_VERSION,
          "data_fingerprint":self.data_fingerprint}])
        self.upsert('candidate_evaluation_cache',frame)

    def aggregate_oos(self,fold_rows):
        if not fold_rows:return None
        returns=np.array([r["metrics"]["total_return"] for r in fold_rows]); btc=np.array([r["metrics"]["btc_return"] for r in fold_rows])
        total=float(np.prod(1+returns)-1); btc_total=float(np.prod(1+btc)-1)
        irs=[r["metrics"]["information_ratio"] for r in fold_rows if r["metrics"]["information_ratio"] is not None]
        return {"folds":len(fold_rows),"total_return":total,"btc_return":btc_total,"btc_excess":total-btc_total,
          "information_ratio":float(np.mean(irs)) if irs else None,
          "maximum_drawdown":min(r["metrics"]["maximum_drawdown"] for r in fold_rows),
          "benchmark_win_rate":float(np.mean([r["metrics"]["benchmark_win_rate"] for r in fold_rows])),
          "objective_mean":float(np.mean([r["metrics"]["objective_score"] for r in fold_rows])),
          "objective_std":float(np.std([r["metrics"]["objective_score"] for r in fold_rows]))}

    def parameter_importance(self,candidates,results):
        merged=[]; score_map={r["candidate_id"]:r["objective_score"] for r in results}
        for c in candidates:
            if c["candidate_id"] in score_map:
                row=dict(c["parameters"]); row["objective_score"]=score_map[c["candidate_id"]]; merged.append(row)
        df=pd.DataFrame(merged); rows=[]
        if df.empty:return pd.DataFrame()
        q1=df.objective_score.quantile(.25); q3=df.objective_score.quantile(.75)
        for col in [c for c in df.columns if c!='objective_score']:
            corr=float(df[col].corr(df.objective_score)) if df[col].nunique()>1 else 0.0
            top=float(df.loc[df.objective_score>=q3,col].mean()); bottom=float(df.loc[df.objective_score<=q1,col].mean())
            rows.append({"experiment_id":self.experiment_id,"parameter_name":col,
              "correlation_to_objective":corr,"top_quartile_mean":top,"bottom_quartile_mean":bottom,
              "importance_score":abs(corr),"calculated_at_utc":utcnow()})
        return pd.DataFrame(rows)

    def run(self):
        cfg=self.config["optimization"]
        self.conn.execute("UPDATE optimization_runs SET status='FAILED',completed_at_utc=? WHERE status='RUNNING'",[utcnow()])
        self.conn.execute("INSERT INTO optimization_runs VALUES (?,?,NULL,'RUNNING',0,0,0,0,0,NULL,NULL,NULL,'4.2.0')",[self.experiment_id,self.started])
        try:
            histories=self.evaluator.histories(); dates=self.evaluator.rebalance_dates(histories)
            self.data_fingerprint=data_fingerprint(histories,dates,self.evaluator.config)
            space=ParameterSpace.from_settings(self.settings)
            generator=CandidateGenerator(space,int(cfg["random_seed"]))
            candidates=generator.generate(int(cfg["candidate_count"]))
            self.upsert('strategy_candidates',pd.DataFrame([candidate_row(self.experiment_id,c,utcnow()) for c in candidates]))
            full_rows=[]; cached_count=0
            cache_enabled=bool(cfg["cache_enabled"])
            for idx,c in enumerate(candidates,1):
                cache=self.cache_lookup(c["parameter_hash"]) if cache_enabled else None
                if cache is not None:
                    metrics=self.cache_metrics(cache); from_cache=True; cached_count+=1
                else:
                    frame=self.evaluator.simulate(histories,dates,c["parameters"])
                    metrics=self.evaluator.evaluate(frame); metrics["objective_score"]=composite_objective(metrics)
                    self.cache_store(c,metrics); from_cache=False
                row=self.metrics_row(c["candidate_id"],'FULL_SAMPLE',0,metrics,from_cache)
                full_rows.append(row)
                if idx%25==0:
                    self.conn.execute("UPDATE optimization_runs SET evaluated_count=?,cached_count=? WHERE experiment_id=?",[idx,cached_count,self.experiment_id])
            self.upsert('candidate_results',pd.DataFrame(full_rows))
            shortlist_count=min(int(cfg["shortlist_count"]),len(full_rows))
            shortlist=sorted(full_rows,key=lambda r:r["objective_score"],reverse=True)[:shortlist_count]
            candidate_map={c["candidate_id"]:c for c in candidates}
            windows=self.evaluator.walk_forward_windows(dates)
            if len(windows)<int(cfg["minimum_walk_forward_folds"]):
                raise RuntimeError(f"Only {len(windows)} walk-forward folds available")
            fold_result_rows=[]; ranking_rows=[]
            rank_map={r["candidate_id"]:i+1 for i,r in enumerate(sorted(full_rows,key=lambda r:r["objective_score"],reverse=True))}
            for short in shortlist:
                cid=short["candidate_id"]; candidate=candidate_map[cid]; folds=[]
                for fold,(train_start,train_end,test_start,test_end) in enumerate(windows,1):
                    test=self.evaluator.simulate(histories,dates,candidate["parameters"],start_date=test_start,end_date=test_end)
                    if test.empty:continue
                    metrics=self.evaluator.evaluate(test); metrics["objective_score"]=composite_objective(metrics)
                    fold_result_rows.append(self.metrics_row(cid,'OOS_TEST',fold,metrics,False))
                    folds.append({"fold":fold,"metrics":metrics})
                agg=self.aggregate_oos(folds)
                if agg is None:continue
                stability=max(0.0,100.0-agg["objective_std"]*4.0)
                robust=(short["objective_score"]*float(self.config["ranking"]["full_sample_weight"])
                  + agg["objective_mean"]*float(self.config["ranking"]["walk_forward_weight"])
                  + stability*float(self.config["ranking"]["stability_weight"]))
                promoted=(agg["information_ratio"] is not None and agg["information_ratio"]>=float(self.config["ranking"]["minimum_oos_information_ratio"])
                  and agg["benchmark_win_rate"]>=float(self.config["ranking"]["minimum_oos_benchmark_win_rate_pct"])
                  and agg["maximum_drawdown"]*100>=float(self.config["ranking"]["maximum_oos_drawdown_pct"]))
                ranking_rows.append({"experiment_id":self.experiment_id,"candidate_id":cid,
                  "full_sample_rank":rank_map[cid],"full_sample_objective":short["objective_score"],
                  "oos_folds":agg["folds"],"oos_total_return_pct":agg["total_return"]*100,
                  "oos_btc_return_pct":agg["btc_return"]*100,"oos_btc_excess_pct":agg["btc_excess"]*100,
                  "oos_information_ratio":agg["information_ratio"],"oos_maximum_drawdown_pct":agg["maximum_drawdown"]*100,
                  "oos_benchmark_win_rate_pct":agg["benchmark_win_rate"],"stability_score":stability,
                  "robust_score":robust,"promotion_status":'MODULE15_CANDIDATE' if promoted else 'RESEARCH_ONLY',
                  "calculated_at_utc":utcnow()})
            self.upsert('candidate_results',pd.DataFrame(fold_result_rows)); self.upsert('candidate_rankings',pd.DataFrame(ranking_rows))
            importance=self.parameter_importance(candidates,full_rows); self.upsert('parameter_importance',importance)
            if not ranking_rows: raise RuntimeError('No candidates completed walk-forward evaluation')
            best=max(ranking_rows,key=lambda r:r["robust_score"])
            self.conn.execute("UPDATE optimization_runs SET completed_at_utc=?,status='SUCCESS',candidate_count=?,evaluated_count=?,cached_count=?,shortlist_count=?,walk_forward_count=?,best_candidate_id=?,best_robust_score=?,notes=? WHERE experiment_id=?",
              [utcnow(),len(candidates),len(full_rows),cached_count,shortlist_count,len(ranking_rows),best["candidate_id"],best["robust_score"],f"parameter_importance_rows={len(importance)}",self.experiment_id])
            self.evaluator.conn.close(); self.conn.close()
            return {"experiment_id":self.experiment_id,"status":"SUCCESS","candidate_count":len(candidates),"cached_count":cached_count,
              "shortlist_count":shortlist_count,"walk_forward_count":len(ranking_rows),"best_candidate_id":best["candidate_id"],
              "best_robust_score":best["robust_score"],"promotion_status":best["promotion_status"]}
        except Exception as exc:
            try:self.conn.execute("UPDATE optimization_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE experiment_id=?",[utcnow(),str(exc)[:1000],self.experiment_id]);self.conn.close();self.evaluator.conn.close()
            finally:pass
            raise

def run_module16(): return Module16Runner().run()
