from __future__ import annotations

import argparse
import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA, clamp

MODULE3_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module3_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    signal_date DATE,
    assets_analyzed INTEGER,
    monthly_contribution_usd DOUBLE,
    cash_weight DOUBLE,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS asset_risk_metrics(
    asset_id VARCHAR,
    observation_date DATE,
    observations INTEGER,
    annualized_return_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    downside_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    sortino_ratio DOUBLE,
    beta_to_btc DOUBLE,
    correlation_to_btc DOUBLE,
    max_drawdown_pct DOUBLE,
    calmar_ratio DOUBLE,
    risk_adjusted_rank INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, observation_date)
);

CREATE TABLE IF NOT EXISTS portfolio_recommendations(
    run_id VARCHAR,
    observation_date DATE,
    asset_id VARCHAR,
    asset_role VARCHAR,
    module2_score DOUBLE,
    confidence DOUBLE,
    risk_level VARCHAR,
    raw_allocation_score DOUBLE,
    target_weight DOUBLE,
    monthly_dca_usd DOUBLE,
    target_units DOUBLE,
    action VARCHAR,
    rationale VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS portfolio_summary(
    run_id VARCHAR PRIMARY KEY,
    observation_date DATE,
    monthly_contribution_usd DOUBLE,
    invested_weight DOUBLE,
    cash_weight DOUBLE,
    weighted_score DOUBLE,
    expected_volatility_pct DOUBLE,
    diversification_score DOUBLE,
    macro_regime VARCHAR,
    market_regime VARCHAR,
    portfolio_posture VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS scenario_projections(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    horizon_years INTEGER,
    scenario VARCHAR,
    annual_return_assumption_pct DOUBLE,
    projected_price_usd DOUBLE,
    projected_multiple DOUBLE,
    methodology VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id, horizon_years, scenario)
);

CREATE TABLE IF NOT EXISTS asset_correlations(
    run_id VARCHAR,
    observation_date DATE,
    asset_id_1 VARCHAR,
    asset_id_2 VARCHAR,
    correlation DOUBLE,
    lookback_days INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id_1, asset_id_2)
);

CREATE TABLE IF NOT EXISTS valuation_zones(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    current_price_usd DOUBLE,
    fair_value_usd DOUBLE,
    buy_below_usd DOUBLE,
    strong_buy_below_usd DOUBLE,
    trim_above_usd DOUBLE,
    overextended_above_usd DOUBLE,
    upside_to_fair_value_pct DOUBLE,
    valuation_label VARCHAR,
    methodology VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS rebalance_recommendations(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    current_weight DOUBLE,
    target_weight DOUBLE,
    weight_difference DOUBLE,
    dollar_adjustment DOUBLE,
    action VARCHAR,
    priority INTEGER,
    rationale VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS position_risk_contributions(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    target_weight DOUBLE,
    marginal_volatility_contribution DOUBLE,
    percent_of_portfolio_risk DOUBLE,
    maximum_recommended_weight DOUBLE,
    risk_budget_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE OR REPLACE VIEW latest_portfolio_recommendations AS
SELECT p.*
FROM portfolio_recommendations p
JOIN (
    SELECT run_id FROM module3_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_portfolio_summary AS
SELECT * FROM portfolio_summary
ORDER BY observation_date DESC, calculated_at_utc DESC LIMIT 1;

CREATE OR REPLACE VIEW latest_risk_metrics AS
SELECT * EXCLUDE(rn)
FROM (
    SELECT *, ROW_NUMBER() OVER(
        PARTITION BY asset_id
        ORDER BY observation_date DESC, calculated_at_utc DESC
    ) rn
    FROM asset_risk_metrics
) x
WHERE rn=1;

CREATE OR REPLACE VIEW latest_scenario_projections AS
SELECT s.*
FROM scenario_projections s
JOIN (
    SELECT run_id FROM module3_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_valuation_zones AS
SELECT v.*
FROM valuation_zones v
JOIN (
    SELECT run_id FROM module3_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_rebalance_recommendations AS
SELECT v.*
FROM rebalance_recommendations v
JOIN (
    SELECT run_id FROM module3_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_position_risk_contributions AS
SELECT v.*
FROM position_risk_contributions v
JOIN (
    SELECT run_id FROM module3_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);
"""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def geometric_cagr(prices: pd.Series) -> float | None:
    clean = prices.dropna()
    if len(clean) < 2:
        return None
    start_price = float(clean.iloc[0])
    end_price = float(clean.iloc[-1])
    days = max((clean.index[-1] - clean.index[0]).days, 1)
    if start_price <= 0 or end_price <= 0:
        return None
    years = days / 365.25
    return float((end_price / start_price) ** (1 / years) - 1)

def max_drawdown_from_returns(returns: pd.Series) -> float | None:
    if returns.empty:
        return None
    wealth = (1.0 + returns).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    return float(drawdown.min() * 100.0)

def safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return float(numerator / denominator)

class Module3Runner:
    def __init__(
        self,
        monthly_contribution_usd: float | None = None,
        current_holdings: dict[str, float] | None = None,
    ):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE2_SCHEMA)
        self.conn.execute(MODULE3_SCHEMA)
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        self.config = self.settings["module3"]
        self.module4 = self.settings["module4"]
        self.monthly_override = monthly_contribution_usd
        self.current_holdings = current_holdings or {}

    def upsert(self, table: str, frame: pd.DataFrame, keys: list[str]) -> tuple[int, int]:
        if frame.empty:
            return 0, 0
        self.conn.register("_m3_stage", frame)
        condition = " AND ".join(f"t.{key}=s.{key}" for key in keys)
        updated = int(self.conn.execute(
            f"SELECT COUNT(*) FROM {table} t JOIN _m3_stage s ON {condition}"
        ).fetchone()[0])
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m3_stage"
        )
        self.conn.unregister("_m3_stage")
        return len(frame) - updated, updated

    def price_matrix(self) -> pd.DataFrame:
        lookback = int(self.config["risk"]["lookback_days"])
        frame = self.conn.execute(
            """
            SELECT asset_id, observation_date, price_usd
            FROM asset_market_daily
            WHERE source='coingecko'
              AND observation_date >= CURRENT_DATE - ? * INTERVAL 1 DAY
            ORDER BY observation_date, asset_id
            """,
            [lookback + 20],
        ).fetchdf()
        if frame.empty:
            raise RuntimeError("No price history is available for Module 3.")
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame.pivot_table(
            index="observation_date", columns="asset_id",
            values="price_usd", aggfunc="last"
        ).sort_index().ffill()

    def calculate_risk_metrics(
        self, prices: pd.DataFrame, signal_date
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        returns = prices.pct_change(fill_method=None).dropna(how="all")
        risk_free = float(self.config["risk"]["risk_free_rate_pct"]) / 100.0
        minimum = int(self.config["risk"]["minimum_observations"])
        btc = returns["bitcoin"] if "bitcoin" in returns.columns else None
        rows = []

        for asset_id in prices.columns:
            asset_prices = prices[asset_id].dropna()
            series = returns[asset_id].dropna()
            if len(series) < minimum:
                continue

            cagr = geometric_cagr(asset_prices)
            annual_vol = float(series.std(ddof=1) * math.sqrt(365))
            downside = series[series < 0]
            downside_vol = (
                float(downside.std(ddof=1) * math.sqrt(365))
                if len(downside) >= 2 else None
            )
            sharpe = safe_ratio(
                None if cagr is None else cagr - risk_free,
                annual_vol,
            )
            sortino = safe_ratio(
                None if cagr is None else cagr - risk_free,
                downside_vol,
            )
            beta = None
            corr = None
            if btc is not None:
                pair = pd.concat([series, btc], axis=1).dropna()
                if len(pair) >= minimum:
                    covariance = pair.iloc[:, 0].cov(pair.iloc[:, 1])
                    variance = pair.iloc[:, 1].var(ddof=1)
                    beta = safe_ratio(covariance, variance)
                    corr = float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))
            drawdown = max_drawdown_from_returns(series)
            calmar = safe_ratio(
                cagr,
                abs(drawdown / 100.0) if drawdown is not None else None,
            )
            rows.append({
                "asset_id": asset_id,
                "observation_date": signal_date,
                "observations": len(series),
                "annualized_return_pct": (
                    cagr * 100 if cagr is not None else None
                ),
                "annualized_volatility_pct": annual_vol * 100,
                "downside_volatility_pct": (
                    downside_vol * 100 if downside_vol is not None else None
                ),
                "sharpe_ratio": sharpe,
                "sortino_ratio": sortino,
                "beta_to_btc": beta,
                "correlation_to_btc": corr,
                "max_drawdown_pct": drawdown,
                "calmar_ratio": calmar,
                "risk_adjusted_rank": None,
                "calculated_at_utc": utcnow(),
            })

        risk = pd.DataFrame(rows)
        if not risk.empty:
            composite = (
                risk["sharpe_ratio"].fillna(-10).rank(ascending=False)
                + risk["sortino_ratio"].fillna(-10).rank(ascending=False)
                + risk["calmar_ratio"].fillna(-10).rank(ascending=False)
            )
            risk["risk_adjusted_rank"] = composite.rank(
                method="min", ascending=True
            ).astype(int)
            self.upsert(
                "asset_risk_metrics", risk,
                ["asset_id", "observation_date"]
            )

        correlations = returns.corr(min_periods=minimum)
        corr_rows = []
        for asset_1 in correlations.index:
            for asset_2 in correlations.columns:
                if asset_1 > asset_2:
                    continue
                value = correlations.loc[asset_1, asset_2]
                if pd.isna(value):
                    continue
                corr_rows.append({
                    "run_id": self.run_id,
                    "observation_date": signal_date,
                    "asset_id_1": asset_1,
                    "asset_id_2": asset_2,
                    "correlation": float(value),
                    "lookback_days": int(self.config["risk"]["lookback_days"]),
                    "calculated_at_utc": utcnow(),
                })
        corr_frame = pd.DataFrame(corr_rows)
        if not corr_frame.empty:
            self.upsert(
                "asset_correlations", corr_frame,
                ["run_id", "asset_id_1", "asset_id_2"]
            )
        return risk, correlations

    def cash_weight(self, macro: str, market: str) -> float:
        minimum = float(self.config["portfolio"]["minimum_cash_weight"])
        maximum = float(self.config["portfolio"]["maximum_cash_weight"])
        macro_adj = {
            "RISK_ON": -0.03, "SUPPORTIVE": 0.00, "NEUTRAL": 0.05,
            "DEFENSIVE": 0.12, "RISK_OFF": 0.20, "UNKNOWN": 0.10,
        }.get(macro, 0.08)
        market_adj = {
            "EXPANSION": -0.03, "POSITIVE": 0.00, "NEUTRAL": 0.05,
            "CONTRACTION": 0.12, "STRESS": 0.20, "UNKNOWN": 0.10,
        }.get(market, 0.08)
        return float(max(minimum, min(maximum, minimum + macro_adj + market_adj)))

    def dca_multiplier(
        self,
        weighted_score: float,
        macro_label: str,
        market_label: str,
    ) -> float:
        config = self.module4["dynamic_dca"]
        base = float(config["neutral_multiplier"])
        score_adjustment = (weighted_score - 50.0) / 50.0 * 0.35
        macro_adjustment = {
            "RISK_ON": 0.15, "SUPPORTIVE": 0.08, "NEUTRAL": 0.0,
            "DEFENSIVE": -0.12, "RISK_OFF": -0.25, "UNKNOWN": -0.10,
        }.get(macro_label, -0.05)
        market_adjustment = {
            "EXPANSION": 0.10, "POSITIVE": 0.05, "NEUTRAL": 0.0,
            "CONTRACTION": -0.10, "STRESS": -0.20, "UNKNOWN": -0.10,
        }.get(market_label, -0.05)
        multiplier = base + score_adjustment + macro_adjustment + market_adjustment
        return float(max(
            float(config["minimum_multiplier"]),
            min(float(config["maximum_multiplier"]), multiplier),
        ))

    def build_allocations(
        self,
        signals: pd.DataFrame,
        risk: pd.DataFrame,
        correlations: pd.DataFrame,
        macro_label: str,
        market_label: str,
        signal_date,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        merged = signals.merge(
            risk[[
                "asset_id", "sharpe_ratio", "sortino_ratio",
                "annualized_volatility_pct", "risk_adjusted_rank"
            ]],
            on="asset_id", how="left",
        )
        roles = {
            asset["asset_id"]: (
                "CORE" if asset["asset_id"] in
                self.config["portfolio"]["core_assets"] else "SATELLITE"
            )
            for asset in self.assets
        }
        merged["asset_role"] = merged["asset_id"].map(roles)
        merged["score_factor"] = merged["overall_score"].clip(0, 100) / 100
        merged["confidence_factor"] = merged["confidence"].clip(0, 100) / 100
        merged["risk_factor"] = (
            1.0 / np.sqrt(
                merged["annualized_volatility_pct"].fillna(100).clip(lower=20)
            )
        )
        merged["sharpe_factor"] = (
            merged["sharpe_ratio"].fillna(0).clip(lower=-1, upper=2) + 1.25
        ).clip(lower=0.15)
        signal_multiplier = {
            "STRONG_BUY": 1.30, "BUY": 1.15, "HOLD": 0.85,
            "REDUCE": 0.40, "AVOID": 0.10, "INSUFFICIENT_DATA": 0.0,
        }
        merged["signal_factor"] = merged["signal"].map(signal_multiplier).fillna(0)
        merged["raw_allocation_score"] = (
            merged["score_factor"] ** 1.5
            * merged["confidence_factor"]
            * merged["risk_factor"]
            * merged["sharpe_factor"]
            * merged["signal_factor"]
        )

        cash = self.cash_weight(macro_label, market_label)
        investable = 1.0 - cash
        core_min = float(self.config["portfolio"]["core_minimum_total_weight"])
        max_single = float(self.config["portfolio"]["maximum_single_asset_weight"])
        max_sat = float(self.config["portfolio"]["maximum_satellite_weight"])
        min_trade = float(self.config["portfolio"]["minimum_trade_weight"])

        core = merged["asset_role"] == "CORE"
        satellite = ~core
        weights = pd.Series(0.0, index=merged.index)

        core_scores = merged.loc[core, "raw_allocation_score"].clip(lower=0)
        satellite_scores = merged.loc[satellite, "raw_allocation_score"].clip(lower=0)
        core_pool = min(investable, max(core_min, investable * 0.72))
        sat_pool = max(0.0, investable - core_pool)

        if core_scores.sum() > 0:
            weights.loc[core] = core_scores / core_scores.sum() * core_pool
        if satellite_scores.sum() > 0 and sat_pool > 0:
            weights.loc[satellite] = (
                satellite_scores / satellite_scores.sum() * sat_pool
            )

        caps = pd.Series(
            [max_single if role == "CORE" else max_sat
             for role in merged["asset_role"]],
            index=merged.index,
        )
        for _ in range(10):
            excess = (weights - caps).clip(lower=0).sum()
            weights = weights.clip(upper=caps)
            if excess < 1e-9:
                break
            eligible = (weights < caps - 1e-9) & (merged["raw_allocation_score"] > 0)
            if not eligible.any():
                cash += excess
                break
            base = merged.loc[eligible, "raw_allocation_score"]
            weights.loc[eligible] += excess * base / base.sum()

        dropped = weights.where(weights < min_trade, 0.0).sum()
        weights = weights.where(weights >= min_trade, 0.0)
        cash += dropped
        total = weights.sum()
        if total > 1.0 - cash and total > 0:
            weights *= (1.0 - cash) / total

        merged["target_weight"] = weights
        weighted_score = (
            float((merged["overall_score"] * merged["target_weight"]).sum())
            / max(float(merged["target_weight"].sum()), 1e-9)
        )

        base_monthly = (
            float(self.monthly_override)
            if self.monthly_override is not None
            else float(self.config["portfolio"]["monthly_contribution_usd"])
        )
        multiplier = self.dca_multiplier(
            weighted_score, macro_label, market_label
        )
        monthly = base_monthly * multiplier
        merged["monthly_dca_usd"] = merged["target_weight"] * monthly
        merged["target_units"] = (
            merged["monthly_dca_usd"] / merged["price_usd"]
        ).replace([np.inf, -np.inf], np.nan)

        def action(row):
            if row["target_weight"] == 0:
                return "NO_NEW_CAPITAL"
            if row["signal"] in {"STRONG_BUY", "BUY"}:
                return "ACCUMULATE"
            if row["signal"] == "HOLD":
                return "DCA_SELECTIVELY"
            return "MINIMAL_DCA"

        merged["action"] = merged.apply(action, axis=1)
        merged["rationale"] = merged.apply(
            lambda row: (
                f"{row['asset_role']} asset; Module 2 score "
                f"{row['overall_score']:.1f}; confidence "
                f"{row['confidence']:.1f}; {row['risk_level']} risk; "
                f"signal {row['signal']}."
            ),
            axis=1,
        )

        recs = pd.DataFrame({
            "run_id": self.run_id,
            "observation_date": signal_date,
            "asset_id": merged["asset_id"],
            "asset_role": merged["asset_role"],
            "module2_score": merged["overall_score"],
            "confidence": merged["confidence"],
            "risk_level": merged["risk_level"],
            "raw_allocation_score": merged["raw_allocation_score"],
            "target_weight": merged["target_weight"],
            "monthly_dca_usd": merged["monthly_dca_usd"],
            "target_units": merged["target_units"],
            "action": merged["action"],
            "rationale": merged["rationale"],
            "calculated_at_utc": utcnow(),
        })
        self.upsert(
            "portfolio_recommendations", recs,
            ["run_id", "asset_id"]
        )

        nonzero = merged.loc[merged["target_weight"] > 0, "target_weight"]
        diversification = (
            clamp((1.0 - float((nonzero ** 2).sum())) * 140.0)
            if not nonzero.empty else 0.0
        )
        posture = (
            "OFFENSIVE" if cash <= 0.12
            else "BALANCED" if cash <= 0.25
            else "DEFENSIVE"
        )
        summary = pd.DataFrame([{
            "run_id": self.run_id,
            "observation_date": signal_date,
            "monthly_contribution_usd": monthly,
            "invested_weight": float(merged["target_weight"].sum()),
            "cash_weight": float(cash),
            "weighted_score": weighted_score,
            "expected_volatility_pct": None,
            "diversification_score": diversification,
            "macro_regime": macro_label,
            "market_regime": market_label,
            "portfolio_posture": posture,
            "calculated_at_utc": utcnow(),
        }])
        return recs, summary

    def scenario_rows(
        self,
        signals: pd.DataFrame,
        risk: pd.DataFrame,
        market_label: str,
        signal_date,
    ) -> pd.DataFrame:
        merged = signals.merge(
            risk[[
                "asset_id", "annualized_return_pct",
                "annualized_volatility_pct"
            ]],
            on="asset_id", how="left",
        )
        horizons = self.config["scenarios"]["horizons_years"]
        floor = float(self.config["scenarios"]["annual_return_floor_pct"])
        cap = float(self.config["scenarios"]["annual_return_cap_pct"])
        market_tilt = {
            "EXPANSION": 8.0, "POSITIVE": 4.0, "NEUTRAL": 0.0,
            "CONTRACTION": -6.0, "STRESS": -12.0, "UNKNOWN": -4.0,
        }.get(market_label, -2.0)
        rows = []

        for _, row in merged.iterrows():
            historical_cagr = float(row["annualized_return_pct"] or 0)
            volatility = float(row["annualized_volatility_pct"] or 80)
            score_tilt = (float(row["overall_score"]) - 50.0) * 0.8
            macro_tilt = (float(row["macro_score"]) - 50.0) * 0.25
            base_return = np.clip(
                historical_cagr * 0.40
                + score_tilt
                + macro_tilt
                + market_tilt,
                floor, cap,
            )
            stress = min(volatility * 0.45, 55.0)
            assumptions = {
                "BEAR": np.clip(base_return - stress, floor, cap),
                "BASE": base_return,
                "BULL": np.clip(base_return + stress, floor, cap),
            }
            for years in horizons:
                for scenario, annual_pct in assumptions.items():
                    projected = float(row["price_usd"]) * (
                        1.0 + annual_pct / 100.0
                    ) ** int(years)
                    rows.append({
                        "run_id": self.run_id,
                        "asset_id": row["asset_id"],
                        "observation_date": signal_date,
                        "horizon_years": int(years),
                        "scenario": scenario,
                        "annual_return_assumption_pct": float(annual_pct),
                        "projected_price_usd": max(0.0, projected),
                        "projected_multiple": max(
                            0.0, projected / float(row["price_usd"])
                        ),
                        "methodology": (
                            "Geometric CAGR blended with Module 2 score, "
                            "macro regime, market regime, and volatility stress."
                        ),
                        "calculated_at_utc": utcnow(),
                    })
        frame = pd.DataFrame(rows)
        self.upsert(
            "scenario_projections", frame,
            ["run_id", "asset_id", "horizon_years", "scenario"]
        )
        return frame

    def valuation_rows(
        self,
        signals: pd.DataFrame,
        risk: pd.DataFrame,
        scenario_frame: pd.DataFrame,
        signal_date,
    ) -> pd.DataFrame:
        base_1y = scenario_frame[
            (scenario_frame["horizon_years"] == 1)
            & (scenario_frame["scenario"] == "BASE")
        ][["asset_id", "projected_price_usd"]].rename(
            columns={"projected_price_usd": "base_1y_price"}
        )
        merged = signals.merge(risk, on="asset_id", how="left").merge(
            base_1y, on="asset_id", how="left"
        )
        weights = self.module4["valuation"]["fair_value_weights"]
        rows = []
        for _, row in merged.iterrows():
            price = float(row["price_usd"])
            sma50 = float(row["sma_50"] or price)
            sma200 = float(row["sma_200"] or price)
            trend_anchor = 0.4 * sma50 + 0.6 * sma200
            vol = float(row["annualized_volatility_pct"] or 80)
            vol_discount = max(0.55, 1.0 - min(vol, 180) / 1000)
            volatility_anchor = price * vol_discount
            drawdown_anchor = price * (
                1.0 + min(abs(float(row["ath_drawdown_pct"] or 0)), 90) / 300
            )
            score_anchor = float(row["base_1y_price"] or price)

            fair = (
                trend_anchor * float(weights["trend_anchor"])
                + volatility_anchor * float(weights["volatility_anchor"])
                + drawdown_anchor * float(weights["drawdown_anchor"])
                + score_anchor * float(weights["score_anchor"])
            )
            buy = fair * (
                1 - float(self.module4["valuation"]["buy_below_discount_pct"]) / 100
            )
            strong = fair * (
                1 - float(self.module4["valuation"]["strong_buy_discount_pct"]) / 100
            )
            trim = fair * (
                1 + float(self.module4["valuation"]["trim_premium_pct"]) / 100
            )
            over = fair * (
                1 + float(self.module4["valuation"]["overextended_premium_pct"]) / 100
            )
            if price <= strong:
                label = "STRONG_BUY_ZONE"
            elif price <= buy:
                label = "BUY_ZONE"
            elif price <= trim:
                label = "FAIR_RANGE"
            elif price <= over:
                label = "TRIM_ZONE"
            else:
                label = "OVEREXTENDED"

            rows.append({
                "run_id": self.run_id,
                "asset_id": row["asset_id"],
                "observation_date": signal_date,
                "current_price_usd": price,
                "fair_value_usd": fair,
                "buy_below_usd": buy,
                "strong_buy_below_usd": strong,
                "trim_above_usd": trim,
                "overextended_above_usd": over,
                "upside_to_fair_value_pct": (fair / price - 1) * 100,
                "valuation_label": label,
                "methodology": (
                    "Quantitative reference range from moving averages, "
                    "volatility, drawdown, and one-year base scenario."
                ),
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert(
            "valuation_zones", frame, ["run_id", "asset_id"]
        )
        return frame

    def risk_contribution_rows(
        self,
        prices: pd.DataFrame,
        recs: pd.DataFrame,
        signal_date,
    ) -> pd.DataFrame:
        returns = prices.pct_change(fill_method=None).dropna(how="all")
        weights = recs.set_index("asset_id")["target_weight"]
        common = [asset for asset in returns.columns if asset in weights.index]
        if not common:
            return pd.DataFrame()
        covariance = returns[common].cov() * 365
        vector = weights.reindex(common).fillna(0).to_numpy()
        portfolio_variance = float(vector.T @ covariance.to_numpy() @ vector)
        portfolio_vol = math.sqrt(max(portfolio_variance, 0))
        marginal = covariance.to_numpy() @ vector
        max_risk_pct = float(
            self.module4["rebalance"]["maximum_position_risk_contribution_pct"]
        )
        rows = []
        for idx, asset_id in enumerate(common):
            component = (
                vector[idx] * marginal[idx] / portfolio_variance
                if portfolio_variance > 0 else 0.0
            )
            pct_risk = component * 100
            current_weight = float(vector[idx])
            max_weight = (
                current_weight * max_risk_pct / pct_risk
                if pct_risk > max_risk_pct and pct_risk > 0
                else current_weight
            )
            rows.append({
                "run_id": self.run_id,
                "asset_id": asset_id,
                "observation_date": signal_date,
                "target_weight": current_weight,
                "marginal_volatility_contribution": (
                    float(marginal[idx] / portfolio_vol)
                    if portfolio_vol > 0 else 0.0
                ),
                "percent_of_portfolio_risk": pct_risk,
                "maximum_recommended_weight": max(0.0, min(1.0, max_weight)),
                "risk_budget_status": (
                    "OVER_BUDGET" if pct_risk > max_risk_pct else "WITHIN_BUDGET"
                ),
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert(
            "position_risk_contributions", frame, ["run_id", "asset_id"]
        )
        return frame

    def rebalance_rows(
        self,
        recs: pd.DataFrame,
        signal_date,
        total_portfolio_value: float,
    ) -> pd.DataFrame:
        threshold = (
            float(self.module4["rebalance"]["minimum_action_weight_pct"]) / 100
        )
        current_values = {
            asset_id: float(value)
            for asset_id, value in self.current_holdings.items()
            if value is not None and float(value) >= 0
        }
        provided_total = sum(current_values.values())
        denominator = total_portfolio_value if total_portfolio_value > 0 else provided_total
        if denominator <= 0:
            current_weights = {asset_id: 0.0 for asset_id in recs["asset_id"]}
            denominator = float(recs["monthly_dca_usd"].sum())
        else:
            current_weights = {
                asset_id: current_values.get(asset_id, 0.0) / denominator
                for asset_id in recs["asset_id"]
            }

        rows = []
        for _, row in recs.iterrows():
            current = float(current_weights.get(row["asset_id"], 0.0))
            target = float(row["target_weight"])
            diff = target - current
            if abs(diff) < threshold:
                action = "HOLD"
                priority = 3
            elif diff > 0:
                action = "BUY"
                priority = 1 if diff >= threshold * 2 else 2
            else:
                action = "REDUCE"
                priority = 1 if abs(diff) >= threshold * 2 else 2
            rows.append({
                "run_id": self.run_id,
                "asset_id": row["asset_id"],
                "observation_date": signal_date,
                "current_weight": current,
                "target_weight": target,
                "weight_difference": diff,
                "dollar_adjustment": diff * denominator,
                "action": action,
                "priority": priority,
                "rationale": (
                    f"Current weight {current:.1%}; target {target:.1%}; "
                    f"difference {diff:+.1%}."
                ),
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert(
            "rebalance_recommendations", frame, ["run_id", "asset_id"]
        )
        return frame

    def run(self) -> dict[str, Any]:
        if self.conn.execute(
            "SELECT COUNT(*) FROM latest_asset_signals"
        ).fetchone()[0] == 0:
            raise RuntimeError("Run Module 2 before Module 3.")

        signals = self.conn.execute(
            "SELECT * FROM latest_asset_signals"
        ).fetchdf()
        macro = self.conn.execute(
            "SELECT * FROM latest_macro_regime"
        ).fetchdf()
        market = self.conn.execute(
            "SELECT * FROM latest_market_regime"
        ).fetchdf()

        signal_date = signals["observation_date"].max()
        macro_label = macro.iloc[0]["regime_label"] if not macro.empty else "UNKNOWN"
        market_label = market.iloc[0]["regime_label"] if not market.empty else "UNKNOWN"

        base_monthly = (
            float(self.monthly_override)
            if self.monthly_override is not None
            else float(self.config["portfolio"]["monthly_contribution_usd"])
        )

        self.conn.execute(
            """
            INSERT INTO module3_runs(
                run_id,started_at_utc,status,signal_date,assets_analyzed,
                monthly_contribution_usd,cash_weight,notes,platform_version
            ) VALUES (?,?,'RUNNING',?,0,?,NULL,NULL,'1.4.0')
            """,
            [self.run_id, self.started, signal_date, base_monthly],
        )

        prices = self.price_matrix()
        risk, correlations = self.calculate_risk_metrics(prices, signal_date)
        recs, summary = self.build_allocations(
            signals, risk, correlations, macro_label, market_label, signal_date
        )

        returns = prices.pct_change(fill_method=None).dropna(how="all")
        weights = recs.set_index("asset_id")["target_weight"]
        common = [c for c in returns.columns if c in weights.index]
        if common:
            covariance = returns[common].cov() * 365
            vector = weights.reindex(common).fillna(0).to_numpy()
            variance = float(vector.T @ covariance.to_numpy() @ vector)
            summary.loc[0, "expected_volatility_pct"] = (
                math.sqrt(max(variance, 0)) * 100
            )
        self.upsert("portfolio_summary", summary, ["run_id"])

        scenarios = self.scenario_rows(
            signals, risk, market_label, signal_date
        )
        valuations = self.valuation_rows(
            signals, risk, scenarios, signal_date
        )
        risk_contrib = self.risk_contribution_rows(
            prices, recs, signal_date
        )

        holdings_total = sum(
            float(value) for value in self.current_holdings.values()
        )
        rebalance = self.rebalance_rows(
            recs, signal_date, holdings_total
        )

        cash = float(summary.iloc[0]["cash_weight"])
        monthly = float(summary.iloc[0]["monthly_contribution_usd"])
        notes = (
            f"{len(recs)} assets analyzed; cash={cash:.1%}; "
            f"monthly={monthly:.2f}; macro={macro_label}; "
            f"market={market_label}; {len(scenarios)} scenario rows; "
            f"{len(valuations)} valuation rows."
        )
        self.conn.execute(
            """
            UPDATE module3_runs
            SET completed_at_utc=?,status='SUCCESS',assets_analyzed=?,
                monthly_contribution_usd=?,cash_weight=?,notes=?
            WHERE run_id=?
            """,
            [utcnow(), len(recs), monthly, cash, notes, self.run_id],
        )
        self.conn.close()
        return {
            "run_id": self.run_id,
            "status": "SUCCESS",
            "signal_date": str(signal_date),
            "assets_analyzed": len(recs),
            "cash_weight": cash,
            "macro_regime": macro_label,
            "market_regime": market_label,
            "monthly_contribution_usd": monthly,
        }

def run_module3(
    monthly_contribution_usd: float | None = None,
    current_holdings: dict[str, float] | None = None,
) -> dict[str, Any]:
    return Module3Runner(
        monthly_contribution_usd=monthly_contribution_usd,
        current_holdings=current_holdings,
    ).run()
