from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(SETTINGS)
    backup = SETTINGS.with_name("settings_before_v13_0_0.yaml")
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")
    settings = yaml.safe_load(SETTINGS.read_text(encoding="utf-8"))
    settings["module44"] = {
        "minimum_matured_decisions": 30,
        "neutral_action_tolerance_pct": 2.0,
    }
    if "platform" in settings:
        settings["platform"]["version"] = "13.0.0"
    SETTINGS.write_text(yaml.safe_dump(settings, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print("v13.0.0 configuration applied.")
    print("Module 44 economic value thresholds installed.")


if __name__ == "__main__":
    main()
