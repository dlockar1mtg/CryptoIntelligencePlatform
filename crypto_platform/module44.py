from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module40 import MODULE40_SCHEMA
from crypto_platform.module42 import MODULE42_SCHEMA
from crypto_platform.module43 import MODULE43_SCHEMA

MODULE44_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module44_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module42_run_id VARCHAR,
    source_module43_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    decision_rows INTEGER,
    matured_rows INTEGER,
    benchmark_rows INTEGER,
    timing_rows INTEGER,
    action_rows INTEGER,
    horizon_rows INTEGER,
    portfolio_rows INTEGER,
    live_evidence_ratio DOUBLE,
    economic_value_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m44_decision_outcomes(
    run_id VARCHAR,
    source_module42_run_id VARCHAR,
    recommendation_date DATE,
    asset_id VARCHAR,
    horizon_days INTEGER,
    best_action VARCHAR,
    investment_score DOUBLE,
    target_portfolio_pct DOUBLE,
    forecast_confidence DOUBLE,
    current_price DOUBLE,
    outcome_due_date DATE,
    outcome_status VARCHAR,
    realized_date DATE,
    realized_price DOUBLE,
    realized_return_pct DOUBLE,
    strategy_position DOUBLE,
    strategy_return_pct DOUBLE,
    cash_return_pct DOUBLE,
    buy_hold_return_pct DOUBLE,
    excess_vs_cash_pct DOUBLE,
    excess_vs_buy_hold_pct DOUBLE,
    direction_correct BOOLEAN,
    economic_value_positive BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, source_module42_run_id, asset_id, horizon_days)
);

CREATE TABLE IF NOT EXISTS m44_benchmark_comparison(
    run_id VARCHAR,
    benchmark_name VARCHAR,
    horizon_days INTEGER,
    observations INTEGER,
    cumulative_return_pct DOUBLE,
    annualized_return_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    positive_period_pct DOUBLE,
    mean_period_return_pct DOUBLE,
    median_period_return_pct DOUBLE,
    value_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, benchmark_name, horizon_days)
);

CREATE TABLE IF NOT EXISTS m44_action_value(
    run_id VARCHAR,
    best_action VARCHAR,
    horizon_days INTEGER,
    decisions INTEGER,
    matured_decisions INTEGER,
    mean_realized_return_pct DOUBLE,
    mean_strategy_return_pct DOUBLE,
    mean_excess_vs_cash_pct DOUBLE,
    mean_excess_vs_buy_hold_pct DOUBLE,
    positive_value_rate_pct DOUBLE,
    directional_accuracy_pct DOUBLE,
    action_value_score DOUBLE,
    action_value_grade VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, best_action, horizon_days)
);

CREATE TABLE IF NOT EXISTS m44_timing_value(
    run_id VARCHAR,
    asset_id VARCHAR,
    recommendation_date DATE,
    current_action VARCHAR,
    horizon_days INTEGER,
    buy_now_return_pct DOUBLE,
    modeled_wait_entry_price DOUBLE,
    realized_wait_entry_price DOUBLE,
    wait_strategy_return_pct DOUBLE,
    wait_advantage_pct DOUBLE,
    timing_call_correct BOOLEAN,
    timing_value_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id, recommendation_date, horizon_days)
);

CREATE TABLE IF NOT EXISTS m44_horizon_value(
    run_id VARCHAR,
    horizon_days INTEGER,
    matured_decisions INTEGER,
    strategy_return_pct DOUBLE,
    buy_hold_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    directional_accuracy_pct DOUBLE,
    positive_value_rate_pct DOUBLE,
    sharpe_ratio DOUBLE,
    horizon_value_score DOUBLE,
    preferred_horizon BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, horizon_days)
);

CREATE TABLE IF NOT EXISTS m44_portfolio_value(
    run_id VARCHAR,
    recommendation_date DATE,
    horizon_days INTEGER,
    decisions INTEGER,
    target_crypto_pct DOUBLE,
    strategy_portfolio_return_pct DOUBLE,
    equal_weight_crypto_return_pct DOUBLE,
    buy_hold_weighted_return_pct DOUBLE,
    cash_return_pct DOUBLE,
    excess_vs_equal_weight_pct DOUBLE,
    excess_vs_buy_hold_pct DOUBLE,
    excess_vs_cash_pct DOUBLE,
    strategy_volatility_proxy_pct DOUBLE,
    risk_adjusted_value_score DOUBLE,
    portfolio_value_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, recommendation_date, horizon_days)
);

CREATE TABLE IF NOT EXISTS m44_economic_value_summary(
    run_id VARCHAR PRIMARY KEY,
    matured_decisions INTEGER,
    pending_decisions INTEGER,
    economic_value_positive_rate_pct DOUBLE,
    mean_excess_vs_cash_pct DOUBLE,
    mean_excess_vs_buy_hold_pct DOUBLE,
    best_action VARCHAR,
    best_horizon_days INTEGER,
    strategy_portfolio_return_pct DOUBLE,
    benchmark_return_pct DOUBLE,
    economic_value_score DOUBLE,
    evidence_status VARCHAR,
    economic_value_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m44_decision_outcomes AS
SELECT * FROM m44_decision_outcomes
WHERE run_id=(SELECT run_id FROM module44_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY recommendation_date, asset_id, horizon_days;

CREATE OR REPLACE VIEW latest_m44_benchmark_comparison AS
SELECT * FROM m44_benchmark_comparison
WHERE run_id=(SELECT run_id FROM module44_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY horizon_days, benchmark_name;

CREATE OR REPLACE VIEW latest_m44_action_value AS
SELECT * FROM m44_action_value
WHERE run_id=(SELECT run_id FROM module44_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY horizon_days, action_value_score DESC;

CREATE OR REPLACE VIEW latest_m44_timing_value AS
SELECT * FROM m44_timing_value
WHERE run_id=(SELECT run_id FROM module44_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY wait_advantage_pct DESC;

CREATE OR REPLACE VIEW latest_m44_horizon_value AS
SELECT * FROM m44_horizon_value
WHERE run_id=(SELECT run_id FROM module44_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY horizon_days;

CREATE OR REPLACE VIEW latest_m44_portfolio_value AS
SELECT * FROM m44_portfolio_value
WHERE run_id=(SELECT run_id FROM module44_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY recommendation_date, horizon_days;

CREATE OR REPLACE VIEW latest_m44_economic_value_summary AS
SELECT * FROM m44_economic_value_summary
WHERE run_id=(SELECT run_id FROM module44_runs ORDER BY started_at_utc DESC LIMIT 1);
"""

HORIZONS = [7, 30, 90, 180]
ACTION_POSITION = {
    "STRONG_BUY": 1.00,
    "BUY": 0.80,
    "SCALE_IN": 0.50,
    "HOLD": 0.00,
    "WAIT": 0.00,
    "REDUCE": -0.50,
    "AVOID": 0.00,
}


def utcnow():
    return datetime.now(timezone.utc)


def safe_float(value, default=0.0):
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


class Module44Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE40_SCHEMA)
        self.conn.execute(MODULE42_SCHEMA)
        self.conn.execute(MODULE43_SCHEMA)
        self.conn.execute(MODULE44_SCHEMA)
        self.cfg = self.settings["module44"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        row42 = self.conn.execute(
            "SELECT run_id FROM module42_runs WHERE status='SUCCESS' ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        row43 = self.conn.execute(
            "SELECT run_id FROM module43_runs WHERE status='SUCCESS' ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        if row42 is None or row43 is None:
            raise RuntimeError("Successful Modules 42 and 43 are required.")
        self.source42 = str(row42[0])
        self.source43 = str(row43[0])

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m44_stage", frame)
        cols = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _m44_stage"
        )
        self.conn.unregister("_m44_stage")

    def recommendations(self):
        return self.conn.execute(
            "SELECT * FROM m42_asset_recommendations WHERE run_id=?",
            [self.source42],
        ).fetchdf()

    def price_on_or_after(self, asset, date):
        return self.conn.execute(
            """
            SELECT observation_date, price_usd
            FROM canonical_market_daily
            WHERE asset_id=? AND observation_date>=? AND price_usd IS NOT NULL
            ORDER BY observation_date LIMIT 1
            """,
            [asset, date],
        ).fetchone()

    def outcomes(self, recs):
        rows = []
        today = pd.Timestamp.utcnow().date()
        for _, rec in recs.iterrows():
            rec_date = pd.Timestamp(rec["recommendation_date"]).date()
            asset = rec["asset_id"]
            current = safe_float(rec["current_price"])
            action = str(rec["best_action"])
            position = ACTION_POSITION.get(action, 0.0)
            for horizon in HORIZONS:
                due = (pd.Timestamp(rec_date) + pd.Timedelta(days=horizon)).date()
                realized = self.price_on_or_after(asset, due) if due <= today else None
                if realized is None:
                    status = "PENDING"
                    realized_date = pd.NaT
                    realized_price = realized_return = strategy_return = np.nan
                    buy_hold = excess_cash = excess_hold = np.nan
                    direction_correct = value_positive = pd.NA
                else:
                    status = "MATURED"
                    realized_date = pd.Timestamp(realized[0]).date()
                    realized_price = float(realized[1])
                    realized_return = (realized_price / current - 1) * 100
                    strategy_return = position * realized_return
                    buy_hold = realized_return
                    excess_cash = strategy_return
                    excess_hold = strategy_return - buy_hold
                    expected_dir = 1 if position > 0 else -1 if position < 0 else 0
                    actual_dir = 1 if realized_return > 0 else -1 if realized_return < 0 else 0
                    direction_correct = (
                        expected_dir == actual_dir
                        if expected_dir != 0
                        else abs(realized_return)
                        <= float(self.cfg["neutral_action_tolerance_pct"])
                    )
                    value_positive = excess_cash > 0
                rows.append({
                    "run_id": self.run_id,
                    "source_module42_run_id": self.source42,
                    "recommendation_date": rec_date,
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "best_action": action,
                    "investment_score": safe_float(rec["investment_score"]),
                    "target_portfolio_pct": safe_float(rec["best_current_portfolio_pct"]),
                    "forecast_confidence": safe_float(rec["forecast_confidence"]),
                    "current_price": current,
                    "outcome_due_date": due,
                    "outcome_status": status,
                    "realized_date": realized_date,
                    "realized_price": realized_price,
                    "realized_return_pct": realized_return,
                    "strategy_position": position,
                    "strategy_return_pct": strategy_return,
                    "cash_return_pct": 0.0 if status == "MATURED" else np.nan,
                    "buy_hold_return_pct": buy_hold,
                    "excess_vs_cash_pct": excess_cash,
                    "excess_vs_buy_hold_pct": excess_hold,
                    "direction_correct": direction_correct,
                    "economic_value_positive": value_positive,
                    "calculated_at_utc": utcnow(),
                })
        return pd.DataFrame(rows)

    def action_value(self, outcomes):
        rows = []
        for (action, horizon), group in outcomes.groupby(["best_action", "horizon_days"]):
            matured = group[group["outcome_status"] == "MATURED"]
            if matured.empty:
                metrics = [np.nan] * 7
                grade = "INSUFFICIENT_EVIDENCE"
            else:
                mean_realized = matured["realized_return_pct"].mean()
                mean_strategy = matured["strategy_return_pct"].mean()
                excess_cash = matured["excess_vs_cash_pct"].mean()
                excess_hold = matured["excess_vs_buy_hold_pct"].mean()
                positive = matured["economic_value_positive"].astype(float).mean() * 100
                directional = matured["direction_correct"].astype(float).mean() * 100
                score = (
                    0.35 * min(max(excess_cash + 50, 0), 100)
                    + 0.25 * min(max(excess_hold + 50, 0), 100)
                    + 0.20 * positive
                    + 0.20 * directional
                )
                metrics = [mean_realized, mean_strategy, excess_cash, excess_hold, positive, directional, score]
                grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"
            rows.append({
                "run_id": self.run_id,
                "best_action": action,
                "horizon_days": int(horizon),
                "decisions": len(group),
                "matured_decisions": len(matured),
                "mean_realized_return_pct": metrics[0],
                "mean_strategy_return_pct": metrics[1],
                "mean_excess_vs_cash_pct": metrics[2],
                "mean_excess_vs_buy_hold_pct": metrics[3],
                "positive_value_rate_pct": metrics[4],
                "directional_accuracy_pct": metrics[5],
                "action_value_score": metrics[6],
                "action_value_grade": grade,
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def benchmark_comparison(self, outcomes):
        rows = []
        matured = outcomes[outcomes["outcome_status"] == "MATURED"]
        for horizon, group in matured.groupby("horizon_days"):
            benchmarks = {
                "MODULE42_ACTION": group["strategy_return_pct"],
                "BUY_AND_HOLD": group["buy_hold_return_pct"],
                "CASH": group["cash_return_pct"],
                "EQUAL_WEIGHT_CRYPTO": group.groupby("recommendation_date")["buy_hold_return_pct"].mean(),
            }
            for name, series in benchmarks.items():
                series = pd.Series(series).dropna().astype(float)
                if series.empty:
                    continue
                r = series / 100
                cumulative = (np.prod(1 + r) - 1) * 100
                annualized = ((1 + cumulative / 100) ** (365 / max(len(series) * int(horizon), 1)) - 1) * 100
                vol = r.std(ddof=0) * math.sqrt(365 / max(int(horizon), 1)) * 100
                sharpe = r.mean() / r.std(ddof=0) * math.sqrt(365 / max(int(horizon), 1)) if r.std(ddof=0) > 0 else 0.0
                wealth = (1 + r).cumprod()
                drawdown = (wealth / wealth.cummax() - 1).min() * 100
                rows.append({
                    "run_id": self.run_id,
                    "benchmark_name": name,
                    "horizon_days": int(horizon),
                    "observations": len(series),
                    "cumulative_return_pct": cumulative,
                    "annualized_return_pct": annualized,
                    "annualized_volatility_pct": vol,
                    "sharpe_ratio": sharpe,
                    "maximum_drawdown_pct": drawdown,
                    "positive_period_pct": (series > 0).mean() * 100,
                    "mean_period_return_pct": series.mean(),
                    "median_period_return_pct": series.median(),
                    "value_status": "POSITIVE" if cumulative > 0 else "NEGATIVE" if cumulative < 0 else "FLAT",
                    "calculated_at_utc": utcnow(),
                })
        return pd.DataFrame(rows)

    def horizon_value(self, outcomes):
        rows = []
        matured = outcomes[outcomes["outcome_status"] == "MATURED"]
        for horizon, group in matured.groupby("horizon_days"):
            strategy = group["strategy_return_pct"].astype(float)
            buy_hold = group["buy_hold_return_pct"].astype(float)
            excess = strategy - buy_hold
            sharpe = strategy.mean() / strategy.std(ddof=0) * math.sqrt(365 / int(horizon)) if strategy.std(ddof=0) > 0 else 0.0
            score = (
                0.40 * min(max(excess.mean() + 50, 0), 100)
                + 0.25 * group["direction_correct"].astype(float).mean() * 100
                + 0.20 * group["economic_value_positive"].astype(float).mean() * 100
                + 0.15 * min(max(sharpe * 20 + 50, 0), 100)
            )
            rows.append({
                "run_id": self.run_id,
                "horizon_days": int(horizon),
                "matured_decisions": len(group),
                "strategy_return_pct": strategy.mean(),
                "buy_hold_return_pct": buy_hold.mean(),
                "excess_return_pct": excess.mean(),
                "directional_accuracy_pct": group["direction_correct"].astype(float).mean() * 100,
                "positive_value_rate_pct": group["economic_value_positive"].astype(float).mean() * 100,
                "sharpe_ratio": sharpe,
                "horizon_value_score": score,
                "preferred_horizon": False,
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        if not frame.empty:
            frame.loc[frame["horizon_value_score"].idxmax(), "preferred_horizon"] = True
        return frame

    def timing_value(self):
        analysis = self.conn.execute(
            "SELECT * FROM m43_buy_wait_analysis WHERE run_id=?",
            [self.source43],
        ).fetchdf()
        committee = self.conn.execute(
            "SELECT recommendation_date FROM m43_committee_brief WHERE run_id=?",
            [self.source43],
        ).fetchone()
        if committee is None:
            return pd.DataFrame()
        rec_date = pd.Timestamp(committee[0]).date()
        rows = []
        for _, timing in analysis.iterrows():
            asset = timing["asset_id"]
            for horizon, delay in [(30, 7), (90, 30)]:
                due = (pd.Timestamp(rec_date) + pd.Timedelta(days=horizon)).date()
                entry_date = (pd.Timestamp(rec_date) + pd.Timedelta(days=delay)).date()
                end = self.price_on_or_after(asset, due)
                entry = self.price_on_or_after(asset, entry_date)
                if end is None or entry is None:
                    continue
                current = safe_float(timing["current_price"])
                end_price = float(end[1])
                entry_price = float(entry[1])
                buy_now = (end_price / current - 1) * 100
                wait_return = (end_price / entry_price - 1) * 100
                advantage = wait_return - buy_now
                preference = str(timing["timing_preference"])
                predicted_wait = preference in {"WAIT_FOR_7D_ENTRY", "WAIT_FOR_30D_ENTRY"}
                correct = advantage > 0 if predicted_wait else advantage <= 0
                rows.append({
                    "run_id": self.run_id,
                    "asset_id": asset,
                    "recommendation_date": rec_date,
                    "current_action": timing["current_action"],
                    "horizon_days": horizon,
                    "buy_now_return_pct": buy_now,
                    "modeled_wait_entry_price": safe_float(timing["median_7d_price"] if horizon == 30 else timing["median_30d_price"]),
                    "realized_wait_entry_price": entry_price,
                    "wait_strategy_return_pct": wait_return,
                    "wait_advantage_pct": advantage,
                    "timing_call_correct": correct,
                    "timing_value_status": "VALUE_ADDED" if correct else "VALUE_LOST",
                    "calculated_at_utc": utcnow(),
                })
        return pd.DataFrame(rows)

    def portfolio_value(self, outcomes):
        rows = []
        matured = outcomes[outcomes["outcome_status"] == "MATURED"]
        for (rec_date, horizon), group in matured.groupby(["recommendation_date", "horizon_days"]):
            weights = group["target_portfolio_pct"].astype(float) / 100
            strategy_r = group["strategy_return_pct"].astype(float) / 100
            hold_r = group["buy_hold_return_pct"].astype(float) / 100
            strategy_portfolio = (weights * strategy_r).sum() * 100
            weighted_hold = (weights * hold_r).sum() * 100
            equal_weight = hold_r.mean() * 100
            vol_proxy = (weights * strategy_r.abs()).sum() * 100
            score = strategy_portfolio - equal_weight - 0.25 * vol_proxy
            rows.append({
                "run_id": self.run_id,
                "recommendation_date": rec_date,
                "horizon_days": int(horizon),
                "decisions": len(group),
                "target_crypto_pct": weights.sum() * 100,
                "strategy_portfolio_return_pct": strategy_portfolio,
                "equal_weight_crypto_return_pct": equal_weight,
                "buy_hold_weighted_return_pct": weighted_hold,
                "cash_return_pct": 0.0,
                "excess_vs_equal_weight_pct": strategy_portfolio - equal_weight,
                "excess_vs_buy_hold_pct": strategy_portfolio - weighted_hold,
                "excess_vs_cash_pct": strategy_portfolio,
                "strategy_volatility_proxy_pct": vol_proxy,
                "risk_adjusted_value_score": score,
                "portfolio_value_status": "VALUE_ADDED" if score > 0 else "VALUE_LOST" if score < 0 else "NEUTRAL",
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def run(self):
        self.conn.execute(
            "INSERT INTO module44_runs VALUES(?,?,?, ?,NULL,'RUNNING',0,0,0,0,0,0,0,0,NULL,NULL,NULL,'13.0.0')",
            [self.run_id, self.source42, self.source43, self.started],
        )
        try:
            recs = self.recommendations()
            outcomes = self.outcomes(recs)
            actions = self.action_value(outcomes)
            benchmarks = self.benchmark_comparison(outcomes)
            horizons = self.horizon_value(outcomes)
            timing = self.timing_value()
            portfolio = self.portfolio_value(outcomes)
            for table, frame in [
                ("m44_decision_outcomes", outcomes),
                ("m44_action_value", actions),
                ("m44_benchmark_comparison", benchmarks),
                ("m44_horizon_value", horizons),
                ("m44_timing_value", timing),
                ("m44_portfolio_value", portfolio),
            ]:
                self.upsert(table, frame)

            matured = outcomes[outcomes["outcome_status"] == "MATURED"]
            pending = outcomes[outcomes["outcome_status"] == "PENDING"]
            ratio = len(matured) / max(len(outcomes), 1)

            if matured.empty:
                positive_rate = excess_cash = excess_hold = strategy_return = benchmark_return = score = np.nan
                best_action = "NOT_AVAILABLE"
                best_horizon = 0
                evidence = "ACCUMULATING_EVIDENCE"
                value_status = "NOT_YET_MEASURABLE"
                recommendation = "WAIT_FOR_MATURED_OUTCOMES"
            else:
                positive_rate = matured["economic_value_positive"].astype(float).mean() * 100
                excess_cash = matured["excess_vs_cash_pct"].mean()
                excess_hold = matured["excess_vs_buy_hold_pct"].mean()
                mature_actions = actions[actions["matured_decisions"] > 0]
                best_action = mature_actions.sort_values("action_value_score", ascending=False).iloc[0]["best_action"] if not mature_actions.empty else "NOT_AVAILABLE"
                best_horizon = int(horizons.sort_values("horizon_value_score", ascending=False).iloc[0]["horizon_days"]) if not horizons.empty else 0
                strategy_return = portfolio["strategy_portfolio_return_pct"].mean() if not portfolio.empty else matured["strategy_return_pct"].mean()
                benchmark_return = portfolio["equal_weight_crypto_return_pct"].mean() if not portfolio.empty else matured["buy_hold_return_pct"].mean()
                score = (
                    0.35 * min(max(excess_cash + 50, 0), 100)
                    + 0.30 * min(max(excess_hold + 50, 0), 100)
                    + 0.20 * positive_rate
                    + 0.15 * min(max(strategy_return - benchmark_return + 50, 0), 100)
                )
                minimum = int(self.cfg["minimum_matured_decisions"])
                evidence = "LIVE_EVIDENCE_SUFFICIENT" if len(matured) >= minimum else "ACCUMULATING_EVIDENCE"
                value_status = "VALUE_ADDED" if score >= 60 else "VALUE_NEUTRAL" if score >= 45 else "VALUE_LOST"
                recommendation = "PROMOTE_ECONOMIC_VALUE_LAYER" if evidence == "LIVE_EVIDENCE_SUFFICIENT" and value_status == "VALUE_ADDED" else "CONTINUE_LIVE_VALIDATION"

            summary = pd.DataFrame([{
                "run_id": self.run_id,
                "matured_decisions": len(matured),
                "pending_decisions": len(pending),
                "economic_value_positive_rate_pct": positive_rate,
                "mean_excess_vs_cash_pct": excess_cash,
                "mean_excess_vs_buy_hold_pct": excess_hold,
                "best_action": best_action,
                "best_horizon_days": best_horizon,
                "strategy_portfolio_return_pct": strategy_return,
                "benchmark_return_pct": benchmark_return,
                "economic_value_score": score,
                "evidence_status": evidence,
                "economic_value_status": value_status,
                "advancement_recommendation": recommendation,
                "calculated_at_utc": utcnow(),
            }])
            self.upsert("m44_economic_value_summary", summary)
            notes = "Evaluated Module 42/43 decisions against cash, buy-and-hold, equal-weight crypto, action, timing, horizon, and portfolio economic value."
            self.conn.execute(
                """
                UPDATE module44_runs SET completed_at_utc=?,status='SUCCESS',decision_rows=?,matured_rows=?,benchmark_rows=?,timing_rows=?,action_rows=?,horizon_rows=?,portfolio_rows=?,live_evidence_ratio=?,economic_value_status=?,recommendation=?,notes=? WHERE run_id=?
                """,
                [utcnow(), len(outcomes), len(matured), len(benchmarks), len(timing), len(actions), len(horizons), len(portfolio), ratio, value_status, recommendation, notes, self.run_id],
            )
            self.conn.close()
            return summary.iloc[0].to_dict()
        except Exception as exc:
            self.conn.execute(
                "UPDATE module44_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",
                [utcnow(), str(exc)[:1000], self.run_id],
            )
            self.conn.close()
            raise


def run_module44():
    return Module44Runner().run()
