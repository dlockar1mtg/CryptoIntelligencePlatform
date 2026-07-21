from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect, path_for

MODULE2_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module2_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    assets_scored INTEGER,
    assets_skipped INTEGER,
    signal_date DATE,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS macro_regime_daily(
    observation_date DATE PRIMARY KEY,
    real_yield DOUBLE,
    nominal_yield DOUBLE,
    fed_funds_rate DOUBLE,
    breakeven_inflation DOUBLE,
    vix DOUBLE,
    high_yield_spread DOUBLE,
    dollar_index DOUBLE,
    dollar_90d_change_pct DOUBLE,
    m2_yoy_pct DOUBLE,
    unemployment_rate DOUBLE,
    unemployment_6m_change DOUBLE,
    liquidity_score DOUBLE,
    risk_appetite_score DOUBLE,
    macro_score DOUBLE,
    regime_label VARCHAR,
    confidence DOUBLE,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS market_regime_daily(
    observation_date DATE PRIMARY KEY,
    total_market_cap_usd DOUBLE,
    total_volume_usd DOUBLE,
    btc_dominance_pct DOUBLE,
    eth_dominance_pct DOUBLE,
    market_cap_30d_change_pct DOUBLE,
    volume_30d_change_pct DOUBLE,
    btc_dominance_30d_change DOUBLE,
    breadth_score DOUBLE,
    market_score DOUBLE,
    regime_label VARCHAR,
    confidence DOUBLE,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS asset_signals_daily(
    asset_id VARCHAR,
    observation_date DATE,
    price_usd DOUBLE,
    market_cap_usd DOUBLE,
    volume_24h_usd DOUBLE,
    return_7d_pct DOUBLE,
    return_30d_pct DOUBLE,
    return_90d_pct DOUBLE,
    return_365d_pct DOUBLE,
    sma_20 DOUBLE,
    sma_50 DOUBLE,
    sma_200 DOUBLE,
    price_vs_sma50_pct DOUBLE,
    price_vs_sma200_pct DOUBLE,
    rsi_14 DOUBLE,
    volatility_30d_annualized_pct DOUBLE,
    max_drawdown_365d_pct DOUBLE,
    ath_drawdown_pct DOUBLE,
    turnover_pct DOUBLE,
    volume_30d_change_pct DOUBLE,
    momentum_score DOUBLE,
    trend_score DOUBLE,
    liquidity_score DOUBLE,
    macro_score DOUBLE,
    risk_score DOUBLE,
    relative_value_score DOUBLE,
    overall_score DOUBLE,
    confidence DOUBLE,
    signal VARCHAR,
    risk_level VARCHAR,
    calculation_version VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, observation_date)
);

CREATE TABLE IF NOT EXISTS score_components(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    component_name VARCHAR,
    raw_value DOUBLE,
    normalized_score DOUBLE,
    weight DOUBLE,
    weighted_score DOUBLE,
    explanation VARCHAR,
    PRIMARY KEY(run_id, asset_id, component_name)
);

CREATE OR REPLACE VIEW latest_asset_signals AS
SELECT * EXCLUDE(rn)
FROM (
    SELECT *,
           ROW_NUMBER() OVER(
               PARTITION BY asset_id
               ORDER BY observation_date DESC, calculated_at_utc DESC
           ) rn
    FROM asset_signals_daily
) x
WHERE rn=1;

CREATE OR REPLACE VIEW latest_macro_regime AS
SELECT * FROM macro_regime_daily
ORDER BY observation_date DESC LIMIT 1;

CREATE OR REPLACE VIEW latest_market_regime AS
SELECT * FROM market_regime_daily
ORDER BY observation_date DESC LIMIT 1;
"""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def clamp(value: float | None, low: float = 0.0, high: float = 100.0) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(max(low, min(high, value)))

def linear_score(value: float | None, bad: float, good: float) -> float | None:
    if value is None or pd.isna(value):
        return None
    if good == bad:
        return 50.0
    return clamp((float(value) - bad) / (good - bad) * 100.0)

def inverse_score(value: float | None, good: float, bad: float) -> float | None:
    return linear_score(value, bad, good)

def weighted_average(items: list[tuple[float | None, float]]) -> tuple[float | None, float]:
    valid = [(score, weight) for score, weight in items if score is not None and not pd.isna(score)]
    if not valid:
        return None, 0.0
    total_weight = sum(weight for _, weight in valid)
    return (
        sum(float(score) * weight for score, weight in valid) / total_weight,
        total_weight,
    )

def pct_change(series: pd.Series, periods: int) -> float | None:
    if len(series) <= periods:
        return None
    current = series.iloc[-1]
    prior = series.iloc[-periods - 1]
    if pd.isna(current) or pd.isna(prior) or prior == 0:
        return None
    return float((current / prior - 1.0) * 100.0)

def rsi(series: pd.Series, periods: int = 14) -> float | None:
    if len(series) < periods + 1:
        return None
    delta = series.diff()
    gains = delta.clip(lower=0).rolling(periods).mean()
    losses = -delta.clip(upper=0).rolling(periods).mean()
    avg_gain = gains.iloc[-1]
    avg_loss = losses.iloc[-1]
    if pd.isna(avg_gain) or pd.isna(avg_loss):
        return None
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - 100.0 / (1.0 + rs))

def annualized_volatility(series: pd.Series, periods: int = 30) -> float | None:
    returns = series.pct_change().dropna()
    if len(returns) < periods:
        return None
    return float(returns.tail(periods).std(ddof=1) * math.sqrt(365) * 100.0)

def max_drawdown(series: pd.Series, periods: int = 365) -> float | None:
    values = series.tail(periods).dropna()
    if values.empty:
        return None
    peaks = values.cummax()
    drawdowns = values / peaks - 1.0
    return float(drawdowns.min() * 100.0)

class Module2Runner:
    def __init__(self):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE2_SCHEMA)
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        self.components: list[dict[str, Any]] = []

    def macro_series(self, series_key: str) -> pd.DataFrame:
        return self.conn.execute(
            """
            SELECT observation_date, value
            FROM macro_observations
            WHERE series_key=?
            ORDER BY observation_date
            """,
            [series_key],
        ).fetchdf()

    def latest_asof(self, frame: pd.DataFrame, date: pd.Timestamp) -> float | None:
        if frame.empty:
            return None
        work = frame.copy()
        work["observation_date"] = pd.to_datetime(work["observation_date"])
        work = work[work["observation_date"] <= date]
        if work.empty:
            return None
        return float(work.iloc[-1]["value"])

    def calculate_macro_regime(self, signal_date: pd.Timestamp) -> dict[str, Any]:
        keys = {
            "fed": "FRED::DFF", "nominal": "FRED::DGS10",
            "real": "FRED::DFII10", "breakeven": "FRED::T10YIE",
            "m2": "FRED::M2SL", "dollar": "FRED::DTWEXBGS",
            "vix": "FRED::VIXCLS", "hy": "FRED::BAMLH0A0HYM2",
            "unemployment": "FRED::UNRATE",
        }
        frames = {name: self.macro_series(key) for name, key in keys.items()}
        values = {name: self.latest_asof(frame, signal_date) for name, frame in frames.items()}

        dollar = frames["dollar"].copy()
        dollar["observation_date"] = pd.to_datetime(dollar["observation_date"])
        dollar = dollar[dollar["observation_date"] <= signal_date]
        dollar_90 = pct_change(dollar["value"], 90) if not dollar.empty else None

        m2 = frames["m2"].copy()
        m2["observation_date"] = pd.to_datetime(m2["observation_date"])
        m2 = m2[m2["observation_date"] <= signal_date]
        m2_yoy = pct_change(m2["value"], 12) if not m2.empty else None

        un = frames["unemployment"].copy()
        un["observation_date"] = pd.to_datetime(un["observation_date"])
        un = un[un["observation_date"] <= signal_date]
        un_change = None
        if len(un) >= 7:
            un_change = float(un["value"].iloc[-1] - un["value"].iloc[-7])

        liquidity_score, liquidity_weight = weighted_average([
            (linear_score(m2_yoy, -2, 10), 0.45),
            (inverse_score(values["real"], -1, 3), 0.30),
            (inverse_score(dollar_90, -8, 8), 0.25),
        ])
        risk_score, risk_weight = weighted_average([
            (inverse_score(values["vix"], 12, 40), 0.40),
            (inverse_score(values["hy"], 2.5, 8.0), 0.35),
            (inverse_score(un_change, -0.2, 1.0), 0.25),
        ])
        macro_score, used_weight = weighted_average([
            (liquidity_score, 0.55),
            (risk_score, 0.45),
        ])
        confidence = clamp(used_weight * 100)
        if macro_score is None:
            label = "UNKNOWN"
        elif macro_score >= 70:
            label = "RISK_ON"
        elif macro_score >= 55:
            label = "SUPPORTIVE"
        elif macro_score >= 40:
            label = "NEUTRAL"
        elif macro_score >= 25:
            label = "DEFENSIVE"
        else:
            label = "RISK_OFF"

        row = {
            "observation_date": signal_date.date(),
            "real_yield": values["real"],
            "nominal_yield": values["nominal"],
            "fed_funds_rate": values["fed"],
            "breakeven_inflation": values["breakeven"],
            "vix": values["vix"],
            "high_yield_spread": values["hy"],
            "dollar_index": values["dollar"],
            "dollar_90d_change_pct": dollar_90,
            "m2_yoy_pct": m2_yoy,
            "unemployment_rate": values["unemployment"],
            "unemployment_6m_change": un_change,
            "liquidity_score": liquidity_score,
            "risk_appetite_score": risk_score,
            "macro_score": macro_score,
            "regime_label": label,
            "confidence": confidence,
            "calculated_at_utc": utcnow(),
        }
        self.upsert("macro_regime_daily", pd.DataFrame([row]), ["observation_date"])
        return row


    def calculate_market_regime(self, signal_date: pd.Timestamp) -> dict[str, Any]:
        """
        Calculate a broad tracked-universe regime.

        CoinGecko's historical global market-cap chart is a paid endpoint, so
        the free platform uses the six configured assets as a transparent
        market proxy. The current global snapshot is still retained for total
        market cap, volume, and dominance context.
        """
        config = self.settings["module2"].get("market_regime", {})
        lookback = int(config.get("lookback_days", 30))
        minimum_assets = int(config.get("minimum_assets", 4))

        global_frame = self.conn.execute(
            """
            SELECT *
            FROM crypto_global_daily
            WHERE observation_date <= ?
            ORDER BY observation_date
            """,
            [signal_date.date()],
        ).fetchdf()
        global_latest = global_frame.iloc[-1] if not global_frame.empty else None

        history = self.conn.execute(
            """
            SELECT asset_id, observation_date, market_cap_usd, volume_24h_usd,
                   price_usd
            FROM asset_market_daily
            WHERE source='coingecko'
              AND observation_date <= ?
            ORDER BY asset_id, observation_date
            """,
            [signal_date.date()],
        ).fetchdf()

        tracked_cap_change = None
        tracked_volume_change = None
        breadth_pct = None
        btc_return = None
        alt_return = None
        available_assets = 0

        if not history.empty:
            history["observation_date"] = pd.to_datetime(history["observation_date"])
            current_rows = []
            prior_rows = []
            return_rows = []

            for asset_id, group in history.groupby("asset_id"):
                group = group.sort_values("observation_date")
                current = group[group["observation_date"] <= signal_date]
                if current.empty:
                    continue
                latest = current.iloc[-1]
                target_date = latest["observation_date"] - pd.Timedelta(days=lookback)
                prior_candidates = current[current["observation_date"] <= target_date]
                if prior_candidates.empty:
                    continue
                prior = prior_candidates.iloc[-1]

                if (
                    pd.notna(latest["market_cap_usd"])
                    and pd.notna(prior["market_cap_usd"])
                    and prior["market_cap_usd"] > 0
                ):
                    current_rows.append(float(latest["market_cap_usd"]))
                    prior_rows.append(float(prior["market_cap_usd"]))

                if (
                    pd.notna(latest["price_usd"])
                    and pd.notna(prior["price_usd"])
                    and prior["price_usd"] > 0
                ):
                    asset_return = (
                        float(latest["price_usd"]) / float(prior["price_usd"]) - 1
                    ) * 100
                    return_rows.append((asset_id, asset_return))

            available_assets = len(return_rows)
            if current_rows and prior_rows and sum(prior_rows) > 0:
                tracked_cap_change = (
                    sum(current_rows) / sum(prior_rows) - 1
                ) * 100

            # Use aggregate daily volume at the endpoints. Volume is noisy,
            # so it receives less weight than capitalization and breadth.
            current_date = history["observation_date"].max()
            prior_date = current_date - pd.Timedelta(days=lookback)
            current_volume = history[
                history["observation_date"] == current_date
            ]["volume_24h_usd"].sum(min_count=1)
            prior_candidates = history[history["observation_date"] <= prior_date]
            if not prior_candidates.empty:
                prior_actual_date = prior_candidates["observation_date"].max()
                prior_volume = prior_candidates[
                    prior_candidates["observation_date"] == prior_actual_date
                ]["volume_24h_usd"].sum(min_count=1)
                if (
                    pd.notna(current_volume) and pd.notna(prior_volume)
                    and prior_volume > 0
                ):
                    tracked_volume_change = (
                        float(current_volume) / float(prior_volume) - 1
                    ) * 100

            if return_rows:
                breadth_pct = (
                    sum(value > 0 for _, value in return_rows)
                    / len(return_rows) * 100
                )
                btc_values = [value for asset, value in return_rows if asset == "bitcoin"]
                alt_values = [value for asset, value in return_rows if asset != "bitcoin"]
                btc_return = btc_values[0] if btc_values else None
                alt_return = (
                    sum(alt_values) / len(alt_values) if alt_values else None
                )

        cap_score = linear_score(tracked_cap_change, -25, 25)
        volume_score = linear_score(tracked_volume_change, -50, 75)
        breadth_component = linear_score(breadth_pct, 0, 100)
        relative_breadth = None
        if btc_return is not None and alt_return is not None:
            relative_breadth = linear_score(alt_return - btc_return, -20, 20)

        market_score, used_weight = weighted_average([
            (cap_score, 0.45),
            (breadth_component, 0.30),
            (volume_score, 0.15),
            (relative_breadth, 0.10),
        ])

        data_coverage = min(1.0, available_assets / max(minimum_assets, 1))
        confidence = clamp(used_weight * data_coverage * 100)

        if market_score is None or available_assets < minimum_assets:
            label = "UNKNOWN"
        elif market_score >= 70:
            label = "EXPANSION"
        elif market_score >= 55:
            label = "POSITIVE"
        elif market_score >= 40:
            label = "NEUTRAL"
        elif market_score >= 25:
            label = "CONTRACTION"
        else:
            label = "STRESS"

        row = {
            "observation_date": signal_date.date(),
            "total_market_cap_usd": (
                global_latest["total_market_cap_usd"]
                if global_latest is not None else None
            ),
            "total_volume_usd": (
                global_latest["total_volume_usd"]
                if global_latest is not None else None
            ),
            "btc_dominance_pct": (
                global_latest["btc_dominance_pct"]
                if global_latest is not None else None
            ),
            "eth_dominance_pct": (
                global_latest["eth_dominance_pct"]
                if global_latest is not None else None
            ),
            "market_cap_30d_change_pct": tracked_cap_change,
            "volume_30d_change_pct": tracked_volume_change,
            "btc_dominance_30d_change": (
                alt_return - btc_return
                if alt_return is not None and btc_return is not None
                else None
            ),
            "breadth_score": breadth_pct,
            "market_score": market_score,
            "regime_label": label,
            "confidence": confidence,
            "calculated_at_utc": utcnow(),
        }
        self.upsert("market_regime_daily", pd.DataFrame([row]), ["observation_date"])
        return row

    def asset_history(self, asset_id: str) -> pd.DataFrame:
        return self.conn.execute(
            """
            SELECT observation_date, price_usd, market_cap_usd, volume_24h_usd,
                   ath_change_pct
            FROM asset_market_daily
            WHERE asset_id=? AND source='coingecko'
            ORDER BY observation_date
            """,
            [asset_id],
        ).fetchdf()

    def add_component(
        self, asset_id: str, date, name: str, raw: float | None,
        score: float | None, weight: float, explanation: str
    ) -> None:
        self.components.append({
            "run_id": self.run_id, "asset_id": asset_id,
            "observation_date": date, "component_name": name,
            "raw_value": raw, "normalized_score": score, "weight": weight,
            "weighted_score": None if score is None else score * weight,
            "explanation": explanation,
        })

    def score_asset(
        self,
        asset: dict[str, Any],
        macro: dict[str, Any],
        market: dict[str, Any],
    ) -> dict[str, Any] | None:
        frame = self.asset_history(asset["asset_id"])
        minimum = int(self.settings["module2"]["minimum_history_days"])
        if len(frame) < minimum:
            return None
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        frame = frame.dropna(subset=["price_usd"]).sort_values("observation_date")
        price = frame["price_usd"].astype(float)
        latest = frame.iloc[-1]
        date = latest["observation_date"].date()

        returns = {
            7: pct_change(price, 7), 30: pct_change(price, 30),
            90: pct_change(price, 90), 365: pct_change(price, 365),
        }
        sma20 = float(price.tail(20).mean()) if len(price) >= 20 else None
        sma50 = float(price.tail(50).mean()) if len(price) >= 50 else None
        sma200 = float(price.tail(200).mean()) if len(price) >= 200 else None
        vs50 = (latest["price_usd"] / sma50 - 1) * 100 if sma50 else None
        vs200 = (latest["price_usd"] / sma200 - 1) * 100 if sma200 else None
        rsi14 = rsi(price)
        vol30 = annualized_volatility(price)
        drawdown365 = max_drawdown(price)
        ath_drawdown = float(latest["ath_change_pct"]) if pd.notna(latest["ath_change_pct"]) else None
        turnover = None
        if pd.notna(latest["market_cap_usd"]) and latest["market_cap_usd"]:
            turnover = float(latest["volume_24h_usd"] / latest["market_cap_usd"] * 100)
        volume_change = pct_change(frame["volume_24h_usd"].astype(float), 30)

        momentum_score, _ = weighted_average([
            (linear_score(returns[30], -25, 35), 0.35),
            (linear_score(returns[90], -40, 70), 0.40),
            (linear_score(returns[365], -65, 150), 0.25),
        ])
        trend_score, _ = weighted_average([
            (linear_score(vs50, -20, 20), 0.40),
            (linear_score(vs200, -40, 40), 0.45),
            (inverse_score(abs((rsi14 or 50) - 55), 0, 45), 0.15),
        ])
        liquidity_score, _ = weighted_average([
            (linear_score(math.log10(max(float(latest["market_cap_usd"] or 1), 1)), 8, 12.5), 0.60),
            (linear_score(turnover, 0.2, 8.0), 0.25),
            (linear_score(volume_change, -50, 80), 0.15),
        ])
        risk_score, _ = weighted_average([
            (inverse_score(vol30, 35, 160), 0.55),
            (inverse_score(abs(drawdown365 or 0), 10, 80), 0.45),
        ])
        relative_value_score, _ = weighted_average([
            (linear_score(abs(ath_drawdown or 0), 10, 85), 0.60),
            (inverse_score(rsi14, 35, 80), 0.40),
        ])
        macro_score = macro.get("macro_score")

        weights = self.settings["module2"]["weights"]
        component_map = {
            "momentum": momentum_score, "trend": trend_score,
            "liquidity": liquidity_score, "macro": macro_score,
            "risk": risk_score, "relative_value": relative_value_score,
        }
        overall, used_weight = weighted_average([
            (component_map[name], float(weights[name])) for name in weights
        ])
        completeness = (
            sum(v is not None for v in component_map.values())
            / len(component_map)
        )
        confidence_config = self.settings["module2"].get("confidence", {})
        freshness_days = (
            pd.Timestamp.now(tz="UTC").normalize()
            - pd.Timestamp(latest["observation_date"], tz="UTC")
        ).days
        stale_days = int(confidence_config.get("stale_market_days", 3))
        freshness_factor = (
            1.0 if freshness_days <= stale_days
            else max(0.0, 1 - (freshness_days - stale_days) / 10)
        )

        full_history_days = int(
            confidence_config.get("full_history_days", 730)
        )
        history_factor = min(1.0, len(frame) / max(full_history_days, 1))

        market_cap_floor = float(
            confidence_config.get("liquidity_market_cap_floor", 100_000_000)
        )
        market_cap_full = float(
            confidence_config.get("liquidity_market_cap_full", 100_000_000_000)
        )
        current_market_cap = float(latest["market_cap_usd"] or 0)
        if current_market_cap <= market_cap_floor:
            liquidity_factor = 0.45
        elif current_market_cap >= market_cap_full:
            liquidity_factor = 1.0
        else:
            liquidity_factor = 0.45 + 0.55 * (
                math.log10(current_market_cap)
                - math.log10(market_cap_floor)
            ) / (
                math.log10(market_cap_full)
                - math.log10(market_cap_floor)
            )

        agreement = self.conn.execute(
            """
            SELECT AVG(deviation_pct)
            FROM asset_price_crosscheck
            WHERE asset_id=?
              AND observation_date >= ? - INTERVAL 7 DAY
            """,
            [asset["asset_id"], date],
        ).fetchone()[0]
        good_dev = float(
            confidence_config.get("provider_agreement_good_pct", 1.0)
        )
        bad_dev = float(
            confidence_config.get("provider_agreement_bad_pct", 7.5)
        )
        if agreement is None:
            agreement_factor = 0.75
        elif agreement <= good_dev:
            agreement_factor = 1.0
        elif agreement >= bad_dev:
            agreement_factor = 0.45
        else:
            agreement_factor = 1.0 - 0.55 * (
                float(agreement) - good_dev
            ) / (bad_dev - good_dev)

        macro_factor = float(macro.get("confidence") or 0) / 100
        market_factor = float(market.get("confidence") or 0) / 100

        base_confidence = weighted_average([
            (completeness * 100, 0.20),
            (freshness_factor * 100, 0.12),
            (history_factor * 100, 0.12),
            (liquidity_factor * 100, 0.14),
            (agreement_factor * 100, 0.14),
            (macro_factor * 100, 0.07),
            (market_factor * 100, 0.07),
        ])[0] or 0.0

        # Penalize disagreement among otherwise complete model components.
        valid_component_scores = [
            float(value) for value in component_map.values()
            if value is not None and not pd.isna(value)
        ]
        component_dispersion = (
            float(np.std(valid_component_scores, ddof=0))
            if len(valid_component_scores) >= 2 else 25.0
        )
        agreement_inside_model = clamp(
            100.0 - component_dispersion * 1.7, 45.0, 100.0
        )

        # A score close to a signal boundary is less certain than one centered
        # within a band, even when the underlying data is complete.
        threshold_values = sorted(
            float(value)
            for value in self.settings["module2"]["signal_thresholds"].values()
        )
        boundary_distance = (
            min(abs(float(overall) - value) for value in threshold_values)
            if overall is not None else 0.0
        )
        signal_margin_factor = clamp(
            55.0 + min(boundary_distance, 12.0) / 12.0 * 40.0,
            55.0, 95.0,
        )

        confidence = clamp(
            base_confidence * 0.72
            + agreement_inside_model * 0.16
            + signal_margin_factor * 0.12,
            35.0,
            95.0,
        )

        thresholds = self.settings["module2"]["signal_thresholds"]
        if overall is None:
            signal = "INSUFFICIENT_DATA"
        elif overall >= thresholds["strong_buy"]:
            signal = "STRONG_BUY"
        elif overall >= thresholds["buy"]:
            signal = "BUY"
        elif overall >= thresholds["hold"]:
            signal = "HOLD"
        elif overall >= thresholds["reduce"]:
            signal = "REDUCE"
        else:
            signal = "AVOID"

        if vol30 is None:
            risk_level = "UNKNOWN"
        elif vol30 < 55:
            risk_level = "MODERATE"
        elif vol30 < 90:
            risk_level = "HIGH"
        else:
            risk_level = "VERY_HIGH"

        explanations = {
            "momentum": "Composite of 30-, 90-, and 365-day total returns.",
            "trend": "Price position versus 50/200-day averages with RSI balance.",
            "liquidity": "Market capitalization, turnover, and recent volume change.",
            "macro": f"Current macro regime: {macro.get('regime_label', 'UNKNOWN')}.",
            "risk": "Inverse score from annualized volatility and trailing drawdown.",
            "relative_value": "Drawdown and RSI-based opportunity measure; not intrinsic valuation.",
        }
        raw_map = {
            "momentum": returns[90], "trend": vs200, "liquidity": turnover,
            "macro": macro_score, "risk": vol30,
            "relative_value": ath_drawdown,
        }
        for name, score in component_map.items():
            self.add_component(
                asset["asset_id"], date, name, raw_map[name], score,
                float(weights[name]), explanations[name],
            )

        return {
            "asset_id": asset["asset_id"], "observation_date": date,
            "price_usd": latest["price_usd"],
            "market_cap_usd": latest["market_cap_usd"],
            "volume_24h_usd": latest["volume_24h_usd"],
            "return_7d_pct": returns[7], "return_30d_pct": returns[30],
            "return_90d_pct": returns[90], "return_365d_pct": returns[365],
            "sma_20": sma20, "sma_50": sma50, "sma_200": sma200,
            "price_vs_sma50_pct": vs50, "price_vs_sma200_pct": vs200,
            "rsi_14": rsi14, "volatility_30d_annualized_pct": vol30,
            "max_drawdown_365d_pct": drawdown365,
            "ath_drawdown_pct": ath_drawdown, "turnover_pct": turnover,
            "volume_30d_change_pct": volume_change,
            "momentum_score": momentum_score, "trend_score": trend_score,
            "liquidity_score": liquidity_score, "macro_score": macro_score,
            "risk_score": risk_score,
            "relative_value_score": relative_value_score,
            "overall_score": overall, "confidence": confidence,
            "signal": signal, "risk_level": risk_level,
            "calculation_version": "2.7.0",
            "calculated_at_utc": utcnow(),
        }

    def upsert(self, table: str, frame: pd.DataFrame, keys: list[str]) -> tuple[int, int]:
        if frame.empty:
            return 0, 0
        self.conn.register("_m2_stage", frame)
        condition = " AND ".join(f"t.{k}=s.{k}" for k in keys)
        updated = int(self.conn.execute(
            f"SELECT COUNT(*) FROM {table} t JOIN _m2_stage s ON {condition}"
        ).fetchone()[0])
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m2_stage"
        )
        self.conn.unregister("_m2_stage")
        return len(frame) - updated, updated

    def run(self) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO module2_runs
            (run_id,started_at_utc,status,assets_scored,assets_skipped,
             platform_version)
            VALUES (?,?,'RUNNING',0,0,'4.0.0')
            """,
            [self.run_id, self.started],
        )
        latest_date = self.conn.execute(
            "SELECT MAX(observation_date) FROM asset_market_daily"
        ).fetchone()[0]
        if latest_date is None:
            raise RuntimeError("Module 1 market data is empty. Run Module 1 first.")
        signal_date = pd.Timestamp(latest_date)
        macro = self.calculate_macro_regime(signal_date)
        market = self.calculate_market_regime(signal_date)

        rows = []
        skipped = 0
        for asset in self.assets:
            row = self.score_asset(asset, macro, market)
            if row is None:
                skipped += 1
            else:
                rows.append(row)
        if rows:
            self.upsert(
                "asset_signals_daily", pd.DataFrame(rows),
                ["asset_id", "observation_date"],
            )
        if self.components:
            self.upsert(
                "score_components", pd.DataFrame(self.components),
                ["run_id", "asset_id", "component_name"],
            )

        status = "SUCCESS" if rows else "FAILED"
        notes = (
            f"{len(rows)} assets scored; {skipped} skipped; "
            f"macro={macro.get('regime_label')}; "
            f"market={market.get('regime_label')}"
        )
        self.conn.execute(
            """
            UPDATE module2_runs
            SET completed_at_utc=?, status=?, assets_scored=?,
                assets_skipped=?, signal_date=?, notes=?
            WHERE run_id=?
            """,
            [utcnow(), status, len(rows), skipped, signal_date.date(),
             notes, self.run_id],
        )
        self.conn.close()
        return {
            "run_id": self.run_id, "status": status,
            "assets_scored": len(rows), "assets_skipped": skipped,
            "signal_date": str(signal_date.date()),
            "macro_regime": macro.get("regime_label"),
            "market_regime": market.get("regime_label"),
        }

def run_module2() -> dict[str, Any]:
    return Module2Runner().run()
