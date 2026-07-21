from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA, clamp
from crypto_platform.module3 import MODULE3_SCHEMA

MODULE5_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module5_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    signal_date DATE,
    assets_analyzed INTEGER,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS multi_horizon_returns(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    cagr_1y_pct DOUBLE,
    cagr_3y_pct DOUBLE,
    cagr_5y_pct DOUBLE,
    cagr_since_inception_pct DOUBLE,
    blended_cagr_pct DOUBLE,
    available_weight DOUBLE,
    history_days INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS cycle_analytics(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    days_since_ath INTEGER,
    ath_drawdown_pct DOUBLE,
    drawdown_percentile DOUBLE,
    price_percentile_3y DOUBLE,
    momentum_percentile DOUBLE,
    volatility_percentile DOUBLE,
    macd DOUBLE,
    macd_signal DOUBLE,
    macd_histogram DOUBLE,
    adx_14 DOUBLE,
    cycle_phase VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS expected_returns(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    blended_cagr_pct DOUBLE,
    valuation_score DOUBLE,
    momentum_score DOUBLE,
    trend_quality_score DOUBLE,
    macro_score DOUBLE,
    market_regime_score DOUBLE,
    expected_return_1y_pct DOUBLE,
    confidence DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS optimized_allocations(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    pre_risk_weight DOUBLE,
    post_risk_weight DOUBLE,
    risk_contribution_pct DOUBLE,
    risk_budget_pct DOUBLE,
    adjustment DOUBLE,
    status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE OR REPLACE VIEW latest_multi_horizon_returns AS
SELECT x.*
FROM multi_horizon_returns x
JOIN (
    SELECT run_id FROM module5_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_cycle_analytics AS
SELECT x.*
FROM cycle_analytics x
JOIN (
    SELECT run_id FROM module5_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_expected_returns AS
SELECT x.*
FROM expected_returns x
JOIN (
    SELECT run_id FROM module5_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_optimized_allocations AS
SELECT x.*
FROM optimized_allocations x
JOIN (
    SELECT run_id FROM module5_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);
"""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def cagr_from_window(series: pd.Series, years: float | None = None) -> float | None:
    clean = series.dropna()
    if len(clean) < 2:
        return None
    start = float(clean.iloc[0])
    end = float(clean.iloc[-1])
    if start <= 0 or end <= 0:
        return None
    if years is None:
        days = max((clean.index[-1] - clean.index[0]).days, 1)
        years = days / 365.25
    if years <= 0:
        return None
    return float((end / start) ** (1 / years) - 1) * 100

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float | None:
    if len(close) < period * 2 + 2:
        return None
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    plus_di = 100 * plus_dm.rolling(period).mean() / atr
    minus_di = 100 * minus_dm.rolling(period).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(period).mean().iloc[-1]
    return None if pd.isna(adx) else float(adx)

def percentile_rank(history: pd.Series, value: float) -> float | None:
    clean = history.dropna()
    if clean.empty:
        return None
    return float((clean <= value).mean() * 100)

class Module5Runner:
    def __init__(self):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE2_SCHEMA)
        self.conn.execute(MODULE3_SCHEMA)
        self.conn.execute(MODULE5_SCHEMA)
        self.config = self.settings["module5"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table: str, frame: pd.DataFrame, keys: list[str]) -> None:
        if frame.empty:
            return
        self.conn.register("_m5_stage", frame)
        cols = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _m5_stage"
        )
        self.conn.unregister("_m5_stage")

    def prices(self) -> pd.DataFrame:
        tables = {
            row[0] for row in self.conn.execute("SHOW TABLES").fetchall()
        }
        source_table = (
            "canonical_market_daily"
            if "canonical_market_daily" in tables
            and self.conn.execute(
                "SELECT COUNT(*) FROM canonical_market_daily"
            ).fetchone()[0] > 0
            else "asset_market_daily"
        )
        where = "" if source_table == "canonical_market_daily" else "WHERE source='coingecko'"
        frame = self.conn.execute(
            f"""
            SELECT asset_id, observation_date, price_usd
            FROM {source_table}
            {where}
            ORDER BY observation_date, asset_id
            """
        ).fetchdf()
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame.pivot_table(
            index="observation_date",
            columns="asset_id",
            values="price_usd",
            aggfunc="last"
        ).sort_index()

    def ohlc(self, asset_id: str) -> pd.DataFrame:
        frame = self.conn.execute(
            """
            SELECT open_time_utc, open, high, low, close
            FROM asset_ohlcv
            WHERE asset_id=? AND interval='1d'
            ORDER BY open_time_utc
            """,
            [asset_id],
        ).fetchdf()
        if not frame.empty:
            frame["open_time_utc"] = pd.to_datetime(frame["open_time_utc"])
            frame = frame.set_index("open_time_utc")
        return frame

    def calculate_returns(self, prices: pd.DataFrame, signal_date) -> pd.DataFrame:
        weights = self.config["return_blend"]["weights"]
        mins = self.config["return_blend"]["min_observations"]
        rows = []
        for asset_id in prices.columns:
            series = prices[asset_id].dropna()
            if len(series) < 2:
                continue
            values = {}
            windows = {
                "cagr_1y": (365, 1.0),
                "cagr_3y": (1095, 3.0),
                "cagr_5y": (1826, 5.0),
            }
            for name, (days, years) in windows.items():
                subset = series[series.index >= series.index.max() - pd.Timedelta(days=days)]
                values[name] = (
                    cagr_from_window(subset, years)
                    if len(subset) >= int(mins[name]) else None
                )
            values["cagr_since_inception"] = (
                cagr_from_window(series, None)
                if len(series) >= int(mins["cagr_since_inception"]) else None
            )
            valid = [
                (values[name], float(weight))
                for name, weight in weights.items()
                if values.get(name) is not None
            ]
            available_weight = sum(weight for _, weight in valid)
            blended = (
                sum(value * weight for value, weight in valid) / available_weight
                if available_weight > 0 else None
            )
            rows.append({
                "run_id": self.run_id,
                "asset_id": asset_id,
                "observation_date": signal_date,
                "cagr_1y_pct": values["cagr_1y"],
                "cagr_3y_pct": values["cagr_3y"],
                "cagr_5y_pct": values["cagr_5y"],
                "cagr_since_inception_pct": values["cagr_since_inception"],
                "blended_cagr_pct": blended,
                "available_weight": available_weight,
                "history_days": int((series.index.max() - series.index.min()).days),
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert("multi_horizon_returns", frame, ["run_id", "asset_id"])
        return frame

    def calculate_cycle(self, prices: pd.DataFrame, signals: pd.DataFrame, signal_date) -> pd.DataFrame:
        cycle_cfg = self.config["cycle"]
        rows = []
        for asset_id in prices.columns:
            series = prices[asset_id].dropna()
            if len(series) < 50:
                continue
            current = float(series.iloc[-1])
            ath = float(series.max())
            ath_date = series.idxmax()
            drawdown = (current / ath - 1) * 100
            rolling_ath = series.cummax()
            drawdowns = (series / rolling_ath - 1) * 100
            drawdown_pctile = percentile_rank(drawdowns, drawdown)
            three_year = series[series.index >= series.index.max() - pd.Timedelta(days=1095)]
            price_pctile = percentile_rank(three_year, current)

            momentum_hist = series.pct_change(90).dropna() * 100
            momentum_current = float(momentum_hist.iloc[-1]) if not momentum_hist.empty else np.nan
            momentum_pctile = percentile_rank(momentum_hist, momentum_current) if not pd.isna(momentum_current) else None
            vol_hist = series.pct_change().rolling(30).std() * math.sqrt(365) * 100
            vol_current = float(vol_hist.iloc[-1]) if not pd.isna(vol_hist.iloc[-1]) else np.nan
            vol_pctile = percentile_rank(vol_hist, vol_current) if not pd.isna(vol_current) else None

            macd_line = ema(series, 12) - ema(series, 26)
            signal_line = ema(macd_line, 9)
            macd = float(macd_line.iloc[-1])
            macd_signal = float(signal_line.iloc[-1])
            macd_hist = macd - macd_signal

            ohlc = self.ohlc(asset_id)
            adx = calculate_adx(
                ohlc["high"], ohlc["low"], ohlc["close"]
            ) if not ohlc.empty else None

            signal_row = signals[signals["asset_id"] == asset_id].iloc[0]
            rsi = float(signal_row["rsi_14"])
            vs200 = float(signal_row["price_vs_sma200_pct"])

            if drawdown <= float(cycle_cfg["ath_drawdown_capitulation_pct"]):
                phase = "CAPITULATION"
            elif drawdown <= float(cycle_cfg["ath_drawdown_accumulation_pct"]):
                phase = "ACCUMULATION"
            elif rsi >= float(cycle_cfg["overextended_rsi"]) and vs200 > float(cycle_cfg["expansion_sma200_pct"]):
                phase = "EUPHORIA"
            elif vs200 >= float(cycle_cfg["expansion_sma200_pct"]) and macd_hist > 0:
                phase = "EXPANSION"
            elif vs200 <= float(cycle_cfg["contraction_sma200_pct"]) and macd_hist < 0:
                phase = "CONTRACTION"
            elif macd_hist > 0:
                phase = "RECOVERY"
            else:
                phase = "DISTRIBUTION"

            rows.append({
                "run_id": self.run_id,
                "asset_id": asset_id,
                "observation_date": signal_date,
                "days_since_ath": int((series.index.max() - ath_date).days),
                "ath_drawdown_pct": drawdown,
                "drawdown_percentile": drawdown_pctile,
                "price_percentile_3y": price_pctile,
                "momentum_percentile": momentum_pctile,
                "volatility_percentile": vol_pctile,
                "macd": macd,
                "macd_signal": macd_signal,
                "macd_histogram": macd_hist,
                "adx_14": adx,
                "cycle_phase": phase,
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert("cycle_analytics", frame, ["run_id", "asset_id"])
        return frame

    def expected_return_rows(
        self,
        returns_frame: pd.DataFrame,
        cycle_frame: pd.DataFrame,
        signals: pd.DataFrame,
        valuations: pd.DataFrame,
        market_score: float,
        signal_date,
    ) -> pd.DataFrame:
        cfg = self.config["expected_return"]
        weights = cfg["weights"]
        merged = (
            signals
            .merge(returns_frame[["asset_id", "blended_cagr_pct", "available_weight"]], on="asset_id", how="left")
            .merge(cycle_frame[["asset_id", "momentum_percentile", "adx_14", "macd_histogram"]], on="asset_id", how="left")
            .merge(valuations[["asset_id", "upside_to_fair_value_pct"]], on="asset_id", how="left")
        )
        rows = []
        for _, row in merged.iterrows():
            blended = float(row["blended_cagr_pct"] or 0)
            valuation_score = clamp(50 + float(row["upside_to_fair_value_pct"] or 0) * 2.0)
            momentum_score = float(row["momentum_percentile"] or 50)
            adx = float(row["adx_14"] or 20)
            macd_positive = 1 if float(row["macd_histogram"] or 0) > 0 else -1
            trend_quality = clamp(
                50 + macd_positive * min(adx, 50) * 0.8
            )
            macro_score = float(row["macro_score"] or 50)
            market_regime_score = float(market_score or 50)

            expected = (
                blended * float(weights["multi_horizon_return"])
                + (valuation_score - 50) * 1.1 * float(weights["valuation"])
                + (momentum_score - 50) * 0.8 * float(weights["momentum"])
                + (trend_quality - 50) * 0.8 * float(weights["trend_quality"])
                + (macro_score - 50) * 0.6 * float(weights["macro"])
                + (market_regime_score - 50) * 0.6 * float(weights["market_regime"])
            ) / max(sum(float(v) for v in weights.values()), 1e-9)
            expected = max(
                float(cfg["annual_return_floor_pct"]),
                min(float(cfg["annual_return_cap_pct"]), expected),
            )
            confidence = clamp(
                55
                + float(row["available_weight"] or 0) * 25
                + float(row["confidence"] or 0) * 0.15
            , 40, 95)

            rows.append({
                "run_id": self.run_id,
                "asset_id": row["asset_id"],
                "observation_date": signal_date,
                "blended_cagr_pct": blended,
                "valuation_score": valuation_score,
                "momentum_score": momentum_score,
                "trend_quality_score": trend_quality,
                "macro_score": macro_score,
                "market_regime_score": market_regime_score,
                "expected_return_1y_pct": expected,
                "confidence": confidence,
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert("expected_returns", frame, ["run_id", "asset_id"])
        return frame

    def optimize_risk_budget(
        self,
        prices: pd.DataFrame,
        recommendations: pd.DataFrame,
        signal_date,
    ) -> pd.DataFrame:
        cfg = self.config["risk_budget"]
        weights = recommendations.set_index("asset_id")["target_weight"].copy()
        returns = prices.pct_change(fill_method=None).dropna(how="all")
        common = [asset for asset in returns.columns if asset in weights.index]
        covariance = returns[common].cov() * 365
        w = weights.reindex(common).fillna(0).astype(float)
        budget = float(
            self.settings["module4"]["rebalance"]["maximum_position_risk_contribution_pct"]
        )
        tolerance = float(cfg["tolerance_pct"])
        initial = w.copy()

        def contributions(vector: pd.Series) -> pd.Series:
            arr = vector.to_numpy()
            var = float(arr.T @ covariance.to_numpy() @ arr)
            if var <= 0:
                return pd.Series(0.0, index=vector.index)
            marginal = covariance.to_numpy() @ arr
            return pd.Series(arr * marginal / var * 100, index=vector.index)

        if bool(cfg["enforce"]):
            for _ in range(int(cfg["max_iterations"])):
                rc = contributions(w)
                over = rc[rc > budget + tolerance]
                if over.empty:
                    break
                for asset_id, risk_pct in over.items():
                    reduction_factor = max(0.50, budget / risk_pct)
                    w.loc[asset_id] *= reduction_factor
                removed = max(0.0, initial.sum() - w.sum())
                eligible = rc[rc <= budget + tolerance].index
                if len(eligible) and removed > 0:
                    base = w.loc[eligible]
                    if base.sum() > 0:
                        w.loc[eligible] += removed * base / base.sum()
                if w.sum() > initial.sum() and w.sum() > 0:
                    w *= initial.sum() / w.sum()

        final_rc = contributions(w)
        rows = []
        for asset_id in common:
            rows.append({
                "run_id": self.run_id,
                "asset_id": asset_id,
                "observation_date": signal_date,
                "pre_risk_weight": float(initial.loc[asset_id]),
                "post_risk_weight": float(w.loc[asset_id]),
                "risk_contribution_pct": float(final_rc.loc[asset_id]),
                "risk_budget_pct": budget,
                "adjustment": float(w.loc[asset_id] - initial.loc[asset_id]),
                "status": (
                    "WITHIN_BUDGET"
                    if final_rc.loc[asset_id] <= budget + tolerance
                    else "OVER_BUDGET"
                ),
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert("optimized_allocations", frame, ["run_id", "asset_id"])
        return frame

    def run(self) -> dict[str, Any]:
        signals = self.conn.execute("SELECT * FROM latest_asset_signals").fetchdf()
        valuations = self.conn.execute("SELECT * FROM latest_valuation_zones").fetchdf()
        recommendations = self.conn.execute("SELECT * FROM latest_portfolio_recommendations").fetchdf()
        market = self.conn.execute("SELECT * FROM latest_market_regime").fetchdf()
        if signals.empty or valuations.empty or recommendations.empty:
            raise RuntimeError("Run Modules 2 and 3 before Module 5.")

        signal_date = signals["observation_date"].max()
        self.conn.execute(
            """
            INSERT INTO module5_runs(
                run_id,started_at_utc,status,signal_date,assets_analyzed,
                notes,platform_version
            ) VALUES (?,?,'RUNNING',?,0,NULL,'4.0.0')
            """,
            [self.run_id, self.started, signal_date],
        )

        prices = self.prices()
        returns_frame = self.calculate_returns(prices, signal_date)
        cycle_frame = self.calculate_cycle(prices, signals, signal_date)
        market_score = float(market.iloc[0]["market_score"]) if not market.empty else 50.0
        expected = self.expected_return_rows(
            returns_frame, cycle_frame, signals, valuations,
            market_score, signal_date
        )
        optimized = self.optimize_risk_budget(
            prices, recommendations, signal_date
        )

        notes = (
            f"{len(expected)} assets analyzed; "
            f"{len(cycle_frame)} cycle rows; "
            f"{len(optimized)} optimized allocations."
        )
        self.conn.execute(
            """
            UPDATE module5_runs
            SET completed_at_utc=?,status='SUCCESS',assets_analyzed=?,notes=?
            WHERE run_id=?
            """,
            [utcnow(), len(expected), notes, self.run_id],
        )
        self.conn.close()
        return {
            "run_id": self.run_id,
            "status": "SUCCESS",
            "signal_date": str(signal_date),
            "assets_analyzed": len(expected),
        }

def run_module5() -> dict[str, Any]:
    return Module5Runner().run()
