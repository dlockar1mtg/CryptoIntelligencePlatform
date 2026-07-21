from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module22 import MODULE22_SCHEMA

EXPORTS = {
    "latest_intelligence_features": "SELECT * FROM latest_intelligence_features",
    "intelligence_features_daily": "SELECT * FROM intelligence_features_daily",
    "latest_intelligence_model_comparison":
        "SELECT * FROM latest_intelligence_model_comparison",
    "intelligence_model_comparison":
        "SELECT * FROM intelligence_model_comparison",
    "latest_ensemble_regime": "SELECT * FROM latest_ensemble_regime",
    "ensemble_regime_daily": "SELECT * FROM ensemble_regime_daily",
    "latest_six_asset_allocations": "SELECT * FROM latest_six_asset_allocations",
    "six_asset_allocations": "SELECT * FROM six_asset_allocations",
    "latest_intelligence_walk_forward":
        "SELECT * FROM latest_intelligence_walk_forward",
    "intelligence_walk_forward_folds":
        "SELECT * FROM intelligence_walk_forward_folds",
    "latest_intelligence_portfolio_periods":
        "SELECT * FROM latest_intelligence_portfolio_periods",
    "intelligence_portfolio_periods":
        "SELECT * FROM intelligence_portfolio_periods",
    "latest_intelligence_portfolio_summary":
        "SELECT * FROM latest_intelligence_portfolio_summary",
    "intelligence_portfolio_summary":
        "SELECT * FROM intelligence_portfolio_summary",
    "module22_runs": "SELECT * FROM module22_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE22_SCHEMA)
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
