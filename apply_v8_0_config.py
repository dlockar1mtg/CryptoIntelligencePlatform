from pathlib import Path
import shutil
import yaml


ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


CONFIG = {
    "models": {
        "random_state": 800,
    },
    "feature_evidence": {
        "minimum_coverage": 0.70,
        "permutation_repeats": 8,
    },
    "walk_forward": {
        "minimum_training_days": 540,
        "test_days": 90,
    },
    "bootstrap": {
        "iterations": 300,
        "top_features_per_iteration": 8,
        "seed": 800,
    },
    "rolling": {
        "window_days": 365,
        "step_days": 90,
        "permutation_repeats": 5,
    },
    "selection": {
        "minimum_stability_score": 55,
        "minimum_positive_fold_rate_pct": 40,
        "minimum_bootstrap_selection_rate_pct": 30,
        "maximum_stable_features": 8,
        "minimum_core_features": 5,
        "maximum_pairwise_correlation": 0.88,
    },
    "validation": {
        "minimum_stable_model_accuracy_pct": 55,
        "minimum_worst_fold_accuracy_pct": 20,
        "maximum_representation_features": 2,
    },
}


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS}"
        )

    backup = SETTINGS.with_name(
        "settings_before_v8_0.yaml"
    )
    if not backup.exists():
        shutil.copy2(
            SETTINGS,
            backup,
        )
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS.read_text(encoding="utf-8")
    )
    settings["module29"] = CONFIG
    if "platform" in settings:
        settings["platform"]["version"] = "8.0.0"

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print("v8.0 configuration applied.")


if __name__ == "__main__":
    main()
