from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module14 import MODULE14_SCHEMA

EXPORTS = {
    "latest_score_validation":
        "SELECT * FROM latest_score_validation",
    "historical_score_validation":
        "SELECT * FROM historical_score_validation",
    "latest_score_validation_summary":
        "SELECT * FROM latest_score_validation_summary",
    "score_validation_summary":
        "SELECT * FROM score_validation_summary",
    "latest_portfolio_backtest_periods":
        "SELECT * FROM latest_portfolio_backtest_periods",
    "portfolio_backtest_periods":
        "SELECT * FROM portfolio_backtest_periods",
    "latest_portfolio_backtest_summary":
        "SELECT * FROM latest_portfolio_backtest_summary",
    "portfolio_backtest_summary":
        "SELECT * FROM portfolio_backtest_summary",
    "latest_portfolio_regime_validation":
        "SELECT * FROM latest_portfolio_regime_validation",
    "portfolio_regime_validation":
        "SELECT * FROM portfolio_regime_validation",
    "module14_runs":
        "SELECT * FROM module14_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE14_SCHEMA)
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
