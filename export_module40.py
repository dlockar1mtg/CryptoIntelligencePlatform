from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module40 import MODULE40_SCHEMA


EXPORTS = {
    "latest_m40_memory_summary":
        "SELECT * FROM latest_m40_memory_summary",
    "latest_m40_forecast_memory":
        "SELECT * FROM latest_m40_forecast_memory",
    "latest_m40_pending_forecasts":
        "SELECT * FROM latest_m40_pending_forecasts",
    "latest_m40_matured_forecasts":
        "SELECT * FROM latest_m40_matured_forecasts",
    "latest_m40_learning_summary":
        "SELECT * FROM latest_m40_learning_summary",
    "latest_m40_calibration_curve":
        "SELECT * FROM latest_m40_calibration_curve",
    "latest_m40_model_leaderboard":
        "SELECT * FROM latest_m40_model_leaderboard",
    "latest_m40_retraining_recommendations":
        "SELECT * FROM latest_m40_retraining_recommendations",
    "module40_runs":
        "SELECT * FROM module40_runs",
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE40_SCHEMA)
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
