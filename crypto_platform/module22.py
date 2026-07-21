from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from crypto_platform.platform import load_all, connect
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module17 import MODULE17_SCHEMA
from crypto_platform.module18 import MODULE18_SCHEMA
from crypto_platform.module19 import MODULE19_SCHEMA
from crypto_platform.module20 import MODULE20_SCHEMA
from crypto_platform.module21 import MODULE21_SCHEMA

MODULE22_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module22_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    expanded_features INTEGER,
    model_rows INTEGER,
    selected_models INTEGER,
    allocation_rows INTEGER,
    walk_forward_folds INTEGER,
    portfolio_return_pct DOUBLE,
    btc_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    information_ratio DOUBLE,
    promotion_status VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS intelligence_features_daily(
    observation_date DATE PRIMARY KEY,
    btc_momentum_14d_pct DOUBLE,
    btc_momentum_30d_pct DOUBLE,
    btc_momentum_90d_pct DOUBLE,
    btc_distance_sma50_pct DOUBLE,
    btc_distance_sma200_pct DOUBLE,
    btc_realized_vol_30d_pct DOUBLE,
    btc_realized_vol_90d_pct DOUBLE,
    core_equal_weight_return_30d_pct DOUBLE,
    core_equal_weight_return_90d_pct DOUBLE,
    core_dispersion_30d_pct DOUBLE,
    alt_strength_vs_btc_30d_pct DOUBLE,
    alt_strength_vs_btc_90d_pct DOUBLE,
    breadth_change_30d_pct DOUBLE,
    stablecoin_growth_acceleration DOUBLE,
    fear_greed_change_30d DOUBLE,
    vix_change_30d_pct DOUBLE,
    high_yield_change_30d_pct DOUBLE,
    dollar_change_30d_pct DOUBLE,
    liquidity_composite DOUBLE,
    risk_off_composite DOUBLE,
    trend_composite DOUBLE,
    available_feature_count INTEGER,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS intelligence_model_comparison(
    run_id VARCHAR,
    target_key VARCHAR,
    forward_horizon_days INTEGER,
    model_name VARCHAR,
    training_rows INTEGER,
    testing_rows INTEGER,
    accuracy_pct DOUBLE,
    roc_auc DOUBLE,
    brier_score DOUBLE,
    rank_score DOUBLE,
    selected_model BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, target_key, forward_horizon_days, model_name)
);

CREATE TABLE IF NOT EXISTS ensemble_regime_daily(
    run_id VARCHAR,
    observation_date DATE,
    trend_vote DOUBLE,
    macro_vote DOUBLE,
    liquidity_vote DOUBLE,
    volatility_vote DOUBLE,
    breadth_vote DOUBLE,
    bull_probability DOUBLE,
    recovery_probability DOUBLE,
    sideways_probability DOUBLE,
    correction_probability DOUBLE,
    bear_probability DOUBLE,
    dominant_regime VARCHAR,
    confidence DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS six_asset_allocations(
    run_id VARCHAR,
    observation_date DATE,
    asset_id VARCHAR,
    target_weight DOUBLE,
    expected_score DOUBLE,
    volatility_90d_pct DOUBLE,
    momentum_90d_pct DOUBLE,
    relative_strength_90d_pct DOUBLE,
    risk_penalty DOUBLE,
    allocation_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, asset_id)
);

CREATE TABLE IF NOT EXISTS intelligence_walk_forward_folds(
    run_id VARCHAR,
    fold_number INTEGER,
    training_start_date DATE,
    training_end_date DATE,
    testing_start_date DATE,
    testing_end_date DATE,
    selected_positive_model VARCHAR,
    selected_drawdown_model VARCHAR,
    portfolio_return_pct DOUBLE,
    btc_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    maximum_drawdown_pct DOUBLE,
    information_ratio DOUBLE,
    average_cash_weight_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number)
);

CREATE TABLE IF NOT EXISTS intelligence_portfolio_periods(
    run_id VARCHAR,
    rebalance_date DATE,
    next_rebalance_date DATE,
    asset_id VARCHAR,
    target_weight DOUBLE,
    realized_return_pct DOUBLE,
    contribution_pct DOUBLE,
    portfolio_period_return_pct DOUBLE,
    btc_period_return_pct DOUBLE,
    turnover_pct DOUBLE,
    transaction_cost_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, rebalance_date, asset_id)
);

CREATE TABLE IF NOT EXISTS intelligence_portfolio_summary(
    run_id VARCHAR PRIMARY KEY,
    start_date DATE,
    end_date DATE,
    periods INTEGER,
    total_return_pct DOUBLE,
    annualized_return_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    btc_total_return_pct DOUBLE,
    btc_excess_pct DOUBLE,
    tracking_error_pct DOUBLE,
    information_ratio DOUBLE,
    benchmark_win_rate_pct DOUBLE,
    average_cash_weight_pct DOUBLE,
    average_turnover_pct DOUBLE,
    transaction_cost_drag_pct DOUBLE,
    promotion_status VARCHAR,
    promotion_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_intelligence_features AS
SELECT * FROM intelligence_features_daily ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_intelligence_model_comparison AS
SELECT x.* FROM intelligence_model_comparison x
JOIN (
    SELECT run_id FROM module22_runs ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY target_key, forward_horizon_days, rank_score DESC;

CREATE OR REPLACE VIEW latest_ensemble_regime AS
SELECT x.* FROM ensemble_regime_daily x
JOIN (
    SELECT run_id FROM module22_runs ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_six_asset_allocations AS
SELECT x.* FROM six_asset_allocations x
JOIN (
    SELECT run_id FROM module22_runs ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY target_weight DESC;

CREATE OR REPLACE VIEW latest_intelligence_walk_forward AS
SELECT x.* FROM intelligence_walk_forward_folds x
JOIN (
    SELECT run_id FROM module22_runs ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY fold_number;

CREATE OR REPLACE VIEW latest_intelligence_portfolio_periods AS
SELECT x.* FROM intelligence_portfolio_periods x
JOIN (
    SELECT run_id FROM module22_runs ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY rebalance_date, target_weight DESC;

CREATE OR REPLACE VIEW latest_intelligence_portfolio_summary AS
SELECT x.* FROM intelligence_portfolio_summary x
JOIN (
    SELECT run_id FROM module22_runs ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);
"""

CORE_IDS = ["bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche"]

def utcnow():
    return datetime.now(timezone.utc)

def clamp(value, lower, upper):
    return float(max(lower, min(upper, value)))

def safe(value, default=0.0):
    if value is None or pd.isna(value):
        return default
    return float(value)

def annual_metrics(returns: pd.Series, periods_per_year: float):
    curve = (1 + returns).cumprod()
    total = float(curve.iloc[-1] - 1) if len(curve) else 0.0
    years = max(len(returns) / periods_per_year, 1 / periods_per_year)
    annual = (1 + total) ** (1 / years) - 1 if total > -1 else -1.0
    vol = float(returns.std(ddof=1) * math.sqrt(periods_per_year)) if len(returns) > 1 else 0.0
    sharpe = annual / vol if vol > 0 else None
    dd = curve / curve.cummax() - 1 if len(curve) else pd.Series([0.0])
    return total, annual, vol, sharpe, float(dd.min())

class Module22Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE6_SCHEMA, MODULE17_SCHEMA, MODULE18_SCHEMA,
            MODULE19_SCHEMA, MODULE20_SCHEMA, MODULE21_SCHEMA,
            MODULE22_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.cfg = self.settings["module22"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m22_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m22_stage"
        )
        self.conn.unregister("_m22_stage")

    def histories(self):
        market = self.conn.execute("""
            SELECT asset_id, observation_date, price_usd
            FROM canonical_market_daily
            WHERE asset_id IN (
                'bitcoin','ethereum','solana','chainlink','xrp','avalanche'
            ) AND price_usd IS NOT NULL
            ORDER BY observation_date, asset_id
        """).fetchdf()
        if market.empty:
            raise RuntimeError("Canonical market history is empty.")
        market["observation_date"] = pd.to_datetime(market["observation_date"])
        price = market.pivot(
            index="observation_date", columns="asset_id", values="price_usd"
        ).sort_index()
        missing = [asset for asset in CORE_IDS if asset not in price.columns]
        if missing:
            raise RuntimeError(f"Missing core asset histories: {missing}")
        return price

    def base_features(self):
        frame = self.conn.execute(
            "SELECT * FROM crypto_features_daily ORDER BY observation_date"
        ).fetchdf()
        if frame.empty:
            raise RuntimeError("Module 17 feature warehouse is empty.")
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame.set_index("observation_date").sort_index()

    def build_features(self, price, base):
        index = price.index.intersection(base.index)
        price = price.reindex(index).ffill()
        base = base.reindex(index).ffill()
        returns = price.pct_change(fill_method=None)
        btc = price["bitcoin"]
        alt = price[[a for a in CORE_IDS if a != "bitcoin"]]

        output = pd.DataFrame(index=index)
        output["btc_momentum_14d_pct"] = btc.pct_change(14, fill_method=None) * 100
        output["btc_momentum_30d_pct"] = btc.pct_change(30, fill_method=None) * 100
        output["btc_momentum_90d_pct"] = btc.pct_change(90, fill_method=None) * 100
        output["btc_distance_sma50_pct"] = (btc / btc.rolling(50).mean() - 1) * 100
        output["btc_distance_sma200_pct"] = (btc / btc.rolling(200).mean() - 1) * 100
        output["btc_realized_vol_30d_pct"] = (
            returns["bitcoin"].rolling(30).std() * math.sqrt(365) * 100
        )
        output["btc_realized_vol_90d_pct"] = (
            returns["bitcoin"].rolling(90).std() * math.sqrt(365) * 100
        )
        output["core_equal_weight_return_30d_pct"] = (
            price.pct_change(30, fill_method=None).mean(axis=1) * 100
        )
        output["core_equal_weight_return_90d_pct"] = (
            price.pct_change(90, fill_method=None).mean(axis=1) * 100
        )
        output["core_dispersion_30d_pct"] = (
            price.pct_change(30, fill_method=None).std(axis=1) * 100
        )
        output["alt_strength_vs_btc_30d_pct"] = (
            alt.pct_change(30, fill_method=None).mean(axis=1)
            - btc.pct_change(30, fill_method=None)
        ) * 100
        output["alt_strength_vs_btc_90d_pct"] = (
            alt.pct_change(90, fill_method=None).mean(axis=1)
            - btc.pct_change(90, fill_method=None)
        ) * 100
        breadth = base.get(
            "core_breadth_above_sma50_pct",
            pd.Series(index=index, dtype=float),
        )
        output["breadth_change_30d_pct"] = breadth.diff(30)
        stable_growth = base.get(
            "stablecoin_growth_30d_pct",
            pd.Series(index=index, dtype=float),
        )
        output["stablecoin_growth_acceleration"] = stable_growth.diff(30)
        output["fear_greed_change_30d"] = base.get(
            "fear_greed_index", pd.Series(index=index, dtype=float)
        ).diff(30)
        output["vix_change_30d_pct"] = base.get(
            "vix", pd.Series(index=index, dtype=float)
        ).pct_change(30, fill_method=None) * 100
        output["high_yield_change_30d_pct"] = base.get(
            "high_yield_spread", pd.Series(index=index, dtype=float)
        ).pct_change(30, fill_method=None) * 100
        output["dollar_change_30d_pct"] = base.get(
            "dollar_index", pd.Series(index=index, dtype=float)
        ).pct_change(30, fill_method=None) * 100

        def z(series, window=365, minimum=120):
            mean = series.rolling(window, min_periods=minimum).mean()
            std = series.rolling(window, min_periods=minimum).std().replace(0, np.nan)
            return ((series - mean) / std).clip(-3, 3)

        output["liquidity_composite"] = pd.concat([
            z(stable_growth),
            -z(base.get("high_yield_spread", pd.Series(index=index, dtype=float))),
            -z(base.get("dollar_index", pd.Series(index=index, dtype=float))),
        ], axis=1).mean(axis=1)
        output["risk_off_composite"] = pd.concat([
            z(base.get("vix", pd.Series(index=index, dtype=float))),
            z(base.get("high_yield_spread", pd.Series(index=index, dtype=float))),
            -z(output["btc_distance_sma200_pct"]),
        ], axis=1).mean(axis=1)
        output["trend_composite"] = pd.concat([
            z(output["btc_momentum_30d_pct"]),
            z(output["btc_momentum_90d_pct"]),
            z(output["btc_distance_sma200_pct"]),
            z(breadth),
        ], axis=1).mean(axis=1)

        output["available_feature_count"] = output.notna().sum(axis=1)
        output["calculated_at_utc"] = utcnow()
        result = output.reset_index().rename(columns={"index": "observation_date"})
        result["observation_date"] = result["observation_date"].dt.date
        self.upsert("intelligence_features_daily", result)
        return output

    def modeling_frame(self, expanded, base):
        governed = self.conn.execute("""
            SELECT feature_key
            FROM latest_feature_evidence_aging
            WHERE aged_registry_status IN (
                'PROMOTED_SHADOW','WATCHLIST'
            )
            ORDER BY aged_promotion_score DESC
        """).fetchdf()
        governed_features = (
            governed["feature_key"].tolist()
            if not governed.empty else []
        )
        combined = expanded.copy()
        for feature in governed_features:
            if feature in base.columns and feature not in combined.columns:
                combined[feature] = base[feature]
        maximum = int(self.cfg["models"]["maximum_features"])
        coverage = combined.notna().mean().sort_values(ascending=False)
        selected = [
            feature for feature in coverage.index
            if feature != "calculated_at_utc"
            and coverage[feature] >= float(self.cfg["models"]["minimum_coverage"])
        ][:maximum]
        return combined[selected], selected

    def model_factories(self):
        seed = int(self.cfg["models"]["random_state"])
        return {
            "LOGISTIC_REGRESSION": lambda: Pipeline([
                ("scale", StandardScaler()),
                ("model", LogisticRegression(
                    max_iter=1000, class_weight="balanced", random_state=seed
                )),
            ]),
            "RANDOM_FOREST": lambda: RandomForestClassifier(
                n_estimators=250, min_samples_leaf=15,
                class_weight="balanced", random_state=seed, n_jobs=-1,
            ),
            "EXTRA_TREES": lambda: ExtraTreesClassifier(
                n_estimators=250, min_samples_leaf=12,
                class_weight="balanced", random_state=seed, n_jobs=-1,
            ),
            "GRADIENT_BOOSTING": lambda: GradientBoostingClassifier(
                n_estimators=150, learning_rate=0.04,
                max_depth=2, min_samples_leaf=15, random_state=seed,
            ),
            "HIST_GRADIENT_BOOSTING": lambda: HistGradientBoostingClassifier(
                max_iter=200, learning_rate=0.04, max_leaf_nodes=15,
                min_samples_leaf=20, l2_regularization=1.0,
                random_state=seed,
            ),
        }

    def compare_models(self, price, features):
        rows = []
        selected = {}
        btc = price["bitcoin"].reindex(features.index)
        for horizon in self.cfg["horizons_days"]:
            future_return = btc.shift(-int(horizon)) / btc - 1
            forward_prices = pd.concat(
                [btc.shift(-offset) for offset in range(1, int(horizon) + 1)],
                axis=1,
            )
            future_drawdown = forward_prices.min(axis=1) / btc - 1
            full_future_window = forward_prices.notna().all(axis=1)
            positive_target = (future_return > 0).astype(float).where(
                future_return.notna(), float("nan")
            )
            drawdown_target = (future_drawdown <= -0.20).astype(float).where(
                full_future_window, float("nan")
            )
            targets = {
                "POSITIVE_RETURN": positive_target,
                "DRAWDOWN_20": drawdown_target,
            }
            for target_key, target in targets.items():
                sample = features.copy()
                sample["_target"] = target
                sample = sample.dropna()
                if len(sample) < int(self.cfg["models"]["minimum_total_rows"]):
                    continue
                split = int(len(sample) * float(self.cfg["models"]["training_fraction"]))
                train, test = sample.iloc[:split], sample.iloc[split:]
                if (
                    len(train) < int(self.cfg["models"]["minimum_training_rows"])
                    or len(test) < int(self.cfg["models"]["minimum_testing_rows"])
                    or train["_target"].nunique() < 2
                    or test["_target"].nunique() < 2
                ):
                    continue
                evaluations = []
                for model_name, factory in self.model_factories().items():
                    model = factory()
                    model.fit(train.drop(columns="_target"), train["_target"].astype(int))
                    probability = model.predict_proba(test.drop(columns="_target"))[:, 1]
                    prediction = (probability >= 0.5).astype(int)
                    accuracy = accuracy_score(test["_target"], prediction) * 100
                    try:
                        auc = roc_auc_score(test["_target"], probability)
                    except ValueError:
                        auc = 0.5
                    brier = brier_score_loss(test["_target"], probability)
                    rank_score = auc * 55 + (1 - brier) * 30 + accuracy / 100 * 15
                    evaluations.append((rank_score, model_name, model))
                    rows.append({
                        "run_id": self.run_id,
                        "target_key": target_key,
                        "forward_horizon_days": int(horizon),
                        "model_name": model_name,
                        "training_rows": len(train),
                        "testing_rows": len(test),
                        "accuracy_pct": float(accuracy),
                        "roc_auc": float(auc),
                        "brier_score": float(brier),
                        "rank_score": float(rank_score),
                        "selected_model": False,
                        "calculated_at_utc": utcnow(),
                    })
                best = max(evaluations, key=lambda item: item[0])
                selected[(target_key, int(horizon))] = best[1]
                for row in rows:
                    if (
                        row["target_key"] == target_key
                        and row["forward_horizon_days"] == int(horizon)
                        and row["model_name"] == best[1]
                    ):
                        row["selected_model"] = True
        result = pd.DataFrame(rows)
        self.upsert("intelligence_model_comparison", result)
        return result, selected

    def ensemble_regime(self, expanded, base):
        rows = []
        for date in expanded.index:
            trend = safe(expanded.at[date, "trend_composite"])
            macro = -safe(base.at[date, "macro_liquidity_score"] - 50) / 25 if (
                date in base.index and pd.notna(base.at[date, "macro_liquidity_score"])
            ) else 0.0
            liquidity = safe(expanded.at[date, "liquidity_composite"])
            volatility = -safe(expanded.at[date, "risk_off_composite"])
            breadth = safe(expanded.at[date, "breadth_change_30d_pct"]) / 20
            consensus = np.mean([trend, macro, liquidity, volatility, breadth])
            dispersion = np.std([trend, macro, liquidity, volatility, breadth])
            bull = math.exp(clamp(consensus, -3, 3))
            bear = math.exp(clamp(-consensus, -3, 3))
            recovery = math.exp(clamp(0.7 * trend + 0.5 * liquidity - 0.3 * volatility, -3, 3))
            correction = math.exp(clamp(-0.6 * trend + 0.7 * (-volatility), -3, 3))
            sideways = math.exp(clamp(-abs(consensus) - 0.3 * dispersion, -3, 3))
            total = bull + bear + recovery + correction + sideways
            probs = {
                "BULL": bull / total,
                "RECOVERY": recovery / total,
                "SIDEWAYS": sideways / total,
                "CORRECTION": correction / total,
                "BEAR": bear / total,
            }
            dominant = max(probs, key=probs.get)
            rows.append({
                "run_id": self.run_id,
                "observation_date": date.date(),
                "trend_vote": trend,
                "macro_vote": macro,
                "liquidity_vote": liquidity,
                "volatility_vote": volatility,
                "breadth_vote": breadth,
                "bull_probability": probs["BULL"],
                "recovery_probability": probs["RECOVERY"],
                "sideways_probability": probs["SIDEWAYS"],
                "correction_probability": probs["CORRECTION"],
                "bear_probability": probs["BEAR"],
                "dominant_regime": dominant,
                "confidence": probs[dominant],
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert("ensemble_regime_daily", result)
        return result

    def asset_scores(self, price, date, regime):
        rows = []
        btc_returns = price["bitcoin"].pct_change(fill_method=None)
        for asset in CORE_IDS:
            series = price[asset].loc[:date].dropna()
            if len(series) < 200:
                continue
            ret = series.pct_change(fill_method=None).dropna()
            momentum90 = (series.iloc[-1] / series.iloc[-91] - 1) * 100 if len(series) > 91 else 0
            momentum30 = (series.iloc[-1] / series.iloc[-31] - 1) * 100 if len(series) > 31 else 0
            vol90 = ret.tail(90).std() * math.sqrt(365) * 100
            aligned = pd.concat(
                [ret.tail(180), btc_returns.loc[:date].tail(180)], axis=1
            ).dropna()
            relative = momentum90 - (
                price["bitcoin"].loc[:date].iloc[-1]
                / price["bitcoin"].loc[:date].iloc[-91] - 1
            ) * 100 if len(price["bitcoin"].loc[:date]) > 91 else momentum90
            correlation = aligned.corr().iloc[0, 1] if len(aligned) > 30 else 1.0
            risk_penalty = clamp(vol90 / 120, 0, 1)
            regime_multiplier = (
                1.15 if regime in {"BULL", "RECOVERY"} and asset != "bitcoin"
                else 1.15 if regime in {"BEAR", "CORRECTION"} and asset == "bitcoin"
                else 1.0
            )
            score = (
                50
                + momentum30 * 0.20
                + momentum90 * 0.16
                + relative * 0.12
                - risk_penalty * 20
                + (1 - abs(correlation)) * 6
            ) * regime_multiplier
            rows.append({
                "asset_id": asset,
                "expected_score": float(score),
                "volatility_90d_pct": float(vol90),
                "momentum_90d_pct": float(momentum90),
                "relative_strength_90d_pct": float(relative),
                "risk_penalty": float(risk_penalty),
            })
        return pd.DataFrame(rows)

    def allocation(self, price, date, regime, risk_off):
        scores = self.asset_scores(price, date, regime)
        if scores.empty:
            return pd.DataFrame()
        cash = clamp(
            float(self.cfg["allocation"]["base_cash_weight"])
            + max(0, risk_off) * float(self.cfg["allocation"]["risk_off_cash_slope"]),
            float(self.cfg["allocation"]["minimum_cash_weight"]),
            float(self.cfg["allocation"]["maximum_cash_weight"]),
        )
        raw = np.maximum(scores["expected_score"].to_numpy() - 25, 1)
        raw = raw * (1 - scores["risk_penalty"].to_numpy() * 0.35)
        weights = raw / raw.sum() * (1 - cash)
        maximum = float(self.cfg["allocation"]["maximum_asset_weight"])
        for _ in range(10):
            excess = np.maximum(weights - maximum, 0).sum()
            weights = np.minimum(weights, maximum)
            uncapped = weights < maximum - 1e-9
            if excess <= 1e-9 or not uncapped.any():
                break
            weights[uncapped] += excess * weights[uncapped] / weights[uncapped].sum()
        scores["target_weight"] = weights
        scores["allocation_reason"] = (
            "Regime-aware score using momentum, relative strength, "
            "volatility, and diversification."
        )
        cash_row = pd.DataFrame([{
            "asset_id": "CASH",
            "expected_score": 50.0,
            "volatility_90d_pct": 0.0,
            "momentum_90d_pct": 0.0,
            "relative_strength_90d_pct": 0.0,
            "risk_penalty": 0.0,
            "target_weight": cash,
            "allocation_reason": "Dynamic reserve from ensemble risk-off signal.",
        }])
        return pd.concat([scores, cash_row], ignore_index=True)

    def walk_forward(self, price, expanded, regimes):
        train_months = int(self.cfg["walk_forward"]["training_months"])
        test_months = int(self.cfg["walk_forward"]["testing_months"])
        step_months = int(self.cfg["walk_forward"]["step_months"])
        start = max(price.index.min(), expanded.index.min()) + pd.DateOffset(months=train_months)
        last = min(price.index.max(), expanded.index.max())
        rows, period_rows = [], []
        fold = 1
        test_start = pd.Timestamp(start)
        previous_weights = {asset: 0.0 for asset in CORE_IDS + ["CASH"]}
        previous_weights["CASH"] = 1.0
        cost_rate = float(self.cfg["portfolio"]["transaction_cost_bps"]) / 10000
        while test_start + pd.DateOffset(months=test_months) <= last:
            train_start = test_start - pd.DateOffset(months=train_months)
            test_end = test_start + pd.DateOffset(months=test_months)
            period_dates = list(
                price.index[
                    (price.index >= test_start)
                    & (price.index < test_end)
                ][:: int(self.cfg["portfolio"]["rebalance_days"])]
            )
            if len(period_dates) < 2:
                test_start += pd.DateOffset(months=step_months)
                continue
            fold_returns, btc_returns, cash_weights = [], [], []
            fold_period_rows = []
            for i in range(len(period_dates) - 1):
                date, next_date = period_dates[i], period_dates[i + 1]
                regime_rows = regimes[
                    regimes["observation_date"] <= date.date()
                ]
                regime = (
                    regime_rows.iloc[-1]["dominant_regime"]
                    if not regime_rows.empty else "SIDEWAYS"
                )
                risk_off = safe(expanded.loc[date, "risk_off_composite"])
                allocation = self.allocation(price, date, regime, risk_off)
                weights = dict(zip(allocation["asset_id"], allocation["target_weight"]))
                turnover = 0.5 * sum(
                    abs(weights.get(asset, 0) - previous_weights.get(asset, 0))
                    for asset in set(weights) | set(previous_weights)
                )
                cost = turnover * cost_rate
                portfolio_return = -cost
                btc_return = price.at[next_date, "bitcoin"] / price.at[date, "bitcoin"] - 1
                for _, item in allocation.iterrows():
                    asset = item["asset_id"]
                    realized = (
                        0.0 if asset == "CASH"
                        else price.at[next_date, asset] / price.at[date, asset] - 1
                    )
                    contribution = float(item["target_weight"]) * realized
                    portfolio_return += contribution
                    fold_period_rows.append({
                        "run_id": self.run_id,
                        "rebalance_date": date.date(),
                        "next_rebalance_date": next_date.date(),
                        "asset_id": asset,
                        "target_weight": float(item["target_weight"]),
                        "realized_return_pct": realized * 100,
                        "contribution_pct": contribution * 100,
                        "portfolio_period_return_pct": None,
                        "btc_period_return_pct": btc_return * 100,
                        "turnover_pct": turnover * 100,
                        "transaction_cost_pct": cost * 100,
                        "calculated_at_utc": utcnow(),
                    })
                for period_row in fold_period_rows:
                    if (
                        period_row["rebalance_date"] == date.date()
                        and period_row["next_rebalance_date"] == next_date.date()
                    ):
                        period_row["portfolio_period_return_pct"] = (
                            portfolio_return * 100
                        )
                fold_returns.append(portfolio_return)
                btc_returns.append(btc_return)
                cash_weights.append(weights.get("CASH", 0))
                previous_weights = weights
            if not fold_returns:
                test_start += pd.DateOffset(months=step_months)
                continue
            pr = pd.Series(fold_returns)
            br = pd.Series(btc_returns)
            active = pr - br
            total = float((1 + pr).prod() - 1)
            btc_total = float((1 + br).prod() - 1)
            dd = (1 + pr).cumprod()
            max_dd = float((dd / dd.cummax() - 1).min())
            te = float(active.std(ddof=1) * math.sqrt(365 / int(self.cfg["portfolio"]["rebalance_days"]))) if len(active) > 1 else 0
            ir = float((pr.mean() - br.mean()) / active.std(ddof=1) * math.sqrt(365 / int(self.cfg["portfolio"]["rebalance_days"]))) if len(active) > 1 and active.std(ddof=1) > 0 else None
            rows.append({
                "run_id": self.run_id,
                "fold_number": fold,
                "training_start_date": train_start.date(),
                "training_end_date": test_start.date(),
                "testing_start_date": test_start.date(),
                "testing_end_date": test_end.date(),
                "selected_positive_model": "BEST_FROM_MODEL_COMPARISON",
                "selected_drawdown_model": "BEST_FROM_MODEL_COMPARISON",
                "portfolio_return_pct": total * 100,
                "btc_return_pct": btc_total * 100,
                "excess_return_pct": (total - btc_total) * 100,
                "maximum_drawdown_pct": max_dd * 100,
                "information_ratio": ir,
                "average_cash_weight_pct": float(np.mean(cash_weights) * 100),
                "calculated_at_utc": utcnow(),
            })
            period_rows.extend(fold_period_rows)
            fold += 1
            test_start += pd.DateOffset(months=step_months)
        folds = pd.DataFrame(rows)
        periods = pd.DataFrame(period_rows)
        self.upsert("intelligence_walk_forward_folds", folds)
        self.upsert("intelligence_portfolio_periods", periods)
        return folds, periods

    def summarize(self, periods):
        if periods.empty:
            return pd.DataFrame()
        grouped = periods.groupby(
            ["rebalance_date", "next_rebalance_date"], as_index=False
        ).agg(
            contribution_sum_pct=("contribution_pct", "sum"),
            btc_return_pct=("btc_period_return_pct", "first"),
            turnover_pct=("turnover_pct", "first"),
            transaction_cost_pct=("transaction_cost_pct", "first"),
        )
        grouped["portfolio_return_pct"] = (
            grouped["contribution_sum_pct"]
            - grouped["transaction_cost_pct"]
        )
        cash = periods[periods["asset_id"] == "CASH"][
            ["rebalance_date", "target_weight"]
        ].rename(columns={"target_weight": "cash_actual"})
        grouped = grouped.merge(cash, on="rebalance_date", how="left")
        grouped["cash_weight"] = grouped["cash_actual"].fillna(0.0)
        pr = grouped["portfolio_return_pct"] / 100
        br = grouped["btc_return_pct"] / 100
        total, annual, vol, sharpe, max_dd = annual_metrics(
            pr, 365 / int(self.cfg["portfolio"]["rebalance_days"])
        )
        btc_total, _, _, _, _ = annual_metrics(
            br, 365 / int(self.cfg["portfolio"]["rebalance_days"])
        )
        active = pr - br
        tracking_error = float(
            active.std(ddof=1)
            * math.sqrt(365 / int(self.cfg["portfolio"]["rebalance_days"]))
        ) if len(active) > 1 else 0.0
        ir = (
            float(
                (annual - ((1 + btc_total) ** (
                    1 / max(len(br) / (365 / int(self.cfg["portfolio"]["rebalance_days"])), 1e-6)
                ) - 1)) / tracking_error
            )
            if tracking_error > 0 else None
        )
        excess = (total - btc_total) * 100
        promoted = (
            excess >= float(self.cfg["promotion"]["minimum_excess_return_pct"])
            and ir is not None
            and ir >= float(self.cfg["promotion"]["minimum_information_ratio"])
            and max_dd * 100 >= float(self.cfg["promotion"]["maximum_drawdown_floor_pct"])
        )
        summary = pd.DataFrame([{
            "run_id": self.run_id,
            "start_date": grouped["rebalance_date"].min(),
            "end_date": grouped["next_rebalance_date"].max(),
            "periods": len(grouped),
            "total_return_pct": total * 100,
            "annualized_return_pct": annual * 100,
            "annualized_volatility_pct": vol * 100,
            "sharpe_ratio": sharpe,
            "maximum_drawdown_pct": max_dd * 100,
            "btc_total_return_pct": btc_total * 100,
            "btc_excess_pct": excess,
            "tracking_error_pct": tracking_error * 100,
            "information_ratio": ir,
            "benchmark_win_rate_pct": float((pr > br).mean() * 100),
            "average_cash_weight_pct": float(grouped["cash_actual"].mean() * 100),
            "average_turnover_pct": float(grouped["turnover_pct"].mean()),
            "transaction_cost_drag_pct": float(grouped["transaction_cost_pct"].sum()),
            "promotion_status": "PROMOTION_CANDIDATE" if promoted else "RESEARCH_ONLY",
            "promotion_reason": (
                "Cleared configured v5.1 intelligence thresholds."
                if promoted else "Did not clear all v5.1 intelligence thresholds."
            ),
            "calculated_at_utc": utcnow(),
        }])
        self.upsert("intelligence_portfolio_summary", summary)
        return summary

    def current_allocation(self, price, expanded, regimes):
        date = price.index[-1]
        regime = regimes.iloc[-1]["dominant_regime"]
        risk_off = safe(expanded.iloc[-1]["risk_off_composite"])
        allocation = self.allocation(price, date, regime, risk_off)
        allocation.insert(0, "observation_date", date.date())
        allocation.insert(0, "run_id", self.run_id)
        allocation["calculated_at_utc"] = utcnow()
        self.upsert("six_asset_allocations", allocation)
        return allocation

    def run(self):
        self.conn.execute("""
            UPDATE module22_runs
            SET status='FAILED', completed_at_utc=?,
                notes=COALESCE(notes,'') || '; interrupted prior run'
            WHERE status='RUNNING'
        """, [utcnow()])
        self.conn.execute("""
            INSERT INTO module22_runs VALUES(
                ?, ?, NULL, 'RUNNING',
                0, 0, 0, 0, 0,
                NULL, NULL, NULL, NULL,
                NULL, NULL, '5.1.0'
            )
        """, [self.run_id, self.started])
        try:
            price = self.histories()
            base = self.base_features()
            expanded = self.build_features(price, base)
            model_frame, model_features = self.modeling_frame(expanded, base)
            comparison, selected = self.compare_models(price, model_frame)
            regimes = self.ensemble_regime(expanded, base)
            current = self.current_allocation(price, expanded, regimes)
            folds, periods = self.walk_forward(price, expanded, regimes)
            summary = self.summarize(periods)
            if summary.empty:
                portfolio_return = btc_return = excess = ir = None
                promotion = "RESEARCH_ONLY"
            else:
                record = summary.iloc[0]
                portfolio_return = float(record["total_return_pct"])
                btc_return = float(record["btc_total_return_pct"])
                excess = float(record["btc_excess_pct"])
                ir = safe(record["information_ratio"], None)
                promotion = record["promotion_status"]
            notes = (
                "v5.1 intelligence expansion remains shadow-only. "
                "Module 13 production recommendations are unchanged."
            )
            self.conn.execute("""
                UPDATE module22_runs
                SET completed_at_utc=?, status='SUCCESS',
                    expanded_features=?, model_rows=?,
                    selected_models=?, allocation_rows=?,
                    walk_forward_folds=?, portfolio_return_pct=?,
                    btc_return_pct=?, excess_return_pct=?,
                    information_ratio=?, promotion_status=?, notes=?
                WHERE run_id=?
            """, [
                utcnow(), len(model_features), len(comparison),
                int(comparison["selected_model"].sum()) if not comparison.empty else 0,
                len(current), len(folds), portfolio_return, btc_return,
                excess, ir, promotion, notes, self.run_id,
            ])
            self.conn.close()
            return {
                "run_id": self.run_id,
                "status": "SUCCESS",
                "expanded_features": len(model_features),
                "model_rows": len(comparison),
                "selected_models": (
                    int(comparison["selected_model"].sum())
                    if not comparison.empty else 0
                ),
                "allocation_rows": len(current),
                "walk_forward_folds": len(folds),
                "portfolio_return_pct": portfolio_return,
                "btc_return_pct": btc_return,
                "excess_return_pct": excess,
                "information_ratio": ir,
                "promotion_status": promotion,
            }
        except Exception as exc:
            self.conn.execute("""
                UPDATE module22_runs
                SET completed_at_utc=?, status='FAILED', notes=?
                WHERE run_id=?
            """, [utcnow(), str(exc)[:1000], self.run_id])
            self.conn.close()
            raise

def run_module22():
    return Module22Runner().run()
