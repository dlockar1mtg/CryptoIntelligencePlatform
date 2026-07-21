from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "config" / "settings.yaml"

MODULE21_CONFIG = {
    "horizons_days": [30, 90, 180],
    "governance": {
        "permitted_statuses": ["PROMOTED_SHADOW"],
    },
    "signals": {
        "zscore_window_days": 365,
        "minimum_zscore_history": 120,
    },
    "probabilities": {
        "training_fraction": 0.75,
        "minimum_total_rows": 365,
        "minimum_training_rows": 240,
        "minimum_testing_rows": 60,
        "max_iterations": 250,
        "learning_rate": 0.04,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 20,
        "l2_regularization": 1.0,
        "random_state": 500,
        "minimum_acceptable_auc": 0.55,
        "maximum_acceptable_brier": 0.27,
    },
    "decision": {
        "governed_signal_weight": 0.45,
        "regime_weight": 0.25,
        "probability_weight": 0.20,
        "risk_weight": 0.35,
        "maximum_rationales": 8,
        "stance_thresholds": {
            "strong_buy": 1.00,
            "buy": 0.35,
            "hold": -0.20,
            "reduce": -0.80,
        },
    },
    "allocation": {
        "minimum_btc_weight": 0.20,
        "neutral_btc_weight": 0.70,
        "maximum_btc_weight": 1.00,
        "action_score_slope": 0.15,
        "weak_model_multiplier": 0.50,
    },
    "shadow": {
        "rebalance_days": 30,
        "transaction_cost_bps": 15,
        "minimum_excess_return_pct": 0,
        "minimum_information_ratio": 0,
        "maximum_drawdown_floor_pct": -65,
    },
}

def main():
    if not SETTINGS_PATH.exists():
        raise FileNotFoundError(f"Missing settings: {SETTINGS_PATH}")

    backup = SETTINGS_PATH.with_name("settings_before_v5_0.yaml")
    if not backup.exists():
        shutil.copy2(SETTINGS_PATH, backup)
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS_PATH.read_text(encoding="utf-8")
    )
    settings["module21"] = MODULE21_CONFIG
    if "platform" in settings:
        settings["platform"]["version"] = "5.0.0"

    SETTINGS_PATH.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print("v5.0 configuration applied.")

if __name__ == "__main__":
    main()
