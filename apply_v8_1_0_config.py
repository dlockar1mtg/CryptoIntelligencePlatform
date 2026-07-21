from pathlib import Path
import shutil
import yaml


ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


CONFIG = {
    "features": {
        "minimum_stable_features": 5,
    },
    "models": {
        "random_state": 810,
        "gradient_weight_candidates": [
            0.00,
            0.25,
            0.50,
            0.60,
            0.75,
            1.00,
        ],
    },
    "validation": {
        "minimum_training_days": 540,
        "internal_validation_days": 120,
        "outer_test_days": 90,
    },
    "drift": {
        "recent_window_days": 90,
    },
    "promotion": {
        "minimum_accuracy_pct": 55,
        "maximum_log_loss": 1.50,
        "minimum_outer_folds": 4,
        "minimum_observation_days": 180,
    },
}


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS}"
        )

    backup = SETTINGS.with_name(
        "settings_before_v8_1_0.yaml"
    )
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS.read_text(encoding="utf-8")
    )
    settings["module30"] = CONFIG
    if "platform" in settings:
        settings["platform"]["version"] = "8.1.0"

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print("v8.1.0 configuration applied.")


if __name__ == "__main__":
    main()
