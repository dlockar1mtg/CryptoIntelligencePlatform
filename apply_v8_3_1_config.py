from pathlib import Path
import shutil
import yaml


ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


CONFIG = {
    "transaction_cost_bps": 10,
    "cost_sensitivity_bps": [10, 25, 50],
    "drift": {
        "rolling_reference_days": 180,
        "window_days": [30, 60, 90],
    },
    "optimization": {
        "temperatures": [1.20, 1.50, 1.80],
        "probability_floors": [0.01, 0.025],
        "switch_margins": [0.05, 0.10, 0.15],
        "minimum_hold_days": [7, 14, 30],
        "confidence_floors": [0.30, 0.40, 0.50],
        "maximum_risk_exposures": [0.60, 0.80, 1.00],
    },
    "validation": {
        "maximum_turnover_pct": 250,
        "minimum_cost_pass_rate_pct": 66.67,
    },
}


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS}"
        )

    backup = SETTINGS.with_name(
        "settings_before_v8_3_1.yaml"
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
    settings["module33"] = CONFIG
    if "platform" in settings:
        settings["platform"]["version"] = "8.3.1"

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print("v8.3.1 configuration applied.")


if __name__ == "__main__":
    main()
