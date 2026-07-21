from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module27 import MODULE27_SCHEMA

EXPORTS = {
    "latest_m27_research_summary":
        "SELECT * FROM latest_m27_research_summary",
    "latest_m27_representation_features":
        "SELECT * FROM latest_m27_representation_features",
    "latest_m27_random_search":
        "SELECT * FROM latest_m27_random_search",
    "latest_m27_nested_predictions":
        "SELECT * FROM latest_m27_nested_predictions",
    "latest_m27_fold_summary":
        "SELECT * FROM latest_m27_fold_summary",
    "latest_m27_calibration_summary":
        "SELECT * FROM latest_m27_calibration_summary",
    "latest_m27_empirical_sensitivity":
        "SELECT * FROM latest_m27_empirical_sensitivity",
    "module27_runs":
        "SELECT * FROM module27_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE27_SCHEMA)
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
