from pathlib import Path
import shutil
import yaml


ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


MODULE40 = {
    "minimum_matured_forecasts": 30,
    "retraining_mae_multiplier": 1.25,
}

MODULE39_UPDATES = {
    "minimum_calibration_rows": 30,
    "minimum_total_calibration_rows": 180,
    "minimum_stability_snapshots": 5,
}


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS}"
        )

    backup = SETTINGS.with_name(
        "settings_before_v10_2_0.yaml"
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
    settings["module40"] = MODULE40

    module39 = settings.setdefault(
        "module39",
        {},
    )
    module39.update(MODULE39_UPDATES)
    validation = module39.setdefault(
        "validation",
        {},
    )
    validation[
        "minimum_realized_scorecards"
    ] = 6

    if "platform" in settings:
        settings["platform"]["version"] = "10.2.0"

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print("v10.2.0 configuration applied.")
    print("v10.1.1 evidence-aware validation settings applied.")


if __name__ == "__main__":
    main()
