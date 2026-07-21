from pathlib import Path
import shutil
import yaml


ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(f"Missing settings: {SETTINGS}")

    backup = SETTINGS.with_name(
        "settings_before_v8_1_1.yaml"
    )
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS.read_text(encoding="utf-8")
    )
    module30 = settings.setdefault("module30", {})
    promotion = module30.setdefault("promotion", {})
    promotion.setdefault("minimum_accuracy_pct", 55)
    promotion.setdefault("maximum_log_loss", 1.50)
    promotion.setdefault("minimum_outer_folds", 4)
    promotion.setdefault("minimum_observation_days", 180)

    confidence = module30.setdefault("confidence", {})
    confidence["high_probability"] = 0.70
    confidence["high_agreement"] = 0.80
    confidence["moderate_probability"] = 0.50
    confidence["moderate_agreement"] = 0.55

    if "platform" in settings:
        settings["platform"]["version"] = "8.1.1"

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print("v8.1.1 stabilization configuration applied.")


if __name__ == "__main__":
    main()
