from __future__ import annotations

import itertools
import json
import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import wasserstein_distance

from crypto_platform.platform import load_all, connect
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.module33 import MODULE33_SCHEMA
from crypto_platform.ml.classes import canonical_classes
from crypto_platform.ml.validation import validate_probability_matrix

MODULE34_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module34_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module33_run_id VARCHAR,
    source_module30_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    execution_candidate_rows INTEGER,
    execution_daily_rows INTEGER,
    trade_rows INTEGER,
    drift_rows INTEGER,
    cost_rows INTEGER,
    selected_candidate_id VARCHAR,
    selected_sharpe DOUBLE,
    selected_max_drawdown_pct DOUBLE,
    selected_turnover_pct DOUBLE,
    btc_sharpe DOUBLE,
    btc_max_drawdown_pct DOUBLE,
    execution_drift_status VARCHAR,
    validation_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m34_execution_candidates(
    run_id VARCHAR,
    candidate_id VARCHAR,
    rebalance_frequency_days INTEGER,
    rebalance_band_pct DOUBLE,
    minimum_trade_pct DOUBLE,
    exposure_smoothing_alpha DOUBLE,
    annual_turnover_budget_pct DOUBLE,
    observations INTEGER,
    trade_days INTEGER,
    total_trades INTEGER,
    cumulative_return_pct DOUBLE,
    cagr_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    sortino_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    calmar_ratio DOUBLE,
    annualized_turnover_pct DOUBLE,
    total_transaction_cost_pct DOUBLE,
    tracking_error_pct DOUBLE,
    objective_score DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, candidate_id)
);

CREATE TABLE IF NOT EXISTS m34_execution_daily(
    run_id VARCHAR,
    observation_date DATE,
    candidate_id VARCHAR,
    held_regime VARCHAR,
    target_risk_exposure DOUBLE,
    smoothed_risk_exposure DOUBLE,
    target_gross_weight DOUBLE,
    executed_gross_weight DOUBLE,
    daily_return DOUBLE,
    cumulative_return DOUBLE,
    turnover DOUBLE,
    transaction_cost DOUBLE,
    trade_executed BOOLEAN,
    turnover_budget_remaining_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS m34_trade_ledger(
    run_id VARCHAR,
    observation_date DATE,
    asset_id VARCHAR,
    prior_weight DOUBLE,
    target_weight DOUBLE,
    executed_weight DOUBLE,
    trade_weight DOUBLE,
    trade_notional_pct DOUBLE,
    transaction_cost DOUBLE,
    execution_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, asset_id)
);

CREATE TABLE IF NOT EXISTS m34_execution_drift(
    run_id VARCHAR,
    window_end_date DATE,
    window_days INTEGER,
    reference_days INTEGER,
    observations INTEGER,
    jensen_shannon_distance DOUBLE,
    wasserstein_top_probability DOUBLE,
    wasserstein_entropy DOUBLE,
    disagreement_rate_pct DOUBLE,
    execution_tracking_error_pct DOUBLE,
    drift_score DOUBLE,
    drift_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, window_end_date, window_days)
);

CREATE TABLE IF NOT EXISTS m34_cost_sensitivity(
    run_id VARCHAR,
    transaction_cost_bps DOUBLE,
    observations INTEGER,
    cumulative_return_pct DOUBLE,
    cagr_pct DOUBLE,
    sharpe_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    annualized_turnover_pct DOUBLE,
    total_transaction_cost_pct DOUBLE,
    passed BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, transaction_cost_bps)
);

CREATE TABLE IF NOT EXISTS m34_benchmark_summary(
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
    annualized_turnover_pct DOUBLE,
    total_transaction_cost_pct DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, strategy_key)
);

CREATE TABLE IF NOT EXISTS m34_validation_summary(
    run_id VARCHAR PRIMARY KEY,
    selected_candidate_id VARCHAR,
    rebalance_frequency_days INTEGER,
    rebalance_band_pct DOUBLE,
    minimum_trade_pct DOUBLE,
    exposure_smoothing_alpha DOUBLE,
    annual_turnover_budget_pct DOUBLE,
    execution_drift_status VARCHAR,
    optimized_sharpe DOUBLE,
    btc_sharpe DOUBLE,
    optimized_max_drawdown_pct DOUBLE,
    btc_max_drawdown_pct DOUBLE,
    optimized_turnover_pct DOUBLE,
    trade_days INTEGER,
    total_trades INTEGER,
    cost_sensitivity_pass_rate_pct DOUBLE,
    validation_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m34_execution_candidates AS
SELECT * FROM m34_execution_candidates
WHERE run_id=(SELECT run_id FROM module34_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY selected DESC, objective_score DESC;

CREATE OR REPLACE VIEW latest_m34_execution_daily AS
SELECT * FROM m34_execution_daily
WHERE run_id=(SELECT run_id FROM module34_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_m34_trade_ledger AS
SELECT * FROM m34_trade_ledger
WHERE run_id=(SELECT run_id FROM module34_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY observation_date, asset_id;

CREATE OR REPLACE VIEW latest_m34_execution_drift AS
SELECT * FROM m34_execution_drift
WHERE run_id=(SELECT run_id FROM module34_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY window_end_date DESC, window_days;

CREATE OR REPLACE VIEW latest_m34_cost_sensitivity AS
SELECT * FROM m34_cost_sensitivity
WHERE run_id=(SELECT run_id FROM module34_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY transaction_cost_bps;

CREATE OR REPLACE VIEW latest_m34_benchmark_summary AS
SELECT * FROM m34_benchmark_summary
WHERE run_id=(SELECT run_id FROM module34_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY selected DESC, sharpe_ratio DESC;

CREATE OR REPLACE VIEW latest_m34_validation_summary AS
SELECT * FROM m34_validation_summary
WHERE run_id=(SELECT run_id FROM module34_runs ORDER BY started_at_utc DESC LIMIT 1);
"""

ASSETS = ["bitcoin","ethereum","solana","chainlink","xrp","avalanche"]

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


def entropy(matrix):
    matrix = np.clip(np.asarray(matrix,dtype=float),1e-12,1)
    return -np.sum(matrix*np.log(matrix),axis=1)


def performance_metrics(returns, turnover, costs):
    returns=pd.Series(returns).dropna()
    turnover=pd.Series(turnover).reindex(returns.index).fillna(0)
    costs=pd.Series(costs).reindex(returns.index).fillna(0)
    cumulative=(1+returns).cumprod()
    years=max(len(returns)/365,1/365)
    cagr=float(cumulative.iloc[-1]**(1/years)-1)
    vol=float(returns.std()*math.sqrt(365))
    sharpe=float(returns.mean()/returns.std()*math.sqrt(365)) if returns.std()>0 else 0.0
    downside=returns[returns<0].std()
    sortino=float(returns.mean()/downside*math.sqrt(365)) if downside is not None and not pd.isna(downside) and downside>0 else 0.0
    drawdown=cumulative/cumulative.cummax()-1
    maxdd=float(drawdown.min())
    calmar=float(cagr/abs(maxdd)) if maxdd<0 else 0.0
    return {
        "cumulative":cumulative,
        "cumulative_return_pct":float((cumulative.iloc[-1]-1)*100),
        "cagr_pct":cagr*100,
        "annualized_volatility_pct":vol*100,
        "sharpe_ratio":sharpe,
        "sortino_ratio":sortino,
        "maximum_drawdown_pct":maxdd*100,
        "calmar_ratio":calmar,
        "annualized_turnover_pct":float(turnover.mean()*365*100),
        "total_transaction_cost_pct":float(costs.sum()*100),
    }


class Module34Runner:
    def __init__(self):
        self.settings,_=load_all()
        self.conn=connect(self.settings)
        self.conn.execute(MODULE30_SCHEMA)
        self.conn.execute(MODULE33_SCHEMA)
        self.conn.execute(MODULE34_SCHEMA)
        self.cfg=self.settings["module34"]
        self.run_id=str(uuid.uuid4())
        self.started=utcnow()
        self.classes=canonical_classes()
        row=self.conn.execute(
            "SELECT run_id,source_module30_run_id FROM module33_runs "
            "WHERE status='SUCCESS' ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("No successful Module 33 run is available.")
        self.source_m33=str(row[0])
        self.source_m30=str(row[1])

    def upsert(self,table,frame):
        if frame.empty: return
        self.conn.register("_m34_stage",frame)
        columns=",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m34_stage"
        )
        self.conn.unregister("_m34_stage")

    def optimized_targets(self):
        frame=self.conn.execute(
            "SELECT observation_date,held_regime,target_risk_exposure,"
            "regularized_probability FROM m33_optimized_daily "
            "WHERE run_id=? ORDER BY observation_date",
            [self.source_m33]
        ).fetchdf()
        frame["observation_date"]=pd.to_datetime(frame["observation_date"])
        return frame.set_index("observation_date")

    def probabilities(self):
        frame=self.conn.execute(
            "SELECT observation_date,regime,probability FROM clean_probability_history "
            "WHERE run_id=? ORDER BY observation_date,regime",
            [self.source_m30]
        ).fetchdf()
        frame["observation_date"]=pd.to_datetime(frame["observation_date"])
        matrix=frame.pivot(index="observation_date",columns="regime",values="probability").reindex(columns=self.classes)
        validate_probability_matrix(matrix.to_numpy(),self.classes)
        return matrix.sort_index()

    def disagreement(self):
        frame=self.conn.execute(
            "SELECT observation_date,model_agreement FROM clean_regime_history "
            "WHERE run_id=? ORDER BY observation_date",[self.source_m30]
        ).fetchdf()
        frame["observation_date"]=pd.to_datetime(frame["observation_date"])
        return frame.set_index("observation_date")["model_agreement"]

    def prices(self):
        frame=self.conn.execute(
            "SELECT asset_id,observation_date,price_usd FROM canonical_market_daily "
            "WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche') "
            "AND price_usd IS NOT NULL ORDER BY observation_date,asset_id"
        ).fetchdf()
        frame["observation_date"]=pd.to_datetime(frame["observation_date"])
        return frame.pivot(index="observation_date",columns="asset_id",values="price_usd").reindex(columns=ASSETS).sort_index()

    def execute_policy(self,targets,returns,parameters,cost_bps):
        frequency=int(parameters["rebalance_frequency_days"])
        band=float(parameters["rebalance_band_pct"])/100
        minimum_trade=float(parameters["minimum_trade_pct"])/100
        alpha=float(parameters["exposure_smoothing_alpha"])
        annual_budget=float(parameters["annual_turnover_budget_pct"])/100

        dates=targets.index
        current=np.zeros(len(ASSETS))
        smoothed_exposure=0.0
        annual_turnover_used=0.0
        current_year=None
        last_rebalance_index=-10_000
        daily=[]
        trades=[]

        for i,date in enumerate(dates):
            if current_year != date.year:
                current_year=date.year
                annual_turnover_used=0.0

            row=targets.loc[date]
            regime=row["held_regime"]
            raw_exposure=float(row["target_risk_exposure"])
            smoothed_exposure=(
                raw_exposure if i==0
                else alpha*raw_exposure+(1-alpha)*smoothed_exposure
            )
            target=REGIME_WEIGHTS[regime]*smoothed_exposure
            difference=target-current

            due=(i-last_rebalance_index)>=frequency
            outside_band=np.abs(difference)>=band
            large_enough=np.abs(difference)>=minimum_trade
            desired=np.where(outside_band & large_enough,difference,0.0)
            requested_turnover=float(np.abs(desired).sum())
            remaining=max(annual_budget-annual_turnover_used,0.0)

            executed=np.zeros(len(ASSETS))
            reason="NO_TRADE"
            if due and requested_turnover>0 and remaining>0:
                scale=min(1.0,remaining/requested_turnover)
                executed=desired*scale
                reason="BAND_REBALANCE" if scale>=.999 else "TURNOVER_BUDGET_LIMIT"
                current=current+executed
                actual_turnover=float(np.abs(executed).sum())
                annual_turnover_used += actual_turnover
                last_rebalance_index=i
            else:
                actual_turnover=0.0
                if not due and requested_turnover>0:
                    reason="BATCHED_UNTIL_REBALANCE_DATE"
                elif remaining<=0 and requested_turnover>0:
                    reason="TURNOVER_BUDGET_EXHAUSTED"

            transaction_cost=actual_turnover*(float(cost_bps)/10000)
            daily_return=float(
                np.dot(current,returns.loc[date].fillna(0).to_numpy())
                -transaction_cost
            )
            for asset_index,asset in enumerate(ASSETS):
                if abs(executed[asset_index])>1e-12:
                    trades.append({
                        "observation_date":date,
                        "asset_id":asset,
                        "prior_weight":float(current[asset_index]-executed[asset_index]),
                        "target_weight":float(target[asset_index]),
                        "executed_weight":float(current[asset_index]),
                        "trade_weight":float(executed[asset_index]),
                        "trade_notional_pct":float(abs(executed[asset_index])*100),
                        "transaction_cost":float(abs(executed[asset_index])*(float(cost_bps)/10000)),
                        "execution_reason":reason,
                    })
            daily.append({
                "observation_date":date,
                "held_regime":regime,
                "target_risk_exposure":raw_exposure,
                "smoothed_risk_exposure":smoothed_exposure,
                "target_gross_weight":float(target.sum()),
                "executed_gross_weight":float(current.sum()),
                "daily_return":daily_return,
                "turnover":actual_turnover,
                "transaction_cost":transaction_cost,
                "trade_executed":bool(actual_turnover>0),
                "turnover_budget_remaining_pct":float(max(annual_budget-annual_turnover_used,0)*100),
            })

        daily=pd.DataFrame(daily).set_index("observation_date")
        metrics=performance_metrics(
            daily["daily_return"],daily["turnover"],daily["transaction_cost"]
        )
        daily["cumulative_return"]=metrics["cumulative"]
        trade_frame=pd.DataFrame(trades)
        tracking_error=float(
            np.sqrt(np.mean(
                (
                    daily["target_gross_weight"]
                    -daily["executed_gross_weight"]
                )**2
            ))*100
        )
        return daily,trade_frame,metrics,tracking_error

    def candidate_search(self,targets,returns):
        cfg=self.cfg["optimization"]
        grid=itertools.product(
            cfg["rebalance_frequency_days"],
            cfg["rebalance_band_pct"],
            cfg["minimum_trade_pct"],
            cfg["exposure_smoothing_alpha"],
            cfg["annual_turnover_budget_pct"],
        )
        rows=[]; paths={}; ledgers={}
        cost=float(self.cfg["transaction_cost_bps"])
        max_turnover=float(self.cfg["validation"]["maximum_turnover_pct"])
        for index,values in enumerate(grid,1):
            parameters={
                "rebalance_frequency_days":int(values[0]),
                "rebalance_band_pct":float(values[1]),
                "minimum_trade_pct":float(values[2]),
                "exposure_smoothing_alpha":float(values[3]),
                "annual_turnover_budget_pct":float(values[4]),
            }
            candidate_id=f"E{index:04d}"
            daily,trades,metrics,tracking=self.execute_policy(
                targets,returns,parameters,cost
            )
            turnover_penalty=max(metrics["annualized_turnover_pct"]-max_turnover,0)
            objective=float(
                65*metrics["sharpe_ratio"]
                +22*metrics["calmar_ratio"]
                +.18*metrics["cagr_pct"]
                -.08*abs(metrics["maximum_drawdown_pct"])
                -.05*turnover_penalty
                -.30*metrics["total_transaction_cost_pct"]
                -.03*tracking
            )
            rows.append({
                "run_id":self.run_id,
                "candidate_id":candidate_id,
                **parameters,
                "observations":len(daily),
                "trade_days":int(daily["trade_executed"].sum()),
                "total_trades":len(trades),
                "cumulative_return_pct":metrics["cumulative_return_pct"],
                "cagr_pct":metrics["cagr_pct"],
                "annualized_volatility_pct":metrics["annualized_volatility_pct"],
                "sharpe_ratio":metrics["sharpe_ratio"],
                "sortino_ratio":metrics["sortino_ratio"],
                "maximum_drawdown_pct":metrics["maximum_drawdown_pct"],
                "calmar_ratio":metrics["calmar_ratio"],
                "annualized_turnover_pct":metrics["annualized_turnover_pct"],
                "total_transaction_cost_pct":metrics["total_transaction_cost_pct"],
                "tracking_error_pct":tracking,
                "objective_score":objective,
                "selected":False,
                "calculated_at_utc":utcnow(),
            })
            paths[candidate_id]=daily
            ledgers[candidate_id]=trades
        candidates=pd.DataFrame(rows)
        selected_index=candidates["objective_score"].idxmax()
        candidates.loc[selected_index,"selected"]=True
        selected_id=str(candidates.loc[selected_index,"candidate_id"])
        return candidates,selected_id,paths[selected_id],ledgers[selected_id]

    def execution_drift(self,probabilities,disagreement,daily):
        windows=[int(x) for x in self.cfg["drift"]["window_days"]]
        reference_days=int(self.cfg["drift"]["reference_days"])
        top=probabilities.max(axis=1)
        ent=pd.Series(entropy(probabilities.to_numpy()),index=probabilities.index)
        rows=[]
        for window in windows:
            for end in range(reference_days+window,len(probabilities)+1,window):
                actual=probabilities.iloc[end-window:end]
                reference=probabilities.iloc[end-window-reference_days:end-window]
                mean_actual=actual.mean(axis=0).to_numpy()
                mean_reference=reference.mean(axis=0).to_numpy()
                js=float(jensenshannon(mean_reference,mean_actual,base=2))
                w_top=float(wasserstein_distance(
                    top.reindex(reference.index),top.reindex(actual.index)
                ))
                w_entropy=float(wasserstein_distance(
                    ent.reindex(reference.index),ent.reindex(actual.index)
                ))
                disagree=float((disagreement.reindex(actual.index)<.55).mean()*100)
                tracking=float(np.sqrt(np.mean(
                    (
                        daily.reindex(actual.index)["target_gross_weight"]
                        -daily.reindex(actual.index)["executed_gross_weight"]
                    )**2
                ))*100)
                score=float(
                    .35*min(js/.35,1)
                    +.20*min(w_top/.20,1)
                    +.15*min(w_entropy/.35,1)
                    +.15*min(disagree/50,1)
                    +.15*min(tracking/15,1)
                )
                status="CRITICAL" if score>=.75 else "WARNING" if score>=.45 else "STABLE"
                rows.append({
                    "run_id":self.run_id,
                    "window_end_date":actual.index.max().date(),
                    "window_days":window,
                    "reference_days":reference_days,
                    "observations":len(actual),
                    "jensen_shannon_distance":js,
                    "wasserstein_top_probability":w_top,
                    "wasserstein_entropy":w_entropy,
                    "disagreement_rate_pct":disagree,
                    "execution_tracking_error_pct":tracking,
                    "drift_score":score,
                    "drift_status":status,
                    "calculated_at_utc":utcnow(),
                })
        return pd.DataFrame(rows)

    def cost_sensitivity(self,targets,returns,parameters,btc_metrics):
        rows=[]
        max_turnover=float(self.cfg["validation"]["maximum_turnover_pct"])
        for cost in self.cfg["cost_sensitivity_bps"]:
            daily,_,metrics,_=self.execute_policy(
                targets,returns,parameters,float(cost)
            )
            passed=bool(
                metrics["sharpe_ratio"]>=btc_metrics["sharpe_ratio"]
                and metrics["maximum_drawdown_pct"]>btc_metrics["maximum_drawdown_pct"]
                and metrics["annualized_turnover_pct"]<=max_turnover
            )
            rows.append({
                "run_id":self.run_id,
                "transaction_cost_bps":float(cost),
                "observations":len(daily),
                "cumulative_return_pct":metrics["cumulative_return_pct"],
                "cagr_pct":metrics["cagr_pct"],
                "sharpe_ratio":metrics["sharpe_ratio"],
                "maximum_drawdown_pct":metrics["maximum_drawdown_pct"],
                "annualized_turnover_pct":metrics["annualized_turnover_pct"],
                "total_transaction_cost_pct":metrics["total_transaction_cost_pct"],
                "passed":passed,
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows)

    def benchmarks(self,returns,selected_daily):
        common=selected_daily.index
        selected_metrics=performance_metrics(
            selected_daily["daily_return"],
            selected_daily["turnover"],
            selected_daily["transaction_cost"],
        )
        zero=pd.Series(0.0,index=common)
        btc=returns.reindex(common)["bitcoin"].fillna(0)
        btc_metrics=performance_metrics(btc,zero,zero)
        equal=returns.reindex(common).fillna(0).mean(axis=1)
        equal_metrics=performance_metrics(equal,zero,zero)
        rows=[]
        for key,metrics,selected in [
            ("EXECUTION_OPTIMIZED",selected_metrics,True),
            ("BTC_BUY_HOLD",btc_metrics,False),
            ("EQUAL_WEIGHT_6",equal_metrics,False),
        ]:
            rows.append({
                "run_id":self.run_id,
                "strategy_key":key,
                "observations":len(common),
                "cumulative_return_pct":metrics["cumulative_return_pct"],
                "cagr_pct":metrics["cagr_pct"],
                "annualized_volatility_pct":metrics["annualized_volatility_pct"],
                "sharpe_ratio":metrics["sharpe_ratio"],
                "sortino_ratio":metrics["sortino_ratio"],
                "maximum_drawdown_pct":metrics["maximum_drawdown_pct"],
                "calmar_ratio":metrics["calmar_ratio"],
                "annualized_turnover_pct":metrics["annualized_turnover_pct"],
                "total_transaction_cost_pct":metrics["total_transaction_cost_pct"],
                "selected":selected,
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows),btc_metrics

    def run(self):
        self.conn.execute(
            """
            INSERT INTO module34_runs(
                run_id,source_module33_run_id,source_module30_run_id,
                started_at_utc,completed_at_utc,status,
                execution_candidate_rows,execution_daily_rows,trade_rows,
                drift_rows,cost_rows,selected_candidate_id,
                selected_sharpe,selected_max_drawdown_pct,selected_turnover_pct,
                btc_sharpe,btc_max_drawdown_pct,execution_drift_status,
                validation_status,recommendation,notes,platform_version
            )
            VALUES(
                ?,?,?,?,NULL,'RUNNING',
                0,0,0,0,0,NULL,
                NULL,NULL,NULL,NULL,NULL,NULL,
                NULL,NULL,NULL,'8.4.0'
            )
            """,
            [self.run_id,self.source_m33,self.source_m30,self.started],
        )
        try:
            targets=self.optimized_targets()
            probabilities=self.probabilities()
            prices=self.prices()
            returns=prices.pct_change(fill_method=None).fillna(0)
            common=targets.index.intersection(returns.index).intersection(probabilities.index)
            targets=targets.reindex(common)
            returns=returns.reindex(common)
            probabilities=probabilities.reindex(common)
            disagreement=self.disagreement().reindex(common)

            candidates,selected_id,daily,trades=self.candidate_search(targets,returns)
            selected=candidates[candidates["candidate_id"]==selected_id].iloc[0]
            benchmarks,btc_metrics=self.benchmarks(returns,daily)

            parameters={
                "rebalance_frequency_days":int(selected["rebalance_frequency_days"]),
                "rebalance_band_pct":float(selected["rebalance_band_pct"]),
                "minimum_trade_pct":float(selected["minimum_trade_pct"]),
                "exposure_smoothing_alpha":float(selected["exposure_smoothing_alpha"]),
                "annual_turnover_budget_pct":float(selected["annual_turnover_budget_pct"]),
            }
            drift=self.execution_drift(probabilities,disagreement,daily)
            costs=self.cost_sensitivity(targets,returns,parameters,btc_metrics)

            daily_out=daily.reset_index()
            daily_out.insert(0,"run_id",self.run_id)
            daily_out.insert(2,"candidate_id",selected_id)
            daily_out["observation_date"]=pd.to_datetime(daily_out["observation_date"]).dt.date
            daily_out["calculated_at_utc"]=utcnow()

            if trades.empty:
                trades=pd.DataFrame(columns=[
                    "observation_date","asset_id","prior_weight","target_weight",
                    "executed_weight","trade_weight","trade_notional_pct",
                    "transaction_cost","execution_reason"
                ])
            trades_out=trades.copy()
            if not trades_out.empty:
                trades_out.insert(0,"run_id",self.run_id)
                trades_out["observation_date"]=pd.to_datetime(trades_out["observation_date"]).dt.date
                trades_out["calculated_at_utc"]=utcnow()

            current_drift=(
                str(drift.sort_values("window_end_date").iloc[-1]["drift_status"])
                if not drift.empty else "UNKNOWN"
            )
            pass_rate=float(costs["passed"].mean()*100)
            max_turnover=float(self.cfg["validation"]["maximum_turnover_pct"])
            min_pass=float(self.cfg["validation"]["minimum_cost_pass_rate_pct"])
            passed=bool(
                float(selected["sharpe_ratio"])>=btc_metrics["sharpe_ratio"]
                and float(selected["maximum_drawdown_pct"])>btc_metrics["maximum_drawdown_pct"]
                and float(selected["annualized_turnover_pct"])<=max_turnover
                and pass_rate>=min_pass
                and current_drift!="CRITICAL"
            )
            status="PASSED" if passed else "LIMITED"
            recommendation=(
                "READY_FOR_PORTFOLIO_INTELLIGENCE"
                if passed else "EXECUTION_ENGINE_REQUIRES_REFINEMENT"
            )

            summary=pd.DataFrame([{
                "run_id":self.run_id,
                "selected_candidate_id":selected_id,
                "rebalance_frequency_days":int(selected["rebalance_frequency_days"]),
                "rebalance_band_pct":float(selected["rebalance_band_pct"]),
                "minimum_trade_pct":float(selected["minimum_trade_pct"]),
                "exposure_smoothing_alpha":float(selected["exposure_smoothing_alpha"]),
                "annual_turnover_budget_pct":float(selected["annual_turnover_budget_pct"]),
                "execution_drift_status":current_drift,
                "optimized_sharpe":float(selected["sharpe_ratio"]),
                "btc_sharpe":float(btc_metrics["sharpe_ratio"]),
                "optimized_max_drawdown_pct":float(selected["maximum_drawdown_pct"]),
                "btc_max_drawdown_pct":float(btc_metrics["maximum_drawdown_pct"]),
                "optimized_turnover_pct":float(selected["annualized_turnover_pct"]),
                "trade_days":int(selected["trade_days"]),
                "total_trades":int(selected["total_trades"]),
                "cost_sensitivity_pass_rate_pct":pass_rate,
                "validation_status":status,
                "advancement_recommendation":recommendation,
                "calculated_at_utc":utcnow(),
            }])

            for table,frame in [
                ("m34_execution_candidates",candidates),
                ("m34_execution_daily",daily_out),
                ("m34_trade_ledger",trades_out),
                ("m34_execution_drift",drift),
                ("m34_cost_sensitivity",costs),
                ("m34_benchmark_summary",benchmarks),
                ("m34_validation_summary",summary),
            ]:
                self.upsert(table,frame)

            notes=(
                "Rebalance bands, minimum trade sizes, trade batching, "
                "exposure smoothing, annual turnover budgets, Jensen-Shannon "
                "drift, Wasserstein drift, and transaction-cost sensitivity completed."
            )
            self.conn.execute(
                """
                UPDATE module34_runs
                SET completed_at_utc=?,status='SUCCESS',
                    execution_candidate_rows=?,execution_daily_rows=?,
                    trade_rows=?,drift_rows=?,cost_rows=?,
                    selected_candidate_id=?,selected_sharpe=?,
                    selected_max_drawdown_pct=?,selected_turnover_pct=?,
                    btc_sharpe=?,btc_max_drawdown_pct=?,
                    execution_drift_status=?,validation_status=?,
                    recommendation=?,notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),len(candidates),len(daily_out),len(trades_out),
                    len(drift),len(costs),selected_id,
                    float(selected["sharpe_ratio"]),
                    float(selected["maximum_drawdown_pct"]),
                    float(selected["annualized_turnover_pct"]),
                    float(btc_metrics["sharpe_ratio"]),
                    float(btc_metrics["maximum_drawdown_pct"]),
                    current_drift,status,recommendation,notes,self.run_id,
                ],
            )
            self.conn.close()
            return summary.iloc[0].to_dict()
        except Exception as exc:
            self.conn.execute(
                "UPDATE module34_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",
                [utcnow(),str(exc)[:1000],self.run_id],
            )
            self.conn.close()
            raise


def run_module34():
    return Module34Runner().run()
