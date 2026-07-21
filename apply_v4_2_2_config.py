from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "config" / "settings.yaml"

MODULE19_CONFIG = {
    "horizons_days": [30, 90, 180],
    "validation": {
        "minimum_observations": 120,
    },
    "rolling": {
        "training_months": 18,
        "testing_months": 6,
        "step_months": 6,
        "minimum_training_observations": 180,
        "minimum_testing_observations": 45,
    },
    "permutation": {
        "training_fraction": 0.75,
        "minimum_training_rows": 180,
        "minimum_testing_rows": 45,
        "n_estimators": 250,
        "n_repeats": 8,
        "min_samples_leaf": 12,
        "random_state": 422,
    },
    "promotion": {
        "minimum_history_days": 365,
        "minimum_active_window_coverage_pct": 80,
        "minimum_rolling_windows": 3,
        "minimum_window_absolute_spearman": 0.05,
        "minimum_regime_absolute_spearman": 0.10,
        "minimum_sign_consistency_pct": 55,
        "minimum_stable_regimes": 2,
        "target_history_days": 1095,
        "target_absolute_spearman": 0.25,
        "target_positive_windows": 5,
        "target_stable_regimes": 3,
        "target_permutation_importance": 0.05,
        "watchlist_score": 50,
        "promoted_shadow_score": 68,
    },
}

def main():
    if not SETTINGS_PATH.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS_PATH}"
        )

    backup = SETTINGS_PATH.with_name(
        "settings_before_v4_2_2.yaml"
    )
    if not backup.exists():
        shutil.copy2(
            SETTINGS_PATH, backup
        )
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS_PATH.read_text(
            encoding="utf-8"
        )
    )
    settings["module19"] = MODULE19_CONFIG
    if "platform" in settings:
        settings["platform"]["version"] = "4.2.2"

    SETTINGS_PATH.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    print("v4.2.2 configuration applied.")

if __name__ == "__main__":
    main()
