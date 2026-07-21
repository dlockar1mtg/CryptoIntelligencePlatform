from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module33 import MODULE33_SCHEMA


EXPORTS = {
    "latest_m33_validation_summary":
        "SELECT * FROM latest_m33_validation_summary",
    "latest_m33_probability_regularization":
        "SELECT * FROM latest_m33_probability_regularization",
    "latest_m33_adjusted_probability_drift":
        "SELECT * FROM latest_m33_adjusted_probability_drift",
    "latest_m33_decision_candidates":
        "SELECT * FROM latest_m33_decision_candidates",
    "latest_m33_optimized_daily":
        "SELECT * FROM latest_m33_optimized_daily",
    "latest_m33_cost_sensitivity":
        "SELECT * FROM latest_m33_cost_sensitivity",
    "latest_m33_benchmark_comparison":
        "SELECT * FROM latest_m33_benchmark_comparison",
    "module33_runs":
        "SELECT * FROM module33_runs",
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE33_SCHEMA)
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
