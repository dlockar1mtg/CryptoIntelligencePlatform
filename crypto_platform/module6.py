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
from crypto_platform.module5 import MODULE5_SCHEMA

MODULE6_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module6_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    phase VARCHAR,
    canonical_rows BIGINT,
    snapshots_created BIGINT,
    validations_created BIGINT,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS canonical_market_daily(
    asset_id VARCHAR,
    observation_date DATE,
    price_usd DOUBLE,
    market_cap_usd DOUBLE,
    volume_24h_usd DOUBLE,
    price_source VARCHAR,
    market_cap_source VARCHAR,
    volume_source VARCHAR,
    source_priority INTEGER,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, observation_date)
);

CREATE TABLE IF NOT EXISTS model_snapshots_daily(
    asset_id VARCHAR,
    observation_date DATE,
    price_usd DOUBLE,
    return_30d_pct DOUBLE,
    return_90d_pct DOUBLE,
    return_365d_pct DOUBLE,
    sma_50 DOUBLE,
    sma_200 DOUBLE,
    price_vs_sma50_pct DOUBLE,
    price_vs_sma200_pct DOUBLE,
    rsi_14 DOUBLE,
    volatility_30d_pct DOUBLE,
    max_drawdown_365d_pct DOUBLE,
    momentum_score DOUBLE,
    trend_score DOUBLE,
    risk_score DOUBLE,
    historical_overall_score DOUBLE,
    historical_signal VARCHAR,
    cycle_phase VARCHAR,
    valuation_label VARCHAR,
    expected_return_proxy_pct DOUBLE,
    calculation_version VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, observation_date)
);

CREATE TABLE IF NOT EXISTS signal_forward_performance(
    asset_id VARCHAR,
    signal_date DATE,
    historical_signal VARCHAR,
    historical_score DOUBLE,
    horizon_days INTEGER,
    target_date DATE,
    actual_target_date DATE,
    signal_price_usd DOUBLE,
    future_price_usd DOUBLE,
    forward_return_pct DOUBLE,
    benchmark_btc_return_pct DOUBLE,
    excess_vs_btc_pct DOUBLE,
    positive_return BOOLEAN,
    outperformed_btc BOOLEAN,
    completed BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, signal_date, horizon_days)
);

CREATE TABLE IF NOT EXISTS signal_validation_summary(
    historical_signal VARCHAR,
    horizon_days INTEGER,
    sample_count INTEGER,
    positive_rate_pct DOUBLE,
    average_forward_return_pct DOUBLE,
    median_forward_return_pct DOUBLE,
    average_excess_vs_btc_pct DOUBLE,
    btc_outperformance_rate_pct DOUBLE,
    last_updated_utc TIMESTAMPTZ,
    PRIMARY KEY(historical_signal, horizon_days)
);

CREATE TABLE IF NOT EXISTS cycle_transition_history(
    asset_id VARCHAR,
    transition_date DATE,
    previous_phase VARCHAR,
    new_phase VARCHAR,
    price_usd DOUBLE,
    score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, transition_date, new_phase)
);

CREATE OR REPLACE VIEW canonical_history_coverage AS
SELECT asset_id,
       MIN(observation_date) AS first_date,
       MAX(observation_date) AS latest_date,
       COUNT(*) AS row_count,
       SUM(CASE WHEN price_source='coingecko' THEN 1 ELSE 0 END) AS coingecko_rows,
       SUM(CASE WHEN price_source<>'coingecko' THEN 1 ELSE 0 END) AS exchange_fallback_rows,
       SUM(CASE WHEN market_cap_usd IS NOT NULL THEN 1 ELSE 0 END) AS market_cap_rows
FROM canonical_market_daily
GROUP BY asset_id;

CREATE OR REPLACE VIEW latest_model_snapshots AS
SELECT * EXCLUDE(rn)
FROM (
    SELECT *, ROW_NUMBER() OVER(
        PARTITION BY asset_id ORDER BY observation_date DESC
    ) rn
    FROM model_snapshots_daily
) x
WHERE rn=1;

CREATE OR REPLACE VIEW latest_signal_validation_summary AS
SELECT * FROM signal_validation_summary
ORDER BY horizon_days, historical_signal;

CREATE OR REPLACE VIEW recent_cycle_transitions AS
SELECT * FROM cycle_transition_history
ORDER BY transition_date DESC, asset_id;
"""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def pct_change(series: pd.Series, periods: int) -> float | None:
    if len(series) <= periods:
        return None
    prior = float(series.iloc[-periods - 1])
    current = float(series.iloc[-1])
    if prior <= 0:
        return None
    return (current / prior - 1) * 100

def rsi(series: pd.Series, periods: int = 14) -> float | None:
    if len(series) < periods + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(periods).mean().iloc[-1]
    loss = -delta.clip(upper=0).rolling(periods).mean().iloc[-1]
    if pd.isna(gain) or pd.isna(loss):
        return None
    if loss == 0:
        return 100.0
    rs = gain / loss
    return float(100 - 100 / (1 + rs))

def annualized_vol(series: pd.Series, periods: int = 30) -> float | None:
    returns = series.pct_change().dropna()
    if len(returns) < periods:
        return None
    return float(returns.tail(periods).std(ddof=1) * math.sqrt(365) * 100)

def max_drawdown(series: pd.Series, periods: int = 365) -> float | None:
    data = series.tail(periods).dropna()
    if data.empty:
        return None
    return float((data / data.cummax() - 1).min() * 100)

def linear_score(value: float | None, bad: float, good: float) -> float | None:
    if value is None or pd.isna(value):
        return None
    return clamp((float(value) - bad) / (good - bad) * 100)

def inverse_score(value: float | None, good: float, bad: float) -> float | None:
    return linear_score(value, bad, good)

def weighted(items: list[tuple[float | None, float]]) -> float | None:
    valid = [(float(v), float(w)) for v, w in items if v is not None and not pd.isna(v)]
    if not valid:
        return None
    total = sum(w for _, w in valid)
    return sum(v * w for v, w in valid) / total

class Module6Runner:
    def __init__(self):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE2_SCHEMA)
        self.conn.execute(MODULE3_SCHEMA)
        self.conn.execute(MODULE5_SCHEMA)
        self.conn.execute(MODULE6_SCHEMA)
        self.config = self.settings["module6"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m6_stage", frame)
        cols = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _m6_stage"
        )
        self.conn.unregister("_m6_stage")

    def sync_canonical_history(self) -> int:
        now = utcnow()
        market = self.conn.execute(
            """
            SELECT asset_id, observation_date, price_usd, market_cap_usd,
                   volume_24h_usd
            FROM asset_market_daily
            WHERE source='coingecko'
            """
        ).fetchdf()
        if not market.empty:
            market["observation_date"] = pd.to_datetime(
                market["observation_date"]
            ).dt.date

        exchange = self.conn.execute(
            """
            SELECT asset_id, CAST(open_time_utc AS DATE) AS observation_date,
                   close AS price_usd, quote_volume AS volume_24h_usd,
                   exchange
            FROM asset_ohlcv
            WHERE interval='1d'
            QUALIFY ROW_NUMBER() OVER(
                PARTITION BY asset_id, CAST(open_time_utc AS DATE)
                ORDER BY CASE exchange
                    WHEN 'coinbase' THEN 1
                    WHEN 'kraken' THEN 2
                    WHEN 'binance' THEN 3
                    ELSE 9 END
            )=1
            """
        ).fetchdf()
        if not exchange.empty:
            exchange["observation_date"] = pd.to_datetime(
                exchange["observation_date"]
            ).dt.date

        rows = []
        asset_ids = sorted(set(market.get("asset_id", [])) | set(exchange.get("asset_id", [])))
        for asset_id in asset_ids:
            m = (
                market[market["asset_id"] == asset_id].set_index("observation_date")
                if not market.empty else pd.DataFrame()
            )
            e = (
                exchange[exchange["asset_id"] == asset_id].set_index("observation_date")
                if not exchange.empty else pd.DataFrame()
            )
            dates = sorted(set(m.index if not m.empty else []) | set(e.index if not e.empty else []))
            for date in dates:
                mrow = m.loc[date] if not m.empty and date in m.index else None
                erow = e.loc[date] if not e.empty and date in e.index else None

                mprice = None if mrow is None else mrow.get("price_usd")
                eprice = None if erow is None else erow.get("price_usd")
                price = mprice if pd.notna(mprice) else eprice
                if price is None or pd.isna(price):
                    continue

                market_cap = None if mrow is None else mrow.get("market_cap_usd")
                mvolume = None if mrow is None else mrow.get("volume_24h_usd")
                evolume = None if erow is None else erow.get("volume_24h_usd")
                volume = mvolume if pd.notna(mvolume) else evolume
                exchange_name = None if erow is None else erow.get("exchange")

                rows.append({
                    "asset_id": asset_id,
                    "observation_date": date,
                    "price_usd": float(price),
                    "market_cap_usd": (
                        float(market_cap) if pd.notna(market_cap) else None
                    ),
                    "volume_24h_usd": (
                        float(volume) if pd.notna(volume) else None
                    ),
                    "price_source": (
                        "coingecko" if pd.notna(mprice)
                        else str(exchange_name or "exchange")
                    ),
                    "market_cap_source": (
                        "coingecko" if pd.notna(market_cap) else None
                    ),
                    "volume_source": (
                        "coingecko" if pd.notna(mvolume)
                        else str(exchange_name or "exchange")
                        if pd.notna(evolume) else None
                    ),
                    "source_priority": 1 if pd.notna(mprice) else 2,
                    "collected_at_utc": now,
                })
        frame = pd.DataFrame(rows)
        self.upsert("canonical_market_daily", frame)
        return len(frame)

    def canonical_prices(self) -> pd.DataFrame:
        frame = self.conn.execute(
            """
            SELECT asset_id, observation_date, price_usd
            FROM canonical_market_daily
            ORDER BY asset_id, observation_date
            """
        ).fetchdf()
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame

    def classify_signal(self, score: float | None) -> str:
        if score is None or pd.isna(score):
            return "INSUFFICIENT_DATA"
        bands = self.config["research"]["score_bands"]
        if score >= float(bands["strong_buy"]):
            return "STRONG_BUY"
        if score >= float(bands["buy"]):
            return "BUY"
        if score >= float(bands["hold"]):
            return "HOLD"
        if score >= float(bands["reduce"]):
            return "REDUCE"
        return "AVOID"

    def cycle_phase(
        self, price: float, ath: float, vs200: float | None,
        rsi_value: float | None, return_90: float | None
    ) -> str:
        drawdown = (price / ath - 1) * 100 if ath > 0 else None
        if drawdown is not None and drawdown <= -75:
            return "CAPITULATION"
        if drawdown is not None and drawdown <= -55:
            return "ACCUMULATION"
        if (
            rsi_value is not None and rsi_value >= 72
            and vs200 is not None and vs200 >= 12
        ):
            return "EUPHORIA"
        if vs200 is not None and vs200 >= 12 and (return_90 or 0) > 0:
            return "EXPANSION"
        if vs200 is not None and vs200 <= -15 and (return_90 or 0) < 0:
            return "CONTRACTION"
        if (return_90 or 0) > 0:
            return "RECOVERY"
        return "DISTRIBUTION"

    def build_snapshots(self) -> int:
        if not bool(self.config["snapshots"]["enabled"]):
            return 0
        history_days = int(self.config["snapshots"]["history_days"])
        minimum = int(self.config["snapshots"]["minimum_history_days"])
        step = max(1, int(self.config["snapshots"]["sampling_frequency_days"]))
        frame = self.canonical_prices()
        now = utcnow()
        rows = []

        for asset_id, group in frame.groupby("asset_id"):
            group = group.sort_values("observation_date")
            latest_date = group["observation_date"].max()
            group = group[
                group["observation_date"] >= latest_date - pd.Timedelta(days=history_days + 400)
            ]
            series = group.set_index("observation_date")["price_usd"].astype(float)
            dates = series.index[-history_days::step] if len(series) > history_days else series.index[minimum::step]

            for date in dates:
                hist = series.loc[:date]
                if len(hist) < minimum:
                    continue
                price = float(hist.iloc[-1])
                ret30 = pct_change(hist, 30)
                ret90 = pct_change(hist, 90)
                ret365 = pct_change(hist, 365)
                sma50 = float(hist.tail(50).mean()) if len(hist) >= 50 else None
                sma200 = float(hist.tail(200).mean()) if len(hist) >= 200 else None
                vs50 = (price / sma50 - 1) * 100 if sma50 else None
                vs200 = (price / sma200 - 1) * 100 if sma200 else None
                rsi14 = rsi(hist)
                vol30 = annualized_vol(hist)
                dd365 = max_drawdown(hist)

                momentum = weighted([
                    (linear_score(ret30, -25, 35), 0.35),
                    (linear_score(ret90, -40, 70), 0.40),
                    (linear_score(ret365, -65, 150), 0.25),
                ])
                trend = weighted([
                    (linear_score(vs50, -20, 20), 0.40),
                    (linear_score(vs200, -40, 40), 0.45),
                    (
                        inverse_score(
                            abs((rsi14 if rsi14 is not None else 50) - 55),
                            0, 45
                        ),
                        0.15,
                    ),
                ])
                risk = weighted([
                    (inverse_score(vol30, 35, 160), 0.55),
                    (inverse_score(abs(dd365 or 0), 10, 80), 0.45),
                ])
                overall = weighted([
                    (momentum, 0.40),
                    (trend, 0.35),
                    (risk, 0.25),
                ])
                phase = self.cycle_phase(
                    price, float(hist.max()), vs200, rsi14, ret90
                )
                if vs200 is None:
                    valuation = "UNKNOWN"
                elif vs200 <= -30:
                    valuation = "STRONG_BUY_ZONE"
                elif vs200 <= -15:
                    valuation = "BUY_ZONE"
                elif vs200 <= 20:
                    valuation = "FAIR_RANGE"
                elif vs200 <= 40:
                    valuation = "TRIM_ZONE"
                else:
                    valuation = "OVEREXTENDED"

                expected_proxy = weighted([
                    (ret365, 0.30),
                    ((momentum or 50) - 50, 0.25),
                    ((trend or 50) - 50, 0.25),
                    ((risk or 50) - 50, 0.20),
                ])

                rows.append({
                    "asset_id": asset_id,
                    "observation_date": date.date(),
                    "price_usd": price,
                    "return_30d_pct": ret30,
                    "return_90d_pct": ret90,
                    "return_365d_pct": ret365,
                    "sma_50": sma50,
                    "sma_200": sma200,
                    "price_vs_sma50_pct": vs50,
                    "price_vs_sma200_pct": vs200,
                    "rsi_14": rsi14,
                    "volatility_30d_pct": vol30,
                    "max_drawdown_365d_pct": dd365,
                    "momentum_score": momentum,
                    "trend_score": trend,
                    "risk_score": risk,
                    "historical_overall_score": overall,
                    "historical_signal": self.classify_signal(overall),
                    "cycle_phase": phase,
                    "valuation_label": valuation,
                    "expected_return_proxy_pct": expected_proxy,
                    "calculation_version": "historical_v1.0",
                    "calculated_at_utc": now,
                })
        snapshots = pd.DataFrame(rows)
        self.upsert("model_snapshots_daily", snapshots)
        self.build_cycle_transitions()
        return len(snapshots)

    def build_cycle_transitions(self) -> None:
        snapshots = self.conn.execute(
            """
            SELECT asset_id, observation_date, cycle_phase, price_usd,
                   historical_overall_score
            FROM model_snapshots_daily
            ORDER BY asset_id, observation_date
            """
        ).fetchdf()
        if snapshots.empty:
            return
        rows = []
        for asset_id, group in snapshots.groupby("asset_id"):
            group = group.sort_values("observation_date").copy()
            group["previous_phase"] = group["cycle_phase"].shift(1)
            changed = group[
                group["previous_phase"].notna()
                & (group["cycle_phase"] != group["previous_phase"])
            ]
            for _, row in changed.iterrows():
                rows.append({
                    "asset_id": asset_id,
                    "transition_date": row["observation_date"],
                    "previous_phase": row["previous_phase"],
                    "new_phase": row["cycle_phase"],
                    "price_usd": row["price_usd"],
                    "score": row["historical_overall_score"],
                    "calculated_at_utc": utcnow(),
                })
        self.upsert("cycle_transition_history", pd.DataFrame(rows))

    def build_validation(self) -> int:
        snapshots = self.conn.execute(
            """
            SELECT asset_id, observation_date, historical_signal,
                   historical_overall_score, price_usd
            FROM model_snapshots_daily
            """
        ).fetchdf()
        prices = self.conn.execute(
            """
            SELECT asset_id, observation_date, price_usd
            FROM canonical_market_daily
            ORDER BY asset_id, observation_date
            """
        ).fetchdf()
        if snapshots.empty or prices.empty:
            return 0
        snapshots["observation_date"] = pd.to_datetime(snapshots["observation_date"])
        prices["observation_date"] = pd.to_datetime(prices["observation_date"])
        latest_date = prices["observation_date"].max()
        horizons = [
            int(x) for x in self.config["validation"]["forward_horizons_days"]
        ]
        price_maps = {
            asset: group.set_index("observation_date")["price_usd"].sort_index()
            for asset, group in prices.groupby("asset_id")
        }
        btc_prices = price_maps.get("bitcoin")
        rows = []

        for _, snapshot in snapshots.iterrows():
            asset_id = snapshot["asset_id"]
            asset_prices = price_maps.get(asset_id)
            if asset_prices is None:
                continue
            for horizon in horizons:
                target = snapshot["observation_date"] + pd.Timedelta(days=horizon)
                completed = target <= latest_date
                future_price = None
                actual_date = None
                btc_return = None
                asset_return = None
                if completed:
                    candidates = asset_prices[asset_prices.index >= target]
                    candidates = candidates[
                        candidates.index <= target + pd.Timedelta(days=7)
                    ]
                    if not candidates.empty:
                        actual_date = candidates.index[0]
                        future_price = float(candidates.iloc[0])
                        asset_return = (
                            future_price / float(snapshot["price_usd"]) - 1
                        ) * 100
                    if btc_prices is not None:
                        btc_start_candidates = btc_prices[
                            btc_prices.index >= snapshot["observation_date"]
                        ]
                        btc_end_candidates = btc_prices[btc_prices.index >= target]
                        if not btc_start_candidates.empty and not btc_end_candidates.empty:
                            btc_start = float(btc_start_candidates.iloc[0])
                            btc_end = float(btc_end_candidates.iloc[0])
                            btc_return = (btc_end / btc_start - 1) * 100

                rows.append({
                    "asset_id": asset_id,
                    "signal_date": snapshot["observation_date"].date(),
                    "historical_signal": snapshot["historical_signal"],
                    "historical_score": snapshot["historical_overall_score"],
                    "horizon_days": horizon,
                    "target_date": target.date(),
                    "actual_target_date": (
                        actual_date.date() if actual_date is not None else None
                    ),
                    "signal_price_usd": snapshot["price_usd"],
                    "future_price_usd": future_price,
                    "forward_return_pct": asset_return,
                    "benchmark_btc_return_pct": btc_return,
                    "excess_vs_btc_pct": (
                        asset_return - btc_return
                        if asset_return is not None and btc_return is not None
                        else None
                    ),
                    "positive_return": (
                        asset_return > 0 if asset_return is not None else None
                    ),
                    "outperformed_btc": (
                        asset_return > btc_return
                        if asset_return is not None and btc_return is not None
                        else None
                    ),
                    "completed": bool(completed and asset_return is not None),
                    "calculated_at_utc": utcnow(),
                })
        validation = pd.DataFrame(rows)
        self.upsert("signal_forward_performance", validation)
        self.refresh_validation_summary()
        return len(validation)

    def refresh_validation_summary(self) -> None:
        frame = self.conn.execute(
            """
            SELECT historical_signal, horizon_days, forward_return_pct,
                   excess_vs_btc_pct, positive_return, outperformed_btc
            FROM signal_forward_performance
            WHERE completed=TRUE
            """
        ).fetchdf()
        if frame.empty:
            return
        rows = []
        for (signal, horizon), group in frame.groupby(
            ["historical_signal", "horizon_days"]
        ):
            rows.append({
                "historical_signal": signal,
                "horizon_days": int(horizon),
                "sample_count": len(group),
                "positive_rate_pct": float(group["positive_return"].mean() * 100),
                "average_forward_return_pct": float(group["forward_return_pct"].mean()),
                "median_forward_return_pct": float(group["forward_return_pct"].median()),
                "average_excess_vs_btc_pct": (
                    float(group["excess_vs_btc_pct"].mean())
                    if group["excess_vs_btc_pct"].notna().any() else None
                ),
                "btc_outperformance_rate_pct": (
                    float(group["outperformed_btc"].mean() * 100)
                    if group["outperformed_btc"].notna().any() else None
                ),
                "last_updated_utc": utcnow(),
            })
        self.upsert("signal_validation_summary", pd.DataFrame(rows))

    def run(self, phase: str = "all") -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO module6_runs(
                run_id,started_at_utc,status,phase,canonical_rows,
                snapshots_created,validations_created,notes,platform_version
            ) VALUES (?,?,'RUNNING',?,0,0,0,NULL,'4.0.0')
            """,
            [self.run_id, self.started, phase],
        )
        canonical = snapshots = validations = 0
        if phase in {"all", "sync"}:
            canonical = self.sync_canonical_history()
        if phase in {"all", "research"}:
            if self.conn.execute(
                "SELECT COUNT(*) FROM canonical_market_daily"
            ).fetchone()[0] == 0:
                canonical = self.sync_canonical_history()
            snapshots = self.build_snapshots()
            validations = self.build_validation()

        notes = (
            f"canonical={canonical}; snapshots={snapshots}; "
            f"validations={validations}; phase={phase}"
        )
        self.conn.execute(
            """
            UPDATE module6_runs
            SET completed_at_utc=?,status='SUCCESS',canonical_rows=?,
                snapshots_created=?,validations_created=?,notes=?
            WHERE run_id=?
            """,
            [utcnow(), canonical, snapshots, validations, notes, self.run_id],
        )
        self.conn.close()
        return {
            "run_id": self.run_id,
            "status": "SUCCESS",
            "phase": phase,
            "canonical_rows": canonical,
            "snapshots_created": snapshots,
            "validations_created": validations,
        }

def run_module6(phase: str = "all") -> dict[str, Any]:
    return Module6Runner().run(phase)
