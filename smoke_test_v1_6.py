from pathlib import Path
import tempfile
import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect, upsert
from crypto_platform.module2 import Module2Runner, MODULE2_SCHEMA
from crypto_platform.module3 import Module3Runner, MODULE3_SCHEMA
from crypto_platform.module5 import Module5Runner, MODULE5_SCHEMA
from crypto_platform.module6 import Module6Runner, MODULE6_SCHEMA

def main():
    settings, assets = load_all()
    with tempfile.TemporaryDirectory() as temp:
        settings["platform"]["database_path"] = str(Path(temp) / "test.duckdb")
        settings["module6"]["snapshots"]["history_days"] = 500
        conn = connect(settings)
        for schema in [MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA, MODULE6_SCHEMA]:
            conn.execute(schema)

        asset_frame = pd.DataFrame(assets)
        asset_frame["active"] = True
        asset_frame["created_at_utc"] = pd.Timestamp.now(tz="UTC")
        upsert(conn, "assets", asset_frame, ["asset_id"])

        dates = pd.date_range("2020-01-01", periods=2200, freq="D")
        rng = np.random.default_rng(11)
        market_rows, ohlcv_rows = [], []
        for i, asset in enumerate(assets):
            daily = rng.normal(0.00035+i*0.00002, 0.02+i*0.002, len(dates))
            prices = 100*np.exp(np.cumsum(daily))
            for n, (d,p) in enumerate(zip(dates, prices)):
                if n >= len(dates)-365:
                    market_rows.append({
                        "asset_id": asset["asset_id"], "observation_date": d.date(),
                        "price_usd": float(p), "market_cap_usd": float(p*(2e7+i*1e8)),
                        "volume_24h_usd": float(p*(8e5+i*1e5)),
                        "circulating_supply": None, "total_supply": None, "max_supply": None,
                        "fully_diluted_value_usd": None, "market_cap_rank": i+1,
                        "ath_usd": float(max(prices)),
                        "ath_change_pct": float((p/max(prices)-1)*100),
                        "source": "coingecko",
                        "collected_at_utc": pd.Timestamp.now(tz="UTC"),
                    })
                ohlcv_rows.append({
                    "asset_id": asset["asset_id"], "exchange": "coinbase",
                    "symbol": asset["coinbase_product"], "interval": "1d",
                    "open_time_utc": pd.Timestamp(d, tz="UTC"),
                    "close_time_utc": pd.Timestamp(d, tz="UTC")+pd.Timedelta(days=1),
                    "open": float(p*.995), "high": float(p*1.01), "low": float(p*.99),
                    "close": float(p), "base_volume": 1000.0,
                    "quote_volume": float(p*1000), "trade_count": 100,
                    "taker_buy_base_volume": None, "taker_buy_quote_volume": None,
                    "collected_at_utc": pd.Timestamp.now(tz="UTC"),
                })
        upsert(conn, "asset_market_daily", pd.DataFrame(market_rows),
               ["asset_id","observation_date","source"])
        upsert(conn, "asset_ohlcv", pd.DataFrame(ohlcv_rows),
               ["exchange","symbol","interval","open_time_utc"])

        global_rows = pd.DataFrame([{
            "observation_date": d.date(), "total_market_cap_usd": 2e12*(1.0002**n),
            "total_volume_usd": 8e10*(1.0001**n), "btc_dominance_pct": 52.0,
            "eth_dominance_pct": 18.0, "stablecoin_dominance_pct": 6.0,
            "active_asset_count": 10000, "markets_count": 800, "source": "coingecko",
            "collected_at_utc": pd.Timestamp.now(tz="UTC"),
        } for n,d in enumerate(dates[-500:])])
        upsert(conn, "crypto_global_daily", global_rows, ["observation_date","source"])

        macro_specs = {
            "FRED::DFF":4.0,"FRED::DGS10":4.2,"FRED::DFII10":1.8,
            "FRED::T10YIE":2.4,"FRED::M2SL":21000,"FRED::DTWEXBGS":120,
            "FRED::VIXCLS":18,"FRED::BAMLH0A0HYM2":3.5,"FRED::UNRATE":4.1,
        }
        macro_rows=[]
        for key,base in macro_specs.items():
            freq="MS" if key in {"FRED::M2SL","FRED::UNRATE"} else "D"
            md=pd.date_range("2019-01-01", periods=90 if freq=="MS" else 2600, freq=freq)
            for n,d in enumerate(md):
                macro_rows.append({
                    "series_key":key,"observation_date":d.date(),
                    "value":float(base+n*.0005),"source":"fred_api",
                    "collected_at_utc":pd.Timestamp.now(tz="UTC"),
                })
        upsert(conn,"macro_observations",pd.DataFrame(macro_rows),
               ["series_key","observation_date","source"])
        conn.close()

        m6 = Module6Runner()
        m6.conn.close(); m6.settings=settings; m6.assets=assets
        m6.config=settings["module6"]; m6.conn=connect(settings)
        for schema in [MODULE2_SCHEMA,MODULE3_SCHEMA,MODULE5_SCHEMA,MODULE6_SCHEMA]:
            m6.conn.execute(schema)
        sync = m6.run("sync")
        assert sync["canonical_rows"] >= 6*2000

        m2=Module2Runner(); m2.conn.close(); m2.settings=settings; m2.assets=assets
        m2.conn=connect(settings); m2.conn.execute(MODULE2_SCHEMA)
        assert m2.run()["status"]=="SUCCESS"

        m3=Module3Runner(); m3.conn.close(); m3.settings=settings; m3.assets=assets
        m3.config=settings["module3"]; m3.module4=settings["module4"]
        m3.conn=connect(settings); m3.conn.execute(MODULE2_SCHEMA); m3.conn.execute(MODULE3_SCHEMA)
        assert m3.run()["status"]=="SUCCESS"

        m5=Module5Runner(); m5.conn.close(); m5.settings=settings; m5.assets=assets
        m5.config=settings["module5"]; m5.conn=connect(settings)
        for schema in [MODULE2_SCHEMA,MODULE3_SCHEMA,MODULE5_SCHEMA,MODULE6_SCHEMA]:
            m5.conn.execute(schema)
        assert m5.run()["status"]=="SUCCESS"

        research=Module6Runner(); research.conn.close()
        research.settings=settings; research.assets=assets; research.config=settings["module6"]
        research.conn=connect(settings)
        for schema in [MODULE2_SCHEMA,MODULE3_SCHEMA,MODULE5_SCHEMA,MODULE6_SCHEMA]:
            research.conn.execute(schema)
        result=research.run("research")
        assert result["snapshots_created"] > 0
        assert result["validations_created"] > 0

        check=connect(settings)
        coverage=check.execute(
            "SELECT MIN(row_count),MAX(row_count) FROM canonical_history_coverage"
        ).fetchone()
        assert coverage[0] >= 2000
        assert check.execute("SELECT COUNT(*) FROM model_snapshots_daily").fetchone()[0] > 0
        assert check.execute("SELECT COUNT(*) FROM signal_forward_performance").fetchone()[0] > 0
        check.close()
    print("Crypto v1.6 historical intelligence smoke test passed.")

if __name__=="__main__":
    main()
