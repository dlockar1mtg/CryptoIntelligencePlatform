from pathlib import Path
import shutil
import yaml


ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


CONFIG = {
    "lookback_days": 365,
    "covariance_ridge": 0.000001,
    "frontier_points": 25,
    "expected_returns": {
        "historical_weight": 0.40,
        "regime_weight": 0.40,
        "prior_weight": 0.20,
    },
    "constraints": {
        "minimum_asset_weight": 0.00,
        "maximum_asset_weight": 0.025,
        "minimum_cash_weight": 0.75,
        "maximum_risky_exposure": 0.25,
    },
    "optimization": {
        "turnover_penalty": 12.0,
        "concentration_penalty": 0.75,
        "risk_aversion": 2.5,
    },
    "validation": {
        "maximum_concentration_pct": 40.0,
        "maximum_turnover_pct": 25.0,
    },
}


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS}"
        )

    backup = SETTINGS.with_name(
        "settings_before_v9_2_0.yaml"
    )
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS.read_text(encoding="utf-8")
    )
    settings["module37"] = CONFIG
    if "platform" in settings:
        settings["platform"]["version"] = "9.2.0"

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print("v9.2.0 configuration applied.")


if __name__ == "__main__":
    main()
