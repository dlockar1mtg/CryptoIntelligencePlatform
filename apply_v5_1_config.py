from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"

CONFIG = {
    "horizons_days": [30, 90, 180],
    "models": {
        "maximum_features": 24,
        "minimum_coverage": 0.65,
        "training_fraction": 0.75,
        "minimum_total_rows": 365,
        "minimum_training_rows": 240,
        "minimum_testing_rows": 60,
        "random_state": 510,
    },
    "allocation": {
        "base_cash_weight": 0.12,
        "minimum_cash_weight": 0.03,
        "maximum_cash_weight": 0.45,
        "risk_off_cash_slope": 0.10,
        "maximum_asset_weight": 0.40,
    },
    "portfolio": {
        "rebalance_days": 30,
        "transaction_cost_bps": 15,
    },
    "walk_forward": {
        "training_months": 24,
        "testing_months": 6,
        "step_months": 6,
    },
    "promotion": {
        "minimum_excess_return_pct": 0,
        "minimum_information_ratio": 0,
        "maximum_drawdown_floor_pct": -65,
    },
}

def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(f"Missing settings: {SETTINGS}")
    backup = SETTINGS.with_name("settings_before_v5_1.yaml")
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")
    settings = yaml.safe_load(SETTINGS.read_text(encoding="utf-8"))
    settings["module22"] = CONFIG
    if "platform" in settings:
        settings["platform"]["version"] = "5.1.0"
    SETTINGS.write_text(
        yaml.safe_dump(settings, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print("v5.1 configuration applied.")

if __name__ == "__main__":
    main()
