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
from sklearn.linear_model import LogisticRegression

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA, clamp
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA

MODULE11_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module11_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    mapped_assets INTEGER,
    history_rows INTEGER,
    derivatives_rows INTEGER,
    taxonomy_rows INTEGER,
    calibrated_predictions INTEGER,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS exchange_symbol_map(
    asset_id VARCHAR,
    provider VARCHAR,
    provider_symbol VARCHAR,
    quote_currency VARCHAR,
    market_type VARCHAR,
    mapping_method VARCHAR,
    mapping_confidence DOUBLE,
    active BOOLEAN,
    last_verified_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, provider, market_type)
);

CREATE TABLE IF NOT EXISTS historical_provider_health(
    provider VARCHAR,
    asset_id VARCHAR,
    checked_at_utc TIMESTAMPTZ,
    status VARCHAR,
    rows_received INTEGER,
    first_date DATE,
    latest_date DATE,
    error_message VARCHAR,
    PRIMARY KEY(provider, asset_id, checked_at_utc)
);

CREATE TABLE IF NOT EXISTS research_history_quality(
    asset_id VARCHAR PRIMARY KEY,
    first_date DATE,
    latest_date DATE,
    row_count INTEGER,
    expected_days INTEGER,
    coverage_pct DOUBLE,
    provider_count INTEGER,
    primary_provider VARCHAR,
    stale_days INTEGER,
    quality_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS research_asset_taxonomy(
    asset_id VARCHAR PRIMARY KEY,
    sector VARCHAR,
    subsector VARCHAR,
    layer_type VARCHAR,
    is_meme BOOLEAN,
    is_exchange_token BOOLEAN,
    is_privacy BOOLEAN,
    is_rwa BOOLEAN,
    is_ai BOOLEAN,
    taxonomy_method VARCHAR,
    updated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS sector_market_snapshot(
    observation_date DATE,
    sector VARCHAR,
    asset_count INTEGER,
    total_market_cap_usd DOUBLE,
    total_volume_24h_usd DOUBLE,
    median_return_7d_pct DOUBLE,
    median_return_30d_pct DOUBLE,
    positive_30d_pct DOUBLE,
    market_cap_weight_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(observation_date, sector)
);

CREATE TABLE IF NOT EXISTS derivatives_collection_status(
    asset_id VARCHAR,
    provider VARCHAR,
    provider_symbol VARCHAR,
    supported BOOLEAN,
    funding_rows INTEGER,
    open_interest_rows INTEGER,
    status VARCHAR,
    error_message VARCHAR,
    checked_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, provider, provider_symbol)
);

CREATE TABLE IF NOT EXISTS probability_calibration_registry(
    run_id VARCHAR,
    target_name VARCHAR,
    calibration_method VARCHAR,
    training_rows INTEGER,
    mean_absolute_error DOUBLE,
    brier_score DOUBLE,
    x_min DOUBLE,
    x_max DOUBLE,
    promoted BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, target_name)
);

CREATE TABLE IF NOT EXISTS robust_calibrated_predictive_current(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    raw_probability_outperform DOUBLE,
    calibrated_probability_outperform DOUBLE,
    outperform_calibration_method VARCHAR,
    raw_probability_positive DOUBLE,
    calibrated_probability_positive DOUBLE,
    positive_calibration_method VARCHAR,
    predictive_weight_raw DOUBLE,
    predictive_weight_capped DOUBLE,
    rules_score DOUBLE,
    calibrated_predictive_score DOUBLE,
    final_score DOUBLE,
    final_signal VARCHAR,
    final_confidence DOUBLE,
    promotion_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE OR REPLACE VIEW latest_symbol_map AS
SELECT * FROM exchange_symbol_map
WHERE active=TRUE
ORDER BY asset_id, provider;

CREATE OR REPLACE VIEW latest_history_quality AS
SELECT * FROM research_history_quality
ORDER BY coverage_pct DESC, asset_id;

CREATE OR REPLACE VIEW latest_sector_snapshot AS
SELECT * FROM sector_market_snapshot
WHERE observation_date=(
    SELECT MAX(observation_date) FROM sector_market_snapshot
)
ORDER BY total_market_cap_usd DESC;

CREATE OR REPLACE VIEW latest_derivatives_status AS
SELECT * FROM derivatives_collection_status
ORDER BY supported DESC, asset_id;

CREATE OR REPLACE VIEW latest_robust_calibrated_predictive AS
SELECT x.*
FROM robust_calibrated_predictive_current x
JOIN (
    SELECT run_id FROM module11_runs
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

class Module11Runner:
    def __init__(self):
        self.settings, self.core_assets = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
            MODULE9_SCHEMA, MODULE10_SCHEMA, MODULE11_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.config = self.settings["module11"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CryptoIntelligencePlatform/4.0"
        })

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m11_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m11_stage"
        )
        self.conn.unregister("_m11_stage")

    def get_json(
        self, url: str, params: dict[str, Any] | None = None,
        retries: int = 3
    ) -> Any:
        last_error = None
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
        raise RuntimeError(f"{url}: {last_error}")

    def provider_symbols(self) -> dict[str, set[str]]:
        result: dict[str, set[str]] = {
            "binance": set(),
            "coinbase": set(),
            "kraken": set(),
        }
        try:
            payload = self.get_json(
                "https://api.binance.com/api/v3/exchangeInfo"
            )
            result["binance"] = {
                row["symbol"]
                for row in payload.get("symbols", [])
                if row.get("status") == "TRADING"
                and row.get("quoteAsset") in {"USDT", "USDC", "USD"}
            }
        except Exception:
            pass
        try:
            payload = self.get_json(
                "https://api.exchange.coinbase.com/products"
            )
            result["coinbase"] = {
                row["id"]
                for row in payload
                if row.get("status") == "online"
                and row.get("quote_currency") in {"USD", "USDC", "USDT"}
            }
        except Exception:
            pass
        try:
            payload = self.get_json(
                "https://api.kraken.com/0/public/AssetPairs"
            )
            result["kraken"] = set(payload.get("result", {}).keys())
        except Exception:
            pass
        return result

    def build_symbol_map(self, universe: pd.DataFrame) -> pd.DataFrame:
        available = self.provider_symbols()
        now = utcnow()
        rows = []
        aliases = {
            "BTC": ["BTC", "XBT"],
            "XRP": ["XRP"],
            "DOGE": ["DOGE", "XDG"],
        }
        for _, asset in universe.iterrows():
            symbol = str(asset["symbol"]).upper()
            candidates = aliases.get(symbol, [symbol])
            # Binance
            provider_symbol = None
            for base in candidates:
                for quote in ["USDT", "USDC"]:
                    candidate = f"{base}{quote}"
                    if candidate in available["binance"]:
                        provider_symbol = candidate
                        break
                if provider_symbol:
                    break
            if provider_symbol:
                rows.append({
                    "asset_id": asset["asset_id"],
                    "provider": "binance",
                    "provider_symbol": provider_symbol,
                    "quote_currency": (
                        "USDT" if provider_symbol.endswith("USDT") else "USDC"
                    ),
                    "market_type": "spot",
                    "mapping_method": "verified_exchange_info",
                    "mapping_confidence": 0.98,
                    "active": True,
                    "last_verified_utc": now,
                })

            # Coinbase
            provider_symbol = None
            for base in candidates:
                for quote in ["USD", "USDC", "USDT"]:
                    candidate = f"{base}-{quote}"
                    if candidate in available["coinbase"]:
                        provider_symbol = candidate
                        break
                if provider_symbol:
                    break
            if provider_symbol:
                rows.append({
                    "asset_id": asset["asset_id"],
                    "provider": "coinbase",
                    "provider_symbol": provider_symbol,
                    "quote_currency": provider_symbol.split("-")[-1],
                    "market_type": "spot",
                    "mapping_method": "verified_products",
                    "mapping_confidence": 0.98,
                    "active": True,
                    "last_verified_utc": now,
                })

            # Kraken approximate verified match.
            provider_symbol = None
            for candidate in available["kraken"]:
                normalized = candidate.replace("X", "").replace("Z", "")
                if any(
                    normalized.startswith(base)
                    and normalized.endswith(("USD", "USDT"))
                    for base in candidates
                ):
                    provider_symbol = candidate
                    break
            if provider_symbol:
                rows.append({
                    "asset_id": asset["asset_id"],
                    "provider": "kraken",
                    "provider_symbol": provider_symbol,
                    "quote_currency": (
                        "USDT" if "USDT" in provider_symbol else "USD"
                    ),
                    "market_type": "spot",
                    "mapping_method": "verified_asset_pairs",
                    "mapping_confidence": 0.90,
                    "active": True,
                    "last_verified_utc": now,
                })

            # Binance futures mapping separately.
            for base in candidates:
                future_symbol = f"{base}USDT"
                if future_symbol in available["binance"]:
                    rows.append({
                        "asset_id": asset["asset_id"],
                        "provider": "binance",
                        "provider_symbol": future_symbol,
                        "quote_currency": "USDT",
                        "market_type": "perpetual",
                        "mapping_method": "spot_proxy_verified",
                        "mapping_confidence": 0.85,
                        "active": True,
                        "last_verified_utc": now,
                    })
                    break

        frame = pd.DataFrame(rows)
        self.upsert("exchange_symbol_map", frame)
        return frame

    def existing_latest_date(
        self, asset_id: str, provider: str
    ) -> pd.Timestamp | None:
        row = self.conn.execute(
            """
            SELECT MAX(observation_date)
            FROM research_market_daily
            WHERE asset_id=? AND source=?
            """,
            [asset_id, provider],
        ).fetchone()
        if row and row[0] is not None:
            return pd.Timestamp(row[0])
        return None

    def binance_history(
        self, asset_id: str, symbol: str, start: pd.Timestamp,
        end: pd.Timestamp
    ) -> pd.DataFrame:
        rows = []
        cursor = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        while cursor <= end_ms:
            payload = self.get_json(
                "https://api.binance.com/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval": "1d",
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 1000,
                },
                retries=2,
            )
            if not payload:
                break
            for candle in payload:
                rows.append({
                    "asset_id": asset_id,
                    "observation_date": pd.to_datetime(
                        int(candle[0]), unit="ms", utc=True
                    ).date(),
                    "price_usd": float(candle[4]),
                    "market_cap_usd": None,
                    "volume_24h_usd": float(candle[7]),
                    "source": "binance",
                    "source_symbol": symbol,
                    "collected_at_utc": utcnow(),
                })
            next_cursor = int(payload[-1][0]) + 86400000
            if next_cursor <= cursor or len(payload) < 1000:
                break
            cursor = next_cursor
            time.sleep(0.1)
        return pd.DataFrame(rows)

    def coinbase_history(
        self, asset_id: str, symbol: str, start: pd.Timestamp,
        end: pd.Timestamp
    ) -> pd.DataFrame:
        rows = []
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + pd.Timedelta(days=299), end)
            payload = self.get_json(
                f"https://api.exchange.coinbase.com/products/{symbol}/candles",
                params={
                    "granularity": 86400,
                    "start": cursor.isoformat(),
                    "end": chunk_end.isoformat(),
                },
                retries=2,
            )
            for candle in payload:
                rows.append({
                    "asset_id": asset_id,
                    "observation_date": pd.to_datetime(
                        int(candle[0]), unit="s", utc=True
                    ).date(),
                    "price_usd": float(candle[4]),
                    "market_cap_usd": None,
                    "volume_24h_usd": float(candle[5]) * float(candle[4]),
                    "source": "coinbase",
                    "source_symbol": symbol,
                    "collected_at_utc": utcnow(),
                })
            cursor = chunk_end + pd.Timedelta(days=1)
            time.sleep(0.12)
        return pd.DataFrame(rows)

    def kraken_history(
        self, asset_id: str, symbol: str, start: pd.Timestamp,
        end: pd.Timestamp
    ) -> pd.DataFrame:
        payload = self.get_json(
            "https://api.kraken.com/0/public/OHLC",
            params={
                "pair": symbol,
                "interval": 1440,
                "since": int(start.timestamp()),
            },
            retries=2,
        )
        result = payload.get("result", {})
        key = next((k for k in result.keys() if k != "last"), None)
        if key is None:
            return pd.DataFrame()
        rows = []
        for candle in result[key]:
            timestamp = pd.to_datetime(
                int(candle[0]), unit="s", utc=True
            )
            if timestamp > end:
                continue
            rows.append({
                "asset_id": asset_id,
                "observation_date": timestamp.date(),
                "price_usd": float(candle[4]),
                "market_cap_usd": None,
                "volume_24h_usd": float(candle[6]) * float(candle[4]),
                "source": "kraken",
                "source_symbol": symbol,
                "collected_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def backfill_history(
        self, universe: pd.DataFrame, mappings: pd.DataFrame
    ) -> int:
        cfg = self.config["historical_backfill"]
        end = pd.Timestamp.now(tz="UTC").normalize()
        target_start = end - pd.Timedelta(days=int(cfg["target_days"]))
        overlap = int(cfg["incremental_overlap_days"])
        all_rows = []
        health = []

        for _, asset in universe.head(
            int(cfg["max_assets_per_run"])
        ).iterrows():
            asset_id = asset["asset_id"]
            asset_mappings = mappings[
                (mappings["asset_id"] == asset_id)
                & (mappings["market_type"] == "spot")
                & (
                    mappings["mapping_confidence"]
                    >= float(
                        self.config["symbol_mapping"][
                            "minimum_mapping_confidence"
                        ]
                    )
                )
            ]
            success = False
            for provider in cfg["providers"]:
                matches = asset_mappings[
                    asset_mappings["provider"] == provider
                ]
                if matches.empty:
                    continue
                symbol = matches.iloc[0]["provider_symbol"]
                existing = self.existing_latest_date(asset_id, provider)
                start = (
                    max(
                        target_start,
                        existing.tz_localize("UTC")
                        - pd.Timedelta(days=overlap),
                    )
                    if existing is not None
                    else target_start
                )
                try:
                    if provider == "binance":
                        frame = self.binance_history(
                            asset_id, symbol, start, end
                        )
                    elif provider == "coinbase":
                        frame = self.coinbase_history(
                            asset_id, symbol, start, end
                        )
                    else:
                        frame = self.kraken_history(
                            asset_id, symbol, start, end
                        )
                    if not frame.empty:
                        all_rows.append(frame)
                        health.append({
                            "provider": provider,
                            "asset_id": asset_id,
                            "checked_at_utc": utcnow(),
                            "status": "ONLINE",
                            "rows_received": len(frame),
                            "first_date": frame["observation_date"].min(),
                            "latest_date": frame["observation_date"].max(),
                            "error_message": None,
                        })
                        success = True
                        break
                except Exception as exc:
                    health.append({
                        "provider": provider,
                        "asset_id": asset_id,
                        "checked_at_utc": utcnow(),
                        "status": "FAILED",
                        "rows_received": 0,
                        "first_date": None,
                        "latest_date": None,
                        "error_message": str(exc)[:500],
                    })
            if not success:
                health.append({
                    "provider": "all",
                    "asset_id": asset_id,
                    "checked_at_utc": utcnow(),
                    "status": "UNAVAILABLE",
                    "rows_received": 0,
                    "first_date": None,
                    "latest_date": None,
                    "error_message": "No verified provider returned history.",
                })

        combined = (
            pd.concat(all_rows, ignore_index=True)
            if all_rows else pd.DataFrame()
        )
        self.upsert("research_market_daily", combined)
        self.upsert(
            "historical_provider_health",
            pd.DataFrame(health),
        )
        return len(combined)

    def calculate_quality(self, universe: pd.DataFrame) -> int:
        now = pd.Timestamp.now(tz="UTC")
        target_days = int(
            self.config["historical_backfill"]["target_days"]
        )
        minimum_coverage = float(
            self.config["quality"]["minimum_history_coverage_pct"]
        )
        stale_limit = int(self.config["quality"]["stale_days"])
        rows = []
        for _, asset in universe.iterrows():
            history = self.conn.execute(
                """
                SELECT observation_date, source
                FROM research_market_daily
                WHERE asset_id=?
                """,
                [asset["asset_id"]],
            ).fetchdf()
            if history.empty:
                rows.append({
                    "asset_id": asset["asset_id"],
                    "first_date": None,
                    "latest_date": None,
                    "row_count": 0,
                    "expected_days": target_days,
                    "coverage_pct": 0.0,
                    "provider_count": 0,
                    "primary_provider": None,
                    "stale_days": None,
                    "quality_status": "NO_HISTORY",
                    "calculated_at_utc": utcnow(),
                })
                continue
            history["observation_date"] = pd.to_datetime(
                history["observation_date"]
            )
            unique_days = history["observation_date"].nunique()
            first = history["observation_date"].min()
            latest = history["observation_date"].max()
            stale_days = max(0, (now.date() - latest.date()).days)
            coverage = min(100.0, unique_days / target_days * 100)
            primary = (
                history["source"].value_counts().index[0]
                if not history.empty else None
            )
            if stale_days > stale_limit:
                status = "STALE"
            elif coverage >= minimum_coverage:
                status = "GOOD"
            elif unique_days >= int(
                self.config["historical_backfill"][
                    "minimum_required_days"
                ]
            ):
                status = "PARTIAL"
            else:
                status = "INSUFFICIENT"
            rows.append({
                "asset_id": asset["asset_id"],
                "first_date": first.date(),
                "latest_date": latest.date(),
                "row_count": unique_days,
                "expected_days": target_days,
                "coverage_pct": coverage,
                "provider_count": history["source"].nunique(),
                "primary_provider": primary,
                "stale_days": stale_days,
                "quality_status": status,
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert("research_history_quality", frame)
        return len(frame)

    def collect_derivatives(
        self, universe: pd.DataFrame, mappings: pd.DataFrame
    ) -> int:
        if not bool(self.config["derivatives"]["enabled"]):
            return 0
        rows_funding = []
        rows_oi = []
        status_rows = []
        now = utcnow()
        futures = mappings[
            (mappings["provider"] == "binance")
            & (mappings["market_type"] == "perpetual")
        ]
        for _, asset in universe.iterrows():
            match = futures[futures["asset_id"] == asset["asset_id"]]
            if match.empty:
                status_rows.append({
                    "asset_id": asset["asset_id"],
                    "provider": "binance",
                    "provider_symbol": None,
                    "supported": False,
                    "funding_rows": 0,
                    "open_interest_rows": 0,
                    "status": "NO_MAPPING",
                    "error_message": None,
                    "checked_at_utc": now,
                })
                continue
            symbol = match.iloc[0]["provider_symbol"]
            funding_count = 0
            oi_count = 0
            error = None
            try:
                payload = self.get_json(
                    "https://fapi.binance.com/fapi/v1/fundingRate",
                    params={"symbol": symbol, "limit": 100},
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
                        rows_funding.append({
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
                        funding_count += 1
                oi = self.get_json(
                    "https://fapi.binance.com/fapi/v1/openInterest",
                    params={"symbol": symbol},
                    retries=2,
                )
                rows_oi.append({
                    "asset_id": asset["asset_id"],
                    "symbol": symbol,
                    "observation_time_utc": now,
                    "open_interest_contracts": float(
                        oi["openInterest"]
                    ),
                    "source": "binance_futures",
                    "collected_at_utc": now,
                })
                oi_count = 1
            except Exception as exc:
                error = str(exc)[:500]
            status_rows.append({
                "asset_id": asset["asset_id"],
                "provider": "binance",
                "provider_symbol": symbol,
                "supported": funding_count > 0 or oi_count > 0,
                "funding_rows": funding_count,
                "open_interest_rows": oi_count,
                "status": (
                    "ONLINE"
                    if funding_count > 0 or oi_count > 0
                    else "FAILED"
                ),
                "error_message": error,
                "checked_at_utc": now,
            })

        self.upsert(
            "derivatives_funding_daily",
            pd.DataFrame(rows_funding),
        )
        self.upsert(
            "derivatives_open_interest",
            pd.DataFrame(rows_oi),
        )
        self.upsert(
            "derivatives_collection_status",
            pd.DataFrame(status_rows),
        )
        return len(rows_funding) + len(rows_oi)

    def classify_taxonomy(self, universe: pd.DataFrame) -> pd.DataFrame:
        sector_rules = {
            "MEME": {"DOGE","SHIB","PEPE","BONK","FLOKI","WIF","M"},
            "PRIVACY": {"XMR","ZEC","DASH"},
            "EXCHANGE": {"BNB","OKB","WBT","HT","HTX","CRO","BGB"},
            "DEFI": {"AAVE","UNI","MKR","SKY","CRV","SNX","MORPHO","ONDO"},
            "AI": {"TAO","FET","RENDER","RNDR","WLD","AKT","ICP"},
            "PAYMENTS": {"XRP","XLM","LTC","BCH","TRX","XNO"},
            "LAYER_2": {"ARB","OP","POL","MATIC","STRK","IMX","MNT"},
            "RWA": {"ONDO","XAUT","PAXG","CFG","MPL"},
            "ORACLE": {"LINK","PYTH","BAND","API3"},
            "GAMING": {"IMX","GALA","SAND","MANA","AXS","BEAM"},
        }
        layer1 = {
            "BTC","ETH","SOL","ADA","AVAX","DOT","ATOM","NEAR","SUI",
            "HBAR","TON","TRX","APT","ICP","ETC","SEI",
        }
        rows = []
        now = utcnow()
        for _, asset in universe.iterrows():
            symbol = str(asset["symbol"]).upper()
            sectors = [
                sector for sector, symbols in sector_rules.items()
                if symbol in symbols
            ]
            sector = sectors[0] if sectors else (
                "LAYER_1" if symbol in layer1 else
                self.config["taxonomy"]["default_sector"]
            )
            rows.append({
                "asset_id": asset["asset_id"],
                "sector": sector,
                "subsector": sector,
                "layer_type": (
                    "L1" if sector == "LAYER_1"
                    else "L2" if sector == "LAYER_2"
                    else "NA"
                ),
                "is_meme": sector == "MEME",
                "is_exchange_token": sector == "EXCHANGE",
                "is_privacy": sector == "PRIVACY",
                "is_rwa": sector == "RWA",
                "is_ai": sector == "AI",
                "taxonomy_method": "symbol_rules_v1",
                "updated_at_utc": now,
            })
        frame = pd.DataFrame(rows)
        self.upsert("research_asset_taxonomy", frame)
        return frame

    def sector_snapshot(
        self, universe: pd.DataFrame, taxonomy: pd.DataFrame
    ) -> int:
        merged = universe.merge(taxonomy, on="asset_id", how="left")
        if merged.empty:
            return 0
        total_market_cap = float(
            merged["market_cap_usd"].fillna(0).sum()
        ) or 1.0
        rows = []
        now = utcnow()
        for sector, group in merged.groupby("sector"):
            returns30 = pd.to_numeric(
                group["price_change_30d_pct"], errors="coerce"
            )
            returns7 = pd.to_numeric(
                group["price_change_7d_pct"], errors="coerce"
            )
            rows.append({
                "observation_date": now.date(),
                "sector": sector,
                "asset_count": len(group),
                "total_market_cap_usd": float(
                    group["market_cap_usd"].fillna(0).sum()
                ),
                "total_volume_24h_usd": float(
                    group["volume_24h_usd"].fillna(0).sum()
                ),
                "median_return_7d_pct": (
                    float(returns7.median())
                    if returns7.notna().any() else None
                ),
                "median_return_30d_pct": (
                    float(returns30.median())
                    if returns30.notna().any() else None
                ),
                "positive_30d_pct": (
                    float((returns30 > 0).mean() * 100)
                    if returns30.notna().any() else None
                ),
                "market_cap_weight_pct": float(
                    group["market_cap_usd"].fillna(0).sum()
                    / total_market_cap * 100
                ),
                "calculated_at_utc": now,
            })
        frame = pd.DataFrame(rows)
        self.upsert("sector_market_snapshot", frame)
        return len(frame)

    def probability_rows(self, target: str) -> pd.DataFrame:
        return self.conn.execute(
            """
            SELECT sample_count, average_predicted_probability,
                   observed_rate
            FROM probability_calibration_bins
            WHERE target_name=?
              AND sample_count > 0
            ORDER BY probability_bin_low
            """,
            [target],
        ).fetchdf()

    def fit_calibrator(
        self, data: pd.DataFrame, target_name: str
    ) -> tuple[str, Any, float | None, float | None]:
        if data.empty:
            return "NONE", None, None, None
        x = data["average_predicted_probability"].to_numpy(
            dtype=float
        )
        y = data["observed_rate"].to_numpy(dtype=float)
        weights = data["sample_count"].to_numpy(dtype=float)
        total = int(weights.sum())
        isotonic_min = int(
            self.config["calibration"]["isotonic_minimum_rows"]
        )
        platt_min = int(
            self.config["calibration"]["platt_minimum_rows"]
        )
        if total >= isotonic_min and len(np.unique(x)) >= 4:
            model = IsotonicRegression(
                y_min=0.01, y_max=0.99,
                out_of_bounds="clip",
            )
            model.fit(x, y, sample_weight=weights)
            prediction = model.predict(x)
            method = "ISOTONIC"
        elif total >= platt_min and len(np.unique(y)) >= 2:
            expanded_x = np.repeat(x, weights.astype(int))
            expanded_y = np.concatenate([
                np.r_[
                    np.ones(int(round(rate * count))),
                    np.zeros(
                        max(
                            0,
                            int(count)
                            - int(round(rate * count))
                        )
                    ),
                ]
                for rate, count in zip(y, weights.astype(int))
            ])
            if len(expanded_x) != len(expanded_y):
                minimum = min(len(expanded_x), len(expanded_y))
                expanded_x = expanded_x[:minimum]
                expanded_y = expanded_y[:minimum]
            model = LogisticRegression(
                C=1.0, solver="lbfgs"
            )
            model.fit(
                expanded_x.reshape(-1, 1),
                expanded_y,
            )
            prediction = model.predict_proba(
                x.reshape(-1, 1)
            )[:, 1]
            method = "PLATT"
        else:
            return "NONE", None, None, None
        mae = float(np.average(
            np.abs(prediction - y), weights=weights
        ))
        brier = float(np.average(
            (prediction - y) ** 2, weights=weights
        ))
        return method, model, mae, brier

    def apply_calibrator(
        self, method: str, model: Any, value: float
    ) -> float:
        if method == "ISOTONIC":
            return float(model.predict([value])[0])
        if method == "PLATT":
            return float(
                model.predict_proba([[value]])[0, 1]
            )
        return value

    def robust_calibration(self) -> int:
        latest = self.conn.execute(
            """
            SELECT *
            FROM latest_predictive_classifications
            ORDER BY asset_id
            """
        ).fetchdf()
        if latest.empty:
            return 0
        calibrators = {}
        registry = []
        for target in ["OUTPERFORM_BTC", "POSITIVE_RETURN"]:
            data = self.probability_rows(target)
            method, model, mae, brier = self.fit_calibrator(
                data, target
            )
            calibrators[target] = (method, model)
            registry.append({
                "run_id": self.run_id,
                "target_name": target,
                "calibration_method": method,
                "training_rows": (
                    int(data["sample_count"].sum())
                    if not data.empty else 0
                ),
                "mean_absolute_error": mae,
                "brier_score": brier,
                "x_min": (
                    float(data[
                        "average_predicted_probability"
                    ].min()) if not data.empty else None
                ),
                "x_max": (
                    float(data[
                        "average_predicted_probability"
                    ].max()) if not data.empty else None
                ),
                "promoted": method != "NONE",
                "calculated_at_utc": utcnow(),
            })
        self.upsert(
            "probability_calibration_registry",
            pd.DataFrame(registry),
        )

        cap = min(
            0.20,
            float(
                self.config["calibration"][
                    "maximum_predictive_weight"
                ]
            ),
        )
        rows = []
        for _, row in latest.iterrows():
            raw_out = float(row["probability_outperform_btc"])
            raw_pos = float(row["probability_positive_return"])
            out_method, out_model = calibrators["OUTPERFORM_BTC"]
            pos_method, pos_model = calibrators["POSITIVE_RETURN"]
            cal_out = self.apply_calibrator(
                out_method, out_model, raw_out
            )
            cal_pos = self.apply_calibrator(
                pos_method, pos_model, raw_pos
            )
            predictive_score = clamp(
                50
                + (cal_out - 0.5) * 55
                + (cal_pos - 0.5) * 35
                + float(row["calibrated_excess_return_pct"]) * 0.05
            )
            raw_weight = float(row["predictive_weight"])
            capped = min(raw_weight, cap)
            rules_score = float(row["rules_score"])
            final_score = (
                rules_score * (1 - capped)
                + predictive_score * capped
            )
            confidence = clamp(
                float(row["final_ensemble_confidence"])
                * (1 - capped)
                + (
                    45
                    + (
                        abs(cal_out - 0.5)
                        + abs(cal_pos - 0.5)
                    ) / 2 * 60
                ) * capped,
                35, 92,
            )
            rows.append({
                "run_id": self.run_id,
                "asset_id": row["asset_id"],
                "observation_date": row["observation_date"],
                "raw_probability_outperform": raw_out,
                "calibrated_probability_outperform": cal_out,
                "outperform_calibration_method": out_method,
                "raw_probability_positive": raw_pos,
                "calibrated_probability_positive": cal_pos,
                "positive_calibration_method": pos_method,
                "predictive_weight_raw": raw_weight,
                "predictive_weight_capped": capped,
                "rules_score": rules_score,
                "calibrated_predictive_score": predictive_score,
                "final_score": final_score,
                "final_signal": signal_from_score(final_score),
                "final_confidence": confidence,
                "promotion_status": (
                    "CAPPED_PROMOTED"
                    if capped > 0 else "RESEARCH_ONLY"
                ),
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert(
            "robust_calibrated_predictive_current",
            result,
        )
        return len(result)

    def run(self) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO module11_runs(
                run_id,started_at_utc,status,mapped_assets,
                history_rows,derivatives_rows,taxonomy_rows,
                calibrated_predictions,notes,platform_version
            ) VALUES (?,?,'RUNNING',0,0,0,0,0,NULL,'4.0.0')
            """,
            [self.run_id, self.started],
        )
        universe = self.conn.execute(
            "SELECT * FROM latest_research_universe"
        ).fetchdf()
        if universe.empty:
            raise RuntimeError(
                "Run Module 10 once before Module 11."
            )
        mappings = self.build_symbol_map(universe)
        history_rows = self.backfill_history(
            universe, mappings
        )
        quality_rows = self.calculate_quality(universe)
        derivative_rows = self.collect_derivatives(
            universe, mappings
        )
        taxonomy = self.classify_taxonomy(universe)
        sector_rows = self.sector_snapshot(
            universe, taxonomy
        )
        calibrated = self.robust_calibration()

        notes = (
            f"mappings={len(mappings)}; history={history_rows}; "
            f"quality={quality_rows}; derivatives={derivative_rows}; "
            f"taxonomy={len(taxonomy)}; sectors={sector_rows}; "
            f"calibrated={calibrated}."
        )
        self.conn.execute(
            """
            UPDATE module11_runs
            SET completed_at_utc=?,status='SUCCESS',
                mapped_assets=?,history_rows=?,
                derivatives_rows=?,taxonomy_rows=?,
                calibrated_predictions=?,notes=?
            WHERE run_id=?
            """,
            [
                utcnow(),
                mappings["asset_id"].nunique()
                if not mappings.empty else 0,
                history_rows,
                derivative_rows,
                len(taxonomy),
                calibrated,
                notes,
                self.run_id,
            ],
        )
        self.conn.close()
        return {
            "run_id": self.run_id,
            "status": "SUCCESS",
            "mapped_assets": (
                mappings["asset_id"].nunique()
                if not mappings.empty else 0
            ),
            "mapping_rows": len(mappings),
            "history_rows": history_rows,
            "quality_rows": quality_rows,
            "derivatives_rows": derivative_rows,
            "taxonomy_rows": len(taxonomy),
            "sector_rows": sector_rows,
            "calibrated_predictions": calibrated,
        }

def run_module11() -> dict[str, Any]:
    return Module11Runner().run()
