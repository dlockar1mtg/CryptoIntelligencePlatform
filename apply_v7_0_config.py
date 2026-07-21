from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"

CONFIG = {
    "features": {
        "minimum_completeness_pct": 70,
    },
    "models": {
        "minimum_model_rows": 365,
        "random_state": 700,
    },
    "ensemble": {
        "gmm_weight": 0.35,
        "kmeans_weight": 0.20,
        "rule_weight": 0.35,
        "change_weight": 0.10,
        "probability_smoothing": 0.75,
    },
    "validation": {
        "minimum_classified_days": 365,
        "minimum_mean_confidence": 0.22,
        "maximum_daily_switch_rate": 0.20,
        "minimum_mean_model_agreement": 0.40,
        "minimum_reproducibility_pct": 100,
    },
}

def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS}"
        )

    backup = SETTINGS.with_name(
        "settings_before_v7_0.yaml"
    )
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS.read_text(encoding="utf-8")
    )
    settings["module25"] = CONFIG
    if "platform" in settings:
        settings["platform"]["version"] = "7.0.0"

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print("v7.0 configuration applied.")

if __name__ == "__main__":
    main()
