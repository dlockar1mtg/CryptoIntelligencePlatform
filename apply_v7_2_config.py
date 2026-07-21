from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"

CONFIG = {
    "models": {
        "random_state": 720,
    },
    "random_search": {
        "seed": 720,
        "candidates_per_fold": 240,
    },
    "nested_walk_forward": {
        "minimum_training_days": 540,
        "inner_validation_days": 120,
        "outer_test_days": 90,
    },
    "sensitivity": {
        "candidates_per_scenario": 80,
    },
    "validation": {
        "minimum_nested_agreement_pct": 55,
        "maximum_calibrated_mae": 0.15,
        "minimum_empirical_stability_pct": 75,
    },
}

def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(f"Missing settings: {SETTINGS}")
    backup = SETTINGS.with_name("settings_before_v7_2.yaml")
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")
    settings = yaml.safe_load(SETTINGS.read_text(encoding="utf-8"))
    settings["module27"] = CONFIG
    if "platform" in settings:
        settings["platform"]["version"] = "7.2.0"
    SETTINGS.write_text(
        yaml.safe_dump(settings, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print("v7.2 configuration applied.")

if __name__ == "__main__":
    main()
