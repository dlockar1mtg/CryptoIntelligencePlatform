from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    roc_auc_score,
)

from crypto_platform.platform import load_all, connect
from crypto_platform.module17 import MODULE17_SCHEMA
from crypto_platform.module18 import MODULE18_SCHEMA
from crypto_platform.module19 import MODULE19_SCHEMA
from crypto_platform.module20 import MODULE20_SCHEMA

MODULE21_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module21_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    governed_features INTEGER,
    probability_models INTEGER,
    decision_rows INTEGER,
    shadow_periods INTEGER,
    current_stance VARCHAR,
    current_btc_weight DOUBLE,
    shadow_return_pct DOUBLE,
    btc_return_pct DOUBLE,
    shadow_excess_pct DOUBLE,
    promoted BOOLEAN,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS decision_model_quality(
    run_id VARCHAR,
    target_key VARCHAR,
    forward_horizon_days INTEGER,
    feature_count INTEGER,
    training_rows INTEGER,
    testing_rows INTEGER,
    accuracy_pct DOUBLE,
    roc_auc DOUBLE,
    brier_score DOUBLE,
    quality_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, target_key, forward_horizon_days)
);

CREATE TABLE IF NOT EXISTS market_regime_probabilities(
    run_id VARCHAR,
    observation_date DATE,
    bull_probability DOUBLE,
    recovery_probability DOUBLE,
    sideways_probability DOUBLE,
    correction_probability DOUBLE,
    bear_probability DOUBLE,
    dominant_regime VARCHAR,
    regime_confidence DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS investment_probabilities(
    run_id VARCHAR,
    observation_date DATE,
    forward_horizon_days INTEGER,
    positive_return_probability DOUBLE,
    drawdown_20_probability DOUBLE,
    liquidity_expansion_probability DOUBLE,
    probability_confidence DOUBLE,
    model_quality_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, forward_horizon_days)
);

CREATE TABLE IF NOT EXISTS investment_risk_snapshot(
    run_id VARCHAR,
    observation_date DATE,
    volatility_30d_pct DOUBLE,
    volatility_90d_pct DOUBLE,
    historical_var_95_1d_pct DOUBLE,
    historical_cvar_95_1d_pct DOUBLE,
    maximum_drawdown_365d_pct DOUBLE,
    expected_30d_loss_pct DOUBLE,
    risk_score DOUBLE,
    risk_level VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS investment_decisions(
    run_id VARCHAR,
    observation_date DATE,
    stance VARCHAR,
    confidence DOUBLE,
    target_btc_weight DOUBLE,
    target_cash_weight DOUBLE,
    action_score DOUBLE,
    dominant_regime VARCHAR,
    positive_return_probability_90d DOUBLE,
    drawdown_20_probability_90d DOUBLE,
    risk_score DOUBLE,
    governed_feature_count INTEGER,
    production_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS investment_decision_rationale(
    run_id VARCHAR,
    observation_date DATE,
    rationale_rank INTEGER,
    rationale_type VARCHAR,
    feature_key VARCHAR,
    feature_value DOUBLE,
    standardized_value DOUBLE,
    inferred_direction VARCHAR,
    contribution DOUBLE,
    rationale_text VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, rationale_rank)
);

CREATE TABLE IF NOT EXISTS decision_shadow_periods(
    run_id VARCHAR,
    rebalance_date DATE,
    next_rebalance_date DATE,
    stance VARCHAR,
    btc_weight DOUBLE,
    cash_weight DOUBLE,
    action_score DOUBLE,
    positive_return_probability DOUBLE,
    drawdown_probability DOUBLE,
    portfolio_return_pct DOUBLE,
    btc_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    turnover_pct DOUBLE,
    transaction_cost_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, rebalance_date)
);

CREATE TABLE IF NOT EXISTS decision_shadow_summary(
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

CREATE OR REPLACE VIEW latest_decision_model_quality AS
SELECT x.* FROM decision_model_quality x
JOIN (
    SELECT run_id FROM module21_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY forward_horizon_days, target_key;

CREATE OR REPLACE VIEW latest_market_regime_probabilities AS
SELECT x.* FROM market_regime_probabilities x
JOIN (
    SELECT run_id FROM module21_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_investment_probabilities AS
SELECT x.* FROM investment_probabilities x
JOIN (
    SELECT run_id FROM module21_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY observation_date, forward_horizon_days;

CREATE OR REPLACE VIEW latest_investment_risk_snapshot AS
SELECT x.* FROM investment_risk_snapshot x
JOIN (
    SELECT run_id FROM module21_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_investment_decision AS
SELECT x.* FROM investment_decisions x
JOIN (
    SELECT run_id FROM module21_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_investment_decision_rationale AS
SELECT x.* FROM investment_decision_rationale x
JOIN (
    SELECT run_id FROM module21_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY observation_date, rationale_rank;

CREATE OR REPLACE VIEW latest_decision_shadow_periods AS
SELECT x.* FROM decision_shadow_periods x
JOIN (
    SELECT run_id FROM module21_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY rebalance_date;

CREATE OR REPLACE VIEW latest_decision_shadow_summary AS
SELECT x.* FROM decision_shadow_summary x
JOIN (
    SELECT run_id FROM module21_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);
"""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def clamp(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))

def sigmoid(value: float) -> float:
    return float(1.0 / (1.0 + math.exp(-clamp(value, -30, 30))))

def softmax(values: dict[str, float]) -> dict[str, float]:
    maximum = max(values.values())
    exp = {key: math.exp(value - maximum) for key, value in values.items()}
    total = sum(exp.values())
    return {key: value / total for key, value in exp.items()}

def safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None or pd.isna(value):
        return default
    return float(value)

def annual_metrics(returns: pd.Series, periods_per_year: float):
    if returns.empty:
        return 0.0, 0.0, 0.0, None, 0.0
    curve = (1 + returns).cumprod()
    total = float(curve.iloc[-1] - 1)
    years = max(len(returns) / periods_per_year, 1 / periods_per_year)
    annual = (1 + total) ** (1 / years) - 1 if total > -1 else -1.0
    volatility = (
        float(returns.std(ddof=1) * math.sqrt(periods_per_year))
        if len(returns) > 1 else 0.0
    )
    sharpe = annual / volatility if volatility > 0 else None
    drawdown = curve / curve.cummax() - 1
    return total, annual, volatility, sharpe, float(drawdown.min())

class Module21Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE17_SCHEMA)
        self.conn.execute(MODULE18_SCHEMA)
        self.conn.execute(MODULE19_SCHEMA)
        self.conn.execute(MODULE20_SCHEMA)
        self.conn.execute(MODULE21_SCHEMA)
        self.cfg = self.settings["module21"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m21_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m21_stage"
        )
        self.conn.unregister("_m21_stage")

    def frame(self) -> pd.DataFrame:
        frame = self.conn.execute(
            "SELECT * FROM crypto_features_daily ORDER BY observation_date"
        ).fetchdf()
        if frame.empty:
            raise RuntimeError(
                "Feature warehouse is empty. Run Modules 17-20 first."
            )
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame

    def governed_features(self, frame: pd.DataFrame) -> tuple[list[str], dict[str, float], dict[str, str]]:
        registry = self.conn.execute(
            """
            SELECT feature_key, promotion_score, registry_status
            FROM latest_feature_registry
            WHERE production_eligible=TRUE
            """
        ).fetchdf()
        aging = self.conn.execute(
            """
            SELECT feature_key, aged_registry_status,
                   aged_promotion_score, recent_mean_spearman
            FROM latest_feature_evidence_aging
            """
        ).fetchdf()
        if not aging.empty:
            registry = registry.merge(aging, on="feature_key", how="left")
        else:
            registry["aged_registry_status"] = registry["registry_status"]
            registry["aged_promotion_score"] = registry["promotion_score"]
            registry["recent_mean_spearman"] = np.nan

        permitted_statuses = set(self.cfg["governance"]["permitted_statuses"])
        registry["effective_status"] = registry[
            "aged_registry_status"
        ].fillna(registry["registry_status"])
        selected = registry[
            registry["effective_status"].isin(permitted_statuses)
        ].copy()
        selected = selected[
            selected["feature_key"].isin(frame.columns)
        ]
        features = selected["feature_key"].tolist()
        scores = dict(
            zip(
                selected["feature_key"],
                selected["aged_promotion_score"].fillna(
                    selected["promotion_score"]
                ),
            )
        )
        directions = {}
        for _, row in selected.iterrows():
            recent = safe_float(row.get("recent_mean_spearman"), 0.0) or 0.0
            directions[row["feature_key"]] = (
                "POSITIVE" if recent >= 0 else "NEGATIVE"
            )
        return features, scores, directions

    def rolling_zscore(self, series: pd.Series) -> pd.Series:
        window = int(self.cfg["signals"]["zscore_window_days"])
        minimum = int(self.cfg["signals"]["minimum_zscore_history"])
        mean = series.rolling(window, min_periods=minimum).mean()
        std = series.rolling(window, min_periods=minimum).std().replace(0, np.nan)
        return ((series - mean) / std).clip(-3, 3)

    def regime_probabilities(self, frame: pd.DataFrame) -> pd.DataFrame:
        btc = frame["btc_price_usd"].astype(float)
        sma200 = btc.rolling(200, min_periods=120).mean()
        momentum30 = btc.pct_change(30, fill_method=None)
        momentum90 = btc.pct_change(90, fill_method=None)
        breadth = frame.get(
            "core_breadth_above_sma50_pct",
            pd.Series(index=frame.index, dtype=float),
        ).fillna(50) / 100
        vix_z = self.rolling_zscore(
            frame.get("vix", pd.Series(index=frame.index, dtype=float))
        ).fillna(0)
        hy_z = self.rolling_zscore(
            frame.get(
                "high_yield_spread",
                pd.Series(index=frame.index, dtype=float),
            )
        ).fillna(0)
        stable_growth = frame.get(
            "stablecoin_growth_30d_pct",
            pd.Series(index=frame.index, dtype=float),
        ).fillna(0)

        rows = []
        for index, date in enumerate(frame["observation_date"]):
            if pd.isna(sma200.iloc[index]):
                continue
            price_gap = (btc.iloc[index] / sma200.iloc[index] - 1)
            m30 = safe_float(momentum30.iloc[index], 0.0) or 0.0
            m90 = safe_float(momentum90.iloc[index], 0.0) or 0.0
            b = safe_float(breadth.iloc[index], 0.5) or 0.5
            vz = safe_float(vix_z.iloc[index], 0.0) or 0.0
            hz = safe_float(hy_z.iloc[index], 0.0) or 0.0
            sg = safe_float(stable_growth.iloc[index], 0.0) or 0.0

            scores = {
                "BULL": 3.0 * price_gap + 1.8 * m90 + 0.8 * (b - 0.5) - 0.25 * vz - 0.35 * hz,
                "RECOVERY": -1.2 * abs(price_gap) + 1.5 * max(m30, 0) + 0.8 * max(m90, 0) + 0.3 * sg,
                "SIDEWAYS": -2.0 * abs(price_gap) - 1.5 * abs(m30) - 0.6 * abs(m90),
                "CORRECTION": 1.5 * max(price_gap, 0) + 1.7 * max(-m30, 0) + 0.45 * vz + 0.25 * hz,
                "BEAR": -3.0 * price_gap + 1.8 * max(-m90, 0) + 0.7 * (0.5 - b) + 0.35 * vz + 0.45 * hz,
            }
            probabilities = softmax(scores)
            dominant = max(probabilities, key=probabilities.get)
            rows.append({
                "run_id": self.run_id,
                "observation_date": date.date(),
                "bull_probability": probabilities["BULL"],
                "recovery_probability": probabilities["RECOVERY"],
                "sideways_probability": probabilities["SIDEWAYS"],
                "correction_probability": probabilities["CORRECTION"],
                "bear_probability": probabilities["BEAR"],
                "dominant_regime": dominant,
                "regime_confidence": probabilities[dominant],
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert("market_regime_probabilities", result)
        return result

    def model_probabilities(
        self, frame: pd.DataFrame, features: list[str]
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        if not features:
            return pd.DataFrame(), pd.DataFrame()

        probability_rows = []
        quality_rows = []
        model_outputs: dict[tuple[str, int], tuple[HistGradientBoostingClassifier, list[str], str]] = {}
        training_fraction = float(self.cfg["probabilities"]["training_fraction"])

        for horizon in self.cfg["horizons_days"]:
            evaluated = frame.copy()
            evaluated["forward_return"] = (
                evaluated["btc_price_usd"].shift(-int(horizon))
                / evaluated["btc_price_usd"] - 1
            )
            forward_prices = pd.concat(
                [
                    evaluated["btc_price_usd"].shift(-offset)
                    for offset in range(1, int(horizon) + 1)
                ],
                axis=1,
            )
            future_min = forward_prices.min(axis=1)
            evaluated["forward_drawdown"] = (
                future_min / evaluated["btc_price_usd"] - 1
            )
            if "stablecoin_growth_30d_pct" in evaluated:
                evaluated["liquidity_expansion_target"] = (
                    evaluated["stablecoin_growth_30d_pct"].shift(-int(horizon))
                    > evaluated["stablecoin_growth_30d_pct"]
                ).astype(float)
            else:
                evaluated["liquidity_expansion_target"] = np.nan

            targets = {
                "POSITIVE_RETURN": (evaluated["forward_return"] > 0).astype(float),
                "DRAWDOWN_20": (evaluated["forward_drawdown"] <= -0.20).astype(float),
                "LIQUIDITY_EXPANSION": evaluated["liquidity_expansion_target"],
            }

            for target_key, target_series in targets.items():
                sample = evaluated[features].copy()
                sample["_target"] = target_series
                sample = sample.dropna()
                if (
                    len(sample)
                    < int(self.cfg["probabilities"]["minimum_total_rows"])
                    or sample["_target"].nunique() < 2
                ):
                    continue
                split = int(len(sample) * training_fraction)
                train = sample.iloc[:split]
                test = sample.iloc[split:]
                if (
                    len(train) < int(self.cfg["probabilities"]["minimum_training_rows"])
                    or len(test) < int(self.cfg["probabilities"]["minimum_testing_rows"])
                    or train["_target"].nunique() < 2
                    or test["_target"].nunique() < 2
                ):
                    continue

                model = HistGradientBoostingClassifier(
                    max_iter=int(self.cfg["probabilities"]["max_iterations"]),
                    learning_rate=float(self.cfg["probabilities"]["learning_rate"]),
                    max_leaf_nodes=int(self.cfg["probabilities"]["max_leaf_nodes"]),
                    min_samples_leaf=int(self.cfg["probabilities"]["min_samples_leaf"]),
                    l2_regularization=float(self.cfg["probabilities"]["l2_regularization"]),
                    random_state=int(self.cfg["probabilities"]["random_state"]),
                )
                model.fit(train[features], train["_target"].astype(int))
                test_probability = model.predict_proba(test[features])[:, 1]
                test_prediction = (test_probability >= 0.5).astype(int)
                accuracy = accuracy_score(test["_target"], test_prediction) * 100
                try:
                    auc = roc_auc_score(test["_target"], test_probability)
                except ValueError:
                    auc = None
                brier = brier_score_loss(test["_target"], test_probability)
                quality = (
                    "ACCEPTABLE"
                    if (
                        (auc is not None and auc >= float(self.cfg["probabilities"]["minimum_acceptable_auc"]))
                        and brier <= float(self.cfg["probabilities"]["maximum_acceptable_brier"])
                    )
                    else "WEAK"
                )
                quality_rows.append({
                    "run_id": self.run_id,
                    "target_key": target_key,
                    "forward_horizon_days": int(horizon),
                    "feature_count": len(features),
                    "training_rows": len(train),
                    "testing_rows": len(test),
                    "accuracy_pct": float(accuracy),
                    "roc_auc": safe_float(auc),
                    "brier_score": float(brier),
                    "quality_status": quality,
                    "calculated_at_utc": utcnow(),
                })

                model.fit(sample[features], sample["_target"].astype(int))
                model_outputs[(target_key, int(horizon))] = (
                    model, features, quality
                )

        latest = frame.iloc[[-1]]
        for horizon in self.cfg["horizons_days"]:
            probabilities: dict[str, float | None] = {}
            statuses = []
            for target_key in [
                "POSITIVE_RETURN",
                "DRAWDOWN_20",
                "LIQUIDITY_EXPANSION",
            ]:
                key = (target_key, int(horizon))
                if key not in model_outputs or latest[features].isna().any(axis=None):
                    probabilities[target_key] = None
                    continue
                model, model_features, quality = model_outputs[key]
                probabilities[target_key] = float(
                    model.predict_proba(latest[model_features])[:, 1][0]
                )
                statuses.append(quality)

            available = [
                value for value in probabilities.values()
                if value is not None
            ]
            confidence = (
                float(np.mean([abs(value - 0.5) * 2 for value in available]))
                if available else 0.0
            )
            status = (
                "ACCEPTABLE"
                if statuses and all(value == "ACCEPTABLE" for value in statuses)
                else "MIXED_OR_WEAK"
            )
            probability_rows.append({
                "run_id": self.run_id,
                "observation_date": frame["observation_date"].iloc[-1].date(),
                "forward_horizon_days": int(horizon),
                "positive_return_probability": probabilities["POSITIVE_RETURN"],
                "drawdown_20_probability": probabilities["DRAWDOWN_20"],
                "liquidity_expansion_probability": probabilities["LIQUIDITY_EXPANSION"],
                "probability_confidence": confidence,
                "model_quality_status": status,
                "calculated_at_utc": utcnow(),
            })

        quality_frame = pd.DataFrame(quality_rows)
        probability_frame = pd.DataFrame(probability_rows)
        self.upsert("decision_model_quality", quality_frame)
        self.upsert("investment_probabilities", probability_frame)
        return quality_frame, probability_frame

    def risk_snapshot(self, frame: pd.DataFrame) -> pd.DataFrame:
        prices = frame.set_index("observation_date")["btc_price_usd"].astype(float)
        returns = prices.pct_change(fill_method=None).dropna()
        latest_date = prices.index.max()
        vol30 = float(returns.tail(30).std(ddof=1) * math.sqrt(365) * 100)
        vol90 = float(returns.tail(90).std(ddof=1) * math.sqrt(365) * 100)
        var95 = float(returns.tail(365).quantile(0.05) * 100)
        cvar_values = returns.tail(365)[returns.tail(365) <= returns.tail(365).quantile(0.05)]
        cvar95 = float(cvar_values.mean() * 100) if not cvar_values.empty else var95
        trailing = prices.tail(365)
        drawdown = trailing / trailing.cummax() - 1
        maximum_drawdown = float(drawdown.min() * 100)
        expected_loss = float((cvar95 / 100) * math.sqrt(30) * 100)
        risk_score = clamp(
            vol90 / 1.2
            + abs(maximum_drawdown) * 0.55
            + abs(cvar95) * 3.0,
            0,
            100,
        )
        risk_level = (
            "LOW" if risk_score < 35
            else "MODERATE" if risk_score < 55
            else "HIGH" if risk_score < 75
            else "EXTREME"
        )
        result = pd.DataFrame([{
            "run_id": self.run_id,
            "observation_date": latest_date.date(),
            "volatility_30d_pct": vol30,
            "volatility_90d_pct": vol90,
            "historical_var_95_1d_pct": var95,
            "historical_cvar_95_1d_pct": cvar95,
            "maximum_drawdown_365d_pct": maximum_drawdown,
            "expected_30d_loss_pct": expected_loss,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "calculated_at_utc": utcnow(),
        }])
        self.upsert("investment_risk_snapshot", result)
        return result

    def governed_signal(
        self,
        frame: pd.DataFrame,
        features: list[str],
        scores: dict[str, float],
        directions: dict[str, str],
    ) -> tuple[pd.Series, pd.DataFrame]:
        if not features:
            return pd.Series(0.0, index=frame.index), pd.DataFrame()
        signals = []
        weights = []
        detail_rows = []
        for feature in features:
            z = self.rolling_zscore(frame[feature].astype(float))
            direction = 1.0 if directions.get(feature) == "POSITIVE" else -1.0
            weight = max(1.0, scores.get(feature, 50.0))
            signals.append(z * direction)
            weights.append(weight)
            latest_z = safe_float(z.iloc[-1], 0.0) or 0.0
            detail_rows.append({
                "feature_key": feature,
                "feature_value": safe_float(frame[feature].iloc[-1]),
                "standardized_value": latest_z,
                "inferred_direction": directions.get(feature, "NEUTRAL"),
                "contribution": latest_z * direction * weight,
            })
        matrix = pd.concat(signals, axis=1)
        weighted = matrix.mul(weights, axis=1)
        denominator = matrix.notna().mul(weights, axis=1).sum(axis=1)
        composite = weighted.sum(axis=1) / denominator.replace(0, np.nan)
        return composite.fillna(0).clip(-3, 3), pd.DataFrame(detail_rows)

    def stance(self, score: float) -> str:
        thresholds = self.cfg["decision"]["stance_thresholds"]
        if score >= float(thresholds["strong_buy"]):
            return "STRONG_BUY"
        if score >= float(thresholds["buy"]):
            return "BUY"
        if score >= float(thresholds["hold"]):
            return "HOLD"
        if score >= float(thresholds["reduce"]):
            return "REDUCE"
        return "DEFENSIVE"

    def make_decision(
        self,
        frame: pd.DataFrame,
        regimes: pd.DataFrame,
        probabilities: pd.DataFrame,
        risk: pd.DataFrame,
        features: list[str],
        scores: dict[str, float],
        directions: dict[str, str],
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
        composite, details = self.governed_signal(
            frame, features, scores, directions
        )
        latest_regime = regimes.iloc[-1]
        latest_risk = risk.iloc[0]
        probability90 = probabilities[
            probabilities["forward_horizon_days"] == 90
        ]
        if probability90.empty:
            positive = 0.5
            drawdown = 0.5
            probability_confidence = 0.0
            model_quality = "UNAVAILABLE"
        else:
            row = probability90.iloc[0]
            positive = safe_float(row["positive_return_probability"], 0.5) or 0.5
            drawdown = safe_float(row["drawdown_20_probability"], 0.5) or 0.5
            probability_confidence = safe_float(row["probability_confidence"], 0.0) or 0.0
            model_quality = row["model_quality_status"]

        regime_support = (
            float(latest_regime["bull_probability"])
            + 0.6 * float(latest_regime["recovery_probability"])
            - 0.5 * float(latest_regime["correction_probability"])
            - float(latest_regime["bear_probability"])
        )
        governed_component = float(composite.iloc[-1])
        probability_component = (positive - 0.5) * 2 - drawdown
        risk_penalty = float(latest_risk["risk_score"]) / 100
        action_score = (
            governed_component * float(self.cfg["decision"]["governed_signal_weight"])
            + regime_support * float(self.cfg["decision"]["regime_weight"])
            + probability_component * float(self.cfg["decision"]["probability_weight"])
            - risk_penalty * float(self.cfg["decision"]["risk_weight"])
        )
        action_score = clamp(action_score, -2.5, 2.5)
        stance = self.stance(action_score)

        neutral = float(self.cfg["allocation"]["neutral_btc_weight"])
        target = neutral + action_score * float(
            self.cfg["allocation"]["action_score_slope"]
        )
        if model_quality != "ACCEPTABLE":
            target = neutral + (target - neutral) * float(
                self.cfg["allocation"]["weak_model_multiplier"]
            )
        target = clamp(
            target,
            float(self.cfg["allocation"]["minimum_btc_weight"]),
            float(self.cfg["allocation"]["maximum_btc_weight"]),
        )
        confidence = clamp(
            (
                abs(action_score) / 2.5 * 0.45
                + float(latest_regime["regime_confidence"]) * 0.25
                + probability_confidence * 0.20
                + min(1.0, len(features) / 3) * 0.10
            )
            * 100,
            0,
            100,
        )
        production_status = (
            "SHADOW_ONLY"
            if len(features) > 0
            else "INSUFFICIENT_GOVERNED_FEATURES"
        )
        decision = pd.DataFrame([{
            "run_id": self.run_id,
            "observation_date": frame["observation_date"].iloc[-1].date(),
            "stance": stance,
            "confidence": confidence,
            "target_btc_weight": target,
            "target_cash_weight": 1 - target,
            "action_score": action_score,
            "dominant_regime": latest_regime["dominant_regime"],
            "positive_return_probability_90d": positive,
            "drawdown_20_probability_90d": drawdown,
            "risk_score": float(latest_risk["risk_score"]),
            "governed_feature_count": len(features),
            "production_status": production_status,
            "calculated_at_utc": utcnow(),
        }])
        self.upsert("investment_decisions", decision)

        rationale_rows = []
        narrative = [
            (
                "REGIME",
                None,
                None,
                None,
                regime_support,
                f"Market regime is {latest_regime['dominant_regime']} "
                f"with {float(latest_regime['regime_confidence'])*100:.1f}% confidence.",
            ),
            (
                "PROBABILITY",
                None,
                None,
                None,
                positive - drawdown,
                f"90-day positive-return probability is {positive*100:.1f}% "
                f"and >20% drawdown probability is {drawdown*100:.1f}%.",
            ),
            (
                "RISK",
                None,
                None,
                None,
                -risk_penalty,
                f"Current risk level is {latest_risk['risk_level']} "
                f"with a risk score of {float(latest_risk['risk_score']):.1f}.",
            ),
        ]
        for _, row in details.sort_values("contribution", ascending=False).iterrows():
            text = (
                f"{row['feature_key']} is "
                f"{abs(float(row['standardized_value'])):.2f} standard deviations "
                f"{'above' if float(row['standardized_value']) >= 0 else 'below'} "
                f"its rolling norm and contributes "
                f"{'positively' if float(row['contribution']) >= 0 else 'negatively'}."
            )
            narrative.append(
                (
                    "FEATURE",
                    row["feature_key"],
                    row["feature_value"],
                    row["standardized_value"],
                    row["contribution"],
                    text,
                )
            )
        narrative = sorted(narrative, key=lambda item: abs(float(item[4])), reverse=True)
        for rank, item in enumerate(narrative[: int(self.cfg["decision"]["maximum_rationales"])], start=1):
            rationale_rows.append({
                "run_id": self.run_id,
                "observation_date": frame["observation_date"].iloc[-1].date(),
                "rationale_rank": rank,
                "rationale_type": item[0],
                "feature_key": item[1],
                "feature_value": item[2],
                "standardized_value": item[3],
                "inferred_direction": (
                    directions.get(item[1], "N/A")
                    if item[1] else "N/A"
                ),
                "contribution": float(item[4]),
                "rationale_text": item[5],
                "calculated_at_utc": utcnow(),
            })
        rationale = pd.DataFrame(rationale_rows)
        self.upsert("investment_decision_rationale", rationale)
        return decision, rationale, composite

    def shadow_backtest(
        self,
        frame: pd.DataFrame,
        composite: pd.Series,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        dates = frame["observation_date"]
        btc = frame["btc_price_usd"].astype(float)
        rebalance_days = int(self.cfg["shadow"]["rebalance_days"])
        transaction_cost = float(
            self.cfg["shadow"]["transaction_cost_bps"]
        ) / 10000
        start_index = max(
            int(self.cfg["signals"]["minimum_zscore_history"]),
            200,
        )
        indexes = list(range(start_index, len(frame) - rebalance_days, rebalance_days))
        previous_weight = float(self.cfg["allocation"]["neutral_btc_weight"])
        rows = []

        for index in indexes:
            next_index = min(index + rebalance_days, len(frame) - 1)
            current_price = float(btc.iloc[index])
            next_price = float(btc.iloc[next_index])
            btc_return = next_price / current_price - 1
            signal = float(composite.iloc[index])
            target_weight = clamp(
                float(self.cfg["allocation"]["neutral_btc_weight"])
                + signal * float(self.cfg["allocation"]["action_score_slope"]),
                float(self.cfg["allocation"]["minimum_btc_weight"]),
                float(self.cfg["allocation"]["maximum_btc_weight"]),
            )
            turnover = abs(target_weight - previous_weight)
            cost = turnover * transaction_cost
            portfolio_return = target_weight * btc_return - cost
            stance = self.stance(signal)
            positive_probability = sigmoid(signal)
            drawdown_probability = sigmoid(-signal)
            rows.append({
                "run_id": self.run_id,
                "rebalance_date": dates.iloc[index].date(),
                "next_rebalance_date": dates.iloc[next_index].date(),
                "stance": stance,
                "btc_weight": target_weight,
                "cash_weight": 1 - target_weight,
                "action_score": signal,
                "positive_return_probability": positive_probability,
                "drawdown_probability": drawdown_probability,
                "portfolio_return_pct": portfolio_return * 100,
                "btc_return_pct": btc_return * 100,
                "excess_return_pct": (portfolio_return - btc_return) * 100,
                "turnover_pct": turnover * 100,
                "transaction_cost_pct": cost * 100,
                "calculated_at_utc": utcnow(),
            })
            previous_weight = target_weight

        periods = pd.DataFrame(rows)
        self.upsert("decision_shadow_periods", periods)
        if periods.empty:
            return periods, pd.DataFrame()

        portfolio_returns = periods["portfolio_return_pct"] / 100
        btc_returns = periods["btc_return_pct"] / 100
        periods_per_year = 365 / rebalance_days
        total, annual, volatility, sharpe, max_drawdown = annual_metrics(
            portfolio_returns, periods_per_year
        )
        btc_total, btc_annual, _, _, _ = annual_metrics(
            btc_returns, periods_per_year
        )
        active = portfolio_returns - btc_returns
        tracking_error = float(active.std(ddof=1) * math.sqrt(periods_per_year))
        information_ratio = (
            (annual - btc_annual) / tracking_error
            if tracking_error > 0 else None
        )
        benchmark_win_rate = float(
            (portfolio_returns > btc_returns).mean() * 100
        )
        promoted = (
            total - btc_total
            >= float(self.cfg["shadow"]["minimum_excess_return_pct"]) / 100
            and information_ratio is not None
            and information_ratio
            >= float(self.cfg["shadow"]["minimum_information_ratio"])
            and max_drawdown * 100
            >= float(self.cfg["shadow"]["maximum_drawdown_floor_pct"])
        )
        summary = pd.DataFrame([{
            "run_id": self.run_id,
            "start_date": periods["rebalance_date"].min(),
            "end_date": periods["next_rebalance_date"].max(),
            "periods": len(periods),
            "total_return_pct": total * 100,
            "annualized_return_pct": annual * 100,
            "annualized_volatility_pct": volatility * 100,
            "sharpe_ratio": sharpe,
            "maximum_drawdown_pct": max_drawdown * 100,
            "btc_total_return_pct": btc_total * 100,
            "btc_annualized_return_pct": btc_annual * 100,
            "btc_excess_pct": (total - btc_total) * 100,
            "information_ratio": information_ratio,
            "benchmark_win_rate_pct": benchmark_win_rate,
            "average_btc_weight_pct": float(periods["btc_weight"].mean() * 100),
            "average_turnover_pct": float(periods["turnover_pct"].mean()),
            "transaction_cost_drag_pct": float(periods["transaction_cost_pct"].sum()),
            "promotion_status": (
                "PROMOTION_CANDIDATE" if promoted else "RESEARCH_ONLY"
            ),
            "promotion_reason": (
                "Cleared configured decision-shadow thresholds."
                if promoted
                else "Did not clear all decision-shadow thresholds."
            ),
            "calculated_at_utc": utcnow(),
        }])
        self.upsert("decision_shadow_summary", summary)
        return periods, summary

    def run(self) -> dict[str, Any]:
        self.conn.execute(
            """
            UPDATE module21_runs
            SET status='FAILED', completed_at_utc=?,
                notes=COALESCE(notes,'') || '; interrupted prior run'
            WHERE status='RUNNING'
            """,
            [utcnow()],
        )
        self.conn.execute(
            """
            INSERT INTO module21_runs VALUES(
                ?, ?, NULL, 'RUNNING',
                0, 0, 0, 0, NULL, NULL,
                NULL, NULL, NULL, FALSE,
                NULL, '5.0.0'
            )
            """,
            [self.run_id, self.started],
        )

        try:
            frame = self.frame()
            features, scores, directions = self.governed_features(frame)
            regimes = self.regime_probabilities(frame)
            quality, probabilities = self.model_probabilities(frame, features)
            risk = self.risk_snapshot(frame)
            decision, rationale, composite = self.make_decision(
                frame,
                regimes,
                probabilities,
                risk,
                features,
                scores,
                directions,
            )
            periods, summary = self.shadow_backtest(frame, composite)

            if summary.empty:
                shadow_return = btc_return = excess = None
                promoted = False
            else:
                record = summary.iloc[0]
                shadow_return = float(record["total_return_pct"])
                btc_return = float(record["btc_total_return_pct"])
                excess = float(record["btc_excess_pct"])
                promoted = record["promotion_status"] == "PROMOTION_CANDIDATE"

            latest = decision.iloc[0]
            notes = (
                "Investment Decision Engine remains shadow-only. "
                "Module 13 production allocations are unchanged."
            )
            self.conn.execute(
                """
                UPDATE module21_runs
                SET completed_at_utc=?, status='SUCCESS',
                    governed_features=?, probability_models=?,
                    decision_rows=?, shadow_periods=?,
                    current_stance=?, current_btc_weight=?,
                    shadow_return_pct=?, btc_return_pct=?,
                    shadow_excess_pct=?, promoted=?, notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    len(features),
                    len(quality),
                    len(decision),
                    len(periods),
                    latest["stance"],
                    float(latest["target_btc_weight"]),
                    shadow_return,
                    btc_return,
                    excess,
                    promoted,
                    notes,
                    self.run_id,
                ],
            )
            self.conn.close()
            return {
                "run_id": self.run_id,
                "status": "SUCCESS",
                "governed_features": len(features),
                "probability_models": len(quality),
                "stance": latest["stance"],
                "confidence": float(latest["confidence"]),
                "btc_weight": float(latest["target_btc_weight"]),
                "cash_weight": float(latest["target_cash_weight"]),
                "dominant_regime": latest["dominant_regime"],
                "risk_score": float(latest["risk_score"]),
                "shadow_periods": len(periods),
                "shadow_return_pct": shadow_return,
                "btc_return_pct": btc_return,
                "shadow_excess_pct": excess,
                "promoted": promoted,
            }
        except Exception as exc:
            self.conn.execute(
                """
                UPDATE module21_runs
                SET completed_at_utc=?, status='FAILED', notes=?
                WHERE run_id=?
                """,
                [utcnow(), str(exc)[:1000], self.run_id],
            )
            self.conn.close()
            raise

def run_module21() -> dict[str, Any]:
    return Module21Runner().run()
