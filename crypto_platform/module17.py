from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA
from crypto_platform.module12 import MODULE12_SCHEMA
from crypto_platform.module13 import MODULE13_SCHEMA
from crypto_platform.module14 import MODULE14_SCHEMA
from crypto_platform.module15 import MODULE15_SCHEMA
from crypto_platform.module16 import MODULE16_SCHEMA

MODULE17_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module17_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    fear_greed_rows INTEGER,
    manual_etf_rows INTEGER,
    feature_rows INTEGER,
    validation_rows INTEGER,
    ready_features INTEGER,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS external_feature_observations(
    feature_key VARCHAR,
    observation_date DATE,
    value DOUBLE,
    unit VARCHAR,
    source VARCHAR,
    source_quality VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(feature_key, observation_date, source)
);

CREATE TABLE IF NOT EXISTS crypto_features_daily(
    observation_date DATE PRIMARY KEY,
    btc_price_usd DOUBLE,
    btc_return_30d_pct DOUBLE,
    btc_dominance_pct DOUBLE,
    btc_dominance_proxy_pct DOUBLE,
    total_market_cap_usd DOUBLE,
    total2_market_cap_proxy_usd DOUBLE,
    total3_market_cap_proxy_usd DOUBLE,
    stablecoin_supply_usd DOUBLE,
    stablecoin_growth_30d_pct DOUBLE,
    fear_greed_index DOUBLE,
    etf_net_flow_usd DOUBLE,
    core_breadth_above_sma50_pct DOUBLE,
    core_median_return_30d_pct DOUBLE,
    dollar_index DOUBLE,
    high_yield_spread DOUBLE,
    vix DOUBLE,
    macro_liquidity_score DOUBLE,
    risk_appetite_score DOUBLE,
    available_feature_count INTEGER,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS feature_validation_results(
    run_id VARCHAR,
    feature_key VARCHAR,
    forward_horizon_days INTEGER,
    sample_count INTEGER,
    pearson_correlation DOUBLE,
    spearman_correlation DOUBLE,
    top_quartile_forward_return_pct DOUBLE,
    bottom_quartile_forward_return_pct DOUBLE,
    top_minus_bottom_pct DOUBLE,
    directional_hit_rate_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key, forward_horizon_days)
);

CREATE TABLE IF NOT EXISTS feature_readiness(
    run_id VARCHAR,
    feature_key VARCHAR,
    first_date DATE,
    latest_date DATE,
    history_days INTEGER,
    non_null_count INTEGER,
    non_null_pct DOUBLE,
    best_absolute_spearman DOUBLE,
    readiness_status VARCHAR,
    limitation VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key)
);

CREATE OR REPLACE VIEW latest_crypto_features AS
SELECT * FROM crypto_features_daily ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_feature_validation AS
SELECT v.* FROM feature_validation_results v
JOIN (SELECT run_id FROM module17_runs ORDER BY started_at_utc DESC LIMIT 1) r
USING(run_id)
ORDER BY ABS(spearman_correlation) DESC NULLS LAST;

CREATE OR REPLACE VIEW latest_feature_readiness AS
SELECT f.* FROM feature_readiness f
JOIN (SELECT run_id FROM module17_runs ORDER BY started_at_utc DESC LIMIT 1) r
USING(run_id)
ORDER BY readiness_status, best_absolute_spearman DESC;
"""

CORE_IDS = ["bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche"]

def utcnow():
    return datetime.now(timezone.utc)

def safe_pct(current, prior):
    if prior is None or pd.isna(prior) or float(prior) == 0:
        return None
    return (float(current) / float(prior) - 1) * 100

class Module17Runner:
    def __init__(self):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA, MODULE6_SCHEMA,
            MODULE7_SCHEMA, MODULE8_SCHEMA, MODULE9_SCHEMA, MODULE10_SCHEMA,
            MODULE11_SCHEMA, MODULE12_SCHEMA, MODULE13_SCHEMA,
            MODULE14_SCHEMA, MODULE15_SCHEMA, MODULE16_SCHEMA, MODULE17_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.cfg = self.settings["module17"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CryptoIntelligencePlatform/4.2"})

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m17_stage", frame)
        cols = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _m17_stage"
        )
        self.conn.unregister("_m17_stage")

    def collect_fear_greed(self):
        if not self.cfg["feature_collection"]["fear_greed_enabled"]:
            return 0
        url = self.cfg["feature_collection"]["fear_greed_url"]
        try:
            response = self.session.get(
                url,
                params={"limit": 0, "format": "json"},
                timeout=int(self.cfg["feature_collection"]["request_timeout_seconds"]),
            )
            response.raise_for_status()
            payload = response.json()
            rows = []
            for item in payload.get("data", []):
                timestamp = pd.to_datetime(
                    int(item["timestamp"]), unit="s", utc=True
                )
                value = pd.to_numeric(item.get("value"), errors="coerce")
                if pd.isna(value):
                    continue
                rows.append({
                    "feature_key": "FEAR_GREED_INDEX",
                    "observation_date": timestamp.date(),
                    "value": float(value),
                    "unit": "index_0_100",
                    "source": "alternative_me",
                    "source_quality": "PUBLIC_API",
                    "collected_at_utc": utcnow(),
                })
            frame = pd.DataFrame(rows)
            self.upsert("external_feature_observations", frame)
            return len(frame)
        except Exception:
            return 0

    def import_manual_etf(self):
        configured = Path(self.cfg["manual_inputs"]["etf_flows_csv"])
        if not configured.is_absolute():
            configured = Path.cwd() / configured
        if not configured.exists():
            return 0
        frame = pd.read_csv(configured)
        required = {"observation_date", "net_flow_usd"}
        if not required.issubset(frame.columns):
            raise ValueError(
                f"ETF flow file must contain columns: {sorted(required)}"
            )
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"], errors="coerce"
        ).dt.date
        frame["value"] = pd.to_numeric(
            frame["net_flow_usd"], errors="coerce"
        )
        frame = frame.dropna(subset=["observation_date", "value"])
        source = (
            frame["source"].astype(str)
            if "source" in frame.columns
            else pd.Series(["manual_validated"] * len(frame))
        )
        output = pd.DataFrame({
            "feature_key": "US_SPOT_CRYPTO_ETF_NET_FLOW_USD",
            "observation_date": frame["observation_date"],
            "value": frame["value"],
            "unit": "usd",
            "source": source,
            "source_quality": "MANUAL_VALIDATED",
            "collected_at_utc": utcnow(),
        })
        self.upsert("external_feature_observations", output)
        return len(output)

    def build_features(self):
        market = self.conn.execute("""
            SELECT asset_id, observation_date, price_usd,
                   market_cap_usd, volume_24h_usd
            FROM canonical_market_daily
            WHERE asset_id IN (
                'bitcoin','ethereum','solana','chainlink','xrp','avalanche'
            )
              AND price_usd IS NOT NULL
            ORDER BY observation_date, asset_id
        """).fetchdf()
        if market.empty:
            raise RuntimeError(
                "No canonical core history. Run Module 1 and Module 6 sync."
            )
        market["observation_date"] = pd.to_datetime(market["observation_date"])
        dates = sorted(market["observation_date"].unique())
        price = market.pivot(
            index="observation_date", columns="asset_id", values="price_usd"
        ).sort_index()
        caps = market.pivot(
            index="observation_date", columns="asset_id", values="market_cap_usd"
        ).sort_index()

        # External/global inputs.
        external = self.conn.execute("""
            SELECT feature_key, observation_date, value
            FROM external_feature_observations
        """).fetchdf()
        if not external.empty:
            external["observation_date"] = pd.to_datetime(
                external["observation_date"]
            )
            ext = external.pivot_table(
                index="observation_date", columns="feature_key",
                values="value", aggfunc="last"
            ).sort_index()
        else:
            ext = pd.DataFrame(index=price.index)

        global_frame = self.conn.execute("""
            SELECT observation_date, total_market_cap_usd,
                   btc_dominance_pct
            FROM crypto_global_daily
            QUALIFY ROW_NUMBER() OVER(
                PARTITION BY observation_date ORDER BY collected_at_utc DESC
            )=1
        """).fetchdf()
        if not global_frame.empty:
            global_frame["observation_date"] = pd.to_datetime(
                global_frame["observation_date"]
            )
            global_frame = global_frame.set_index("observation_date")
        else:
            global_frame = pd.DataFrame(index=price.index)

        stable = self.conn.execute("""
            SELECT observation_date,
                   SUM(circulating_supply_usd) AS stablecoin_supply_usd
            FROM stablecoin_supply_daily
            GROUP BY observation_date
            ORDER BY observation_date
        """).fetchdf()
        if not stable.empty:
            stable["observation_date"] = pd.to_datetime(stable["observation_date"])
            stable = stable.set_index("observation_date")
        else:
            stable = pd.DataFrame(index=price.index)

        macro = self.conn.execute("""
            SELECT series_key, observation_date, value
            FROM macro_observations
            WHERE series_key IN (
                'FRED::DTWEXBGS','FRED::VIXCLS','FRED::BAMLH0A0HYM2'
            )
            QUALIFY ROW_NUMBER() OVER(
                PARTITION BY series_key, observation_date
                ORDER BY collected_at_utc DESC
            )=1
        """).fetchdf()
        if not macro.empty:
            macro["observation_date"] = pd.to_datetime(macro["observation_date"])
            macro = macro.pivot(
                index="observation_date", columns="series_key", values="value"
            ).sort_index()
        else:
            macro = pd.DataFrame(index=price.index)

        index = price.index
        ext = ext.reindex(index).ffill()
        global_frame = global_frame.reindex(index).ffill()
        stable = stable.reindex(index).ffill()
        macro = macro.reindex(index).ffill()

        btc = price.get("bitcoin")
        core_cap = caps.sum(axis=1, min_count=1)
        btc_cap = caps.get("bitcoin")
        eth_cap = caps.get("ethereum")
        btc_dom_proxy = btc_cap / core_cap * 100
        total2 = core_cap - btc_cap
        total3 = core_cap - btc_cap - eth_cap

        sma_days = int(self.cfg["feature_engineering"]["breadth_sma_days"])
        sma = price.rolling(sma_days, min_periods=max(20, sma_days // 2)).mean()
        breadth = (price > sma).sum(axis=1) / price.notna().sum(axis=1) * 100
        return30 = price.pct_change(30) * 100
        median_return30 = return30.median(axis=1)
        btc_return30 = btc.pct_change(30) * 100

        stable_supply = (
            stable["stablecoin_supply_usd"]
            if "stablecoin_supply_usd" in stable.columns
            else pd.Series(index=index, dtype=float)
        )
        stable_growth = stable_supply.pct_change(
            int(self.cfg["feature_engineering"]["stablecoin_growth_days"])
        ) * 100

        fear = ext.get("FEAR_GREED_INDEX", pd.Series(index=index, dtype=float))
        etf = ext.get(
            "US_SPOT_CRYPTO_ETF_NET_FLOW_USD",
            pd.Series(index=index, dtype=float),
        )
        dxy = macro.get("FRED::DTWEXBGS", pd.Series(index=index, dtype=float))
        vix = macro.get("FRED::VIXCLS", pd.Series(index=index, dtype=float))
        hy = macro.get(
            "FRED::BAMLH0A0HYM2", pd.Series(index=index, dtype=float)
        )

        def rolling_score(series, positive=True):
            mean = series.rolling(365, min_periods=60).mean()
            std = series.rolling(365, min_periods=60).std().replace(0, np.nan)
            z = (series - mean) / std
            if not positive:
                z = -z
            return (50 + z * 15).clip(0, 100)

        macro_scores = pd.concat([
            rolling_score(dxy, positive=False),
            rolling_score(vix, positive=False),
            rolling_score(hy, positive=False),
        ], axis=1)
        macro_liquidity = macro_scores.mean(axis=1)

        component_scores = pd.concat([
            fear,
            breadth,
            (50 + btc_return30).clip(0, 100),
            (50 + stable_growth * 5).clip(0, 100),
            macro_liquidity,
        ], axis=1)
        risk_appetite = component_scores.mean(axis=1)

        rows = []
        for date in index:
            values = {
                "observation_date": date.date(),
                "btc_price_usd": btc.get(date),
                "btc_return_30d_pct": btc_return30.get(date),
                "btc_dominance_pct": global_frame.get(
                    "btc_dominance_pct", pd.Series(dtype=float)
                ).get(date),
                "btc_dominance_proxy_pct": btc_dom_proxy.get(date),
                "total_market_cap_usd": global_frame.get(
                    "total_market_cap_usd", pd.Series(dtype=float)
                ).get(date),
                "total2_market_cap_proxy_usd": total2.get(date),
                "total3_market_cap_proxy_usd": total3.get(date),
                "stablecoin_supply_usd": stable_supply.get(date),
                "stablecoin_growth_30d_pct": stable_growth.get(date),
                "fear_greed_index": fear.get(date),
                "etf_net_flow_usd": etf.get(date),
                "core_breadth_above_sma50_pct": breadth.get(date),
                "core_median_return_30d_pct": median_return30.get(date),
                "dollar_index": dxy.get(date),
                "high_yield_spread": hy.get(date),
                "vix": vix.get(date),
                "macro_liquidity_score": macro_liquidity.get(date),
                "risk_appetite_score": risk_appetite.get(date),
                "calculated_at_utc": utcnow(),
            }
            feature_values = [
                v for k, v in values.items()
                if k not in {"observation_date", "calculated_at_utc"}
            ]
            values["available_feature_count"] = sum(
                pd.notna(v) for v in feature_values
            )
            rows.append(values)
        frame = pd.DataFrame(rows)
        self.upsert("crypto_features_daily", frame)
        return frame

    def validate(self, features):
        numeric_features = [
            "btc_dominance_pct", "btc_dominance_proxy_pct",
            "total2_market_cap_proxy_usd", "total3_market_cap_proxy_usd",
            "stablecoin_growth_30d_pct", "fear_greed_index",
            "etf_net_flow_usd", "core_breadth_above_sma50_pct",
            "core_median_return_30d_pct", "dollar_index",
            "high_yield_spread", "vix", "macro_liquidity_score",
            "risk_appetite_score",
        ]
        horizons = self.cfg["validation"]["forward_horizons_days"]
        rows = []
        f = features.copy()
        f["observation_date"] = pd.to_datetime(f["observation_date"])
        f = f.sort_values("observation_date")
        for horizon in horizons:
            f[f"forward_{horizon}"] = (
                f["btc_price_usd"].shift(-int(horizon))
                / f["btc_price_usd"] - 1
            ) * 100
            for key in numeric_features:
                pair = f[[key, f"forward_{horizon}"]].dropna()
                if len(pair) < int(self.cfg["validation"]["minimum_observations"]):
                    continue
                pearson = pair[key].corr(pair[f"forward_{horizon}"])
                spearman = pair[key].rank().corr(
                    pair[f"forward_{horizon}"].rank()
                )
                q1 = pair[key].quantile(.25)
                q3 = pair[key].quantile(.75)
                bottom = pair.loc[
                    pair[key] <= q1, f"forward_{horizon}"
                ].mean()
                top = pair.loc[
                    pair[key] >= q3, f"forward_{horizon}"
                ].mean()
                centered = pair[key] - pair[key].median()
                direction = np.sign(centered) == np.sign(
                    pair[f"forward_{horizon}"]
                )
                rows.append({
                    "run_id": self.run_id,
                    "feature_key": key,
                    "forward_horizon_days": int(horizon),
                    "sample_count": len(pair),
                    "pearson_correlation": float(pearson),
                    "spearman_correlation": float(spearman),
                    "top_quartile_forward_return_pct": float(top),
                    "bottom_quartile_forward_return_pct": float(bottom),
                    "top_minus_bottom_pct": float(top - bottom),
                    "directional_hit_rate_pct": float(direction.mean() * 100),
                    "calculated_at_utc": utcnow(),
                })
        frame = pd.DataFrame(rows)
        self.upsert("feature_validation_results", frame)
        return frame

    def readiness(self, features, validation):
        exclude = {
            "observation_date", "btc_price_usd", "calculated_at_utc",
            "available_feature_count",
        }
        keys = [c for c in features.columns if c not in exclude]
        total = len(features)
        rows = []
        for key in keys:
            non_null = int(features[key].notna().sum())
            valid_dates = pd.to_datetime(
                features.loc[features[key].notna(), "observation_date"]
            )
            first = valid_dates.min().date() if len(valid_dates) else None
            latest = valid_dates.max().date() if len(valid_dates) else None
            history_days = (
                (valid_dates.max() - valid_dates.min()).days + 1
                if len(valid_dates) else 0
            )
            subset = validation[validation["feature_key"] == key]
            best = (
                float(subset["spearman_correlation"].abs().max())
                if not subset.empty else 0.0
            )
            pct = non_null / total * 100 if total else 0
            min_days = int(self.cfg["readiness"]["minimum_history_days"])
            min_pct = float(self.cfg["readiness"]["minimum_non_null_pct"])
            if history_days >= min_days and pct >= min_pct and best >= 0.05:
                status = "READY_FOR_RESEARCH"
                limitation = None
            elif non_null == 0:
                status = "NO_DATA"
                limitation = "No observations available."
            else:
                status = "LIMITED"
                limitation = (
                    f"history_days={history_days}; non_null_pct={pct:.1f}; "
                    f"best_abs_spearman={best:.3f}"
                )
            rows.append({
                "run_id": self.run_id,
                "feature_key": key,
                "first_date": first,
                "latest_date": latest,
                "history_days": history_days,
                "non_null_count": non_null,
                "non_null_pct": pct,
                "best_absolute_spearman": best,
                "readiness_status": status,
                "limitation": limitation,
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert("feature_readiness", frame)
        return frame

    def run(self):
        self.conn.execute("""
            UPDATE module17_runs SET status='FAILED',completed_at_utc=?,
            notes=COALESCE(notes,'') || '; interrupted prior run'
            WHERE status='RUNNING'
        """, [utcnow()])
        self.conn.execute("""
            INSERT INTO module17_runs VALUES
            (?, ?, NULL, 'RUNNING', 0, 0, 0, 0, 0, NULL, '4.2.0')
        """, [self.run_id, self.started])
        try:
            fear_rows = self.collect_fear_greed()
            etf_rows = self.import_manual_etf()
            features = self.build_features()
            validation = self.validate(features)
            readiness = self.readiness(features, validation)
            ready = int(
                (readiness["readiness_status"] == "READY_FOR_RESEARCH").sum()
            )
            notes = (
                "ETF flows require validated manual input when no licensed "
                "historical provider is configured."
            )
            self.conn.execute("""
                UPDATE module17_runs SET completed_at_utc=?,status='SUCCESS',
                fear_greed_rows=?,manual_etf_rows=?,feature_rows=?,
                validation_rows=?,ready_features=?,notes=?
                WHERE run_id=?
            """, [
                utcnow(), fear_rows, etf_rows, len(features),
                len(validation), ready, notes, self.run_id,
            ])
            self.conn.close()
            return {
                "run_id": self.run_id,
                "status": "SUCCESS",
                "fear_greed_rows": fear_rows,
                "manual_etf_rows": etf_rows,
                "feature_rows": len(features),
                "validation_rows": len(validation),
                "ready_features": ready,
            }
        except Exception as exc:
            self.conn.execute("""
                UPDATE module17_runs SET completed_at_utc=?,status='FAILED',
                notes=? WHERE run_id=?
            """, [utcnow(), str(exc)[:1000], self.run_id])
            self.conn.close()
            raise

def run_module17():
    return Module17Runner().run()
