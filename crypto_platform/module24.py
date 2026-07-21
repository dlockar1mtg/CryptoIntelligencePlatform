from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from crypto_platform.platform import load_all, connect
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module17 import MODULE17_SCHEMA
from crypto_platform.module22 import MODULE22_SCHEMA
from crypto_platform.module23 import MODULE23_SCHEMA

CORE_IDS = ["bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche"]

MODULE24_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module24_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    factor_rows INTEGER,
    candidates_tested INTEGER,
    walk_forward_folds INTEGER,
    selected_candidate VARCHAR,
    corrected_return_pct DOUBLE,
    btc_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    information_ratio DOUBLE,
    bootstrap_probability_positive DOUBLE,
    audit_status VARCHAR,
    promotion_status VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS alpha_factor_daily(
    observation_date DATE,
    asset_id VARCHAR,
    momentum_30d DOUBLE,
    momentum_90d DOUBLE,
    momentum_180d DOUBLE,
    trend_50_200 DOUBLE,
    reversal_14d DOUBLE,
    realized_volatility_90d DOUBLE,
    max_drawdown_180d DOUBLE,
    relative_strength_90d DOUBLE,
    relative_strength_180d DOUBLE,
    liquidity_regime DOUBLE,
    macro_risk_regime DOUBLE,
    breadth_regime DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(observation_date, asset_id)
);

CREATE TABLE IF NOT EXISTS alpha_candidate_registry(
    run_id VARCHAR,
    candidate_id VARCHAR,
    parameter_hash VARCHAR,
    parameters_json VARCHAR,
    momentum_weight DOUBLE,
    trend_weight DOUBLE,
    relative_strength_weight DOUBLE,
    reversal_weight DOUBLE,
    volatility_penalty DOUBLE,
    drawdown_penalty DOUBLE,
    macro_weight DOUBLE,
    cash_sensitivity DOUBLE,
    maximum_cash_weight DOUBLE,
    maximum_asset_weight DOUBLE,
    status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, candidate_id)
);

CREATE TABLE IF NOT EXISTS alpha_walk_forward_results(
    run_id VARCHAR,
    fold_number INTEGER,
    candidate_id VARCHAR,
    training_start_date DATE,
    training_end_date DATE,
    testing_start_date DATE,
    testing_end_date DATE,
    training_objective DOUBLE,
    testing_return_pct DOUBLE,
    btc_return_pct DOUBLE,
    equal_weight_return_pct DOUBLE,
    inverse_volatility_return_pct DOUBLE,
    excess_vs_btc_pct DOUBLE,
    maximum_drawdown_pct DOUBLE,
    information_ratio DOUBLE,
    average_cash_weight_pct DOUBLE,
    average_turnover_pct DOUBLE,
    transaction_cost_drag_pct DOUBLE,
    selected_for_fold BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number, candidate_id)
);

CREATE TABLE IF NOT EXISTS alpha_portfolio_periods(
    run_id VARCHAR,
    fold_number INTEGER,
    candidate_id VARCHAR,
    rebalance_date DATE,
    next_rebalance_date DATE,
    asset_id VARCHAR,
    target_weight DOUBLE,
    realized_return_pct DOUBLE,
    contribution_pct DOUBLE,
    completed_portfolio_return_pct DOUBLE,
    btc_return_pct DOUBLE,
    equal_weight_return_pct DOUBLE,
    inverse_volatility_return_pct DOUBLE,
    turnover_pct DOUBLE,
    transaction_cost_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number, candidate_id, rebalance_date, asset_id)
);

CREATE TABLE IF NOT EXISTS alpha_label_validation(
    run_id VARCHAR,
    target_key VARCHAR,
    forward_horizon_days INTEGER,
    training_rows INTEGER,
    testing_rows INTEGER,
    event_rate_pct DOUBLE,
    roc_auc DOUBLE,
    inverted_auc DOUBLE,
    label_status VARCHAR,
    recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, target_key, forward_horizon_days)
);

CREATE TABLE IF NOT EXISTS alpha_bootstrap_validation(
    run_id VARCHAR PRIMARY KEY,
    simulations INTEGER,
    mean_excess_pct DOUBLE,
    median_excess_pct DOUBLE,
    lower_95_pct DOUBLE,
    upper_95_pct DOUBLE,
    probability_excess_positive DOUBLE,
    probability_excess_above_10pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS alpha_research_summary(
    run_id VARCHAR PRIMARY KEY,
    selected_candidate VARCHAR,
    start_date DATE,
    end_date DATE,
    folds INTEGER,
    periods INTEGER,
    total_return_pct DOUBLE,
    annualized_return_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    btc_total_return_pct DOUBLE,
    equal_weight_total_return_pct DOUBLE,
    inverse_volatility_total_return_pct DOUBLE,
    btc_excess_pct DOUBLE,
    tracking_error_pct DOUBLE,
    information_ratio DOUBLE,
    benchmark_win_rate_pct DOUBLE,
    average_cash_weight_pct DOUBLE,
    average_turnover_pct DOUBLE,
    transaction_cost_drag_pct DOUBLE,
    accounting_reconciliation_error_pct DOUBLE,
    bootstrap_probability_positive DOUBLE,
    audit_status VARCHAR,
    promotion_status VARCHAR,
    promotion_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_alpha_candidate_registry AS
SELECT x.* FROM alpha_candidate_registry x
JOIN (SELECT run_id FROM module24_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);

CREATE OR REPLACE VIEW latest_alpha_walk_forward_results AS
SELECT x.* FROM alpha_walk_forward_results x
JOIN (SELECT run_id FROM module24_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id)
ORDER BY fold_number, selected_for_fold DESC, training_objective DESC;

CREATE OR REPLACE VIEW latest_alpha_portfolio_periods AS
SELECT x.* FROM alpha_portfolio_periods x
JOIN (SELECT run_id FROM module24_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id)
ORDER BY rebalance_date, target_weight DESC;

CREATE OR REPLACE VIEW latest_alpha_label_validation AS
SELECT x.* FROM alpha_label_validation x
JOIN (SELECT run_id FROM module24_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);

CREATE OR REPLACE VIEW latest_alpha_bootstrap_validation AS
SELECT x.* FROM alpha_bootstrap_validation x
JOIN (SELECT run_id FROM module24_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);

CREATE OR REPLACE VIEW latest_alpha_research_summary AS
SELECT x.* FROM alpha_research_summary x
JOIN (SELECT run_id FROM module24_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def safe(value: Any, default: float = 0.0) -> float:
    return float(default if value is None or pd.isna(value) else value)


def clamp(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))


def annual_metrics(returns: pd.Series, periods_per_year: float):
    if returns.empty:
        return 0.0, 0.0, 0.0, None, 0.0
    curve = (1 + returns).cumprod()
    total = float(curve.iloc[-1] - 1)
    years = max(len(returns) / periods_per_year, 1 / periods_per_year)
    annual = (1 + total) ** (1 / years) - 1 if total > -1 else -1.0
    volatility = float(returns.std(ddof=1) * math.sqrt(periods_per_year)) if len(returns) > 1 else 0.0
    sharpe = annual / volatility if volatility > 0 else None
    drawdown = curve / curve.cummax() - 1
    return total, annual, volatility, sharpe, float(drawdown.min())


class Module24Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        for schema in [MODULE6_SCHEMA, MODULE17_SCHEMA, MODULE22_SCHEMA, MODULE23_SCHEMA, MODULE24_SCHEMA]:
            self.conn.execute(schema)
        self.cfg = self.settings["module24"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m24_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) SELECT {columns} FROM _m24_stage"
        )
        self.conn.unregister("_m24_stage")

    def prices(self) -> pd.DataFrame:
        frame = self.conn.execute("""
            SELECT asset_id, observation_date, price_usd
            FROM canonical_market_daily
            WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
              AND price_usd IS NOT NULL
            ORDER BY observation_date, asset_id
        """).fetchdf()
        if frame.empty:
            raise RuntimeError("Canonical core price history is empty.")
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        price = frame.pivot(index="observation_date", columns="asset_id", values="price_usd").sort_index()
        missing = [asset for asset in CORE_IDS if asset not in price.columns]
        if missing:
            raise RuntimeError(f"Missing core histories: {missing}")
        return price

    def context(self, index: pd.Index) -> pd.DataFrame:
        frame = self.conn.execute(
            "SELECT * FROM crypto_features_daily ORDER BY observation_date"
        ).fetchdf()
        if frame.empty:
            return pd.DataFrame(index=index)
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame.set_index("observation_date").sort_index().reindex(index).ffill()

    def build_factors(self, price: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
        returns = price.pct_change(fill_method=None)
        macro = pd.concat([
            context.get("vix", pd.Series(index=price.index, dtype=float)).rank(pct=True),
            context.get("high_yield_spread", pd.Series(index=price.index, dtype=float)).rank(pct=True),
            context.get("dollar_index", pd.Series(index=price.index, dtype=float)).rank(pct=True),
        ], axis=1).mean(axis=1)
        liquidity = pd.concat([
            context.get("stablecoin_growth_30d_pct", pd.Series(index=price.index, dtype=float)).rank(pct=True),
            1 - context.get("high_yield_spread", pd.Series(index=price.index, dtype=float)).rank(pct=True),
            1 - context.get("dollar_index", pd.Series(index=price.index, dtype=float)).rank(pct=True),
        ], axis=1).mean(axis=1)
        breadth = context.get(
            "core_breadth_above_sma50_pct", pd.Series(index=price.index, dtype=float)
        ) / 100

        rows = []
        for asset in CORE_IDS:
            series = price[asset]
            ret = returns[asset]
            frame = pd.DataFrame({
                "observation_date": price.index,
                "asset_id": asset,
                "momentum_30d": series.pct_change(30, fill_method=None),
                "momentum_90d": series.pct_change(90, fill_method=None),
                "momentum_180d": series.pct_change(180, fill_method=None),
                "trend_50_200": series.rolling(50).mean() / series.rolling(200).mean() - 1,
                "reversal_14d": -series.pct_change(14, fill_method=None),
                "realized_volatility_90d": ret.rolling(90).std() * math.sqrt(365),
                "max_drawdown_180d": series / series.rolling(180).max() - 1,
                "relative_strength_90d": series.pct_change(90, fill_method=None) - price["bitcoin"].pct_change(90, fill_method=None),
                "relative_strength_180d": series.pct_change(180, fill_method=None) - price["bitcoin"].pct_change(180, fill_method=None),
                "liquidity_regime": liquidity,
                "macro_risk_regime": macro,
                "breadth_regime": breadth,
                "calculated_at_utc": utcnow(),
            })
            rows.append(frame)
        result = pd.concat(rows, ignore_index=True)
        result["observation_date"] = pd.to_datetime(result["observation_date"]).dt.date
        self.upsert("alpha_factor_daily", result)
        return result

    def generate_candidates(self) -> pd.DataFrame:
        rng = np.random.default_rng(int(self.cfg["candidate_search"]["random_seed"]))
        rows = []
        for index in range(1, int(self.cfg["candidate_search"]["candidate_count"]) + 1):
            weights = rng.dirichlet([2.2, 1.8, 2.0, 0.8])
            params = {
                "momentum_weight": float(weights[0]),
                "trend_weight": float(weights[1]),
                "relative_strength_weight": float(weights[2]),
                "reversal_weight": float(weights[3]),
                "volatility_penalty": float(rng.uniform(0.15, 1.25)),
                "drawdown_penalty": float(rng.uniform(0.15, 1.25)),
                "macro_weight": float(rng.uniform(0.0, 0.45)),
                "cash_sensitivity": float(rng.uniform(0.2, 1.3)),
                "maximum_cash_weight": float(rng.uniform(0.1, 0.5)),
                "maximum_asset_weight": float(rng.uniform(0.28, 0.48)),
            }
            payload = json.dumps(params, sort_keys=True)
            rows.append({
                "run_id": self.run_id,
                "candidate_id": f"A{index:04d}",
                "parameter_hash": hashlib.sha256(payload.encode()).hexdigest(),
                "parameters_json": payload,
                **params,
                "status": "GENERATED",
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert("alpha_candidate_registry", frame)
        return frame

    @staticmethod
    def zscore(series: pd.Series) -> pd.Series:
        std = series.std(ddof=0)
        if pd.isna(std) or std == 0:
            return pd.Series(0.0, index=series.index)
        return ((series - series.mean()) / std).clip(-3, 3)

    def snapshot(self, factors: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
        eligible = factors[pd.to_datetime(factors["observation_date"]) <= date]
        if eligible.empty:
            return eligible
        latest = pd.to_datetime(eligible["observation_date"]).max()
        return eligible[pd.to_datetime(eligible["observation_date"]) == latest]

    def allocate(self, snapshot: pd.DataFrame, candidate: pd.Series) -> pd.DataFrame:
        data = snapshot.set_index("asset_id").reindex(CORE_IDS)
        momentum = (
            0.25 * self.zscore(data["momentum_30d"])
            + 0.45 * self.zscore(data["momentum_90d"])
            + 0.30 * self.zscore(data["momentum_180d"])
        )
        trend = self.zscore(data["trend_50_200"])
        relative = (
            0.60 * self.zscore(data["relative_strength_90d"])
            + 0.40 * self.zscore(data["relative_strength_180d"])
        )
        reversal = self.zscore(data["reversal_14d"])
        volatility = self.zscore(data["realized_volatility_90d"])
        drawdown = self.zscore(data["max_drawdown_180d"].abs())
        macro_support = (
            safe(data["liquidity_regime"].median(), 0.5)
            + safe(data["breadth_regime"].median(), 0.5)
            - safe(data["macro_risk_regime"].median(), 0.5)
        ) / 2
        score = (
            momentum * candidate["momentum_weight"]
            + trend * candidate["trend_weight"]
            + relative * candidate["relative_strength_weight"]
            + reversal * candidate["reversal_weight"]
            - volatility * candidate["volatility_penalty"]
            - drawdown * candidate["drawdown_penalty"]
            + macro_support * candidate["macro_weight"]
        )
        cash = clamp(
            0.12
            + max(0.0, -safe(score.mean())) * candidate["cash_sensitivity"] * 0.18
            + max(0.0, safe(data["macro_risk_regime"].median(), 0.5) - safe(data["liquidity_regime"].median(), 0.5)) * candidate["cash_sensitivity"] * 0.20,
            0.03,
            candidate["maximum_cash_weight"],
        )
        raw = np.exp((score.fillna(score.median()) - score.max()) * 0.8)
        raw = raw.replace([np.inf, -np.inf], np.nan).fillna(1.0)
        weights = raw / raw.sum() * (1 - cash)
        maximum = candidate["maximum_asset_weight"]
        for _ in range(12):
            excess = np.maximum(weights.to_numpy() - maximum, 0).sum()
            weights = weights.clip(upper=maximum)
            uncapped = weights < maximum - 1e-9
            if excess <= 1e-10 or not uncapped.any() or weights[uncapped].sum() <= 0:
                break
            weights.loc[uncapped] += excess * weights.loc[uncapped] / weights[uncapped].sum()
        allocation = pd.DataFrame({"asset_id": CORE_IDS, "target_weight": weights.reindex(CORE_IDS).fillna(0).to_numpy()})
        return pd.concat([
            allocation,
            pd.DataFrame([{"asset_id": "CASH", "target_weight": cash}]),
        ], ignore_index=True)

    def simulate(self, price, factors, candidate, start, end, fold, store):
        dates = list(price.index[(price.index >= start) & (price.index <= end)][:: int(self.cfg["portfolio"]["rebalance_days"])])
        previous = {asset: 0.0 for asset in CORE_IDS + ["CASH"]}
        previous["CASH"] = 1.0
        summary_rows, detail_rows = [], []
        for index in range(len(dates) - 1):
            date, next_date = dates[index], dates[index + 1]
            snapshot = self.snapshot(factors, date)
            if snapshot["asset_id"].nunique() < len(CORE_IDS):
                continue
            allocation = self.allocate(snapshot, candidate)
            weights = dict(zip(allocation["asset_id"], allocation["target_weight"]))
            turnover = 0.5 * sum(abs(weights.get(asset, 0) - previous.get(asset, 0)) for asset in set(weights) | set(previous))
            cost = turnover * float(self.cfg["portfolio"]["transaction_cost_bps"]) / 10000
            portfolio_return = -cost
            returns = {}
            for asset, weight in weights.items():
                realized = 0.0 if asset == "CASH" else float(price.at[next_date, asset] / price.at[date, asset] - 1)
                returns[asset] = realized
                portfolio_return += weight * realized
            btc_return = returns["bitcoin"]
            equal_weight_return = float(np.mean([returns[a] for a in CORE_IDS]))
            trailing_vol = price.loc[:date].pct_change(fill_method=None).tail(90)[CORE_IDS].std().replace(0, np.nan)
            inverse_weights = (1 / trailing_vol) / (1 / trailing_vol).sum()
            inverse_return = float(sum(inverse_weights.get(a, 0) * returns[a] for a in CORE_IDS))
            summary_rows.append({
                "rebalance_date": date,
                "next_rebalance_date": next_date,
                "portfolio_return": portfolio_return,
                "btc_return": btc_return,
                "equal_weight_return": equal_weight_return,
                "inverse_volatility_return": inverse_return,
                "cash_weight": weights.get("CASH", 0),
                "turnover": turnover,
                "transaction_cost": cost,
            })
            if store:
                for asset, weight in weights.items():
                    detail_rows.append({
                        "run_id": self.run_id,
                        "fold_number": fold,
                        "candidate_id": candidate["candidate_id"],
                        "rebalance_date": date.date(),
                        "next_rebalance_date": next_date.date(),
                        "asset_id": asset,
                        "target_weight": weight,
                        "realized_return_pct": returns[asset] * 100,
                        "contribution_pct": weight * returns[asset] * 100,
                        "completed_portfolio_return_pct": portfolio_return * 100,
                        "btc_return_pct": btc_return * 100,
                        "equal_weight_return_pct": equal_weight_return * 100,
                        "inverse_volatility_return_pct": inverse_return * 100,
                        "turnover_pct": turnover * 100,
                        "transaction_cost_pct": cost * 100,
                        "calculated_at_utc": utcnow(),
                    })
            previous = weights
        return pd.DataFrame(summary_rows), pd.DataFrame(detail_rows)

    def evaluate(self, frame):
        if frame.empty:
            return None
        ppy = 365 / int(self.cfg["portfolio"]["rebalance_days"])
        p = annual_metrics(frame["portfolio_return"], ppy)
        b = annual_metrics(frame["btc_return"], ppy)
        e = annual_metrics(frame["equal_weight_return"], ppy)
        i = annual_metrics(frame["inverse_volatility_return"], ppy)
        active = frame["portfolio_return"] - frame["btc_return"]
        tracking = float(active.std(ddof=1) * math.sqrt(ppy)) if len(active) > 1 else 0.0
        ir = (p[1] - b[1]) / tracking if tracking > 0 else None
        objective = p[1] * 30 + (ir if ir is not None else -1) * 18 + p[4] * 20 + (frame["portfolio_return"] > frame["btc_return"]).mean() * 12 - frame["turnover"].mean() * 20
        return {
            "total": p[0], "annual": p[1], "volatility": p[2], "sharpe": p[3], "drawdown": p[4],
            "btc": b[0], "equal": e[0], "inverse": i[0], "excess": p[0] - b[0],
            "tracking": tracking, "ir": ir, "cash": frame["cash_weight"].mean(),
            "turnover": frame["turnover"].mean(), "cost": frame["transaction_cost"].sum(),
            "objective": objective,
        }

    def windows(self, price):
        train_months = int(self.cfg["walk_forward"]["training_months"])
        test_months = int(self.cfg["walk_forward"]["testing_months"])
        step_months = int(self.cfg["walk_forward"]["step_months"])
        test_start = price.index.min() + pd.DateOffset(months=train_months)
        windows = []
        while test_start + pd.DateOffset(months=test_months) <= price.index.max():
            windows.append((test_start - pd.DateOffset(months=train_months), test_start, test_start, test_start + pd.DateOffset(months=test_months)))
            test_start += pd.DateOffset(months=step_months)
        return windows

    def walk_forward(self, price, factors, candidates):
        result_rows, period_frames = [], []
        shortlist_count = int(self.cfg["candidate_search"]["shortlist_count"])
        for fold, (train_start, train_end, test_start, test_end) in enumerate(self.windows(price), start=1):
            training = []
            for _, candidate in candidates.iterrows():
                frame, _ = self.simulate(price, factors, candidate, train_start, train_end, fold, False)
                metrics = self.evaluate(frame)
                if metrics:
                    training.append((candidate["candidate_id"], metrics["objective"]))
            if not training:
                continue
            ranked = sorted(training, key=lambda item: item[1], reverse=True)[:shortlist_count]
            selected_id = ranked[0][0]
            for candidate_id, objective in ranked:
                candidate = candidates[candidates["candidate_id"] == candidate_id].iloc[0]
                frame, detail = self.simulate(price, factors, candidate, test_start, test_end, fold, candidate_id == selected_id)
                metrics = self.evaluate(frame)
                if not metrics:
                    continue
                result_rows.append({
                    "run_id": self.run_id,
                    "fold_number": fold,
                    "candidate_id": candidate_id,
                    "training_start_date": train_start.date(),
                    "training_end_date": train_end.date(),
                    "testing_start_date": test_start.date(),
                    "testing_end_date": test_end.date(),
                    "training_objective": objective,
                    "testing_return_pct": metrics["total"] * 100,
                    "btc_return_pct": metrics["btc"] * 100,
                    "equal_weight_return_pct": metrics["equal"] * 100,
                    "inverse_volatility_return_pct": metrics["inverse"] * 100,
                    "excess_vs_btc_pct": metrics["excess"] * 100,
                    "maximum_drawdown_pct": metrics["drawdown"] * 100,
                    "information_ratio": metrics["ir"],
                    "average_cash_weight_pct": metrics["cash"] * 100,
                    "average_turnover_pct": metrics["turnover"] * 100,
                    "transaction_cost_drag_pct": metrics["cost"] * 100,
                    "selected_for_fold": candidate_id == selected_id,
                    "calculated_at_utc": utcnow(),
                })
                if not detail.empty:
                    period_frames.append(detail)
        results = pd.DataFrame(result_rows)
        periods = pd.concat(period_frames, ignore_index=True) if period_frames else pd.DataFrame()
        self.upsert("alpha_walk_forward_results", results)
        self.upsert("alpha_portfolio_periods", periods)
        return results, periods

    def validate_labels(self, price, factors):
        btc_factors = factors[factors["asset_id"] == "bitcoin"].copy()
        btc_factors["observation_date"] = pd.to_datetime(btc_factors["observation_date"])
        btc_factors = btc_factors.set_index("observation_date")
        rows = []
        for horizon in [30, 90, 180]:
            future = pd.concat([price["bitcoin"].shift(-offset) for offset in range(1, horizon + 1)], axis=1)
            full_window = future.notna().all(axis=1)
            target = (future.min(axis=1) / price["bitcoin"] - 1 <= -0.20).astype(float).where(full_window, np.nan)
            sample = btc_factors[["liquidity_regime", "macro_risk_regime", "breadth_regime"]].copy()
            sample["target"] = target.reindex(sample.index)
            sample = sample.dropna()
            if len(sample) < 365 or sample["target"].nunique() < 2:
                continue
            split = int(len(sample) * 0.75)
            train, test = sample.iloc[:split], sample.iloc[split:]
            if train["target"].nunique() < 2 or test["target"].nunique() < 2:
                continue
            model = Pipeline([
                ("scale", StandardScaler()),
                ("model", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=600)),
            ])
            model.fit(train.drop(columns="target"), train["target"].astype(int))
            probability = model.predict_proba(test.drop(columns="target"))[:, 1]
            auc = roc_auc_score(test["target"], probability)
            inverted = 1 - auc
            status = "ACCEPTABLE" if auc >= 0.55 else ("POSSIBLY_INVERTED" if inverted >= 0.60 else "WEAK")
            rows.append({
                "run_id": self.run_id,
                "target_key": "DRAWDOWN_20",
                "forward_horizon_days": horizon,
                "training_rows": len(train),
                "testing_rows": len(test),
                "event_rate_pct": sample["target"].mean() * 100,
                "roc_auc": auc,
                "inverted_auc": inverted,
                "label_status": status,
                "recommendation": "Eligible for shadow use." if status == "ACCEPTABLE" else "Do not use for allocation.",
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert("alpha_label_validation", frame)
        return frame

    def aggregate_periods(self, periods):
        grouped = periods.groupby(["fold_number", "candidate_id", "rebalance_date", "next_rebalance_date"], as_index=False).agg(
            contribution_sum_pct=("contribution_pct", "sum"),
            completed=("completed_portfolio_return_pct", "first"),
            btc_return_pct=("btc_return_pct", "first"),
            equal_weight_return_pct=("equal_weight_return_pct", "first"),
            inverse_volatility_return_pct=("inverse_volatility_return_pct", "first"),
            turnover_pct=("turnover_pct", "first"),
            transaction_cost_pct=("transaction_cost_pct", "first"),
        )
        grouped["corrected_return_pct"] = grouped["contribution_sum_pct"] - grouped["transaction_cost_pct"]
        grouped["reconciliation_error_pct"] = grouped["completed"] - grouped["corrected_return_pct"]
        return grouped

    def bootstrap(self, aggregated):
        rng = np.random.default_rng(int(self.cfg["bootstrap"]["seed"]))
        simulations = int(self.cfg["bootstrap"]["simulations"])
        portfolio = aggregated["corrected_return_pct"].to_numpy() / 100
        btc = aggregated["btc_return_pct"].to_numpy() / 100
        n = len(aggregated)
        values = np.empty(simulations)
        for index in range(simulations):
            sample = rng.integers(0, n, n)
            values[index] = (np.prod(1 + portfolio[sample]) - np.prod(1 + btc[sample])) * 100
        frame = pd.DataFrame([{
            "run_id": self.run_id,
            "simulations": simulations,
            "mean_excess_pct": float(np.mean(values)),
            "median_excess_pct": float(np.median(values)),
            "lower_95_pct": float(np.quantile(values, 0.025)),
            "upper_95_pct": float(np.quantile(values, 0.975)),
            "probability_excess_positive": float(np.mean(values > 0)),
            "probability_excess_above_10pct": float(np.mean(values > 10)),
            "calculated_at_utc": utcnow(),
        }])
        self.upsert("alpha_bootstrap_validation", frame)
        return frame

    def summarize(self, results, periods, labels, bootstrap):
        aggregated = self.aggregate_periods(periods)
        ppy = 365 / int(self.cfg["portfolio"]["rebalance_days"])
        portfolio = aggregated["corrected_return_pct"] / 100
        btc = aggregated["btc_return_pct"] / 100
        equal = aggregated["equal_weight_return_pct"] / 100
        inverse = aggregated["inverse_volatility_return_pct"] / 100
        p = annual_metrics(portfolio, ppy)
        b = annual_metrics(btc, ppy)
        e = annual_metrics(equal, ppy)
        i = annual_metrics(inverse, ppy)
        active = portfolio - btc
        tracking = float(active.std(ddof=1) * math.sqrt(ppy)) if len(active) > 1 else 0.0
        ir = (p[1] - b[1]) / tracking if tracking > 0 else None
        reconciliation = float(aggregated["reconciliation_error_pct"].abs().max())
        probability = float(bootstrap["probability_excess_positive"].iloc[0])
        weak_labels = int((labels["label_status"] != "ACCEPTABLE").sum()) if not labels.empty else 3
        audit_pass = (
            reconciliation <= float(self.cfg["promotion"]["maximum_reconciliation_error_pct"])
            and weak_labels <= int(self.cfg["promotion"]["maximum_weak_label_horizons"])
        )
        evidence_pass = (
            (p[0] - b[0]) * 100 >= float(self.cfg["promotion"]["minimum_excess_return_pct"])
            and ir is not None
            and ir >= float(self.cfg["promotion"]["minimum_information_ratio"])
            and probability >= float(self.cfg["promotion"]["minimum_bootstrap_probability"])
        )
        if not audit_pass:
            audit_status, promotion_status, reason = "FAILED_AUDIT", "REVOKED_PENDING_FIX", "Accounting reconciliation or label validation failed."
        elif not evidence_pass:
            audit_status, promotion_status, reason = "PASSED_ACCOUNTING", "RESEARCH_ONLY", "Accounting passed but alpha evidence was insufficient."
        else:
            audit_status, promotion_status, reason = "PASSED", "AUDIT_VALIDATED_ALPHA_CANDIDATE", "Cleared all frozen walk-forward and audit thresholds."
        selected = results[results["selected_for_fold"]]["candidate_id"].mode()
        frame = pd.DataFrame([{
            "run_id": self.run_id,
            "selected_candidate": selected.iloc[0] if not selected.empty else None,
            "start_date": aggregated["rebalance_date"].min(),
            "end_date": aggregated["next_rebalance_date"].max(),
            "folds": int(results[results["selected_for_fold"]]["fold_number"].nunique()),
            "periods": len(aggregated),
            "total_return_pct": p[0] * 100,
            "annualized_return_pct": p[1] * 100,
            "annualized_volatility_pct": p[2] * 100,
            "sharpe_ratio": p[3],
            "maximum_drawdown_pct": p[4] * 100,
            "btc_total_return_pct": b[0] * 100,
            "equal_weight_total_return_pct": e[0] * 100,
            "inverse_volatility_total_return_pct": i[0] * 100,
            "btc_excess_pct": (p[0] - b[0]) * 100,
            "tracking_error_pct": tracking * 100,
            "information_ratio": ir,
            "benchmark_win_rate_pct": float((portfolio > btc).mean() * 100),
            "average_cash_weight_pct": float(results[results["selected_for_fold"]]["average_cash_weight_pct"].mean()),
            "average_turnover_pct": float(aggregated["turnover_pct"].mean()),
            "transaction_cost_drag_pct": float(aggregated["transaction_cost_pct"].sum()),
            "accounting_reconciliation_error_pct": reconciliation,
            "bootstrap_probability_positive": probability,
            "audit_status": audit_status,
            "promotion_status": promotion_status,
            "promotion_reason": reason,
            "calculated_at_utc": utcnow(),
        }])
        self.upsert("alpha_research_summary", frame)
        return frame

    def run(self):
        self.conn.execute("UPDATE module24_runs SET status='FAILED', completed_at_utc=? WHERE status='RUNNING'", [utcnow()])
        self.conn.execute("INSERT INTO module24_runs VALUES(?,?,NULL,'RUNNING',0,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'6.0.0')", [self.run_id, self.started])
        try:
            price = self.prices()
            factors = self.build_factors(price, self.context(price.index))
            candidates = self.generate_candidates()
            results, periods = self.walk_forward(price, factors, candidates)
            if periods.empty:
                raise RuntimeError("No selected walk-forward periods were produced.")
            labels = self.validate_labels(price, factors)
            aggregated = self.aggregate_periods(periods)
            bootstrap = self.bootstrap(aggregated)
            summary = self.summarize(results, periods, labels, bootstrap)
            record = summary.iloc[0]
            self.conn.execute("""
                UPDATE module24_runs
                SET completed_at_utc=?, status='SUCCESS', factor_rows=?, candidates_tested=?,
                    walk_forward_folds=?, selected_candidate=?, corrected_return_pct=?,
                    btc_return_pct=?, excess_return_pct=?, information_ratio=?,
                    bootstrap_probability_positive=?, audit_status=?, promotion_status=?, notes=?
                WHERE run_id=?
            """, [
                utcnow(), len(factors), len(candidates), int(record["folds"]),
                record["selected_candidate"], float(record["total_return_pct"]),
                float(record["btc_total_return_pct"]), float(record["btc_excess_pct"]),
                None if pd.isna(record["information_ratio"]) else float(record["information_ratio"]),
                float(record["bootstrap_probability_positive"]), record["audit_status"],
                record["promotion_status"], "v6.0 is research-only; Module 13 remains unchanged.",
                self.run_id,
            ])
            self.conn.close()
            return {
                "run_id": self.run_id,
                "status": "SUCCESS",
                "factor_rows": len(factors),
                "candidates_tested": len(candidates),
                "walk_forward_folds": int(record["folds"]),
                "selected_candidate": record["selected_candidate"],
                "corrected_return_pct": float(record["total_return_pct"]),
                "btc_return_pct": float(record["btc_total_return_pct"]),
                "excess_return_pct": float(record["btc_excess_pct"]),
                "information_ratio": None if pd.isna(record["information_ratio"]) else float(record["information_ratio"]),
                "bootstrap_probability_positive": float(record["bootstrap_probability_positive"]),
                "audit_status": record["audit_status"],
                "promotion_status": record["promotion_status"],
            }
        except Exception as exc:
            self.conn.execute(
                "UPDATE module24_runs SET completed_at_utc=?, status='FAILED', notes=? WHERE run_id=?",
                [utcnow(), str(exc)[:1000], self.run_id],
            )
            self.conn.close()
            raise


def run_module24():
    return Module24Runner().run()
