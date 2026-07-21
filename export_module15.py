from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module15 import MODULE15_SCHEMA

EXPORTS = {
    "latest_strategy_variant_results":
        "SELECT * FROM latest_strategy_variant_results",
    "strategy_variant_results":
        "SELECT * FROM strategy_variant_results",
    "latest_walk_forward_selection":
        "SELECT * FROM latest_walk_forward_selection",
    "walk_forward_selection":
        "SELECT * FROM walk_forward_selection",
    "latest_benchmark_comparison":
        "SELECT * FROM latest_benchmark_comparison",
    "benchmark_comparison":
        "SELECT * FROM benchmark_comparison",
    "latest_calibrated_strategy_recommendation":
        "SELECT * FROM latest_calibrated_strategy_recommendation",
    "calibrated_strategy_recommendation":
        "SELECT * FROM calibrated_strategy_recommendation",
    "module15_runs":
        "SELECT * FROM module15_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE15_SCHEMA)
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
