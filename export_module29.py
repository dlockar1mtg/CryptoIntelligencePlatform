from crypto_platform.platform import (
    load_all,
    connect,
    path_for,
)
from crypto_platform.module29 import MODULE29_SCHEMA


EXPORTS = {
    "latest_m29_research_summary":
        "SELECT * FROM latest_m29_research_summary",
    "latest_m29_feature_registry":
        "SELECT * FROM latest_m29_feature_registry",
    "latest_m29_walk_forward_importance":
        "SELECT * FROM latest_m29_walk_forward_importance",
    "latest_m29_bootstrap_stability":
        "SELECT * FROM latest_m29_bootstrap_stability",
    "latest_m29_rolling_importance":
        "SELECT * FROM latest_m29_rolling_importance",
    "latest_m29_regime_feature_importance":
        "SELECT * FROM latest_m29_regime_feature_importance",
    "latest_m29_feature_ablation":
        "SELECT * FROM latest_m29_feature_ablation",
    "latest_m29_minimal_model_validation":
        "SELECT * FROM latest_m29_minimal_model_validation",
    "module29_runs":
        "SELECT * FROM module29_runs",
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE29_SCHEMA)
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
