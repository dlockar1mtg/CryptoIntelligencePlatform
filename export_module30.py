from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.ml.registry import EXPERIMENT_REGISTRY_SCHEMA


EXPORTS = {
    "latest_clean_regime_current":
        "SELECT * FROM latest_clean_regime_current",
    "latest_clean_probability_current":
        "SELECT * FROM latest_clean_probability_current",
    "latest_clean_regime_history":
        "SELECT * FROM latest_clean_regime_history",
    "latest_clean_probability_history":
        "SELECT * FROM latest_clean_probability_history",
    "latest_clean_feature_contributions":
        "SELECT * FROM latest_clean_feature_contributions",
    "latest_clean_feature_drift":
        "SELECT * FROM latest_clean_feature_drift",
    "latest_clean_legacy_benchmark":
        "SELECT * FROM latest_clean_legacy_benchmark",
    "latest_clean_validation_folds":
        "SELECT * FROM latest_clean_validation_folds",
    "latest_clean_model_disagreement":
        "SELECT * FROM latest_clean_model_disagreement",
    "module30_runs":
        "SELECT * FROM module30_runs",
    "ml_experiment_registry":
        "SELECT * FROM ml_experiment_registry",
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(EXPERIMENT_REGISTRY_SCHEMA)
    conn.execute(MODULE30_SCHEMA)
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
