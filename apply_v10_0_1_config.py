from pathlib import Path
import shutil
import yaml


ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


MODULE38 = {
    "horizons_days": [7, 30, 90, 180, 365],
    "portfolio_summary_horizon_days": 90,
    "minimum_training_rows": 450,
    "validation_rows": 120,
    "absolute_minimum_training_rows": 160,
    "minimum_validation_rows": 45,
    "maximum_validation_share": 0.25,
    "random_state": 1000,
    "transition_smoothing": 1.0,
    "regime_adjustment_strength": 0.03,
    "optimizer_feedback": {
        "predictive_weight": 0.35,
    },
}


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS}"
        )

    backup = SETTINGS.with_name(
        "settings_before_v10_0_0.yaml"
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
    settings["module38"] = MODULE38

    module37 = settings.setdefault(
        "module37",
        {},
    )
    validation = module37.setdefault(
        "validation",
        {},
    )
    validation[
        "minimum_active_share_for_ir_pct"
    ] = 5.0

    if "platform" in settings:
        settings["platform"]["version"] = "10.0.0"

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print("v10.0.1 configuration applied.")
    print("v9.2.1 stabilization settings applied.")


if __name__ == "__main__":
    main()
