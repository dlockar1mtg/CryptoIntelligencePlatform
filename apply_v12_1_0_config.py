from pathlib import Path
import shutil
import yaml


ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


MODULE43 = {
    "material_change_threshold": 20.0,
    "scale_in_score": 52.0,
    "buy_score": 65.0,
    "strong_buy_score": 78.0,
    "minimum_upgrade_confidence": 0.45,
    "buy_confidence": 0.55,
    "minimum_upgrade_30d_return": 0.0,
    "minimum_upgrade_3m_return": 2.0,
    "downgrade_score": 35.0,
    "downgrade_30d_return": -20.0,
}


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS}"
        )

    backup = SETTINGS.with_name(
        "settings_before_v12_1_0.yaml"
    )
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS.read_text(encoding="utf-8")
    )
    settings["module43"] = MODULE43

    if "platform" in settings:
        settings["platform"]["version"] = "12.1.0"

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    print("v12.1.0 configuration applied.")
    print(
        "Module 43 institutional decision "
        "thresholds installed."
    )


if __name__ == "__main__":
    main()
