from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Iterable

import duckdb
import pandas as pd
import requests
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = r"""
CREATE TABLE IF NOT EXISTS assets(
    asset_id VARCHAR PRIMARY KEY,
    symbol VARCHAR,
    asset_name VARCHAR,
    coingecko_id VARCHAR,
    coinbase_product VARCHAR,
    kraken_pair VARCHAR,
    binance_symbol VARCHAR,
    asset_tier VARCHAR,
    portfolio_enabled BOOLEAN,
    research_enabled BOOLEAN,
    native_chain VARCHAR,
    active BOOLEAN DEFAULT TRUE,
    created_at_utc TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asset_market_daily(
    asset_id VARCHAR,
    observation_date DATE,
    price_usd DOUBLE,
    market_cap_usd DOUBLE,
    volume_24h_usd DOUBLE,
    circulating_supply DOUBLE,
    total_supply DOUBLE,
    max_supply DOUBLE,
    fully_diluted_value_usd DOUBLE,
    market_cap_rank INTEGER,
    ath_usd DOUBLE,
    ath_change_pct DOUBLE,
    source VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, observation_date, source)
);

CREATE TABLE IF NOT EXISTS asset_ohlcv(
    asset_id VARCHAR,
    exchange VARCHAR,
    symbol VARCHAR,
    interval VARCHAR,
    open_time_utc TIMESTAMPTZ,
    close_time_utc TIMESTAMPTZ,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    base_volume DOUBLE,
    quote_volume DOUBLE,
    trade_count BIGINT,
    taker_buy_base_volume DOUBLE,
    taker_buy_quote_volume DOUBLE,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(exchange, symbol, interval, open_time_utc)
);

CREATE TABLE IF NOT EXISTS crypto_global_daily(
    observation_date DATE,
    total_market_cap_usd DOUBLE,
    total_volume_usd DOUBLE,
    btc_dominance_pct DOUBLE,
    eth_dominance_pct DOUBLE,
    stablecoin_dominance_pct DOUBLE,
    active_asset_count INTEGER,
    markets_count INTEGER,
    source VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(observation_date, source)
);

CREATE TABLE IF NOT EXISTS stablecoin_supply_daily(
    stablecoin_id VARCHAR,
    symbol VARCHAR,
    stablecoin_name VARCHAR,
    observation_date DATE,
    chain VARCHAR,
    circulating_supply_usd DOUBLE,
    price_usd DOUBLE,
    peg_type VARCHAR,
    source VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(stablecoin_id, observation_date, chain, source)
);

CREATE TABLE IF NOT EXISTS chain_metrics_daily(
    chain_id VARCHAR,
    chain_name VARCHAR,
    observation_date DATE,
    tvl_usd DOUBLE,
    stablecoin_supply_usd DOUBLE,
    token_symbol VARCHAR,
    token_price_usd DOUBLE,
    source VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(chain_id, observation_date, source)
);

CREATE TABLE IF NOT EXISTS macro_series_catalog(
    series_key VARCHAR PRIMARY KEY,
    series_id VARCHAR,
    series_name VARCHAR,
    frequency VARCHAR,
    unit VARCHAR,
    source VARCHAR,
    active BOOLEAN
);

CREATE TABLE IF NOT EXISTS macro_observations(
    series_key VARCHAR,
    observation_date DATE,
    value DOUBLE,
    source VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(series_key, observation_date, source)
);

CREATE TABLE IF NOT EXISTS collection_runs(
    run_id VARCHAR PRIMARY KEY,
    module_name VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    successful_collectors INTEGER,
    failed_collectors INTEGER,
    rows_received BIGINT,
    rows_inserted BIGINT,
    rows_updated BIGINT,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS collection_results(
    result_id VARCHAR PRIMARY KEY,
    run_id VARCHAR,
    collector_name VARCHAR,
    provider_name VARCHAR,
    dataset_name VARCHAR,
    entity_key VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    duration_seconds DOUBLE,
    status VARCHAR,
    rows_received BIGINT,
    rows_inserted BIGINT,
    rows_updated BIGINT,
    error_type VARCHAR,
    error_message VARCHAR
);

CREATE TABLE IF NOT EXISTS data_quality_results(
    quality_result_id VARCHAR PRIMARY KEY,
    run_id VARCHAR,
    dataset_name VARCHAR,
    entity_key VARCHAR,
    check_name VARCHAR,
    check_status VARCHAR,
    observed_value VARCHAR,
    expected_value VARCHAR,
    details VARCHAR,
    checked_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS provider_health(
    health_id VARCHAR PRIMARY KEY,
    run_id VARCHAR,
    provider_name VARCHAR,
    provider_group VARCHAR,
    endpoint VARCHAR,
    checked_at_utc TIMESTAMPTZ,
    status VARCHAR,
    latency_ms DOUBLE,
    consecutive_failures INTEGER,
    error_type VARCHAR,
    error_message VARCHAR
);
"""

MIGRATIONS = [
    "ALTER TABLE assets ADD COLUMN IF NOT EXISTS coinbase_product VARCHAR",
    "ALTER TABLE assets ADD COLUMN IF NOT EXISTS kraken_pair VARCHAR",
    "ALTER TABLE collection_runs ADD COLUMN IF NOT EXISTS platform_version VARCHAR",
    "ALTER TABLE collection_results ADD COLUMN IF NOT EXISTS provider_name VARCHAR",
    "ALTER TABLE collection_results ADD COLUMN IF NOT EXISTS duration_seconds DOUBLE",
]

VIEWS = r"""
CREATE OR REPLACE VIEW latest_asset_market AS
SELECT * EXCLUDE(rn)
FROM (
    SELECT *,
        ROW_NUMBER() OVER(
            PARTITION BY asset_id
            ORDER BY observation_date DESC,
            CASE WHEN source='coingecko' THEN 1 ELSE 2 END
        ) rn
    FROM asset_market_daily
) x
WHERE rn=1;

CREATE OR REPLACE VIEW latest_chain_metrics AS
SELECT * EXCLUDE(rn)
FROM (
    SELECT *, ROW_NUMBER() OVER(
        PARTITION BY chain_id ORDER BY observation_date DESC
    ) rn
    FROM chain_metrics_daily
) x
WHERE rn=1;

CREATE OR REPLACE VIEW latest_macro_observations AS
SELECT * EXCLUDE(rn)
FROM (
    SELECT *, ROW_NUMBER() OVER(
        PARTITION BY series_key ORDER BY observation_date DESC
    ) rn
    FROM macro_observations
) x
WHERE rn=1;

CREATE OR REPLACE VIEW latest_provider_health AS
SELECT * EXCLUDE(rn)
FROM (
    SELECT *, ROW_NUMBER() OVER(
        PARTITION BY provider_name, provider_group
        ORDER BY checked_at_utc DESC
    ) rn
    FROM provider_health
) x
WHERE rn=1;

CREATE OR REPLACE VIEW current_provider_health AS
SELECT ph.*
FROM provider_health ph
JOIN (
    SELECT run_id
    FROM collection_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW asset_price_crosscheck AS
WITH cg AS (
    SELECT asset_id, observation_date, price_usd
    FROM asset_market_daily
    WHERE source='coingecko'
),
ex AS (
    SELECT asset_id, CAST(open_time_utc AS DATE) observation_date, close price_usd,
           exchange
    FROM asset_ohlcv
    WHERE interval='1d'
)
SELECT cg.asset_id, cg.observation_date, cg.price_usd coingecko_price,
       ex.exchange, ex.price_usd exchange_close,
       CASE WHEN cg.price_usd > 0
            THEN ABS(ex.price_usd-cg.price_usd)/cg.price_usd*100
       END deviation_pct
FROM cg
JOIN ex USING(asset_id, observation_date);
"""

TABLE_KEYS = {
    "asset_market_daily": ["asset_id", "observation_date", "source"],
    "asset_ohlcv": ["exchange", "symbol", "interval", "open_time_utc"],
    "crypto_global_daily": ["observation_date", "source"],
    "stablecoin_supply_daily": ["stablecoin_id", "observation_date", "chain", "source"],
    "chain_metrics_daily": ["chain_id", "observation_date", "source"],
    "macro_observations": ["series_key", "observation_date", "source"],
}

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def load_all() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    load_dotenv(ROOT / ".env")
    settings = yaml.safe_load((ROOT / "config/settings.yaml").read_text(encoding="utf-8"))
    assets = yaml.safe_load((ROOT / "config/assets.yaml").read_text(encoding="utf-8"))["assets"]
    return settings, assets

def path_for(settings: dict[str, Any], key: str) -> Path:
    if key == "database_path":
        override = os.getenv("CRYPTO_DATABASE_PATH", "").strip()

        if override:
            return Path(override).expanduser().resolve()

    p = Path(settings["platform"][key])
    return p if p.is_absolute() else ROOT / p

def configure_logger(settings: dict[str, Any]) -> logging.Logger:
    directory = path_for(settings, "log_directory")
    directory.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("crypto_platform")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | crypto_platform | %(message)s"
    )
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    log.addHandler(stream)
    file_handler = logging.FileHandler(
        directory / f"module1_{utcnow():%Y%m%d}.log", encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)
    return log

class HTTPClient:
    def __init__(self, settings: dict[str, Any]):
        config = settings["collection"]
        self.timeout = (
            config["request_connect_timeout_seconds"],
            config["request_read_timeout_seconds"],
        )
        self.retries = int(config["max_retries"])
        self.backoff = float(config["backoff_seconds"])
        self.ttl = int(config["cache_ttl_minutes"]) * 60
        self.cache = path_for(settings, "cache_directory")
        self.cache.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CryptoIntelligencePlatform/4.0",
            "Accept": "application/json",
        })

    def _cache_path(self, url: str, params: dict[str, Any] | None) -> Path:
        raw = json.dumps({"url": url, "params": params or {}}, sort_keys=True)
        return self.cache / f"{hashlib.sha256(raw.encode()).hexdigest()}.json"

    def request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_type: str = "json",
        use_cache: bool = False,
        retries: int | None = None,
    ) -> Any:
        cache_path = self._cache_path(url, params)
        if use_cache and cache_path.exists():
            if time.time() - cache_path.stat().st_mtime <= self.ttl:
                raw = cache_path.read_text(encoding="utf-8")
                return json.loads(raw) if response_type == "json" else raw

        last_error: Exception | None = None
        attempts = retries if retries is not None else self.retries
        for attempt in range(attempts):
            try:
                response = self.session.get(
                    url, params=params, headers=headers, timeout=self.timeout
                )
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", 0) or 0)
                    time.sleep(max(retry_after, self.backoff * 2**attempt))
                    continue
                response.raise_for_status()
                value = response.json() if response_type == "json" else response.text
                if use_cache:
                    cache_path.write_text(
                        json.dumps(value) if response_type == "json" else value,
                        encoding="utf-8",
                    )
                return value
            except Exception as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    time.sleep(self.backoff * 2**attempt)
        raise RuntimeError(f"GET failed after {attempts} attempts: {url}") from last_error

def connect(settings: dict[str, Any]) -> duckdb.DuckDBPyConnection:
    path = path_for(settings, "database_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(path))
    conn.execute(SCHEMA)
    for sql in MIGRATIONS:
        conn.execute(sql)
    conn.execute(VIEWS)
    return conn

def upsert(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    frame: pd.DataFrame,
    keys: list[str],
) -> tuple[int, int]:
    if frame is None or frame.empty:
        return 0, 0
    frame = frame.copy()
    conn.register("_stage", frame)
    condition = " AND ".join(f"t.{key}=s.{key}" for key in keys)
    updated = int(conn.execute(
        f"SELECT COUNT(*) FROM {table} t JOIN _stage s ON {condition}"
    ).fetchone()[0])
    columns = ",".join(frame.columns)
    conn.execute(
        f"INSERT OR REPLACE INTO {table}({columns}) SELECT {columns} FROM _stage"
    )
    conn.unregister("_stage")
    return len(frame) - updated, updated

def coingecko_setup() -> tuple[str, dict[str, str]]:
    pro = os.getenv("COINGECKO_PRO_API_KEY", "").strip()
    demo = os.getenv("COINGECKO_API_KEY", "").strip()
    if pro:
        return "https://pro-api.coingecko.com/api/v3", {"x-cg-pro-api-key": pro}
    return (
        "https://api.coingecko.com/api/v3",
        {"x-cg-demo-api-key": demo} if demo else {},
    )

@dataclass
class ProviderHealth:
    provider: str
    group: str
    endpoint: str
    status: str
    latency_ms: float
    error_type: str | None = None
    error_message: str | None = None

class Provider:
    name = "provider"
    group = "generic"
    endpoint = ""

    def __init__(self, http: HTTPClient):
        self.http = http

    def healthcheck(self) -> ProviderHealth:
        started = time.perf_counter()
        try:
            self._health_request()
            return ProviderHealth(
                self.name, self.group, self.endpoint, "ONLINE",
                (time.perf_counter() - started) * 1000,
            )
        except Exception as exc:
            return ProviderHealth(
                self.name, self.group, self.endpoint, "OFFLINE",
                (time.perf_counter() - started) * 1000,
                type(exc).__name__, str(exc)[:1000],
            )

    def _health_request(self) -> None:
        raise NotImplementedError

class CoinGeckoProvider(Provider):
    name = "coingecko"
    group = "market"

    def __init__(self, http: HTTPClient):
        super().__init__(http)
        self.base, self.headers = coingecko_setup()
        self.endpoint = self.base

    def _health_request(self) -> None:
        self.http.request(
            f"{self.base}/ping", headers=self.headers, retries=2
        )

    def collect_current_batch(self, assets: list[dict[str, Any]]) -> pd.DataFrame:
        ids = ",".join(a["coingecko_id"] for a in assets)
        payload = self.http.request(
            f"{self.base}/coins/markets",
            params={
                "vs_currency": "usd",
                "ids": ids,
                "sparkline": "false",
                "price_change_percentage": "24h",
            },
            headers=self.headers,
        )
        mapping = {a["coingecko_id"]: a["asset_id"] for a in assets}
        now = utcnow()
        rows = []
        for item in payload:
            rows.append({
                "asset_id": mapping[item["id"]],
                "observation_date": pd.to_datetime(
                    item.get("last_updated") or now, utc=True
                ).date(),
                "price_usd": item.get("current_price"),
                "market_cap_usd": item.get("market_cap"),
                "volume_24h_usd": item.get("total_volume"),
                "circulating_supply": item.get("circulating_supply"),
                "total_supply": item.get("total_supply"),
                "max_supply": item.get("max_supply"),
                "fully_diluted_value_usd": item.get("fully_diluted_valuation"),
                "market_cap_rank": item.get("market_cap_rank"),
                "ath_usd": item.get("ath"),
                "ath_change_pct": item.get("ath_change_percentage"),
                "source": self.name,
                "collected_at_utc": now,
            })
        return pd.DataFrame(rows)

    def collect_history(self, asset: dict[str, Any], days: int | str) -> pd.DataFrame:
        payload = self.http.request(
            f"{self.base}/coins/{asset['coingecko_id']}/market_chart",
            params={"vs_currency": "usd", "days": str(days), "interval": "daily"},
            headers=self.headers,
            use_cache=True,
        )
        prices = pd.DataFrame(payload.get("prices", []), columns=["timestamp", "price_usd"])
        caps = pd.DataFrame(payload.get("market_caps", []), columns=["timestamp", "market_cap_usd"])
        volumes = pd.DataFrame(payload.get("total_volumes", []), columns=["timestamp", "volume_24h_usd"])
        if prices.empty:
            return pd.DataFrame()
        frame = prices.merge(caps, on="timestamp", how="outer").merge(
            volumes, on="timestamp", how="outer"
        )
        frame["observation_date"] = pd.to_datetime(
            frame["timestamp"], unit="ms", utc=True
        ).dt.date
        frame = frame.groupby("observation_date", as_index=False).last()
        frame["asset_id"] = asset["asset_id"]
        for column in [
            "circulating_supply", "total_supply", "max_supply",
            "fully_diluted_value_usd", "market_cap_rank", "ath_usd",
            "ath_change_pct",
        ]:
            frame[column] = None
        frame["source"] = self.name
        frame["collected_at_utc"] = utcnow()
        return frame[[
            "asset_id", "observation_date", "price_usd", "market_cap_usd",
            "volume_24h_usd", "circulating_supply", "total_supply",
            "max_supply", "fully_diluted_value_usd", "market_cap_rank",
            "ath_usd", "ath_change_pct", "source", "collected_at_utc",
        ]]

    def collect_global(self) -> pd.DataFrame:
        data = self.http.request(
            f"{self.base}/global", headers=self.headers
        ).get("data", {})
        now = utcnow()
        caps = data.get("total_market_cap", {})
        volumes = data.get("total_volume", {})
        dominance = data.get("market_cap_percentage", {})
        total = float(caps.get("usd", 0) or 0)
        stable = sum(float(caps.get(s, 0) or 0) for s in [
            "usdt", "usdc", "dai", "usde", "fdusd"
        ])
        return pd.DataFrame([{
            "observation_date": now.date(),
            "total_market_cap_usd": caps.get("usd"),
            "total_volume_usd": volumes.get("usd"),
            "btc_dominance_pct": dominance.get("btc"),
            "eth_dominance_pct": dominance.get("eth"),
            "stablecoin_dominance_pct": stable / total * 100 if total else None,
            "active_asset_count": data.get("active_cryptocurrencies"),
            "markets_count": data.get("markets"),
            "source": self.name,
            "collected_at_utc": now,
        }])

class CoinbaseProvider(Provider):
    name = "coinbase"
    group = "exchange_ohlcv"
    endpoint = "https://api.exchange.coinbase.com"

    def _health_request(self) -> None:
        self.http.request(f"{self.endpoint}/time", retries=2)

    def collect(
        self, asset: dict[str, Any], start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        product = asset.get("coinbase_product")
        if not product:
            return pd.DataFrame()
        rows: list[list[Any]] = []
        cursor = pd.Timestamp(start).tz_convert("UTC") if pd.Timestamp(start).tzinfo else pd.Timestamp(start, tz="UTC")
        end = pd.Timestamp(end).tz_convert("UTC") if pd.Timestamp(end).tzinfo else pd.Timestamp(end, tz="UTC")
        # Coinbase permits at most 300 buckets. Use 290 daily buckets per request.
        while cursor < end:
            chunk_end = min(cursor + pd.Timedelta(days=290), end)
            batch = self.http.request(
                f"{self.endpoint}/products/{product}/candles",
                params={
                    "granularity": 86400,
                    "start": cursor.isoformat(),
                    "end": chunk_end.isoformat(),
                },
                retries=3,
            )
            rows.extend(batch or [])
            cursor = chunk_end + pd.Timedelta(seconds=1)
            time.sleep(0.12)
        if not rows:
            return pd.DataFrame()
        now = utcnow()
        frame = pd.DataFrame(rows, columns=[
            "timestamp", "low", "high", "open", "close", "base_volume"
        ])
        frame = frame.drop_duplicates("timestamp")
        frame["asset_id"] = asset["asset_id"]
        frame["exchange"] = self.name
        frame["symbol"] = product
        frame["interval"] = "1d"
        frame["open_time_utc"] = pd.to_datetime(frame["timestamp"], unit="s", utc=True)
        frame["close_time_utc"] = frame["open_time_utc"] + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
        for col in ["low", "high", "open", "close", "base_volume"]:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
        frame["quote_volume"] = frame["base_volume"] * frame["close"]
        frame["trade_count"] = None
        frame["taker_buy_base_volume"] = None
        frame["taker_buy_quote_volume"] = None
        frame["collected_at_utc"] = now
        return frame[[
            "asset_id", "exchange", "symbol", "interval", "open_time_utc",
            "close_time_utc", "open", "high", "low", "close", "base_volume",
            "quote_volume", "trade_count", "taker_buy_base_volume",
            "taker_buy_quote_volume", "collected_at_utc",
        ]].sort_values("open_time_utc")

class KrakenProvider(Provider):
    name = "kraken"
    group = "exchange_ohlcv"
    endpoint = "https://api.kraken.com"

    def _health_request(self) -> None:
        self.http.request(f"{self.endpoint}/0/public/Time", retries=2)

    def collect(
        self, asset: dict[str, Any], start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        pair = asset.get("kraken_pair")
        if not pair:
            return pd.DataFrame()
        since = int(pd.Timestamp(start, tz="UTC").timestamp()) if pd.Timestamp(start).tzinfo is None else int(pd.Timestamp(start).timestamp())
        payload = self.http.request(
            f"{self.endpoint}/0/public/OHLC",
            params={"pair": pair, "interval": 1440, "since": since},
            retries=3,
        )
        errors = payload.get("error") or []
        if errors:
            raise RuntimeError("; ".join(errors))
        result = payload.get("result", {})
        data_key = next((k for k in result if k != "last"), None)
        rows = result.get(data_key, []) if data_key else []
        if not rows:
            return pd.DataFrame()
        now = utcnow()
        records = []
        for row in rows:
            open_time = pd.to_datetime(int(row[0]), unit="s", utc=True)
            if open_time > pd.Timestamp(end):
                continue
            records.append({
                "asset_id": asset["asset_id"],
                "exchange": self.name,
                "symbol": pair,
                "interval": "1d",
                "open_time_utc": open_time,
                "close_time_utc": open_time + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "base_volume": float(row[6]),
                "quote_volume": float(row[6]) * float(row[4]),
                "trade_count": int(row[7]),
                "taker_buy_base_volume": None,
                "taker_buy_quote_volume": None,
                "collected_at_utc": now,
            })
        # Kraken includes the current, uncommitted candle. Remove it.
        frame = pd.DataFrame(records)
        if not frame.empty:
            frame = frame[frame["open_time_utc"] < pd.Timestamp.now(tz="UTC").normalize()]
        return frame

class BinanceProvider(Provider):
    name = "binance"
    group = "exchange_ohlcv"
    HOSTS = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]

    def __init__(self, http: HTTPClient):
        super().__init__(http)
        self.endpoint = self.HOSTS[0]
        self.live_host: str | None = None

    def _health_request(self) -> None:
        errors = []
        for host in self.HOSTS:
            try:
                self.http.request(f"{host}/api/v3/ping", retries=1)
                self.live_host = host
                self.endpoint = host
                return
            except Exception as exc:
                errors.append(f"{host}: {exc}")
        raise RuntimeError("No Binance public host was reachable. " + " | ".join(errors))

    def collect(
        self, asset: dict[str, Any], start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        if not self.live_host:
            self._health_request()
        symbol = asset.get("binance_symbol")
        if not symbol:
            return pd.DataFrame()
        start_ms = int(pd.Timestamp(start).timestamp() * 1000)
        end_ms = int(pd.Timestamp(end).timestamp() * 1000)
        rows = []
        while start_ms < end_ms:
            batch = self.http.request(
                f"{self.live_host}/api/v3/klines",
                params={
                    "symbol": symbol, "interval": "1d",
                    "startTime": start_ms, "endTime": end_ms, "limit": 1000,
                },
                retries=2,
            )
            if not batch:
                break
            rows.extend(batch)
            next_start = int(batch[-1][0]) + 1
            if next_start <= start_ms:
                break
            start_ms = next_start
            if len(batch) < 1000:
                break
        now = utcnow()
        return pd.DataFrame([{
            "asset_id": asset["asset_id"],
            "exchange": self.name,
            "symbol": symbol,
            "interval": "1d",
            "open_time_utc": pd.to_datetime(row[0], unit="ms", utc=True),
            "close_time_utc": pd.to_datetime(row[6], unit="ms", utc=True),
            "open": float(row[1]), "high": float(row[2]),
            "low": float(row[3]), "close": float(row[4]),
            "base_volume": float(row[5]), "quote_volume": float(row[7]),
            "trade_count": int(row[8]),
            "taker_buy_base_volume": float(row[9]),
            "taker_buy_quote_volume": float(row[10]),
            "collected_at_utc": now,
        } for row in rows])

class DefiLlamaProvider(Provider):
    name = "defillama"
    group = "ecosystem"
    endpoint = "https://api.llama.fi"

    def _health_request(self) -> None:
        self.http.request("https://api.llama.fi/v2/chains", retries=2)

    def stablecoins(self) -> pd.DataFrame:
        payload = self.http.request(
            "https://stablecoins.llama.fi/stablecoins",
            params={"includePrices": "true"},
            retries=3,
        )
        now = utcnow()
        rows = []
        for item in payload.get("peggedAssets", []):
            chains = item.get("chainCirculating") or {"all": item.get("circulating") or {}}
            for chain, values in chains.items():
                current = values.get("current") if isinstance(values, dict) else values
                if isinstance(current, dict):
                    supply = current.get("peggedUSD") or next(iter(current.values()), None)
                else:
                    supply = current
                rows.append({
                    "stablecoin_id": str(item.get("id")),
                    "symbol": item.get("symbol"),
                    "stablecoin_name": item.get("name"),
                    "observation_date": now.date(),
                    "chain": chain,
                    "circulating_supply_usd": supply,
                    "price_usd": item.get("price"),
                    "peg_type": item.get("pegType"),
                    "source": self.name,
                    "collected_at_utc": now,
                })
        return pd.DataFrame(rows)

    def chains(self) -> pd.DataFrame:
        payload = self.http.request(
            "https://api.llama.fi/v2/chains", retries=3
        )
        now = utcnow()
        return pd.DataFrame([{
            "chain_id": str(item.get("name", "")).lower().replace(" ", "-"),
            "chain_name": item.get("name"),
            "observation_date": now.date(),
            "tvl_usd": item.get("tvl"),
            "stablecoin_supply_usd": None,
            "token_symbol": item.get("tokenSymbol"),
            "token_price_usd": None,
            "source": self.name,
            "collected_at_utc": now,
        } for item in payload])



class MacroProvider:
    """Standalone macro collection using the official FRED API and local cache."""

    def __init__(self, settings: dict[str, Any], http: HTTPClient):
        self.settings = settings
        self.http = http

    def _finish(
        self,
        frame: pd.DataFrame,
        series: dict[str, Any],
        source: str,
    ) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame(columns=[
                "series_key", "observation_date", "value",
                "source", "collected_at_utc",
            ])
        frame = frame.copy()
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"], errors="coerce"
        ).dt.date
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        frame = frame.dropna(subset=["observation_date", "value"])
        frame["series_key"] = series["series_key"]
        frame["source"] = source
        frame["collected_at_utc"] = utcnow()
        return frame[[
            "series_key", "observation_date", "value",
            "source", "collected_at_utc",
        ]]

    def from_fred_api(
        self,
        series: dict[str, Any],
        start: str,
    ) -> pd.DataFrame:
        key = os.getenv("FRED_API_KEY", "").strip()
        if not key:
            raise RuntimeError("FRED_API_KEY is not configured.")
        payload = self.http.request(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": series["series_id"],
                "api_key": key,
                "file_type": "json",
                "observation_start": start,
            },
            retries=3,
        )
        frame = pd.DataFrame({
            "observation_date": [
                row.get("date") for row in payload.get("observations", [])
            ],
            "value": [
                row.get("value") for row in payload.get("observations", [])
            ],
        })
        return self._finish(frame, series, "fred_api")

    def from_local_crypto_cache(
        self,
        conn: duckdb.DuckDBPyConnection,
        series: dict[str, Any],
        start: str,
    ) -> pd.DataFrame:
        frame = conn.execute(
            """
            SELECT observation_date, value
            FROM macro_observations
            WHERE series_key = ?
              AND observation_date >= ?
            ORDER BY observation_date
            """,
            [series["series_key"], start],
        ).fetchdf()
        if frame.empty:
            raise RuntimeError(
                f"No locally cached observations exist for {series['series_id']}."
            )
        return self._finish(frame, series, "local_crypto_cache")


class Module1Runner:
    def __init__(self, full_refresh: bool = False):
        self.settings, self.assets = load_all()
        self.full_refresh = full_refresh
        self.log = configure_logger(self.settings)
        self.http = HTTPClient(self.settings)
        self.conn = connect(self.settings)
        self.run_id = str(uuid.uuid4())
        self.results: list[dict[str, Any]] = []
        self.health_rows: list[dict[str, Any]] = []
        self.failure_counts: dict[str, int] = {}
        self.coin_gecko = CoinGeckoProvider(self.http)
        self.defillama = DefiLlamaProvider(self.http)
        self.exchange_providers = {
            "coinbase": CoinbaseProvider(self.http),
            "kraken": KrakenProvider(self.http),
            "binance": BinanceProvider(self.http),
        }
        self.macro = MacroProvider(self.settings, self.http)

    def record_health(self, health: ProviderHealth) -> None:
        failures = self.failure_counts.get(health.provider, 0)
        failures = 0 if health.status == "ONLINE" else failures + 1
        self.failure_counts[health.provider] = failures
        row = {
            "health_id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "provider_name": health.provider,
            "provider_group": health.group,
            "endpoint": health.endpoint,
            "checked_at_utc": utcnow(),
            "status": health.status,
            "latency_ms": health.latency_ms,
            "consecutive_failures": failures,
            "error_type": health.error_type,
            "error_message": health.error_message,
        }
        self.health_rows.append(row)
        self.log.info(
            "provider_health::%s status=%s latency_ms=%.0f",
            health.provider, health.status, health.latency_ms
        )

    def execute(
        self,
        collector_name: str,
        provider_name: str,
        table: str,
        entity: str,
        function: Callable[[], pd.DataFrame],
    ) -> bool:
        started = utcnow()
        perf = time.perf_counter()
        result_id = str(uuid.uuid4())
        try:
            frame = function()
            inserted, updated = upsert(
                self.conn, table, frame, TABLE_KEYS[table]
            )
            status = "SUCCESS" if len(frame) else "NO_DATA"
            self.log.info(
                "%s::%s provider=%s received=%s inserted=%s updated=%s",
                collector_name, entity, provider_name,
                len(frame), inserted, updated,
            )
            self.results.append({
                "result_id": result_id, "run_id": self.run_id,
                "collector_name": collector_name,
                "provider_name": provider_name,
                "dataset_name": table, "entity_key": entity,
                "started_at_utc": started, "completed_at_utc": utcnow(),
                "duration_seconds": time.perf_counter() - perf,
                "status": status, "rows_received": len(frame),
                "rows_inserted": inserted, "rows_updated": updated,
                "error_type": None, "error_message": None,
            })
            return status == "SUCCESS"
        except Exception as exc:
            self.log.exception(
                "%s::%s provider=%s failed",
                collector_name, entity, provider_name,
            )
            self.results.append({
                "result_id": result_id, "run_id": self.run_id,
                "collector_name": collector_name,
                "provider_name": provider_name,
                "dataset_name": table, "entity_key": entity,
                "started_at_utc": started, "completed_at_utc": utcnow(),
                "duration_seconds": time.perf_counter() - perf,
                "status": "FAILED", "rows_received": 0,
                "rows_inserted": 0, "rows_updated": 0,
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:2000],
            })
            return False

    def seed_reference_data(self) -> None:
        assets = pd.DataFrame(self.assets)
        assets["active"] = True
        assets["created_at_utc"] = utcnow()
        upsert(self.conn, "assets", assets, ["asset_id"])
        catalog = pd.DataFrame(self.settings["macro_series"])
        catalog["source"] = "FRED"
        catalog["active"] = True
        upsert(self.conn, "macro_series_catalog", catalog, ["series_key"])

    def run_market(self) -> None:
        health = self.coin_gecko.healthcheck()
        self.record_health(health)
        if health.status != "ONLINE":
            return
        days = "max" if self.full_refresh else self.settings["collection"]["coingecko_history_days"]
        current = self.coin_gecko.collect_current_batch(self.assets)
        for asset in self.assets:
            self.execute(
                "market_history", "coingecko", "asset_market_daily",
                asset["symbol"],
                lambda asset=asset: self._combine_market(
                    self.coin_gecko.collect_history(asset, days),
                    current[current["asset_id"] == asset["asset_id"]],
                ),
            )
        self.execute(
            "global_market", "coingecko", "crypto_global_daily",
            "global", self.coin_gecko.collect_global,
        )

    @staticmethod
    def _combine_market(history: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
        if history.empty:
            return current.copy()
        if current.empty:
            return history
        return pd.concat([history, current], ignore_index=True).drop_duplicates(
            ["asset_id", "observation_date", "source"], keep="last"
        )

    def run_exchange_ohlcv(self) -> None:
        config = self.settings["providers"]["exchange_ohlcv"]
        if not config["enabled"]:
            return
        enabled = config["enabled_providers"]
        provider_status: dict[str, bool] = {}
        for name in config["priority"]:
            if not enabled.get(name, False):
                continue
            provider = self.exchange_providers[name]
            health = provider.healthcheck()
            self.record_health(health)
            provider_status[name] = health.status == "ONLINE"

        end = pd.Timestamp.now(tz="UTC").normalize()
        default_start = pd.Timestamp(
            self.settings["collection"]["exchange_start_date"], tz="UTC"
        )
        overlap = int(self.settings["collection"]["incremental_overlap_days"])

        for asset in self.assets:
            collected = False
            for name in config["priority"]:
                if not enabled.get(name, False) or not provider_status.get(name, False):
                    continue
                provider = self.exchange_providers[name]
                symbol_field = {
                    "coinbase": "coinbase_product",
                    "kraken": "kraken_pair",
                    "binance": "binance_symbol",
                }[name]
                symbol = asset.get(symbol_field)
                if not symbol:
                    continue
                start = default_start
                if not self.full_refresh:
                    latest = self.conn.execute(
                        """SELECT MAX(open_time_utc) FROM asset_ohlcv
                           WHERE exchange=? AND symbol=? AND interval='1d'""",
                        [name, symbol],
                    ).fetchone()[0]
                    if latest:
                        start = pd.Timestamp(latest) - pd.Timedelta(days=overlap)
                success = self.execute(
                    "exchange_ohlcv", name, "asset_ohlcv",
                    f"{asset['symbol']}:1d",
                    lambda provider=provider, asset=asset, start=start:
                        provider.collect(asset, start, end),
                )
                if success:
                    collected = True
                    break
            if not collected:
                self.log.warning(
                    "No exchange OHLC provider succeeded for %s.", asset["symbol"]
                )

    def run_ecosystem(self) -> None:
        health = self.defillama.healthcheck()
        self.record_health(health)
        if health.status != "ONLINE":
            return
        self.execute(
            "stablecoins", "defillama", "stablecoin_supply_daily",
            "stablecoins", self.defillama.stablecoins,
        )
        self.execute(
            "chains", "defillama", "chain_metrics_daily",
            "chains", self.defillama.chains,
        )



    def run_macro(self) -> None:
        config = self.settings["providers"]["macro"]
        if not config["enabled"]:
            return

        api_key_present = bool(os.getenv("FRED_API_KEY", "").strip())
        self.record_health(ProviderHealth(
            "fred_api",
            "macro",
            "https://api.stlouisfed.org/fred/series/observations",
            "AVAILABLE" if api_key_present else "NOT_CONFIGURED",
            0.0,
            None if api_key_present else "MissingCredential",
            None if api_key_present else (
                "FRED_API_KEY is not configured; existing crypto macro cache "
                "will be retained."
            ),
        ))

        overlap = int(self.settings["collection"]["incremental_overlap_days"])
        for series in self.settings["macro_series"]:
            last = None if self.full_refresh else self.conn.execute(
                """
                SELECT MAX(observation_date)
                FROM macro_observations
                WHERE series_key = ?
                """,
                [series["series_key"]],
            ).fetchone()[0]
            start = self.settings["collection"]["default_start_date"]
            if last:
                start = (last - timedelta(days=overlap)).isoformat()

            if api_key_present:
                success = self.execute(
                    "macro", "fred_api", "macro_observations",
                    series["series_id"],
                    lambda series=series, start=start:
                        self.macro.from_fred_api(series, start),
                )
                if success:
                    continue

            # Local cache is an intentional non-network fallback. It is not
            # recorded as a failed collector when unavailable.
            cached = self.conn.execute(
                "SELECT COUNT(*) FROM macro_observations WHERE series_key=?",
                [series["series_key"]],
            ).fetchone()[0]
            if cached:
                self.log.info(
                    "macro::%s provider=local_crypto_cache retained=%s",
                    series["series_id"], cached,
                )
            else:
                self.log.warning(
                    "macro::%s skipped; no FRED key and no local cache.",
                    series["series_id"],
                )

    def finish(self) -> dict[str, Any]:
        if self.results:
            upsert(
                self.conn, "collection_results",
                pd.DataFrame(self.results), ["result_id"]
            )
        if self.health_rows:
            upsert(
                self.conn, "provider_health",
                pd.DataFrame(self.health_rows), ["health_id"]
            )
        failures = sum(row["status"] == "FAILED" for row in self.results)
        successes = sum(row["status"] in {"SUCCESS", "NO_DATA"} for row in self.results)
        status = "SUCCESS" if failures == 0 else (
            "PARTIAL_SUCCESS" if successes else "FAILED"
        )
        received = sum(row["rows_received"] for row in self.results)
        inserted = sum(row["rows_inserted"] for row in self.results)
        updated = sum(row["rows_updated"] for row in self.results)
        notes = (
            f"{successes} successes; {failures} failures; "
            f"{received} rows received; {inserted} inserted; {updated} updated"
        )
        self.conn.execute(
            """UPDATE collection_runs
               SET completed_at_utc=?, status=?, successful_collectors=?,
                   failed_collectors=?, rows_received=?, rows_inserted=?,
                   rows_updated=?, notes=?, platform_version='4.0.0'
               WHERE run_id=?""",
            [utcnow(), status, successes, failures, received, inserted,
             updated, notes, self.run_id],
        )
        self.conn.close()
        return {
            "run_id": self.run_id, "status": status,
            "successful_collectors": successes,
            "failed_collectors": failures,
            "received": received, "inserted": inserted, "updated": updated,
            "database_path": str(path_for(self.settings, "database_path")),
        }

    def run(self) -> dict[str, Any]:
        self.conn.execute(
            """INSERT INTO collection_runs
               (run_id,module_name,started_at_utc,status,successful_collectors,
                failed_collectors,rows_received,rows_inserted,rows_updated,
                notes,platform_version)
               VALUES (?,?,?,'RUNNING',0,0,0,0,0,NULL,'4.0.0')""",
            [self.run_id, "module1", utcnow()],
        )
        self.seed_reference_data()
        self.run_market()
        self.run_exchange_ohlcv()
        self.run_ecosystem()
        self.run_macro()
        return self.finish()

def run_module1(full_refresh: bool = False) -> dict[str, Any]:
    return Module1Runner(full_refresh=full_refresh).run()
