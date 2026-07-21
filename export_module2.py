from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA

EXPORTS = {
    "latest_asset_signals": "SELECT * FROM latest_asset_signals",
    "asset_signals_daily": "SELECT * FROM asset_signals_daily",
    "latest_macro_regime": "SELECT * FROM latest_macro_regime",
    "macro_regime_daily": "SELECT * FROM macro_regime_daily",
    "latest_market_regime": "SELECT * FROM latest_market_regime",
    "market_regime_daily": "SELECT * FROM market_regime_daily",
    "score_components": "SELECT * FROM score_components",
    "module2_runs": "SELECT * FROM module2_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE2_SCHEMA)
    directory = path_for(settings, "export_directory")
    directory.mkdir(parents=True, exist_ok=True)
    for name, sql in EXPORTS.items():
        frame = conn.execute(sql).fetchdf()
        output = directory / f"{name}.csv"
        frame.to_csv(output, index=False)
        print(f"{name}: {len(frame)} rows -> {output}")
    conn.close()

if __name__ == "__main__":
    main()
