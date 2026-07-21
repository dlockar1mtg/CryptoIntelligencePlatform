from pathlib import Path
import tempfile
import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect, upsert
from crypto_platform.module2 import Module2Runner, MODULE2_SCHEMA
from crypto_platform.module3 import Module3Runner, MODULE3_SCHEMA

def main():
    settings, assets = load_all()
    with tempfile.TemporaryDirectory() as temp:
        settings["platform"]["database_path"] = str(Path(temp) / "test.duckdb")
        settings["module3"]["portfolio"]["monthly_contribution_usd"] = 1000
        conn = connect(settings)
        conn.execute(MODULE2_SCHEMA)
        conn.execute(MODULE3_SCHEMA)

        asset_frame = pd.DataFrame(assets)
        asset_frame["active"] = True
        asset_frame["created_at_utc"] = pd.Timestamp.now(tz="UTC")
        upsert(conn, "assets", asset_frame, ["asset_id"])

        dates = pd.date_range("2023-01-01", periods=900, freq="D")
        market_rows = []
        ohlcv_rows = []
        rng = np.random.default_rng(42)
        for i, asset in enumerate(assets):
            daily = rng.normal(0.0006 + i * 0.00003, 0.025 + i * 0.003, len(dates))
            prices = 100 * np.exp(np.cumsum(daily))
            for date, price in zip(dates, prices):
                market_rows.append({
                    "asset_id": asset["asset_id"],
                    "observation_date": date.date(),
                    "price_usd": float(price),
                    "market_cap_usd": float(price * (2e7 + i * 1e8)),
                    "volume_24h_usd": float(price * (8e5 + i * 1e5)),
                    "circulating_supply": None, "total_supply": None,
                    "max_supply": None, "fully_diluted_value_usd": None,
                    "market_cap_rank": i + 1,
                    "ath_usd": float(max(prices) * 1.05),
                    "ath_change_pct": float((price / (max(prices) * 1.05) - 1) * 100),
                    "source": "coingecko",
                    "collected_at_utc": pd.Timestamp.now(tz="UTC"),
                })
                ohlcv_rows.append({
                    "asset_id": asset["asset_id"], "exchange": "coinbase",
                    "symbol": asset["coinbase_product"], "interval": "1d",
                    "open_time_utc": pd.Timestamp(date, tz="UTC"),
                    "close_time_utc": pd.Timestamp(date, tz="UTC") + pd.Timedelta(days=1),
                    "open": float(price * 0.995), "high": float(price * 1.01),
                    "low": float(price * 0.99), "close": float(price * 1.002),
                    "base_volume": 1000.0, "quote_volume": float(price * 1000),
                    "trade_count": 100, "taker_buy_base_volume": None,
                    "taker_buy_quote_volume": None,
                    "collected_at_utc": pd.Timestamp.now(tz="UTC"),
                })
        upsert(conn, "asset_market_daily", pd.DataFrame(market_rows),
               ["asset_id", "observation_date", "source"])
        upsert(conn, "asset_ohlcv", pd.DataFrame(ohlcv_rows),
               ["exchange", "symbol", "interval", "open_time_utc"])

        global_rows = pd.DataFrame([{
            "observation_date": d.date(),
            "total_market_cap_usd": 2e12 * (1.0004 ** n),
            "total_volume_usd": 8e10 * (1.0002 ** n),
            "btc_dominance_pct": 52.0,
            "eth_dominance_pct": 18.0,
            "stablecoin_dominance_pct": 6.0,
            "active_asset_count": 10000, "markets_count": 800,
            "source": "coingecko",
            "collected_at_utc": pd.Timestamp.now(tz="UTC"),
        } for n, d in enumerate(dates)])
        upsert(conn, "crypto_global_daily", global_rows,
               ["observation_date", "source"])

        macro_specs = {
            "FRED::DFF": 4.0, "FRED::DGS10": 4.2, "FRED::DFII10": 1.8,
            "FRED::T10YIE": 2.4, "FRED::M2SL": 21000,
            "FRED::DTWEXBGS": 120, "FRED::VIXCLS": 18,
            "FRED::BAMLH0A0HYM2": 3.5, "FRED::UNRATE": 4.1,
        }
        macro_rows = []
        for key, base in macro_specs.items():
            freq = "MS" if key in {"FRED::M2SL", "FRED::UNRATE"} else "D"
            md = pd.date_range("2022-01-01", periods=48 if freq == "MS" else 1300, freq=freq)
            for n, d in enumerate(md):
                macro_rows.append({
                    "series_key": key, "observation_date": d.date(),
                    "value": float(base + n * 0.001),
                    "source": "fred_api",
                    "collected_at_utc": pd.Timestamp.now(tz="UTC"),
                })
        upsert(conn, "macro_observations", pd.DataFrame(macro_rows),
               ["series_key", "observation_date", "source"])
        conn.close()

        m2 = Module2Runner()
        m2.conn.close()
        m2.settings = settings
        m2.assets = assets
        m2.conn = connect(settings)
        m2.conn.execute(MODULE2_SCHEMA)
        result2 = m2.run()
        assert result2["status"] == "SUCCESS"

        m3 = Module3Runner()
        m3.conn.close()
        m3.settings = settings
        m3.assets = assets
        m3.config = settings["module3"]
        m3.conn = connect(settings)
        m3.conn.execute(MODULE2_SCHEMA)
        m3.conn.execute(MODULE3_SCHEMA)
        result3 = m3.run()
        assert result3["status"] == "SUCCESS"
        assert result3["assets_analyzed"] == 6

        check = connect(settings)
        assert check.execute(
            "SELECT COUNT(*) FROM latest_portfolio_recommendations"
        ).fetchone()[0] == 6
        total = check.execute(
            "SELECT SUM(target_weight) FROM latest_portfolio_recommendations"
        ).fetchone()[0]
        cash = check.execute(
            "SELECT cash_weight FROM latest_portfolio_summary"
        ).fetchone()[0]
        assert abs((total + cash) - 1.0) < 1e-6
        assert check.execute(
            "SELECT COUNT(*) FROM latest_scenario_projections"
        ).fetchone()[0] == 54
        min_conf, max_conf = check.execute(
            "SELECT MIN(confidence),MAX(confidence) FROM latest_asset_signals"
        ).fetchone()
        assert 35 <= min_conf <= max_conf <= 95
        check.close()
    print("Crypto v1.3 Module 1/2/3 smoke test passed.")

if __name__ == "__main__":
    main()
