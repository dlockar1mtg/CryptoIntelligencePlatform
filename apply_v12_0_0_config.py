from pathlib import Path
import shutil
import yaml


ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


MODULE42 = {
    "historical_lookback_days": 730,
    "minimum_matured_for_live": 30,
    "minimum_cash_portfolio_pct": 75.0,
    "maximum_asset_portfolio_pct": 8.0,
    "long_range_neutral_annual_return": 0.08,
    "long_range_weights": {
        "forecast": 0.35,
        "historical": 0.25,
        "neutral_prior": 0.40,
    },
    "maximum_regime_annual_adjustment": 0.12,
    "minimum_long_range_annual_return": -0.35,
    "maximum_long_range_annual_return": 0.60,
    "maximum_projection_volatility": 1.25,
    "scenario_standard_deviations": 1.0,
    "confidence_half_life_days": 730,
}


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS}"
        )

    backup = SETTINGS.with_name(
        "settings_before_v12_0_0.yaml"
    )
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS.read_text(encoding="utf-8")
    )
    settings["module42"] = MODULE42

    if "platform" in settings:
        settings["platform"]["version"] = "12.0.0"

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    print("v12.0.0 configuration applied.")
    print(
        "Module 42 decision and projection "
        "settings installed."
    )


if __name__ == "__main__":
    main()
