from crypto_platform.platform import (
    load_all, connect, path_for
)
from crypto_platform.module19 import MODULE19_SCHEMA

EXPORTS = {
    "latest_feature_validation_refreshed":
        "SELECT * FROM "
        "latest_feature_validation_refreshed",
    "feature_validation_refreshed":
        "SELECT * FROM feature_validation_refreshed",
    "latest_feature_rolling_validation":
        "SELECT * FROM "
        "latest_feature_rolling_validation",
    "feature_rolling_validation":
        "SELECT * FROM feature_rolling_validation",
    "latest_grouped_permutation_importance":
        "SELECT * FROM "
        "latest_grouped_permutation_importance",
    "grouped_feature_permutation_importance":
        "SELECT * FROM "
        "grouped_feature_permutation_importance",
    "latest_feature_registry":
        "SELECT * FROM latest_feature_registry",
    "production_feature_candidates":
        "SELECT * FROM production_feature_candidates",
    "feature_registry":
        "SELECT * FROM feature_registry",
    "feature_registry_history":
        "SELECT * FROM feature_registry_history",
    "module19_runs":
        "SELECT * FROM module19_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE19_SCHEMA)
    directory = path_for(
        settings, "export_directory"
    )
    directory.mkdir(
        parents=True, exist_ok=True
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
