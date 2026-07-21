from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module38 import MODULE38_SCHEMA


EXPORTS = {
    "latest_m38_asset_forecasts":
        "SELECT * FROM latest_m38_asset_forecasts",
    "latest_m38_model_validation":
        "SELECT * FROM latest_m38_model_validation",
    "latest_m38_regime_transitions":
        "SELECT * FROM latest_m38_regime_transitions",
    "latest_m38_forecast_attribution":
        "SELECT * FROM latest_m38_forecast_attribution",
    "latest_m38_portfolio_forecast":
        "SELECT * FROM latest_m38_portfolio_forecast",
    "latest_m38_predictive_expected_returns":
        "SELECT * FROM latest_m38_predictive_expected_returns",
    "module38_runs":
        "SELECT * FROM module38_runs",
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE38_SCHEMA)
    directory = path_for(
        settings,
        "export_directory",
    )
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for name, sql in EXPORTS.items():
        frame = conn.execute(sql).fetchdf()
        output = directory / f"{name}.csv"
        frame.to_csv(output, index=False)
        print(
            f"{name}: {len(frame)} rows -> {output}"
        )

    conn.close()


if __name__ == "__main__":
    main()
