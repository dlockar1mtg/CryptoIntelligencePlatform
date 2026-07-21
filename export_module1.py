from crypto_platform.platform import load_all, connect, path_for

EXPORTS = [
    "assets", "latest_asset_market", "asset_market_daily", "asset_ohlcv",
    "crypto_global_daily", "stablecoin_supply_daily",
    "latest_chain_metrics", "chain_metrics_daily",
    "macro_series_catalog", "macro_observations",
    "latest_macro_observations", "collection_runs",
    "collection_results", "provider_health",
    "latest_provider_health", "asset_price_crosscheck",
]

def main():
    settings, _ = load_all()
    conn = connect(settings)
    directory = path_for(settings, "export_directory")
    directory.mkdir(parents=True, exist_ok=True)
    for name in EXPORTS:
        frame = conn.execute(f"SELECT * FROM {name}").fetchdf()
        output = directory / f"{name}.csv"
        frame.to_csv(output, index=False)
        print(f"{name}: {len(frame)} rows -> {output}")
    conn.close()

if __name__ == "__main__":
    main()
