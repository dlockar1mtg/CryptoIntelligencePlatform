from __future__ import annotations

import math
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import requests
from sklearn.isotonic import IsotonicRegression

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA, clamp
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA

MODULE10_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module10_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    discovered_assets INTEGER,
    selected_assets INTEGER,
    history_rows INTEGER,
    derivative_rows INTEGER,
    sentiment_rows INTEGER,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS research_universe(
    asset_id VARCHAR PRIMARY KEY,
    symbol VARCHAR,
    name VARCHAR,
    market_cap_rank INTEGER,
    market_cap_usd DOUBLE,
    volume_24h_usd DOUBLE,
    current_price_usd DOUBLE,
    price_change_24h_pct DOUBLE,
    price_change_7d_pct DOUBLE,
    price_change_30d_pct DOUBLE,
    circulating_supply DOUBLE,
    total_supply DOUBLE,
    max_supply DOUBLE,
    ath_change_pct DOUBLE,
    inclusion_status VARCHAR,
    inclusion_reason VARCHAR,
    is_core BOOLEAN,
    discovered_at_utc TIMESTAMPTZ,
    updated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS research_market_daily(
    asset_id VARCHAR,
    observation_date DATE,
    price_usd DOUBLE,
    market_cap_usd DOUBLE,
    volume_24h_usd DOUBLE,
    source VARCHAR,
    source_symbol VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, observation_date, source)
);

CREATE TABLE IF NOT EXISTS derivatives_funding_daily(
    asset_id VARCHAR,
    symbol VARCHAR,
    observation_date DATE,
    average_funding_rate DOUBLE,
    minimum_funding_rate DOUBLE,
    maximum_funding_rate DOUBLE,
    funding_observations INTEGER,
    source VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, symbol, observation_date, source)
);

CREATE TABLE IF NOT EXISTS derivatives_open_interest(
    asset_id VARCHAR,
    symbol VARCHAR,
    observation_time_utc TIMESTAMPTZ,
    open_interest_contracts DOUBLE,
    source VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, symbol, observation_time_utc, source)
);

CREATE TABLE IF NOT EXISTS crypto_sentiment_daily(
    observation_date DATE,
    fear_greed_value DOUBLE,
    fear_greed_classification VARCHAR,
    source VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(observation_date, source)
);

CREATE TABLE IF NOT EXISTS defi_market_snapshot(
    observation_date DATE,
    total_chain_tvl_usd DOUBLE,
    total_stablecoin_supply_usd DOUBLE,
    chain_count INTEGER,
    stablecoin_count INTEGER,
    source VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(observation_date, source)
);

CREATE TABLE IF NOT EXISTS research_market_breadth(
    observation_date DATE,
    universe_size INTEGER,
    assets_above_sma50 INTEGER,
    assets_above_sma200 INTEGER,
    breadth_above_sma50_pct DOUBLE,
    breadth_above_sma200_pct DOUBLE,
    positive_7d_count INTEGER,
    positive_30d_count INTEGER,
    positive_90d_count INTEGER,
    positive_7d_pct DOUBLE,
    positive_30d_pct DOUBLE,
    positive_90d_pct DOUBLE,
    median_return_7d_pct DOUBLE,
    median_return_30d_pct DOUBLE,
    median_return_90d_pct DOUBLE,
    breadth_regime VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(observation_date)
);

CREATE TABLE IF NOT EXISTS calibrated_probability_models(
    run_id VARCHAR,
    target_name VARCHAR,
    training_rows INTEGER,
    x_min DOUBLE,
    x_max DOUBLE,
    y_min DOUBLE,
    y_max DOUBLE,
    mean_absolute_calibration_error DOUBLE,
    calibrated BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, target_name)
);

CREATE TABLE IF NOT EXISTS calibrated_predictive_current(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    raw_probability_outperform DOUBLE,
    calibrated_probability_outperform DOUBLE,
    raw_probability_positive DOUBLE,
    calibrated_probability_positive DOUBLE,
    calibration_shift_outperform DOUBLE,
    calibration_shift_positive DOUBLE,
    raw_predictive_weight DOUBLE,
    capped_predictive_weight DOUBLE,
    calibrated_predictive_score DOUBLE,
    calibrated_predictive_signal VARCHAR,
    final_score DOUBLE,
    final_signal VARCHAR,
    final_confidence DOUBLE,
    promotion_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE OR REPLACE VIEW latest_research_universe AS
SELECT * FROM research_universe
WHERE inclusion_status='INCLUDED'
ORDER BY market_cap_rank;

CREATE OR REPLACE VIEW latest_research_breadth AS
SELECT * FROM research_market_breadth
ORDER BY observation_date DESC LIMIT 1;

CREATE OR REPLACE VIEW latest_derivatives_funding AS
SELECT * EXCLUDE(rn)
FROM (
    SELECT *,
           ROW_NUMBER() OVER(
               PARTITION BY asset_id
               ORDER BY observation_date DESC
           ) rn
    FROM derivatives_funding_daily
) x
WHERE rn=1;

CREATE OR REPLACE VIEW latest_sentiment AS
SELECT * FROM crypto_sentiment_daily
ORDER BY observation_date DESC LIMIT 1;

CREATE OR REPLACE VIEW latest_defi_snapshot AS
SELECT * FROM defi_market_snapshot
ORDER BY observation_date DESC LIMIT 1;

CREATE OR REPLACE VIEW latest_calibrated_predictive AS
SELECT x.*
FROM calibrated_predictive_current x
JOIN (
    SELECT run_id FROM module10_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);
"""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def signal_from_score(score: float) -> str:
    if score >= 80:
        return "STRONG_BUY"
    if score >= 68:
        return "BUY"
    if score >= 48:
        return "HOLD"
    if score >= 35:
        return "REDUCE"
    return "AVOID"

# One cheap call per Binance host decides whether the rest of the run calls that host.
# From some regions (including the hosted runners) every Binance call fails, and each of
# the ~150 per-asset calls used to retry with sleeps before falling back.
BINANCE_PROBES = {
    "spot": "https://api.binance.com/api/v3/ping",
    "futures": "https://fapi.binance.com/fapi/v1/ping",
}


class Module10Runner:
    def binance_available(self, market: str) -> bool:
        """Probe a Binance host once per run; False if disabled or the probe fails.

        When this is False the per-asset Binance calls are skipped, and the module writes
        exactly what it wrote before when every one of those calls failed: the CoinGecko
        snapshot row per asset for history, and no derivatives rows.
        """
        status = self.__dict__.setdefault("_binance_status", {})
        if market not in status:
            if not bool(self.config.get("binance", {}).get("enabled", True)):
                print(f"Binance {market} calls skipped: disabled in config.")
                status[market] = False
            else:
                try:
                    self.get_json(BINANCE_PROBES[market], retries=2)
                    status[market] = True
                except Exception as exc:
                    print(f"Binance {market} calls skipped for this run: probe failed ({exc}).")
                    status[market] = False
        return status[market]

    def __init__(self):
        self.settings, self.core_assets = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
            MODULE9_SCHEMA, MODULE10_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.config = self.settings["module10"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CryptoIntelligencePlatform/4.0"
        })
        key = os.getenv("COINGECKO_API_KEY", "").strip()
        if key:
            self.session.headers.update({"x-cg-demo-api-key": key})

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m10_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m10_stage"
        )
        self.conn.unregister("_m10_stage")

    def get_json(
        self, url: str, params: dict[str, Any] | None = None,
        retries: int = 3
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                response = self.session.get(
                    url, params=params, timeout=35
                )
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                if attempt + 1 < retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"Request failed: {url}: {last_error}")

    def discover_universe(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        cfg = self.config["universe"]
        discovery = self.config["discovery"]
        records: list[dict[str, Any]] = []

        for page in range(1, int(discovery["coingecko_pages"]) + 1):
            payload = self.get_json(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": int(discovery["per_page"]),
                    "page": page,
                    "sparkline": "false",
                    "price_change_percentage": "24h,7d,30d",
                },
            )
            records.extend(payload)
            time.sleep(0.6)

        now = utcnow()
        excluded_symbols = {
            str(value).upper()
            for value in cfg["excluded_symbols"]
        }
        excluded_terms = [
            str(value).lower()
            for value in cfg["excluded_name_terms"]
        ]
        core_ids = set(cfg["core_asset_ids"])
        candidates = []
        audit = []

        for row in records:
            asset_id = str(row.get("id", ""))
            symbol = str(row.get("symbol", "")).upper()
            name = str(row.get("name", ""))
            price = row.get("current_price")
            market_cap = row.get("market_cap")
            volume = row.get("total_volume")
            change_24 = row.get("price_change_percentage_24h")
            reason = "Passed institutional research filters."
            included = True

            if symbol in excluded_symbols:
                included = False
                reason = "Excluded stablecoin, wrapped, or staking derivative symbol."
            elif any(term in name.lower() for term in excluded_terms):
                included = False
                reason = "Excluded by asset-name term."
            elif market_cap is None or float(market_cap) < float(
                cfg["minimum_market_cap_usd"]
            ):
                included = False
                reason = "Market capitalization below minimum."
            elif volume is None or float(volume) < float(
                cfg["minimum_24h_volume_usd"]
            ):
                included = False
                reason = "Trading volume below minimum."
            elif (
                price is not None
                and float(cfg["stablecoin_price_floor"])
                <= float(price)
                <= float(cfg["stablecoin_price_ceiling"])
                and change_24 is not None
                and abs(float(change_24))
                <= float(cfg["stablecoin_volatility_ceiling_pct"])
            ):
                included = False
                reason = "Stablecoin-like price behavior."

            item = {
                "asset_id": asset_id,
                "symbol": symbol,
                "name": name,
                "market_cap_rank": row.get("market_cap_rank"),
                "market_cap_usd": market_cap,
                "volume_24h_usd": volume,
                "current_price_usd": price,
                "price_change_24h_pct": change_24,
                "price_change_7d_pct": row.get(
                    "price_change_percentage_7d_in_currency"
                ),
                "price_change_30d_pct": row.get(
                    "price_change_percentage_30d_in_currency"
                ),
                "circulating_supply": row.get("circulating_supply"),
                "total_supply": row.get("total_supply"),
                "max_supply": row.get("max_supply"),
                "ath_change_pct": row.get(
                    "ath_change_percentage"
                ),
                "inclusion_status": (
                    "INCLUDED" if included else "EXCLUDED"
                ),
                "inclusion_reason": reason,
                "is_core": asset_id in core_ids,
                "discovered_at_utc": now,
                "updated_at_utc": now,
            }
            audit.append(item)
            if included:
                candidates.append(item)

        selected = sorted(
            candidates,
            key=lambda x: (
                x["market_cap_rank"]
                if x["market_cap_rank"] is not None
                else 999999
            ),
        )[: int(cfg["research_asset_count"])]

        selected_ids = {row["asset_id"] for row in selected}
        for row in audit:
            if (
                row["inclusion_status"] == "INCLUDED"
                and row["asset_id"] not in selected_ids
            ):
                row["inclusion_status"] = "WAITLIST"
                row["inclusion_reason"] = (
                    "Passed filters but fell outside configured universe size."
                )

        audit_frame = pd.DataFrame(audit)
        selected_frame = pd.DataFrame(selected)
        self.upsert("research_universe", audit_frame)
        return audit_frame, selected_frame

    def binance_symbol(self, symbol: str) -> str:
        return f"{symbol.upper()}USDT"

    def backfill_history(self, universe: pd.DataFrame) -> int:
        if not bool(self.config["history"]["enabled"]):
            return 0
        rows = []
        now = utcnow()
        limit = int(self.config["history"]["binance_page_limit"])
        days = int(self.config["history"]["backfill_days"])
        max_assets = int(self.config["history"]["max_assets_per_run"])
        end_ms = int(now.timestamp() * 1000)
        start_ms = int(
            (now.timestamp() - days * 86400) * 1000
        )

        binance_ok = self.binance_available("spot")
        for _, asset in universe.head(max_assets).iterrows():
            symbol = self.binance_symbol(asset["symbol"])
            cursor = start_ms
            asset_rows = []
            try:
                while binance_ok and cursor < end_ms:
                    payload = self.get_json(
                        "https://api.binance.com/api/v3/klines",
                        params={
                            "symbol": symbol,
                            "interval": "1d",
                            "startTime": cursor,
                            "endTime": end_ms,
                            "limit": limit,
                        },
                        retries=2,
                    )
                    if not payload:
                        break
                    for candle in payload:
                        date = pd.to_datetime(
                            int(candle[0]), unit="ms", utc=True
                        ).date()
                        asset_rows.append({
                            "asset_id": asset["asset_id"],
                            "observation_date": date,
                            "price_usd": float(candle[4]),
                            "market_cap_usd": None,
                            "volume_24h_usd": float(candle[7]),
                            "source": "binance_spot",
                            "source_symbol": symbol,
                            "collected_at_utc": now,
                        })
                    next_cursor = int(payload[-1][0]) + 86400000
                    if next_cursor <= cursor:
                        break
                    cursor = next_cursor
                    if len(payload) < limit:
                        break
                    time.sleep(0.12)
            except Exception:
                asset_rows = []

            if not asset_rows:
                rows.append({
                    "asset_id": asset["asset_id"],
                    "observation_date": now.date(),
                    "price_usd": asset["current_price_usd"],
                    "market_cap_usd": asset["market_cap_usd"],
                    "volume_24h_usd": asset["volume_24h_usd"],
                    "source": "coingecko_snapshot",
                    "source_symbol": asset["symbol"],
                    "collected_at_utc": now,
                })
            else:
                rows.extend(asset_rows)

        frame = pd.DataFrame(rows)
        self.upsert("research_market_daily", frame)
        return len(frame)

    def collect_derivatives(self, universe: pd.DataFrame) -> int:
        if not bool(self.config["derivatives"]["enabled"]):
            return 0
        funding_rows = []
        interest_rows = []
        now = utcnow()
        limit = int(
            self.config["derivatives"]["funding_history_limit"]
        )

        if not self.binance_available("futures"):
            # Same result as every funding and open-interest call failing.
            universe = universe.iloc[0:0]
        for _, asset in universe.iterrows():
            symbol = self.binance_symbol(asset["symbol"])
            try:
                payload = self.get_json(
                    "https://fapi.binance.com/fapi/v1/fundingRate",
                    params={"symbol": symbol, "limit": limit},
                    retries=2,
                )
                if payload:
                    frame = pd.DataFrame(payload)
                    frame["fundingTime"] = pd.to_datetime(
                        frame["fundingTime"].astype("int64"),
                        unit="ms", utc=True
                    )
                    frame["fundingRate"] = pd.to_numeric(
                        frame["fundingRate"], errors="coerce"
                    )
                    for date, group in frame.groupby(
                        frame["fundingTime"].dt.date
                    ):
                        funding_rows.append({
                            "asset_id": asset["asset_id"],
                            "symbol": symbol,
                            "observation_date": date,
                            "average_funding_rate": float(
                                group["fundingRate"].mean()
                            ),
                            "minimum_funding_rate": float(
                                group["fundingRate"].min()
                            ),
                            "maximum_funding_rate": float(
                                group["fundingRate"].max()
                            ),
                            "funding_observations": len(group),
                            "source": "binance_futures",
                            "collected_at_utc": now,
                        })
            except Exception:
                pass

            if bool(
                self.config["derivatives"]["open_interest_enabled"]
            ):
                try:
                    oi = self.get_json(
                        "https://fapi.binance.com/fapi/v1/openInterest",
                        params={"symbol": symbol},
                        retries=2,
                    )
                    interest_rows.append({
                        "asset_id": asset["asset_id"],
                        "symbol": symbol,
                        "observation_time_utc": now,
                        "open_interest_contracts": float(
                            oi["openInterest"]
                        ),
                        "source": "binance_futures",
                        "collected_at_utc": now,
                    })
                except Exception:
                    pass
            time.sleep(0.08)

        funding = pd.DataFrame(funding_rows)
        interest = pd.DataFrame(interest_rows)
        self.upsert("derivatives_funding_daily", funding)
        self.upsert("derivatives_open_interest", interest)
        return len(funding) + len(interest)

    def collect_sentiment(self) -> int:
        if not bool(self.config["sentiment"]["enabled"]):
            return 0
        limit = int(
            self.config["sentiment"]["fear_greed_history_days"]
        )
        payload = self.get_json(
            "https://api.alternative.me/fng/",
            params={"limit": limit, "format": "json"},
        )
        rows = []
        now = utcnow()
        for item in payload.get("data", []):
            rows.append({
                "observation_date": pd.to_datetime(
                    int(item["timestamp"]), unit="s", utc=True
                ).date(),
                "fear_greed_value": float(item["value"]),
                "fear_greed_classification": item[
                    "value_classification"
                ],
                "source": "alternative_me",
                "collected_at_utc": now,
            })
        frame = pd.DataFrame(rows)
        self.upsert("crypto_sentiment_daily", frame)
        return len(frame)

    def collect_defi(self) -> int:
        if not bool(self.config["defi"]["enabled"]):
            return 0
        now = utcnow()
        chains = self.get_json("https://api.llama.fi/v2/chains")
        stablecoins = self.get_json(
            "https://stablecoins.llama.fi/stablecoins",
            params={"includePrices": "true"},
        )
        chain_tvl = sum(
            float(row.get("tvl") or 0)
            for row in chains
        )
        stablecoin_total = 0.0
        assets = stablecoins.get("peggedAssets", [])
        for asset in assets:
            circulating = asset.get("circulating", {})
            value = circulating.get("peggedUSD")
            if value is not None:
                stablecoin_total += float(value)

        frame = pd.DataFrame([{
            "observation_date": now.date(),
            "total_chain_tvl_usd": chain_tvl,
            "total_stablecoin_supply_usd": stablecoin_total,
            "chain_count": len(chains),
            "stablecoin_count": len(assets),
            "source": "defillama",
            "collected_at_utc": now,
        }])
        self.upsert("defi_market_snapshot", frame)
        return 1

    def calculate_breadth(self) -> int:
        history = self.conn.execute(
            """
            SELECT asset_id, observation_date, price_usd
            FROM research_market_daily
            WHERE price_usd IS NOT NULL
            ORDER BY asset_id, observation_date
            """
        ).fetchdf()
        if history.empty:
            return 0
        history["observation_date"] = pd.to_datetime(
            history["observation_date"]
        )
        rows = []
        latest_date = history["observation_date"].max()
        stats = []

        for asset_id, group in history.groupby("asset_id"):
            series = (
                group.sort_values("observation_date")
                .drop_duplicates("observation_date", keep="last")
                .set_index("observation_date")["price_usd"]
                .astype(float)
            )
            if series.empty:
                continue
            current = float(series.iloc[-1])
            item = {"asset_id": asset_id}
            for days in [7, 30, 90]:
                prior = series[
                    series.index <= latest_date - pd.Timedelta(days=days)
                ]
                item[f"return_{days}"] = (
                    (current / float(prior.iloc[-1]) - 1) * 100
                    if not prior.empty and float(prior.iloc[-1]) > 0
                    else None
                )
            item["above_sma50"] = (
                current > float(series.tail(50).mean())
                if len(series) >= 50 else None
            )
            item["above_sma200"] = (
                current > float(series.tail(200).mean())
                if len(series) >= 200 else None
            )
            stats.append(item)

        frame = pd.DataFrame(stats)
        if frame.empty:
            return 0
        universe_size = len(frame)
        above50 = int(frame["above_sma50"].fillna(False).sum())
        above200 = int(frame["above_sma200"].fillna(False).sum())
        counts = {}
        medians = {}
        for days in [7, 30, 90]:
            series = pd.to_numeric(
                frame[f"return_{days}"], errors="coerce"
            )
            counts[days] = int((series > 0).sum())
            medians[days] = (
                float(series.median())
                if series.notna().any() else None
            )
        breadth30 = counts[30] / universe_size * 100
        if breadth30 >= 70 and above200 / universe_size >= 0.60:
            regime = "BROAD_EXPANSION"
        elif breadth30 >= 55:
            regime = "POSITIVE_BREADTH"
        elif breadth30 >= 40:
            regime = "MIXED_BREADTH"
        elif breadth30 >= 25:
            regime = "NARROW_CONTRACTION"
        else:
            regime = "BROAD_STRESS"

        breadth = pd.DataFrame([{
            "observation_date": latest_date.date(),
            "universe_size": universe_size,
            "assets_above_sma50": above50,
            "assets_above_sma200": above200,
            "breadth_above_sma50_pct": above50 / universe_size * 100,
            "breadth_above_sma200_pct": above200 / universe_size * 100,
            "positive_7d_count": counts[7],
            "positive_30d_count": counts[30],
            "positive_90d_count": counts[90],
            "positive_7d_pct": counts[7] / universe_size * 100,
            "positive_30d_pct": breadth30,
            "positive_90d_pct": counts[90] / universe_size * 100,
            "median_return_7d_pct": medians[7],
            "median_return_30d_pct": medians[30],
            "median_return_90d_pct": medians[90],
            "breadth_regime": regime,
            "calculated_at_utc": utcnow(),
        }])
        self.upsert("research_market_breadth", breadth)
        return 1

    def calibration_training_data(
        self, target_name: str
    ) -> pd.DataFrame:
        target_column = (
            "outperformed_btc"
            if target_name == "OUTPERFORM_BTC"
            else "positive_return"
        )
        return self.conn.execute(
            f"""
            SELECT probability_bin_low, probability_bin_high,
                   sample_count, average_predicted_probability,
                   observed_rate
            FROM probability_calibration_bins
            WHERE target_name=?
              AND sample_count > 0
            ORDER BY probability_bin_low
            """,
            [target_name],
        ).fetchdf()

    def calibrate_current_probabilities(self) -> int:
        latest = self.conn.execute(
            """
            SELECT *
            FROM latest_predictive_classifications
            ORDER BY asset_id
            """
        ).fetchdf()
        if latest.empty:
            return 0

        predictive_weight_cap = min(
            float(self.config["calibration"][
                "maximum_predictive_weight"
            ]),
            0.20,
        )
        calibration_models: dict[str, IsotonicRegression | None] = {}
        diagnostics = []

        for target in ["OUTPERFORM_BTC", "POSITIVE_RETURN"]:
            data = self.calibration_training_data(target)
            model = None
            calibrated = False
            mae = None
            if (
                bool(self.config["calibration"]["isotonic_enabled"])
                and data["sample_count"].sum()
                >= int(self.config["calibration"][
                    "minimum_calibration_rows"
                ])
                and data["average_predicted_probability"].nunique() >= 3
            ):
                x = data["average_predicted_probability"].to_numpy(
                    dtype=float
                )
                y = data["observed_rate"].to_numpy(dtype=float)
                weights = data["sample_count"].to_numpy(dtype=float)
                model = IsotonicRegression(
                    y_min=0.01, y_max=0.99,
                    out_of_bounds="clip",
                    increasing=True,
                )
                model.fit(x, y, sample_weight=weights)
                prediction = model.predict(x)
                mae = float(
                    np.average(
                        np.abs(prediction - y),
                        weights=weights,
                    )
                )
                calibrated = True
            calibration_models[target] = model
            diagnostics.append({
                "run_id": self.run_id,
                "target_name": target,
                "training_rows": int(
                    data["sample_count"].sum()
                ) if not data.empty else 0,
                "x_min": (
                    float(data["average_predicted_probability"].min())
                    if not data.empty else None
                ),
                "x_max": (
                    float(data["average_predicted_probability"].max())
                    if not data.empty else None
                ),
                "y_min": (
                    float(data["observed_rate"].min())
                    if not data.empty else None
                ),
                "y_max": (
                    float(data["observed_rate"].max())
                    if not data.empty else None
                ),
                "mean_absolute_calibration_error": mae,
                "calibrated": calibrated,
                "calculated_at_utc": utcnow(),
            })

        self.upsert(
            "calibrated_probability_models",
            pd.DataFrame(diagnostics),
        )

        rows = []
        for _, row in latest.iterrows():
            raw_out = float(row["probability_outperform_btc"])
            raw_pos = float(row["probability_positive_return"])
            out_model = calibration_models["OUTPERFORM_BTC"]
            pos_model = calibration_models["POSITIVE_RETURN"]
            cal_out = (
                float(out_model.predict([raw_out])[0])
                if out_model is not None else raw_out
            )
            cal_pos = (
                float(pos_model.predict([raw_pos])[0])
                if pos_model is not None else raw_pos
            )
            calibrated_score = clamp(
                50
                + (cal_out - 0.5) * 55
                + (cal_pos - 0.5) * 35
                + float(row["calibrated_excess_return_pct"]) * 0.05
            )
            raw_weight = float(row["predictive_weight"])
            capped_weight = min(raw_weight, predictive_weight_cap)
            rules_score = float(row["rules_score"])
            final_score = (
                rules_score * (1 - capped_weight)
                + calibrated_score * capped_weight
            )
            probability_margin = (
                abs(cal_out - 0.5)
                + abs(cal_pos - 0.5)
            ) / 2
            calibrated_confidence = clamp(
                45 + probability_margin * 60,
                40, 85,
            )
            final_confidence = clamp(
                float(row["final_ensemble_confidence"])
                * (1 - capped_weight)
                + calibrated_confidence * capped_weight,
                35, 92,
            )
            rows.append({
                "run_id": self.run_id,
                "asset_id": row["asset_id"],
                "observation_date": row["observation_date"],
                "raw_probability_outperform": raw_out,
                "calibrated_probability_outperform": cal_out,
                "raw_probability_positive": raw_pos,
                "calibrated_probability_positive": cal_pos,
                "calibration_shift_outperform": cal_out - raw_out,
                "calibration_shift_positive": cal_pos - raw_pos,
                "raw_predictive_weight": raw_weight,
                "capped_predictive_weight": capped_weight,
                "calibrated_predictive_score": calibrated_score,
                "calibrated_predictive_signal": signal_from_score(
                    calibrated_score
                ),
                "final_score": final_score,
                "final_signal": signal_from_score(final_score),
                "final_confidence": final_confidence,
                "promotion_status": (
                    "CAPPED_PROMOTED"
                    if raw_weight > 0
                    else "RESEARCH_ONLY"
                ),
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert("calibrated_predictive_current", result)
        return len(result)

    def run(self) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO module10_runs(
                run_id,started_at_utc,status,discovered_assets,
                selected_assets,history_rows,derivative_rows,
                sentiment_rows,notes,platform_version
            ) VALUES (?,?,'RUNNING',0,0,0,0,0,NULL,'4.0.0')
            """,
            [self.run_id, self.started],
        )

        audit, universe = self.discover_universe()
        history_rows = self.backfill_history(universe)
        derivative_rows = self.collect_derivatives(universe)
        sentiment_rows = self.collect_sentiment()
        defi_rows = self.collect_defi()
        breadth_rows = self.calculate_breadth()
        calibrated_rows = self.calibrate_current_probabilities()

        notes = (
            f"discovered={len(audit)}; selected={len(universe)}; "
            f"history={history_rows}; derivatives={derivative_rows}; "
            f"sentiment={sentiment_rows}; defi={defi_rows}; "
            f"breadth={breadth_rows}; calibrated_predictions={calibrated_rows}."
        )
        self.conn.execute(
            """
            UPDATE module10_runs
            SET completed_at_utc=?,status='SUCCESS',
                discovered_assets=?,selected_assets=?,
                history_rows=?,derivative_rows=?,
                sentiment_rows=?,notes=?
            WHERE run_id=?
            """,
            [
                utcnow(), len(audit), len(universe),
                history_rows, derivative_rows,
                sentiment_rows, notes, self.run_id,
            ],
        )
        self.conn.close()
        return {
            "run_id": self.run_id,
            "status": "SUCCESS",
            "discovered_assets": len(audit),
            "selected_assets": len(universe),
            "history_rows": history_rows,
            "derivative_rows": derivative_rows,
            "sentiment_rows": sentiment_rows,
            "calibrated_predictions": calibrated_rows,
        }

def run_module10() -> dict[str, Any]:
    return Module10Runner().run()
